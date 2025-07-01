from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel, Field
from typing import Union, Literal, Annotated, Optional
        
import asyncio
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

app = FastAPI()

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["http://localhost:3000"],  # Add your frontend origin here
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

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
                


manager = ConnectionManager()

@app.post("/telem_data")
async def post_data(telem_dict: TelemetryData):
    # TODO: type enforce the telem dict with the type
    # print(telem_dict)
    
    # TODO: broadcast new data to frontend via web socket connection
    await manager.broadcast(f"{telem_dict}")
    
    return {
        "msg": "got it!<3",
        "telemetry_type": telem_dict.telemetry_type,
        "sensor_id": telem_dict.sensor_id,
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
        


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
