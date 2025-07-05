import grpc
from google.protobuf.json_format import MessageToDict

import telemetry_pb2
import telemetry_pb2_grpc
import psycopg2

import requests
import typing
import json
from pprint import pprint
import time
from functools import wraps



DEBUG = False

DB_SHARED_COLS = [
    'reading_timestamp', 
    'telemetry_type', 
    'sensor_id', 
    'subsystem', 
    'sequence_number', 
    'status_bitmask',
]

DB_TEMPERATURE_COLS = [
    'temperature',
    'temp_unit',
]

DB_PRESSURE_COLS = [
    'pressure',
    'pressure_unit',
    'leak_detected',
]

DB_VELOCITY_COLS = [
    'velocity_x',
    'velocity_y',
    'velocity_z',
    'velocity_unit',
    'vibration_magnitude',
]

accum_perc = 1
count = 1


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
    
    def process_temp_data():
        temp_data = telem_response.temperature
        if DEBUG:
            print(f"Temperature: {temp_data.temperature} {temp_data.unit}")
            print(f"Sensor ID: {temp_data.sensor_id}")
            print(f"Subsystem: {temp_data.subsystem}")
            print(f"Status: {temp_data.status_bitmask}")
            print(f"Sequence: {temp_data.sequence_number}")
        
    def process_press_data():
        press_data = telem_response.pressure
        if DEBUG:
            print(f"Pressure: {press_data.pressure} {press_data.unit}")
            print(f"Sensor ID: {press_data.sensor_id}")
            print(f"Subsystem: {press_data.subsystem}")
            print(f"Leak detected: {press_data.leak_detected}")
            print(f"Status: {press_data.status_bitmask}")
            print(f"Sequence: {press_data.sequence_number}")
        
    def process_velo_data():
        velo_data = telem_response.velocity
        if DEBUG:
            print(f"Velocity: ({velo_data.velocity_x}, {velo_data.velocity_y}, {velo_data.velocity_z}) {velo_data.unit}")
            print(f"Sensor ID: {velo_data.sensor_id}")
            print(f"Subsystem: {velo_data.subsystem}")
            print(f"Vibration magnitude: {velo_data.vibration_mag}")
            print(f"Status: {velo_data.status_bitmask}")
            print(f"Sequence: {velo_data.sequence_number}")
        
    def process_unknown_data():
        raise NotImplementedError(f"Data processing not implemented for telemetry type: {telem_response.type}")

    pprint(f"RAW RESPONSE: {telem_response}")
    telem_dict = MessageToDict(telem_response, always_print_fields_with_no_presence=True)
    
    pprint(f"GOT dictionary: {telem_dict}")
    # remap keys/headers from .proto to sql table
    db_data = {
        'reading_timestamp': telem_dict.get('timestamp'),
        'telemetry_type': None,
        'sensor_id': None,
        'subsystem': None,
        'sequence_number': None,
        'status_bitmask': None,
        # # temp only
        # 'temperature': None,
        # 'temp_unit': None,
        # # pressure only
        # 'pressure': None,
        # 'pressure_unit': None,
        # 'leak_detected': None,
        # # velo only
        # 'velocity_x': None,
        # 'velocity_y': None,
        # 'velocity_z': None,
        # 'velocity_unit': None,
        # 'vibration_magnitude': None
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

    
    # TODO: no use for this yet...
    # if telem_response.type == telemetry_pb2.TelemetryType.TEMPERATURE:
    #     process_temp_data()
    # elif telem_response.type == telemetry_pb2.TelemetryType.PRESSURE:
    #     process_press_data()
    # elif telem_response.type == telemetry_pb2.TelemetryType.VELOCITY:
    #     process_velo_data()
    # else:
    #     process_unknown_data()
        

@timing_decorator
def push_to_db(telem_dict: dict, conn, cur):
    no_null_dict = {k: v for k, v in telem_dict.items() if v is not None}
    
    telem_headers = list(no_null_dict.keys())
    telem_headers = ','.join(telem_headers)
    
    telem_vals = list(no_null_dict.values())
    placeholders = ','.join(['%s'] * len(telem_vals))
    
    # the `,` is important! needs to be interpreted as a tuple
    sql = f"EXPLAIN ANALYZE INSERT INTO telemetry_data ({telem_headers}) VALUES ({placeholders});"
    cur.execute(sql, telem_vals)
    
    # get the EXPLAIN ANALYZE plan
    plan = cur.fetchall()
    print("----- SQL plan start -----")
    for row in plan:
        print(row[0])
    print("----- SQL plan end -----")

    # this is important!
    conn.commit()


if __name__ == "__main__":
    # connect to cpp server
    channel = grpc.insecure_channel('localhost:50051')
    # get generated stub
    stub = telemetry_pb2_grpc.TelemetryServiceStub(channel)
    
    # connect to db
    conn = psycopg2.connect(
        dbname='telemetry',
        user='mirujun',
        password='',
        host='localhost'
    )
    cur = conn.cursor()

    try:
        stream = stub.GetTelemetryStream(telemetry_pb2.TelemetryRequest())
        
        for telem_response in stream:
            print(f"Received [{telem_response.timestamp}]")
            
            telem_dict, time_process = process_data(telem_response)
            time_push = push_to_db(telem_dict, conn, cur)
            print(f"time process: {time_process}")
            print(f"time push: {time_push[1]}")
            print(f"percentage diff for push: {time_push[1] / time_process}")
            accum_perc += (time_push[1] / time_process)
            count += 1
            accum_perc /= count
            print(f"Running avg perc diff: {accum_perc}")
            
            # /POST to dashboard backend
            json_str = json.dumps(telem_dict)
            print(json_str)
            dashboard_response = requests.post(url='http://127.0.0.1:8000/telem_data', json=telem_dict)
            pprint(dashboard_response.json())
            
    except grpc.RpcError as e:
        print(f"Oh no! gRPC error: {e}")
    finally:
        conn.close()
        channel.close()