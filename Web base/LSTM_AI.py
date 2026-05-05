from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel
import numpy as np
import tensorflow as tf
import joblib
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import sqlite3 

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
DB_PATH = "field.db"

class SensorData(BaseModel):
    device_id: str
    name: str
    step: int

@app.get("/")
def serve_webpage():
    return FileResponse("index.html")

@app.post("/predict")
def predict_soil(data: SensorData):
    step_ms = data.step * 60 * 1000
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT AVG(value)
        FROM telemetry 
        WHERE device_id = (SELECT device_id FROM device WHERE device_name = ? OR device_id = ?) 
          AND name = ? 
        GROUP BY CAST(ts / ? AS INTEGER)
        ORDER BY CAST(ts / ? AS INTEGER) DESC 
        LIMIT ?
    """, (data.device_id, data.device_id, data.name, step_ms, step_ms, TIME_STEP))
    
    records = cursor.fetchall()
    conn.close()
    
    if len(records) < TIME_STEP:
        return {
            "status": "waiting",
            "current_step": len(records),
            "total_steps": TIME_STEP,
            "message": f"Chờ thêm dữ liệu ({len(records)}/{TIME_STEP})"
        }
    
    historical_values = [row[0] for row in records]
    historical_values.reverse()
    
    raw_data = np.array(historical_values).reshape(-1, 1)
    scaled_data = scaler.transform(raw_data)
    input_lstm = scaled_data.reshape(1, TIME_STEP, 1)
    
    prediction_scaled = model.predict(input_lstm, verbose=0)
    prediction_real = scaler.inverse_transform(prediction_scaled)
    
    result = float(prediction_real[0][0])
    
    return {
        "status": "success",
        "predicted_next_val": round(result, 2)
    }

if __name__ == "__main__":
    uvicorn.run("LSTM_AI:app", host="0.0.0.0", port=8000, reload=True)