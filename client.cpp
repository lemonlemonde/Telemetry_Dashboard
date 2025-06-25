#include <iostream>
#include <thread>
#include <atomic>
#include <signal.h>
#include <csignal>

#include <grpcpp/grpcpp.h>
#include "telemetry.grpc.pb.h"
#include "telemetry.pb.h"

using grpc::Channel;
using grpc::ClientContext;
using grpc::ClientReader;
using grpc::Status;

std::atomic<bool> running{true};
std::atomic<ClientContext*> current_context{nullptr};

// for CTRL+C, primarily
void signalHandler(int signum) {
    std::cout << "\nReceived signal " << signum << ". Shutting down gracefully..." << std::endl;
    running.store(false);

    // cancel context, and not even `reader->Read()` can block
    ClientContext* ctx = current_context.load();
    if (ctx) {
        std::cout << "Trying to cancel context..." << std::endl;
        ctx->TryCancel();
        std::cout << "Best effort cancellation was made." << std::endl;
    }
}

// inherit from stub class generated via gRPC
class TelemetryClient {
public:
    TelemetryClient(std::shared_ptr<Channel> channel) : stub_(telemetry::TelemetryService::NewStub(channel)) {
        // nothing to construct
    }

    void GetTelemetryStream() {
        telemetry::TelemetryRequest req;
        telemetry::TelemetryResponse resp;

        ClientContext context;
        current_context.store(&context); // Store context for signal handler


        std::unique_ptr<ClientReader<telemetry::TelemetryResponse>> reader(
            stub_->GetTelemetryStream(&context, req)
        );
        while (reader->Read(&resp) && running.load()) {
            std::cout << "[" << resp.timestamp() << "]";
            switch (resp.type()) {
                case telemetry::TelemetryType::TEMPERATURE: {
                    telemetry::TemperatureData temperature_data = resp.temperature();
                    std::cout << " TEMPERATURE - " << temperature_data.sensor_id() << " - " << temperature_data.temperature() << std::endl;
                    break;
                }
                case telemetry::TelemetryType::PRESSURE: {
                    telemetry::PressureData pressure_data = resp.pressure();
                    std::cout << " PRESSURE - " << pressure_data.sensor_id() << " - " << pressure_data.pressure() << std::endl;
                    break;
                }
                case telemetry::TelemetryType::VELOCITY: {
                    telemetry::VelocityData velocity_data = resp.velocity();
                    std::cout << " VELOCITY - " << velocity_data.sensor_id() << " - (" << velocity_data.velocity_x() << ", " << velocity_data.velocity_y() << ", " << velocity_data.velocity_z() << ")" << std::endl;
                    break;
                }
            }
        }

        current_context.store(nullptr);
        context.TryCancel();


        // signal end
        Status status = reader->Finish();
        if (status.ok()) {
            std:: cout << "Telemetry stream ended safely" << std::endl;
        } else {
            std:: cout << "Telemetry stream ended: " << status.error_message() << std::endl;
        }
    }

private:
    std::unique_ptr<telemetry::TelemetryService::Stub> stub_;

};


int main() {
    // handlers
    signal(SIGINT, signalHandler);
    signal(SIGTERM, signalHandler);

    // connect without authentication
    auto channel = grpc::CreateChannel("localhost:50051", grpc::InsecureChannelCredentials());
    TelemetryClient client(channel);

    std::thread telem_stream_client_thread([&client]() {
        client.GetTelemetryStream();
    });

    std::cout << "Press CTRL+C to exit.\n";

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

    if (telem_stream_client_thread.joinable()){
        // block until thread done
        telem_stream_client_thread.join();
    }

    return 0;
}