
## What is this??
A simulated telemetry pipeline (`server --> processing node --> database and backend --> frontend`).

- C++ multithreaded server generating simulated data
- Sent via gRPC to a Python client that runs coroutines in order to:
    - batch insert the data into a Postgres database
    - send the data to a FastAPI endpoint on a dashboard backend service
- Dashboard backend service with FastAPI endpoints is running on a uvicorn server, and it broadcasts new data to all websocket clients (just one for now...)
- Client is Next.js (with Redux) frontend


## Tech stack
- gRPC
- postgres (psycopg (3))
- FastAPI
- uvicorn
- React (Next.js)
- Redux


## Dependencies

- Note this is on macOS, i9, Ventura 13.5.2
- Follow gRPC C++ installation instructions, install into relative dir `.local`
    - most recent (as of June 24, 2025) protobuf version is == 6031000 == 31.0 (https://github.com/grpc/grpc/releases/tag/v1.73.0).
    - may run into version issues if multiple versions of `protobuf` installed
- Follow Redis installation instructions
    - https://redis.io/docs/latest/operate/oss_and_stack/install/install-stack/homebrew/

- more things:

```shell
brew install cmake boost postgresql

python3 -m venv .venv
source .venv/bin/activate

pip install wheel grcpio grpcio-tools
pip install "psycopg[binary]"
pip install "fastapi[standard]" uvicorn
pip install redis

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

**redis**
```shell
redis-server /usr/local/etc/redis.conf
```


## Versioning
- I had some issues with a globally installed `protobuf` version via homebrew. It conflicted with my locally installed `protobuf` version. It was a dependency of my `osrf/simulation/gz-harmonic` installation :/. I ended up uninstalling via brew, and only using the locally installed `.local` version.


## other notes
- `boost` is just for getting iso8601 time


## TODO:
- **< FEATURE / __ >:** *Redis queue buffer to reduce backpressure from gRPC server-->client*
- **< FEATURE / __ >:** *Connect to more interesting data stream...?*
	- Connect to https://celestrak.org/
	- [open apis](https://mixedanalytics.com/blog/list-actually-free-open-no-auth-needed-apis/)
	- I'll load the satellites + run "telemetry" for like 5 of them?
- **< FEATURE / __ >:** *a `client.py` graceful shutdown for the `asyncio` coroutines*
	- --> do this later :/
- **< FEATURE / x >:** *add [[SQLAlchemy]]*
	- --> it adds some slight overhead
	- it's nice for mapping to Python classes and [[ORM (Object Relational Mapping)]],
	- but I'm not doing anything complex, so leave this out
- **< TODO / __ >:** *Bottleneck analysis*
	- `client.py`: [[cProfile]], `yappi` (better for async?), or more [[Python timing decorators]]
	- use `prometheus_client` for various metrics of db and queue sizes
	- tune the batching intervals and sizes based on this analysis
	- measure throughput:
		- rows per sec
	- track `gRPC` call latency
	- cProfile the time spent on psycopg2 'execute'
	- for 10,000 rows of data
	- for regular INSERTs VS COPYs
- **< TODO / __ >:** *Postgres analysis*
	- `EXPLAIN ANALYZE`, `EXPLAIN BUFFERS` for insertion queries? (but I'm using `COPY` now, so it's not supported)
	- check for locks, contention, index maintenance overhead, [[WAL (Write-Ahead Logging)]] pressure
- **< TODO / __ >:** *Remove the postgres view*
	- [[PostgreSQL Views]] was made automatically in `telem.sql`
- **< FEATURE / __ >:** *Kafka or Redis pub/sub channel for client --> backend for better scaling, instead of POSTing*
- **< TODO / __ >:** *Postgres analysis*
- **< FEATURE / __ >:** *add [[dotenv]] for the db connection*
- **< FEATURE / __ >:** *clean logging of stuff*
- **< FEATURE / __ >:** *Dockerize + Docker compose all services*
- **< FEATURE / x >:** *SQL Alchemy ORM*
- Smaller things:
	- [ ] Requirements.txt instead of whatever that is
	- [ ] Need another Redux slice for actual `isStreaming` (websocket state), and change current toggle to `toggleOn` or something
	- [ ] Check this out: https://github.com/encode/broadcaster
	- [ ] Better organize python gRPC files...
	- [ ] Make enums for units
	- [ ] Separate enums for subsystems?