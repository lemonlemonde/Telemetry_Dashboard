from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel, Field
from typing import Union, Literal, Annotated, Optional
        
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Add your frontend origin here
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/telem_data")
def post_data(telem_dict: TelemetryData):
    # TODO: type enforce the telem dict with the type
    print(telem_dict)
    
    return {
        "msg": "got it!<3",
        "telemetry_type": telem_dict.telemetry_type,
        "sensor_id": telem_dict.sensor_id,
    }
    
    # TODO: broadcast new data to frontend via web socket connection
    
    


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
