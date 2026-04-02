from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel
import numpy as np
import tensorflow as tf
import joblib
from collections import deque
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
from typing import Dict

app = FastAPI()

app.add_middleware(
    CORSMiddleware, 
    allow_origins=["*"], 
    allow_methods=["*"], 
    allow_headers=["*"]
)

os.environ['CUDA_VISIBLE_DEVICES'] = '-1' 
model = tf.keras.models.load_model("sensor_lstm_model.keras")
scaler = joblib.load("scaler.save")

TIME_STEP = 5

buffers: Dict[str, deque] = {}

class SensorData(BaseModel):
    sensor_id: str
    val: float

@app.get("/")
def serve_webpage():
    return FileResponse("index.html")

@app.post("/predict")
def predict_soil(data: SensorData):
    
    if data.sensor_id not in buffers:
        buffers[data.sensor_id] = deque(maxlen=TIME_STEP)
        
    current_buffer = buffers[data.sensor_id]
    current_buffer.append(data.val)
    
    if len(current_buffer) < TIME_STEP:
        return {
            "status": "waiting",
            "message": f"Chờ thêm dữ liệu ({len(current_buffer)}/{TIME_STEP})"
        }
    
    raw_data = np.array(list(current_buffer)).reshape(-1, 1)
    scaled_data = scaler.transform(raw_data)
    input_lstm = scaled_data.reshape(1, TIME_STEP, 1)
    
    prediction_scaled = model.predict(input_lstm, verbose=0)
    prediction_real = scaler.inverse_transform(prediction_scaled)
    
    result = float(prediction_real[0][0])
    
    return {
        "status": "success",
        "predicted_next_val": round(result, 2),
        "sensor_id": data.sensor_id
    }

if __name__ == "__main__":
    uvicorn.run("LSTM_AI:app", host="0.0.0.0", port=8000, reload=True)