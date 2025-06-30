from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Add your frontend origin here
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/telem_data")
def post_data(telem_dict):
    # TODO: type enforce the telem dict with a class or something
    
    
    # TODO: broadcast new data to frontend via web socket connection
    
    
