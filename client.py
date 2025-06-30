import grpc
from google.protobuf.json_format import MessageToDict

import telemetry_pb2
import telemetry_pb2_grpc
import psycopg2
import typing



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


    telem_dict = MessageToDict(telem_response)
    if telem_response.type == '0':
        telem_type = 'TEMPERATURE'
    elif telem_response.type == '0':
        telem_type = 'PRESSURE'
    else:
        telem_type = 'VELOCITY'
    # remap keys/headers from .proto to sql table
    db_data = {
        'reading_timestamp': telem_dict.get('timestamp'),
        'telemetry_type': telem_type,
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
        

def push_to_db(telem_dict: dict, conn, cur):
    no_null_dict = {k: v for k, v in telem_dict.items() if v is not None}
    
    telem_headers = list(no_null_dict.keys())
    telem_headers = ','.join(telem_headers)
    
    telem_vals = list(no_null_dict.values())
    placeholders = ','.join(['%s'] * len(telem_vals))
    
    # the `,` is important! needs to be interpreted as a tuple
    sql = f"INSERT INTO telemetry_data ({telem_headers}) VALUES ({placeholders});"
    cur.execute(sql, telem_vals)

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
            
            telem_dict = process_data(telem_response)
            push_to_db(telem_dict, conn, cur)
            
            # TODO: /POST to dashboard backend
            
    except grpc.RpcError as e:
        print(f"Oh no! gRPC error: {e}")
    finally:
        conn.close()
        channel.close()