#include <iostream>
#include <thread>
#include <chrono>
#include <atomic>
#include <cstdlib>
#include "utils.h"

std::atomic<bool> running{true};

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



// struct Temp_Schema {
//     // ISO 8601 UTC
//     std::string timestamp = get_iso8601_timestamp();
//     std::string sensor_id = "UNKNOWN_TEMP_SENSOR";
    
//     System subsystem = System::engine;
    
//     float temperature = 0.0f;
//     std::string unit = "celsius";
    
//     std::uint8_t status_bitmask = 0;
//     std::uint8_t sensor_health = 0;

//     std::int32_t sequence_number = 0;
// };

// struct Pressure_Schema {
//     // ISO 8601 UTC
//     std::string timestamp;
//     std::string sensor_id;
    
//     System subsystem;
    
//     float pressure;
//     std::string unit;
    
//     bool leak_detected;
// };

// struct Velocity_Schema {
//     // ISO 8601 UTC
//     std::string timestamp;
//     std::string sensor_id;

//     System subsystem;
//     float velocity_x;
//     float velocity_y;
//     float velocity_z;

//     std::string unit;

//     float vibration_mag;

    
// };



void temp_sensor_worker(int interval_ms, std::string sensor_id, System subsystem, std::string unit) {
    // default
    Temp_Schema temp_data;
    temp_data.sensor_id = sensor_id;
    temp_data.subsystem = subsystem;
    temp_data.unit = unit;

    while (running.load()) {
        std::this_thread::sleep_for(std::chrono::milliseconds(interval_ms));

        
        temp_data.timestamp = get_iso8601_timestamp();
        temp_data.temperature = temp_data.temperature + get_randf_in_range(-10, 10);
        if (temp_data.temperature >= -10.0 && temp_data.temperature <= 65.0) {
            // ok
            temp_data.status_bitmask = 0;
        } else if (temp_data.temperature >= -20.0 && temp_data.temperature <= 75.0) {
            // warning
            temp_data.status_bitmask = 1;
        } else if (temp_data.temperature >= -30.0 && temp_data.temperature <= 85.0) {
            // critical
            temp_data.status_bitmask = 2;
        } else {
            // offline
            temp_data.status_bitmask = 4;
        }
        
        temp_data.sequence_number = temp_data.sequence_number + 1;
        
        // TODO: send it off via gRPC
        std::cout << "Temp data being sent: " << temp_data.timestamp << " : " << temp_data.temperature << "!\n";


    }
}


int main() {
    // start threads of diff sensors
    std::thread temp_sensor(temp_sensor_worker, 600, "TEMP_ENG_001", System::engine, "celsius");

    std::cout << "Type 'q' + ENTER or CTRL+C to exit.\n";

    while (running.load()) {
        // stdin is blocking by default
        char input;
        if (std::cin >> input) {
            if (input == 'q') {
                running.store(false);
                break;
            }
        }
    }

    temp_sensor.join();

    return 0;

}