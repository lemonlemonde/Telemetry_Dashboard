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
std::vector<std::tuple<std::string, telemetry::TelemetryType, telemetry::System, std::string, std::uint64_t>> sensor_names = {
    // sensor_id, TelemetryType, System, unit, interval_ms
    std::make_tuple(
        "TEMP_ENG_001", 
        telemetry::TelemetryType::TEMPERATURE, 
        telemetry::System::ENGINE, 
        "celsius",
        300
    ),
    std::make_tuple(
        "TEMP_FUEL_001",
        telemetry::TelemetryType::TEMPERATURE,
        telemetry::System::FUEL_TANK,
        "celsius",
        300
    ),
    std::make_tuple("PRESS_ENG_001",
        telemetry::TelemetryType::PRESSURE,
        telemetry::System::ENGINE,
        "bar",
        450
    ),
    std::make_tuple("PRESS_FUEL_002",
        telemetry::TelemetryType::PRESSURE,
        telemetry::System::FUEL_TANK,
        "bar",
        350
    ),
    std::make_tuple("VELO_STAGE1_001",
        telemetry::TelemetryType::VELOCITY,
        telemetry::System::STAGE1,
        "m/s",
        350
    ),
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

    // Range: [-30°C to 85°C]
	// - fluctuations of about -10~10deg per interval_ms
	// - status bitmask
		// - `[-10, 65]` = OK
		// - `[-20, -10)` or `(65, 75]` = WARNING
		// - `[-30, 20)` or `(75, 85]` = CRITICAL
		// - `(-inf, -30)` or `(85, inf)` = OFFLINE

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
        
        std::cout << "Temperature data queued: [" << resp.timestamp() << "] TEMPERATURE - " << sensor_id << " - " << cur_temp << "˚C - " << resp.mutable_temperature()->status_bitmask() << "!\n";
    }
}
void press_sensor_worker(int interval_ms, std::string sensor_id, telemetry::System subsystem, std::string unit) {

    // starting vals for "bar" units
    float cur_press = 200.0f;
    uint32_t seq_num = 0;

    // Range: [100, 300]
        // fluctuations of -5~5 per interval_ms
        // status_bitmask:
            // OK = [180, 220]
            // WARNING = [140, 180) or (220, 260]
            // CRITICAL = [100, 140) or (260, 300]
            // OFFLINE = (-inf, 100) or (300, inf)

    // TODO: use leak_detected... 
        // if consistently falling?

    while (running.load()) {
        std::this_thread::sleep_for(std::chrono::milliseconds(interval_ms));

        // telem response container
        telemetry::TelemetryResponse resp;
        resp.set_timestamp(get_iso8601_timestamp());
        resp.set_type(telemetry::TelemetryType::PRESSURE);

        // the "inner" message "class"
        auto* pressure_data = resp.mutable_pressure();
        
        pressure_data->set_sensor_id(sensor_id);
        pressure_data->set_subsystem(subsystem);
        pressure_data->set_unit(unit);
        
        // get new pressure
        cur_press += get_randf_in_range(-5.0f, 5.0f);
        pressure_data->set_pressure(cur_press);
        uint32_t status_bitmask = 0;
        if (180.0f <= cur_press && cur_press <= 220.0f) {
            // ok
            status_bitmask = 0;
        } else if (140.0f <= cur_press && cur_press <= 260.0f) {
            // warning
            status_bitmask = 1;
        } else if (100.0f <= cur_press && cur_press <= 300.0f) {
            // critical
            status_bitmask = 2;
        } else {
            // offline
            status_bitmask = 4;
        }

        pressure_data->set_status_bitmask(status_bitmask);
        seq_num += 1;
        pressure_data->set_sequence_number(seq_num);
        
        // send it off to TelemetryQueue, and it'll be sent via gRPC
        telem_q.push(resp);

        
        std::cout << "Pressure data queued: [" << resp.timestamp() << "] PRESSURE - " << sensor_id << " - " << cur_press << " " << unit << " - " << pressure_data->status_bitmask() << "!\n";
    }
}
void velo_sensor_worker(int interval_ms, std::string sensor_id, telemetry::System subsystem, std::string unit) {
    // starting vals
    float cur_velo_x = 8000.0f;
    float cur_velo_y = 8000.0f;
    float cur_velo_z = 8000.0f;
    uint32_t seq_num = 0;

    // TODO: use vibration_magnitude?

    // Range: [-15000, 15000]
        // fluctuations of -40~40 per interval_ms
        // status_bitmask:
            // OK (0-12,000): Normal cruise/operational velocity
            // WARNING (12,000-14,000): High velocity, monitor closely
            // CRITICAL (14,000-15,000): At design limits, immediate attention needed
            // OFFLINE (>15,000): Beyond safe limits, system fault

    while (running.load()) {
        std::this_thread::sleep_for(std::chrono::milliseconds(interval_ms));
        
        // telem response container
        telemetry::TelemetryResponse resp;
        resp.set_timestamp(get_iso8601_timestamp());
        resp.set_type(telemetry::TelemetryType::VELOCITY);
        
        // the "inner" message "class"
        auto* velocity_data = resp.mutable_velocity();
        
        velocity_data->set_sensor_id(sensor_id);
        velocity_data->set_subsystem(subsystem);
        velocity_data->set_unit(unit);
        
        // get new velocity mag
        cur_velo_x += get_randf_in_range(-5.0f, 5.0f);
        cur_velo_y += get_randf_in_range(-5.0f, 5.0f);
        cur_velo_z += get_randf_in_range(-5.0f, 5.0f);
        velocity_data->set_velocity_x(cur_velo_x);
        velocity_data->set_velocity_y(cur_velo_y);
        velocity_data->set_velocity_z(cur_velo_z);

        float velocity_magnitude = sqrt(cur_velo_x*cur_velo_x + cur_velo_y*cur_velo_y + cur_velo_z*cur_velo_z);
        uint32_t status_bitmask = 0;
        if (velocity_magnitude <= 12000.0f) {
            // ok
            status_bitmask = 0;
        } else if (velocity_magnitude <= 14000.0f) {
            // warning
            status_bitmask = 1;
        } else if (velocity_magnitude <= 15000.0f) {
            // critical
            status_bitmask = 2;
        } else {
            // offline
            status_bitmask = 4;
        }

        velocity_data->set_status_bitmask(status_bitmask);
        seq_num += 1;
        velocity_data->set_sequence_number(seq_num);
        
        // send it off to TelemetryQueue, and it'll be sent via gRPC
        telem_q.push(resp);
        
        std::cout << "Velocity data queued: [" << resp.timestamp() << "] VELOCITY - " << sensor_id << " - (" << cur_velo_x << ", " << cur_velo_y << ", " << cur_velo_z << ") " << unit << "!\n";
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
        // std::string sensor_id, telemetry::TelemetryType, telemetry::System subsystem, std::string unit, std::uint64_t interval_ms
        std::string sensor_id = std::get<0>(sensor_names[i]);
        telemetry::TelemetryType telem_type = std::get<1>(sensor_names[i]);
        telemetry::System subsystem = std::get<2>(sensor_names[i]);
        std::string unit = std::get<3>(sensor_names[i]);
        std::uint64_t interval_ms = std::get<4>(sensor_names[i]);

        // TODO: change function for velocity, pressure
        if (telem_type == telemetry::TelemetryType::TEMPERATURE) {
            sensor_threads.emplace_back(temp_sensor_worker, interval_ms, sensor_id, subsystem, unit);
        } else if (telem_type == telemetry::TelemetryType::PRESSURE) {
            sensor_threads.emplace_back(press_sensor_worker, interval_ms, sensor_id, subsystem, unit);
        } else if (telem_type == telemetry::TelemetryType::VELOCITY) { 
            sensor_threads.emplace_back(velo_sensor_worker, interval_ms, sensor_id, subsystem, unit);
        }

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