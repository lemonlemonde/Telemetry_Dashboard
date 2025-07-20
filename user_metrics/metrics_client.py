import typing
from typing import Union
import json
from pprint import pprint
import time
from datetime import datetime, timezone
from dateutil.parser import isoparse
import dateutil
from functools import wraps

import dateutil.utils
import requests
import asyncio
import aiohttp

import grpc
from google.protobuf.json_format import MessageToDict

# for protobuf bug
# https://github.com/grpc/grpc/issues/29459
import sys
import os
def add_to_python_path(new_path):
    existing_path = sys.path
    absolute_path = os.path.abspath(new_path)
    if absolute_path not in existing_path:
        sys.path.append(absolute_path)
    return sys.path

file_dir_path = os.path.dirname(os.path.realpath(__file__))
add_to_python_path(file_dir_path + "/proto")

from proto import metrics_pb2
from proto import metrics_pb2_grpc

import psycopg

from prometheus_client import start_http_server, Histogram, Gauge

# prometheus metrics
# TODO: tune the buckets..
DB_INSERT_TIME = Histogram('db_insertion_seconds', 'Time (seconds) spent on inserting into database.', buckets=[0.007, 0.008, 0.0085, 0.009, 0.0092, 0.0094, 0.0096, 0.0098, 0.01, 0.011, 0.012, 0.015, 0.02, 0.08, 0.1, 0.2, 0.3, 0.4, 0.5, 0.8, 1.0, 2.0, 4.0, 10.0])
    # mostly 0.0095
LATENCY_TO_DB_INSERT = Histogram('latency_to_db_insert', 'Time from data creation to db insertion.', buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 150, 200])
    # 4~6
DATA_DICTIONARIZE_TIME = Histogram('data_dictionarize_seconds', 'Time (seconds) spent turning raw data from gRPC into a dictionary.', buckets=[0.007, 0.008, 0.0085, 0.009, 0.0092, 0.0094, 0.0096, 0.0098, 0.01, 0.011, 0.012, 0.015, 0.02, 0.08, 0.1, 0.2])
    # mostly 0.0095
REDIS_QUEUE_LENGTH = Gauge('redis_queue_len', 'Length of Redis queue, indicating backpressure from gRPC server.')
    # 1 - 11 (at start)


DEBUG = False


async def process_data(telem_dict) -> dict:
    # TODO: some dummy processing for testing
    await asyncio.sleep(0.05)
    return telem_dict


class Metric_Data():
    def __init__(self, metric_type, aconn):
        self.metric_type = metric_type
        if self.metric_type not in ['kpm', 'pxm', 'cpm', 'title']:
            print(f"[ERROR] : `metric_type` malformatted. Must be one of : ['kpm', 'pxm', 'cpm', 'title']")
            return
        
        self.db_buffer_lock = asyncio.Lock()
        
        # in seconds
        self.BATCH_INTERVAL = 10
        self.MAX_BATCH_SIZE = 20

        self.db_buffer = []
        self.did_max_out = False
        
        # postgres async conn
        self.aconn = aconn
        
        # connect to python server asynchronously
        channel = grpc.aio.insecure_channel('localhost:50052')
        # get generated stub
        stub = metrics_pb2_grpc.MetricServiceStub(channel)
        
        if self.metric_type == 'kpm':
            self.stream = stub.GetKPMStream(metrics_pb2.MetricRequest())
        elif self.metric_type == 'cpm':
            self.stream = stub.GetCPMStream(metrics_pb2.MetricRequest())
        elif self.metric_type == 'pxm':
            self.stream = stub.GetMouseSpeedStream(metrics_pb2.MetricRequest())
        elif self.metric_type == 'title':
            self.stream = stub.GetMediaStream(metrics_pb2.MetricRequest())

    async def add_to_batch(self, timestamp: str, val: Union[float, str, int]):
        async with self.db_buffer_lock:
            self.db_buffer.append((timestamp, val))

    async def handle_metric_response(self, metric_response):
        timestamp = metric_response.timestamp
        if self.metric_type != metric_response.WhichOneof("data"):
            print(f"[ WARNING ] : `metric_response` and `self.metric_type` mismatch? Skipping...")
            return
        
        try:
            val = getattr(metric_response, self.metric_type)
        except Exception:
            print(f"[ WARNING ] : metric_response is malformatted? Contains unknown metric_type. Skipping...")
            return
        
        # add to db batch list
        await self.add_to_batch(timestamp, val)
        async with self.db_buffer_lock:
            async with self.aconn.cursor() as cur:
                if len(self.db_buffer) >= self.MAX_BATCH_SIZE:
                    self.did_max_out = True
                    await self.push_to_db(cur)
                    self.db_buffer.clear()
                        
        # /POST to dashboard backend
        metric_dict = {
            "timestamp": timestamp,
            "metric_type": self.metric_type,
            "val": val
        }
        async with aiohttp.ClientSession() as session:
           async with session.post('http://127.0.0.1:8000/metric_data', json=metric_dict) as response:
            data = await response.text()
            print(f"[{self.metric_type}] : Sent data: {val}, timestamp [{timestamp}]")
            print (data)
        
    async def run_grpc_stream(self):
        try:
            async for metric_response in self.stream:
                print(f"Received [{metric_response.timestamp}]")
                await self.handle_metric_response(metric_response)
                
        except grpc.RpcError as e:
            print(f"Oh no! gRPC error: {e}")
        # finally:
            # no need to use .close() when using `with`
            # channel.close()
        
    async def run_db_batching(self):
        print(f"[{self.metric_type}] [run_db_batching] : Starting!")
        async with self.aconn.cursor() as cur:
            try:
                while True:
                    async with self.db_buffer_lock:
                        self.did_max_out = False
                    print(f"[{self.metric_type}] [run_db_batching] : Going to sleep...")
                    await asyncio.sleep(self.BATCH_INTERVAL)
                    print(f"[{self.metric_type}] [run_db_batching] : Woke up!")
                    async with self.db_buffer_lock:
                        if not self.did_max_out:
                            await self.push_to_db(cur)
                            self.db_buffer.clear()
            except Exception as e:
                print(f"[ERROR] [{self.metric_type}] [run_db_batching] : {e}")
    
    @DB_INSERT_TIME.time()
    async def push_to_db(self, cur):
        # COPY insert via psycopg3
        print("------- [ I T  I S  T I M E ] -------")
        metric_headers = 'reading_timestamp,val'
        # 'timestamp' (str, ISO8601 with UTC timezone), 
        # 'val' (float)
        
        if not self.db_buffer:
            print("No rows to commit")
            print("------- [ I T  I S  D O N E ] -------")
            return
        
        print(f"Committing {len(self.db_buffer)} rows...")
        
        # table names: `metric_data_kpm`, etc.
        sql = f"COPY metric_data_{self.metric_type} ({metric_headers}) FROM STDIN;"
        async with cur.copy(sql) as copy:
            for record in self.db_buffer:
                await copy.write_row(record)
                
                # time for prometheus
                time_record = isoparse(record[0])
                time_now = datetime.now(timezone.utc)
                time_diff = time_now - time_record
                LATENCY_TO_DB_INSERT.observe(time_diff.total_seconds())
                
                
        await self.aconn.commit()
        print("------- [ I T  I S  D O N E ] -------")

async def main():
    
    
    
    # connect to db
    async with await psycopg.AsyncConnection.connect(
        dbname='dashboard',
        user='mirujun',
        password='',
        host='localhost'
    ) as aconn:
        kpm_data = Metric_Data('kpm', aconn)
        cpm_data = Metric_Data('cpm', aconn)
        pxm_data = Metric_Data('pxm', aconn)
        title_data = Metric_Data('title', aconn)
        
        await asyncio.gather(
            kpm_data.run_grpc_stream(),
            kpm_data.run_db_batching(),
            
            cpm_data.run_grpc_stream(),
            cpm_data.run_db_batching(),
            
            pxm_data.run_grpc_stream(),
            pxm_data.run_db_batching(),
            
            title_data.run_grpc_stream(),
            title_data.run_db_batching()
        )
    

if __name__ == "__main__":
    # start prometheus endpoint
    server, t = start_http_server(8003)
    
    asyncio.run(main())
    
    server.shutdown()
    t.join()