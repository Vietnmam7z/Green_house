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
import math

app = FastAPI()

app.add_middleware(
    CORSMiddleware, 
    allow_origins=["*"], 
    allow_methods=["*"], 
    allow_headers=["*"]
)

os.environ['CUDA_VISIBLE_DEVICES'] = '-1' 

# ==========================================
# CẤU HÌNH ĐƯỜNG DẪN 
# (Nhớ đổi lại tên model và scaler 1 biến của bạn nhé)
# ==========================================
MODEL_PATH = "model_nhiet_do_1_input.keras" 
SCALER_PATH = "scaler_1_input.pkl" # Dùng file pkl chứa scaler trực tiếp
DB_PATH = "field.db"

# Load mô hình và bộ chuẩn hóa 1 biến
model = tf.keras.models.load_model(MODEL_PATH)
scaler = joblib.load(SCALER_PATH)

TIME_STEP = model.input_shape[1] # Tự động lấy sequence length (VD: 5) từ mô hình

class SensorData(BaseModel):
    device_id: str
    step: int # Số phút mỗi nhịp (VD: 5 phút = step 5)

@app.get("/")
def serve_webpage():
    return FileResponse("index.html")

@app.post("/predict")
def predict_smartcare(data: SensorData):
    step_ms = data.step * 60 * 1000
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # SQL CHỈ LẤY DUY NHẤT NHIỆT ĐỘ
    cursor.execute(f"""
        SELECT 
            MIN(ts) as ts_ms,
            AVG(CASE WHEN name = 'temperature' THEN value END) as temperature
        FROM telemetry 
        WHERE device_id = (SELECT device_id FROM device WHERE device_name = ? OR device_id = ?) 
        GROUP BY CAST(ts / ? AS INTEGER)
        HAVING temperature IS NOT NULL 
        ORDER BY CAST(ts / ? AS INTEGER) DESC 
        LIMIT ?
    """, (data.device_id, data.device_id, step_ms, step_ms, TIME_STEP))
    
    records = cursor.fetchall()
    conn.close()
    
    print("DỮ LIỆU NHIỆT ĐỘ AI ĐANG NHÌN THẤY LÀ:", records) 
    print(f"SỐ LƯỢNG MẪU: {len(records)}/{TIME_STEP}")
    
    if len(records) < TIME_STEP:
        return {    
            "status": "waiting",
            "current_step": len(records),
            "total_steps": TIME_STEP,
            "message": f"Chờ thêm dữ liệu nhiệt độ ({len(records)}/{TIME_STEP})"
        }
        
    df = pd.DataFrame(records, columns=['ts_ms', 'temperature'])
    df = df.iloc[::-1].reset_index(drop=True) # Đảo ngược lại đúng thứ tự thời gian
    
    # Vá lỗ hổng dữ liệu (nếu có nhịp nào bị mất kết nối)
    df['temperature'] = df['temperature'].ffill().bfill().infer_objects(copy=False)
    if df['temperature'].isnull().values.any():
        df['temperature'] = df['temperature'].fillna(0.0)
        
    # Lấy đúng mảng giá trị Nhiệt độ
    raw_data = df[['temperature']].values.astype(np.float32)
    
    # ==========================================
    # TIỀN XỬ LÝ VÀ DỰ ĐOÁN (1 BIẾN)
    # ==========================================
    # 1. Chuẩn hóa bằng Scaler duy nhất
    scaled_raw = scaler.transform(raw_data)
    
    # 2. Reshape về đúng chuẩn LSTM: (1 batch, TIME_STEP, 1 feature)
    input_lstm = scaled_raw.reshape(1, TIME_STEP, 1) 
    
    # 3. Chạy mô hình dự đoán
    prediction_scaled = model.predict(input_lstm, verbose=0)
    
    # 4. Giải mã kết quả về độ C thực tế
    out = scaler.inverse_transform(prediction_scaled)
    predicted_temp = float(out[0][0])
    
    # 5. Xử lý lỗi toán học (nếu có)
    if math.isnan(predicted_temp) or math.isinf(predicted_temp):
        safe_temp = None
    else:
        # Nhiệt độ phòng/nhà kính không thể âm quá vô lý, có thể set chặn dưới nếu cần
        safe_temp = round(predicted_temp, 2)
    
    # Trả về kết quả JSON gọn gàng
    return {
        "status": "success",
        "predicted_next_val": {
            "temperature": safe_temp
        }
    }

if __name__ == "__main__":
    uvicorn.run("LSTM_AI:app", host="0.0.0.0", port=8000, reload=True)