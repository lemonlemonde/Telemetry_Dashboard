
## What is this??
A simulated telemetry pipeline (`server --> processing node --> database and backend --> frontend`).
Learning project with simulated data, so no use case yet...!

- C++ multithreaded server generating simulated data
- Sent via gRPC to a Python client that runs coroutines in order to:
    - batch insert the data into a Postgres database
    - send the data to a FastAPI endpoint on a dashboard backend service
- Dashboard backend service with FastAPI endpoints is running on a uvicorn server, and it broadcasts new data to all websocket clients (just one for now...)
- Client is Next.js (with Redux) frontend


## Tech stack
- gRPC
- Redis
- postgres (psycopg (3))
- FastAPI
- uvicorn
- React (Next.js)
- Redux
- Prometheus


## Dependencies

- Note this is on macOS, i9, Ventura 13.5.2
- Follow gRPC C++ installation instructions, install into relative dir `.local`
    - most recent (as of June 24, 2025) protobuf version is == 6031000 == 31.0 (https://github.com/grpc/grpc/releases/tag/v1.73.0).
    - may run into version issues if multiple versions of `protobuf` installed
- Follow Redis installation instructions
    - https://redis.io/docs/latest/operate/oss_and_stack/install/install-stack/homebrew/
- Follow Prometheus installation instructions
	- https://prometheus.io/docs/introduction/first_steps/
- more things:

```shell
brew install cmake boost postgresql

python3 -m venv .venv
source .venv/bin/activate

pip install wheel grcpio grpcio-tools
pip install "psycopg[binary]"
pip install "fastapi[standard]" uvicorn
pip install redis
pip install prometheus-client

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
	# click 'start streaming'
```

**redis**
```shell
redis-server /usr/local/etc/redis.conf

# if too much backlog in redis queue, just delete:
redis-cli
# check size
LLEN queue:telemetry
# del key
DEL queue:telemetry
```

**client (python):**
```shell
source .venv/bin/activate
# in root dir
python -m grpc_tools.protoc --proto_path=. --python_out=. --grpc_python_out=. telemetry.proto
python client.py

# if you want to use SnakeViz, etc.
python -m cProfile -o p_output.prof client.py

# after process ends, you can view output with:
snakeviz p_output.prof
```

**for deprecated cpp client:**
- need to uncomment the client.cpp executable in `CMakeLists.txt`
```shell
cd build
./telemetry_client
```

**Prometheus**
- add this extra config to the `prometheus.yml` file
```yml
scrape_configs:
  - job_name: "telemetry_dashboard"
    static_configs:
      - targets: ["localhost:8001"]
        labels:
          app: "prometheus"
```
```shell
# wherever you installed prometheus
cd ~/prometheus-*
./prometheus --config.file=prometheus.yml
# go to http://localhost:9090 on browser
# to directly see the queries:
	# http://localhost:9090/query?g0.expr=&g0.show_tree=0&g0.tab=graph&g0.range_input=1h&g0.res_type=auto&g0.res_density=medium&g0.display_mode=lines&g0.show_exemplars=0&g1.expr=histogram_quantile%280.95%2C+rate%28db_insertion_seconds_bucket%5B1m%5D%29%29&g1.show_tree=0&g1.tab=graph&g1.range_input=5m&g1.res_type=auto&g1.res_density=medium&g1.display_mode=lines&g1.show_exemplars=0&g2.expr=histogram_quantile%280.95%2C+rate%28latency_to_db_insert_bucket%5B1m%5D%29%29&g2.show_tree=0&g2.tab=table&g2.range_input=1h&g2.res_type=auto&g2.res_density=medium&g2.display_mode=lines&g2.show_exemplars=0&g3.expr=histogram_quantile%280.95%2C+rate%28data_dictionarize_seconds_bucket%5B1m%5D%29%29&g3.show_tree=0&g3.tab=table&g3.range_input=1h&g3.res_type=auto&g3.res_density=medium&g3.display_mode=lines&g3.show_exemplars=0&g4.expr=redis_queue_len&g4.show_tree=0&g4.tab=table&g4.range_input=1h&g4.res_type=auto&g4.res_density=medium&g4.display_mode=lines&g4.show_exemplars=0&g5.expr=histogram_quantile%280.95%2C+rate%28latency_end_to_end_bucket%5B1m%5D%29%29&g5.show_tree=0&g5.tab=table&g5.range_input=1h&g5.res_type=auto&g5.res_density=medium&g5.display_mode=lines&g5.show_exemplars=0
```
- some queries of interest:
	- `histogram_quantile(0.95, rate(db_insertion_seconds_bucket[1m]))`
	- `histogram_quantile(0.95, rate(latency_to_db_insert_bucket[1m]))`
	- `histogram_quantile(0.95, rate(data_dictionarize_seconds_bucket[1m]))`
	- `redis_queue_len`
	- `histogram_quantile(0.95, rate(latency_end_to_end_bucket[1m]))`


**Clean up**
```shell
brew services stop postgresql
redis-cli shutdown
```


## Versioning
- I had some issues with a globally installed `protobuf` version via homebrew. It conflicted with my locally installed `protobuf` version. It was a dependency of my `osrf/simulation/gz-harmonic` installation :/. I ended up uninstalling via brew, and only using the locally installed `.local` version.


## other notes
- `boost` is just for getting iso8601 time


## TODO:
- [x] **< FEATURE >:** *Redis queue buffer to reduce backpressure from gRPC server-->client*
- [ ] **< BUG >:** use an asynchronous version of `requests.post` in `run_redis_reader()` for POSTing to `backend.py`!!!
- [ ] **< BUG >:** `server.cpp`'s queue is causing the most latency!!
- [ ] **< BUG >:** `client.py`'s `dictionarize`'s `MessageToDict()` is taking a lot of time!
	- I already enforced the schema
	- so just read the data directly!!!
- [ ] **< TODO >:** *Bottleneck analysis*
	- `client.py`: [[cProfile]], `yappi` (better for async?), or more [[Python timing decorators]]
	- use `prometheus_client` for various metrics of db and queue sizes
	- tune the batching intervals and sizes based on this analysis
	- measure throughput:
		- rows per sec
	- track `gRPC` call latency
	- cProfile the time spent on psycopg2 'execute'
	- for 10,000 rows of data
	- for regular INSERTs VS COPYs
- [ ] ~~**< TODO >:** *Postgres analysis~~*
	- `EXPLAIN ANALYZE`, `EXPLAIN BUFFERS` for insertion queries? (mm but I'm using `COPY` now, so idk)
	- check for locks, contention, index maintenance overhead, [[WAL (Write-Ahead Logging)]] pressure
- [ ] **< FEATURE >:** *connection retry if C++ server disconnects with* `client.py`
- [ ] **< FEATURE >:** *Kafka or Redis pub/sub channel for client --> backend for better scaling, instead of POSTing*
- [ ] **< FEATURE >:** *Connect to more interesting data stream...?*
	- Connect to https://celestrak.org/
	- [open apis](https://mixedanalytics.com/blog/list-actually-free-open-no-auth-needed-apis/)
	- I'll load the satellites + run "telemetry" for like 5 of them?
- [ ] **< FEATURE >:** *a `client.py` graceful shutdown for the `asyncio` coroutines*
	- --> do this later :/
- [ ] ~~**< FEATURE >:** *add [[SQLAlchemy]]*~~
	- --> it adds some slight overhead
	- it's nice for mapping to Python classes and [[ORM (Object Relational Mapping)]],
	- but I'm not doing anything complex, so leave this out
- [x] **< TODO >:** *Remove the postgres view*
	- [[PostgreSQL Views]] was made automatically in `telem.sql`
- [ ] **< FEATURE >:** *add [[dotenv]] for the db connection*
- [ ] **< FEATURE >:** *clean logging of stuff*
- [ ] **< FEATURE >:** *Dockerize + Docker compose all services*
- [ ] **< FEATURE >:** *SQL Alchemy ORM*
- **< TODO >:** Smaller things:
	- [ ] Requirements.txt instead of whatever that is
	- [ ] Need another Redux slice for actual `isStreaming` (websocket state), and change current toggle to `toggleOn` or something
	- [ ] Check this out: https://github.com/encode/broadcaster
	- [ ] Better organize python gRPC files...
	- [ ] Make enums for units
	- [ ] Separate enums for subsystems?
- [ ] **< FEATURE >:** should I have two batch lists in `client.py`?
	- [ ] while pushing batched data to db
	- [ ] the grpc stream is unable to take in any more data
	- [ ] b/c it's waiting to get the lock
	- [ ] --> I should make a copy of the data??? (may or may not be a good idea, depnding on size of batch...)
- [ ] **< FEATURE >:** add exponential backoff via `redis-py`
- [ ] **< TODO >:** can have multiple workers in `client.py` for `run_redis_reader`, based on telemetry type!
- [ ] **< TODO >:** compare metrics of how batching to db helps in `client.py`
- [x] **< FEATURE >:** add [[Prometheus]]
- [ ] **< FEATURE >:** add [[Grafana]] on top of [[Prometheus]]
