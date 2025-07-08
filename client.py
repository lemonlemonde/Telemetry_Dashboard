import grpc
from google.protobuf.json_format import MessageToDict

import telemetry_pb2
import telemetry_pb2_grpc
import psycopg

import requests
import typing
import json
from pprint import pprint
import time
from functools import wraps

import asyncio



DEBUG = False

DB_ALL_COLS = [
    'reading_timestamp',
    'telemetry_type',
    'sensor_id',
    'subsystem',
    'sequence_number',
    'status_bitmask',
    
    'temperature',
    'temp_unit',
    
    'pressure',
    'pressure_unit',
    'leak_detected',
    
    'velocity_x',
    'velocity_y',
    'velocity_z',
    'velocity_unit',
    'vibration_magnitude'
]

# in seconds
BATCH_INTERVAL = 5
MAX_BATCH_SIZE = 1000
db_buffer = []
db_buffer_lock = asyncio.Lock()


def timing_decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        # the actual func we're wrapping
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        print(f"[TIMING] [{func.__name__}] : {end_time - start_time:.4f} seconds!")
        return result, (end_time - start_time)
    return wrapper

@timing_decorator
def process_data(telem_response) -> dict:
    def process_unknown_data():
        raise NotImplementedError(f"Data processing not implemented for telemetry type: {telem_response.type}")

    # pprint(f"RAW RESPONSE: {telem_response}")
    telem_dict = MessageToDict(telem_response, always_print_fields_with_no_presence=True)
    
    # pprint(f"GOT dictionary: {telem_dict}")
    # remap keys/headers from .proto to sql table
    db_data = {
        'reading_timestamp': telem_dict.get('timestamp'),
        'telemetry_type': None,
        'sensor_id': None,
        'subsystem': None,
        'sequence_number': None,
        'status_bitmask': None,
        # temp only
        'temperature': None,
        'temp_unit': None,
        # pressure only
        'pressure': None,
        'pressure_unit': None,
        'leak_detected': None,
        # velo only
        'velocity_x': None,
        'velocity_y': None,
        'velocity_z': None,
        'velocity_unit': None,
        'vibration_magnitude': None
    }
    
    if 'temperature' in telem_dict:
        db_data['telemetry_type'] = 'TEMPERATURE'
        temp_data = telem_dict['temperature']
        db_data.update({
            'sensor_id': temp_data.get('sensorId'),
            'subsystem': temp_data.get('subsystem'),
            'temperature': temp_data.get('temperature'),
            'temp_unit': temp_data.get('unit'),
            'status_bitmask': temp_data.get('statusBitmask'),
            'sequence_number': temp_data.get('sequenceNumber')
        })
        
    elif 'pressure' in telem_dict:
        db_data['telemetry_type'] = 'PRESSURE'
        pressure_data = telem_dict['pressure']
        db_data.update({
            'sensor_id': pressure_data.get('sensorId'),
            'subsystem': pressure_data.get('subsystem'),
            'pressure': pressure_data.get('pressure'),
            'pressure_unit': pressure_data.get('unit'),
            'status_bitmask': pressure_data.get('statusBitmask'),
            'leak_detected': pressure_data.get('leakDetected'),
            'sequence_number': pressure_data.get('sequenceNumber')
        })
        
    elif 'velocity' in telem_dict:
        db_data['telemetry_type'] = 'VELOCITY'
        velocity_data = telem_dict['velocity']
        db_data.update({
            'sensor_id': velocity_data.get('sensorId'),
            'subsystem': velocity_data.get('subsystem'),
            'velocity_x': velocity_data.get('velocityX'),
            'velocity_y': velocity_data.get('velocityY'),
            'velocity_z': velocity_data.get('velocityZ'),
            'velocity_unit': velocity_data.get('unit'),
            'vibration_magnitude': velocity_data.get('vibrationMag'),
            'status_bitmask': velocity_data.get('statusBitmask'),
            'sequence_number': velocity_data.get('sequenceNumber')
        })
    
    return db_data    


# @timing_decorator
async def push_to_db(aconn, cur, db_buffer):
    # TODO: format for COPY insert via psycopg3
    # 	records = [(10, 20, "hello"), (40, None, "world")]
	#   with cursor.copy("COPY sample (col1, col2, col3) FROM STDIN") as copy:
	#       for record in records:
	#           copy.write_row(record)
 
    print("------- [ I T  I S  T I M E ] -------")
    telem_headers = ','.join(DB_ALL_COLS)
    
    sql = f"COPY telemetry_data ({telem_headers}) FROM STDIN;"
    async with cur.copy(sql) as copy:
        for record in db_buffer:
            await copy.write_row(record)
            
    await aconn.commit()
    print("------- [ I T  I S  D O N E ] -------")

async def run_db_batching(aconn):
    global db_buffer
    
    print("[run_db_batching] : Starting!")
    async with aconn.cursor() as cur:
        try:
            while True:
                print("[run_db_batching] : Going to sleep...")
                await asyncio.sleep(BATCH_INTERVAL)
                print("[run_db_batching] : Woke up!")
                async with db_buffer_lock:
                    # await asyncio.get_running_loop().run_in_executor(None, push_to_db, cur, db_buffer)
                    await push_to_db(aconn, cur, db_buffer)
                    db_buffer.clear()
        except Exception as e:
            print(f"[ERROR] [run_db_batching] : {e}")


async def add_to_batch(telem_dict: dict):
    async with db_buffer_lock:
        db_buffer.append(tuple(telem_dict.values()))

async def run_grpc_stream(aconn):
    global db_buffer
    
    # connect to cpp server asynchronously
    async with grpc.aio.insecure_channel('localhost:50051') as channel:
        # get generated stub
        stub = telemetry_pb2_grpc.TelemetryServiceStub(channel)
        
        async with aconn.cursor() as cur:
            stream = stub.GetTelemetryStream(telemetry_pb2.TelemetryRequest())
        
            try:
                async for telem_response in stream:
                    print(f"Received [{telem_response.timestamp}]")
                    
                    telem_dict, time_process = process_data(telem_response)
                    # print(f"time process: {time_process}")
                    
                    await add_to_batch(telem_dict)
                    async with db_buffer_lock:
                        if len(db_buffer) >= MAX_BATCH_SIZE:
                            await push_to_db(aconn, cur, db_buffer)
                            db_buffer.clear()
                    
                    
                    # /POST to dashboard backend
                    # json_str = json.dumps(telem_dict)
                    # print(json_str)
                    dashboard_response = requests.post(url='http://127.0.0.1:8000/telem_data', json=telem_dict)
                    # pprint(dashboard_response.json())
                        
            except grpc.RpcError as e:
                print(f"Oh no! gRPC error: {e}")
            # finally:
                # no need to use .close() when using `with`
                # channel.close()

async def main():
    # connect to db
    async with await psycopg.AsyncConnection.connect(
        dbname='telemetry',
        user='mirujun',
        password='',
        host='localhost'
    ) as aconn:
        await asyncio.gather(run_grpc_stream(aconn), run_db_batching(aconn))
    
    

    

if __name__ == "__main__":
    asyncio.run(main())