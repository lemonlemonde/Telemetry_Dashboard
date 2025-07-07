
## Dependencies

- Follow gRPC C++ installation instructions, install into relative dir `.local`
    - most recent (as of June 24, 2025) protobuf version is == 6031000 == 31.0 (https://github.com/grpc/grpc/releases/tag/v1.73.0).
    - may run into version issues if multiple versions of `protobuf` installed
- more things:

```shell
brew install cmake boost postgresql

python3 -m venv .venv
source .venv/bin/activate

pip install wheel grcpio grpcio-tools
pip install "psycopg[binary]"
pip install "fastapi[standard]" uvicorn

npm install
```

## Quick start
**build:**
```shell
mkdir build && cd build
cmake ..
make
```

**postgresql:**
```shell
brew services start postgresql

# connect with cur user
psql postgres
# make db
postgres-# CREATE DATABASE IF NOT EXISTS telemetry;

# make everything else
psql -U mirujun -d telemetry -f telem.sql
```

**server:**
```shell
cd build
./telemetry_server
```

**client (python):**
```shell
source .venv/bin/activate
# in root dir
python -m grpc_tools.protoc --proto_path=. --python_out=. --grpc_python_out=. telemetry.proto
python client.py
```

**for deprecated cpp client:**
- need to uncomment the client.cpp executable in `CMakeLists.txt`
```shell
cd build
./telemetry_client
```

**dashboard backend:**
```shell
source .venv/bin/activate
# in root dir 
uvicorn backend:app --reload
```

**dashboard frontend:**
```shell
cd frontend/telemetry_dashboard
npm run dev
# go to http://localhost:3000 on browser
```

## Tech stack
- gRPC
- postgres (psycopg (3))
- FastAPI
- uvicorn
- React (Next.JS)
- Redux


## Versioning
- I had some issues with a globally installed `protobuf` version via homebrew. It conflicted with my locally installed `protobuf` version. It was a dependency of my `osrf/simulation/gz-harmonic` installation :/. I ended up uninstalling via brew, and only using the locally installed `.local` version.



## Future improvements
- [ ] Connect to https://celestrak.org/
- [ ] SQL Alchemy ORM
- [ ] Need another Redux slice for actual `isStreaming` (websocket state), and change current toggle to `toggleOn` or something
- [ ] Redis queue for backpressure
- [ ] Push to DB in batches. (We don't need streaming here)
- [ ] Check this out: https://github.com/encode/broadcaster
- [ ] Requirements.txt instead of whatever that is
- [ ] Better organize python gRPC files...
- [ ] Make enums for units
- [ ] Separate enums for subsystems?


## other notes
- `boost` is just for getting iso8601 time
