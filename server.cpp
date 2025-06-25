#include <iostream>
#include <thread>
#include <queue>
#include <chrono>
#include <atomic>
#include <cstdlib>
#include <signal.h>
#include <csignal>

#include "utils.h"

// grpc
#include <grpcpp/grpcpp.h>
#include "telemetry.pb.h"
#include "telemetry.grpc.pb.h"

using grpc::Server;
using grpc::ServerBuilder;
using grpc::ServerContext;
using grpc::ServerWriter;
using grpc::Status;

// for sensor threads
std::atomic<bool> running{true};

// for CTRL+C, primarily
void signalHandler(int signum) {
    std::cout << "\nReceived signal " << signum << ". Shutting down gracefully..." << std::endl;
    running.store(false);
}

class TelemetryQueue {
    // THREAD SAFE implementation of queue
    private:
    std::queue<telemetry::TelemetryResponse> queue_;
    // lock for queue
    std::mutex mutex_;
    // cv for dinner bell of popping from queue
    std::condition_variable cv_;
    
    public:
    void push(const telemetry::TelemetryResponse& item) {
        // get lock before pushing
        std::lock_guard<std::mutex> lock(mutex_);
        queue_.push(item);
        cv_.notify_one();
        // lock goes out of scope (released)
    }
    
    bool try_pop(telemetry::TelemetryResponse& item, std::chrono::milliseconds timeout = std::chrono::milliseconds(100)) {
        // acquire lock
        std::unique_lock<std::mutex> lock(mutex_);
        // if queue not empty, no need to wait for dinner bell!
        // go ahead and consume
        // otherwise, cv will release lock, and wait for dinner bell, or timeout
        if (cv_.wait_for(lock, timeout, [this] {
            return !queue_.empty();
        })) {
            // fill up TelemetryResponse
            item = queue_.front();
            queue_.pop();
            return true;
        }
        
        return false;
    }
    
    size_t size() {
        std::lock_guard<std::mutex> lock(mutex_);
        return queue_.size();
    }
    
};

// global queue for gRPC streaming
TelemetryQueue telem_q;

// Sensor List
std::vector<std::tuple<std::string, telemetry::System, std::string>> sensor_names = {
    // (std::string sensor_id, telemetry::System subsystem, std::string unit)
    std::make_tuple("TEMP_ENG_001", telemetry::System::ENGINE, "celsius"),
};
// Sensor threads for cleanup (join())
std::vector<std::thread> sensor_threads = {};


float get_randf_in_range(float lower, float upper) {
    // https://stackoverflow.com/questions/686353/random-float-number-generation
    float dividend = static_cast <float>(rand());
    float divisor = static_cast <float>(RAND_MAX/(upper - lower));
    float random_float = lower + (dividend / divisor);

    return random_float;
}

std::string get_iso8601_timestamp() {
    auto now = boost::posix_time::microsec_clock::universal_time();
    return boost::posix_time::to_iso_extended_string(now) + "Z";
}





void temp_sensor_worker(int interval_ms, std::string sensor_id, telemetry::System subsystem, std::string unit) {

    // starting vals
    float cur_temp = 30.0f;
    uint32_t seq_num = 0;

    while (running.load()) {
        std::this_thread::sleep_for(std::chrono::milliseconds(interval_ms));

        // telem response container
        telemetry::TelemetryResponse resp;
        resp.set_timestamp(get_iso8601_timestamp());
        resp.set_type(telemetry::TelemetryType::TEMPERATURE);

        // the "inner" message "class"
        auto* temperature_data = resp.mutable_temperature();
        
        temperature_data->set_sensor_id(sensor_id);
        temperature_data->set_subsystem(subsystem);
        temperature_data->set_unit(unit);
        
        // get new temp
        cur_temp += get_randf_in_range(-10.0f, 10.0f);
        temperature_data->set_temperature(cur_temp);
        uint32_t status_bitmask = 0;
        if (cur_temp >= -10.0 && cur_temp <= 65.0) {
            // ok
            status_bitmask = 0;
        } else if (cur_temp >= -20.0 && cur_temp <= 75.0) {
            // warning
            status_bitmask = 1;
        } else if (cur_temp >= -30.0 && cur_temp <= 85.0) {
            // critical
            status_bitmask = 2;
        } else {
            // offline
            status_bitmask = 4;
        }

        temperature_data->set_status_bitmask(status_bitmask);
        seq_num += 1;
        temperature_data->set_sequence_number(seq_num);
        
        // send it off to TelemetryQueue, and it'll be sent via gRPC
        telem_q.push(resp);
        
        std::cout << "Temperature data queued: [" << resp.timestamp() << "] TEMPERATURE - " << sensor_id << " - " << cur_temp << "˚C!\n";
    }
}

// implement the gRPC generated base class
class TelemetryServiceImpl final : public telemetry::TelemetryService::Service {
public:
    Status GetTelemetryStream(ServerContext* context, const telemetry::TelemetryRequest* request, ServerWriter<telemetry::TelemetryResponse>* writer) override {
        std::cout << "Client connected for telemetry stream!\n";

        // empty response
        telemetry::TelemetryResponse response;

        // while client connected + server not shut down
        while (!context->IsCancelled() && running.load()) {
            // keep filling response with data from queue
            if (telem_q.try_pop(response, std::chrono::milliseconds(500))) {
                if (!writer->Write(response)) {
                    std::cout << "Client disconnected :(\n";
                    break;
                }
            }
        }

        // check again why we're stopping
        if (context->IsCancelled()) {
            std::cout << "Client cancelled connection.\n";
        } else {
            std::cout << "Telemetry stream has been cancelled.\n";
        }

        return Status::OK;
    }
};

void start_grpc_server() {
    std::string server_address("0.0.0.0:50051");
    
    ServerBuilder builder;
    // require no authentication
    builder.AddListeningPort(server_address, grpc::InsecureServerCredentials());
    TelemetryServiceImpl telem_service;
    builder.RegisterService(&telem_service);
    
    std::unique_ptr<Server> server(builder.BuildAndStart());
    
    // check for server shutdown
    while (running.load()) {
        std::this_thread::sleep_for(std::chrono::milliseconds(2000));
    }
    
    server->Shutdown();
    std::cout << "gRPC server has shut down... bye! <3\n";
}


int main() {
    // handlers
    signal(SIGINT, signalHandler);
    signal(SIGTERM, signalHandler);


    // start gRPC server
    std::thread grpc_server_thread(start_grpc_server);


    // start threads of diff sensors
    for (int i = 0; i < sensor_names.size(); i++) {
        // (std::string sensor_id, telemetry::System subsystem, std::string unit)
        std::string sensor_id = std::get<0>(sensor_names[i]);
        telemetry::System subsystem = std::get<1>(sensor_names[i]);
        std::string unit = std::get<2>(sensor_names[i]);

        // TODO: change function for velocity, pressure
        sensor_threads.emplace_back(temp_sensor_worker, 600, sensor_id, subsystem, unit);
    }

    std::cout << "Started " << sensor_threads.size() << " sensor threads!!!\n";
    std::cout << "Type 'q'+ENTER or CTRL+C to exit.\n";

    // while (running.load()) {
    //     // stdin is blocking by default
    //     char input;
    //     if (std::cin >> input) {
    //         if (input == 'q') {
    //             running.store(false);
    //             break;
    //         }
    //     }
    // }

    // end all simulator threads
    for (int i = 0; i < sensor_threads.size(); i++) {
        if (sensor_threads[i].joinable()) {
            sensor_threads[i].join();
        }
    }

    // end grpc server
    if (grpc_server_thread.joinable()) {
        // block until thread done
        grpc_server_thread.join();
    }

    std::cout << "All threads stopped. Remaining queue size: " << telem_q.size() << std::endl;
    return 0;

}