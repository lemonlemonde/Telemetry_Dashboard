import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from pydantic import BaseModel, Field
from typing import Union, Literal, Annotated, Optional
        
import asyncio

from prometheus_client import start_http_server, Histogram

LATENCY_END_TO_END = Histogram('latency_end_to_end', 'Time (seconds) from data creation to reception on frontend.')

class Latency(BaseModel):
    latency: float

class TelemetryBase(BaseModel):
    reading_timestamp: str
    sensor_id: str
    subsystem: str
    sequence_number: int
    status_bitmask: int
    
class TemperatureData(TelemetryBase):
    # temp only
    telemetry_type: Literal["TEMPERATURE"]
    temperature: float
    temp_unit: str

class PressureData(TelemetryBase):
    # pressure only
    telemetry_type: Literal["PRESSURE"]
    pressure: float
    pressure_unit: str
    leak_detected: Optional[int]
    
class VelocityData(TelemetryBase):
    # velocity only
    telemetry_type: Literal["VELOCITY"]
    velocity_x: float
    velocity_y: float
    velocity_z: float
    velocity_unit: str
    vibration_magnitude: Optional[float]

# explicitly discriminate based on `telemetry_type`
TelemetryData = Annotated[
    Union[TemperatureData, PressureData, VelocityData],
    Field(discriminator='telemetry_type')
]


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        print("---- Connected websocket! ----")
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        print("---- Removed websocket! ----")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        print("---- Trying to broadcast to websockets! ----")
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                # throw away bad connection!
                print("------ Need to throw away bad connection! ------")
                self.disconnect(connection)
                print(e)
                


@asynccontextmanager
async def lifespan(app: FastAPI):
    # on startup
    # start prometheus endpoint
    server, t = start_http_server(8002)
    
    yield

    # on shutdown
    server.shutdown()
    t.join()

app = FastAPI(lifespan=lifespan)
manager = ConnectionManager()

# add NextJS frontend for /latency
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/telem_data")
async def post_data(telem_dict: TelemetryData):
    # TODO: type enforce the telem dict with the type
    # print(telem_dict)
    
    # broadcast new data to frontend via web socket connection
    telem_json = telem_dict.model_dump_json()
    print(f"Broadcasting: `{telem_json}`")
    await manager.broadcast(f"{telem_json}")
    
    return {
        "msg": "got it!<3",
        "telemetry_type": telem_dict.telemetry_type,
        "sensor_id": telem_dict.sensor_id,
    }
    
    
@app.post("/latency")
async def post_latency(data: Latency):
    LATENCY_END_TO_END.observe(data.latency)
    
    print(f"Received frontend latency: {data.latency}")
    
    return {
        "msg": "latency logged! <3",
        "latency": str(data.latency),
    }
    
    
# directly from example:
#   https://fastapi.tiangolo.com/advanced/websockets/#create-a-websocket
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    print("****** RECEIVED WS CONNECTION REQUEST *******")
    await manager.connect(websocket)
    try:
        # need to await a receiving websocket call
            # in order for FastAPI to detect websocket disconnects or other exceptions
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast(f"Client '{client_id}' closed the stream.")
    except Exception as e:
        manager.disconnect(websocket)
        print(e)