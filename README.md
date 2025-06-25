
## Dependencies

- Follow gRPC C++ installation instructions, install into relative dir `.local`
    - most recent (as of June 24, 2025) protobuf version is == 6031000 == 31.0 (https://github.com/grpc/grpc/releases/tag/v1.73.0).
    - may run into version issues if multiple versions of `protobuf` installed
- homebrew:

```shell
brew install cmake boost
```

## Quick start
**build:**
```shell
mkdir build && cd build
cmake ..
make
```

**server:**
```shell
cd build
./telemetry_server
```

**client:**
```shell
cd build
./telemetry_client
```



## Versioning
- I had some issues with a globally installed `protobuf` version via homebrew. It conflicted with my locally installed `protobuf` version. It was a dependency of my `osrf/simulation/gz-harmonic` installation :/. I ended up uninstalling via brew, and only using the locally installed `.local` version.


## Future improvements
- [ ] Make enums for units
- [ ] Separate enums for subsystems?