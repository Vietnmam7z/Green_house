from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import numpy as np
import pandas as pd
import tensorflow as tf
import joblib
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import sqlite3 
import math  # Thêm thư viện math để xử lý NaN / Infinity

app = FastAPI()

app.add_middleware(
    CORSMiddleware, 
    allow_origins=["*"], 
    allow_methods=["*"], 
    allow_headers=["*"]
)

os.environ['CUDA_VISIBLE_DEVICES'] = '-1' 


MODEL_PATH = "smartcare_lstm_v3.keras"
META_PATH = "smartcare_scaler_v3.gz"
DB_PATH = "field.db"


model = tf.keras.models.load_model(MODEL_PATH)
meta = joblib.load(META_PATH)

scalers = meta["scalers"]
raw_features = meta["raw_features"]
light_idx = meta["light_idx"]
TIME_STEP = meta["seq_length"]

# ==========================================
# TỪ ĐIỂN MAP TÊN GIỮA MODEL VÀ DATABASE
# ==========================================
DB_MAPPING = {
    "Temperature (*C)": "temperature", 
    "Humidity (%)": "humidity",
    "Light": "light",
    "Soil (%)": "moisture" 
}

class SensorData(BaseModel):
    device_id: str
    step: int

@app.get("/")
def serve_webpage():
    return FileResponse("index.html")

@app.post("/predict")
def predict_smartcare(data: SensorData):
    step_ms = data.step * 60 * 1000
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(f"""
        SELECT 
            MIN(ts) as ts_ms,
            AVG(CASE WHEN name = '{DB_MAPPING["Temperature (*C)"]}' THEN value END) as temp,
            AVG(CASE WHEN name = '{DB_MAPPING["Humidity (%)"]}' THEN value END) as hum,
            AVG(CASE WHEN name = '{DB_MAPPING["Light"]}' THEN value END) as light,
            AVG(CASE WHEN name = '{DB_MAPPING["Soil (%)"]}' THEN value END) as soil
        FROM telemetry 
        WHERE device_id = (SELECT device_id FROM device WHERE device_name = ? OR device_id = ?) 
        GROUP BY CAST(ts / ? AS INTEGER)
        HAVING temp IS NOT NULL 
            OR hum IS NOT NULL 
            OR light IS NOT NULL 
            OR soil IS NOT NULL
        ORDER BY CAST(ts / ? AS INTEGER) DESC 
        LIMIT ?
        
    """, (data.device_id, data.device_id, step_ms, step_ms, TIME_STEP))
    
    records = cursor.fetchall()
    conn.close()
    print("DỮ LIỆU AI ĐANG NHÌN THẤY LÀ:", records) 
    print("SỐ LƯỢNG:", len(records))
    if len(records) < TIME_STEP:
        return {    
            "status": "waiting",
            "current_step": len(records),
            "total_steps": TIME_STEP,
            "message": f"Chờ thêm dữ liệu ({len(records)}/{TIME_STEP})"
        }
    df = pd.DataFrame(records, columns=['ts_ms'] + raw_features)
    df = df.iloc[::-1].reset_index(drop=True)
    

    df[raw_features] = df[raw_features].ffill().bfill().infer_objects(copy=False)
    
    if df[raw_features].isnull().values.any():
        df[raw_features] = df[raw_features].fillna(0.0)
    
    ts = pd.to_datetime(df['ts_ms'], unit='ms', utc=True).dt.tz_convert('Asia/Ho_Chi_Minh')
    minute_of_day = ts.dt.hour * 60 + ts.dt.minute
    angle = 2 * np.pi * minute_of_day / 1440
    sin_h = np.sin(angle).astype(np.float32)
    cos_h = np.cos(angle).astype(np.float32)
    

    raw_data = df[raw_features].values.copy().astype(np.float32)
    raw_data[:, light_idx] = np.log1p(raw_data[:, light_idx])
    
    scaled_raw = np.empty_like(raw_data)
    for i, feat in enumerate(raw_features):
        sc = scalers[feat]
        scaled_raw[:, i] = sc.transform(raw_data[:, i].reshape(-1, 1)).ravel()
        
    data_scaled = np.column_stack([scaled_raw, sin_h, cos_h])
    input_lstm = data_scaled.reshape(1, TIME_STEP, data_scaled.shape[1]) 
    

    prediction_scaled = model.predict(input_lstm, verbose=0)
    
    # Đưa kết quả về đơn vị gốc
    out = np.empty_like(prediction_scaled)
    for i, feat in enumerate(raw_features):
        out[:, i] = scalers[feat].inverse_transform(prediction_scaled[:, i].reshape(-1, 1)).ravel()
    
    out[:, light_idx] = np.expm1(out[:, light_idx]) # expm1 cho Light
    
    safe_predictions = {}
    for i, feat in enumerate(raw_features):
        val = float(out[0, i])
        db_key_name = DB_MAPPING[feat] 
        if math.isnan(val) or math.isinf(val):
            safe_predictions[db_key_name] = None
        else:
            if val < 0 and feat in ['Light', 'Humidity (%)', 'Soil (%)']:
                val = 0.0
            safe_predictions[db_key_name] = round(val, 2)
    
    # Trả về kết quả
    return {
        "status": "success",
        "predicted_next_val": safe_predictions
    }

if __name__ == "__main__":
    uvicorn.run("LSTM_AI:app", host="0.0.0.0", port=8000, reload=True)