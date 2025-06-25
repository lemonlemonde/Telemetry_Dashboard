cmake_minimum_required(VERSION 3.16)
project(PersonGrpcExample)

set(CMAKE_CXX_STANDARD 17)

# homebrew installed version == 5029003 == 29.3
# the locally installed version (in ./.local) == 6031000 == 31.0
set(CMAKE_PREFIX_PATH "${CMAKE_CURRENT_SOURCE_DIR}/.local")

set(CMAKE_FIND_ROOT_PATH "${CMAKE_CURRENT_SOURCE_DIR}/.local")
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)

# Find packages
find_package(Protobuf REQUIRED)
find_package(gRPC REQUIRED)

message(STATUS "Protobuf version: ${Protobuf_VERSION}")
message(STATUS "Protobuf library: ${Protobuf_LIBRARIES}")
message(STATUS "Protobuf include: ${Protobuf_INCLUDE_DIRS}")

# Generate protobuf and gRPC files
set(PROTO_FILES telemetry.proto)
set(PROTO_SRCS)
set(PROTO_HDRS)

foreach(proto_file ${PROTO_FILES})
    get_filename_component(proto_name ${proto_file} NAME_WE)
    set(proto_srcs "${CMAKE_CURRENT_BINARY_DIR}/${proto_name}.pb.cc")
    set(proto_hdrs "${CMAKE_CURRENT_BINARY_DIR}/${proto_name}.pb.h")
    set(grpc_srcs "${CMAKE_CURRENT_BINARY_DIR}/${proto_name}.grpc.pb.cc")
    set(grpc_hdrs "${CMAKE_CURRENT_BINARY_DIR}/${proto_name}.grpc.pb.h")
    
    add_custom_command(
        OUTPUT "${proto_srcs}" "${proto_hdrs}" "${grpc_srcs}" "${grpc_hdrs}"
        COMMAND ${CMAKE_PREFIX_PATH}/bin/protoc
        ARGS --grpc_out "${CMAKE_CURRENT_BINARY_DIR}"
             --cpp_out "${CMAKE_CURRENT_BINARY_DIR}"
             -I "${CMAKE_CURRENT_SOURCE_DIR}"
             --plugin=protoc-gen-grpc="${CMAKE_PREFIX_PATH}/bin/grpc_cpp_plugin"
             "${CMAKE_CURRENT_SOURCE_DIR}/${proto_file}"
        DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/${proto_file}")
    
    list(APPEND PROTO_SRCS ${proto_srcs} ${grpc_srcs})
    list(APPEND PROTO_HDRS ${proto_hdrs} ${grpc_hdrs})
endforeach()

# Server executable
add_executable(telemetry_server 
    server.cpp
    ${PROTO_SRCS}
)

target_link_libraries(telemetry_server
    gRPC::grpc++
    protobuf::libprotobuf
)

target_include_directories(telemetry_server PRIVATE 
    ${CMAKE_CURRENT_BINARY_DIR}
)

# Client executable
add_executable(telemetry_client 
    client.cpp
    ${PROTO_SRCS}
)

target_link_libraries(telemetry_client
    gRPC::grpc++
    protobuf::libprotobuf
)

target_include_directories(telemetry_client PRIVATE 
    ${CMAKE_CURRENT_BINARY_DIR}
)