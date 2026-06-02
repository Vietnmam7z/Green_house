import sqlite3
import json
import config 
from datetime import datetime, timedelta
from flask import session, jsonify
import time
class FieldDB:
    def __init__(self, field_db_path = config.field_db_path):
        self.field_db_path = field_db_path

    def connect(self):
        conn = sqlite3.connect(self.field_db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    
    def add_field(self, field_id: str, field_name: str, username: str):
        with self.connect() as conn:
            cursor = conn.cursor()

            # Kiểm tra xem field_id đã tồn tại chưa
            cursor.execute("SELECT 1 FROM field WHERE field_id = ?", (field_id,))
            if cursor.fetchone():
                return {"success": False, "message": "Ruộng đã tồn tại."} 

            # Thêm field mới với cả field_id và field_name
            cursor.execute(
                "INSERT INTO field (field_id, field_name) VALUES (?, ?)",
                (field_id, field_name)
            )

            # Liên kết field với user
            cursor.execute("""
                INSERT INTO field_user (field_id, username)
                VALUES (?, ?)
            """, (field_id, username))

            # =========================================================
            # THÊM TỰ ĐỘNG 8 THIẾT BỊ MẶC ĐỊNH VÀO DEVICE_CONTROLLER
            # =========================================================
            default_devices = [
                ("Máy bơm nước", "valve"),
                ("Đèn", "light"),
                ("Thông gió", "vent"),
                ("Quạt", "fan"),
                ("Màng giải nhiệt", "cooling_pad"),
                ("Van điện từ CO2", "co2_valve"),
                ("Hệ thống sưởi", "heater"),
                ("Phân bón", "fertilizer")
            ]

            # Khi không chèn dữ liệu vào cột sensor_id, SQLite sẽ tự động để giá trị là NULL
            for device_name, dev_type in default_devices:
                cursor.execute("""
                    INSERT INTO device_controller (field_id, device_name, type, state)
                    VALUES (?, ?, ?, 'DONE')
                """, (field_id, device_name, dev_type))
            # =========================================================

            conn.commit()
            return {"success": True, "message": "Thêm ruộng và khởi tạo thiết bị thành công."}
        
    # 1. Hàm lấy ruộng cho User thường (Đã khôi phục)
    def get_fields(self, username: str):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT f.field_id, f.field_name
                FROM field_user fu
                JOIN field f ON fu.field_id = f.field_id
                WHERE fu.username = ?
            """, (username,))
            return [{"field_id": row[0], "field_name": row[1] if row[1] else "---"} for row in cursor.fetchall()]

    # 2. Hàm lấy toàn bộ ruộng cho Admin (Giữ nguyên)
    def get_all_fields(self):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT field_id, field_name FROM field")
            return [{"field_id": row[0], "field_name": row[1] if row[1] else "---"} for row in cursor.fetchall()]
        
    def get_field_ids(self, field_ids: list):
        with self.connect() as conn:
            cursor = conn.cursor()
            # Tạo chuỗi placeholder theo số lượng phần tử
            placeholders = ','.join(['?'] * len(field_ids))
            cursor.execute(f"""
                SELECT field_id
                FROM field
                WHERE field_id IN ({placeholders})
            """, field_ids)
            rows = cursor.fetchall()
            return [r[0] for r in rows]
       
    def delete_field(self, field_id: str):
        with self.connect() as conn:
            cursor = conn.cursor()
            
            # 1. Xóa tất cả các thiết bị thuộc Field này
            cursor.execute("DELETE FROM device_controller WHERE field_id = ?", (field_id,))
            
            # 2. Xóa các liên kết người dùng quản lý Field này
            cursor.execute("DELETE FROM field_user WHERE field_id = ?", (field_id,))
            
            # 3. Xóa toàn bộ lịch trình (scheduler) của Field này
            cursor.execute("DELETE FROM scheduler WHERE field_id = ?", (field_id,))
            
            # (Tùy chọn) Xóa thêm dữ liệu lịch sử cảm biến hoặc hóa đơn liên quan nếu cần
            # cursor.execute("DELETE FROM telemetry WHERE ...")
            
            # 4. Cuối cùng, mới tiến hành xóa Field ID
            cursor.execute("DELETE FROM field WHERE field_id = ?", (field_id,))
            
            conn.commit()
            return {"success": True, "message": "Đã xóa hoàn toàn Field và các dữ liệu liên quan."}

    def rename_field_id(self, old_field_id: str, new_field_id: str):
        with self.connect() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT 1 FROM field WHERE field_id = ?", (new_field_id,))
            if cursor.fetchone():
                 return {"success": False, "message": "Ruộng đã tồn tại."} 

            cursor.execute("""
                UPDATE field
                SET field_id = ?
                WHERE field_id = ?
            """, (new_field_id, old_field_id))

            conn.commit()
            return {"success": True, "message": "Đổi id ruộng thành công."}

    def rename_field_name(self, field_id: str, new_field_name: str):
        with self.connect() as conn:
            cursor = conn.cursor()

            # Cập nhật tên ruộng theo field_id
            cursor.execute("""
                UPDATE field
                SET field_name = ?
                WHERE field_id = ?
            """, (new_field_name, field_id))

            conn.commit()
            return {"success": True, "message": "Đổi tên ruộng thành công."}
        
    def get_devices(self, field_id: str):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT device_name
                FROM device
                WHERE field_id = ?
            """, (field_id,))
            return [row[0] for row in cursor.fetchall()]

    def add_device(self, field_id: str, device_id: str, device_name: str):
        with self.connect() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT 1 FROM device WHERE device_id = ? OR device_name = ?", (device_id, device_name))
            if cursor.fetchone():
                return {"success": False, "message": "Thiết bị hoặc id đã tồn tại."}   

            cursor.execute("""
                INSERT INTO device (device_id, device_name, field_id)
                VALUES (?, ?, ?)
            """, (device_id, device_name, field_id))

            conn.commit()
            return {"success": True, "message": "Thêm thiết bị thành công."}

    def delete_device(self, field_id: str, device_name: str):
        with self.connect() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                DELETE FROM device
                WHERE field_id = ? AND device_name = ?
            """, (field_id, device_name))

            conn.commit()

    def rename_device(self, old_name: str, new_name: str):
        with self.connect() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT 1 FROM device WHERE device_name = ?", (new_name,))
            if cursor.fetchone():
                return {"success": False, "message": "Thiết bị đã tồn tại."}  

            cursor.execute("""
                UPDATE device
                SET device_name = ?
                WHERE device_name = ?
            """, (new_name, old_name))

            conn.commit()
            return {"success": True, "message": "Đổi tên thiết bị thành công."}
        
    def remove_users_from_field(self, field_id: str, usernames: list):
        """Xóa một hoặc nhiều user cụ thể khỏi ruộng (bảng field_user)."""
        with self.connect() as conn:
            cursor = conn.cursor()
            
            # Xóa các liên kết user cụ thể của ruộng đó
            query = "DELETE FROM field_user WHERE field_id = ? AND username = ?"
            for user in usernames:
                cursor.execute(query, (field_id, user))
                
            conn.commit()
            return {"success": True, "message": f"Đã xóa {len(usernames)} user khỏi ruộng."}
        
    def find_user_id(self, field_id: str, username: str):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 1 FROM field_user
                WHERE field_id = ? AND username = ?
            """, (field_id, username))
            return cursor.fetchone() is not None

    def add_user_to_field(self, field_id: str, username: str):
        with self.connect() as conn:
            cursor = conn.cursor()
            
            # 1. Kiểm tra xem có dòng trống (NULL) nào cho field_id này không
            cursor.execute("SELECT * FROM field_user WHERE field_id = ? AND username IS NULL", (field_id,))
            empty_row = cursor.fetchone()

            if empty_row:
                # 2. Nếu có dòng NULL -> Cập nhật (UPDATE) chèn tên user vào chỗ trống
                cursor.execute("UPDATE field_user SET username = ? WHERE field_id = ? AND username IS NULL", (username, field_id))
            else:
                # 3. Nếu không có dòng NULL -> Thêm mới (INSERT)
                cursor.execute("INSERT INTO field_user (field_id, username) VALUES (?, ?)", (field_id, username))
                
            conn.commit()
        
    def get_device_names(self, field_id: str):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT device_name
                FROM device
                WHERE field_id = ?
                """,
                (field_id,)
            )
            rows = cursor.fetchall()
            return [row[0] for row in rows]

    def insert_telemetry(self, data: dict):
        device_id = data.get("deviceName")   
        ts = data.get("ts")
        telemetry = data.get("data", {})
        print(telemetry)
        with self.connect() as conn:
            cursor = conn.cursor()

            for name, value in telemetry.items():
                cursor.execute(
                    """
                    INSERT INTO telemetry (device_id, name, ts, value)
                    VALUES (?, ?, ?, ?)
                    """,
                    (device_id, name, ts, value)
                )

            conn.commit()
    
    def get_telemetry(self, device_name: str):
        special_counters = [
            "fertilizerCounter",
            "co2Counter",
            "pulseCounter"
        ]

        with self.connect() as conn:

            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT t.name, t.ts, t.value
                FROM telemetry t
                JOIN device d ON t.device_id = d.device_id
                WHERE d.device_name = ?
                AND t.ts = (
                    SELECT MAX(ts)
                    FROM telemetry
                    WHERE device_id = t.device_id
                    AND name = t.name
                )
                """,
                (device_name,)
            )

            latest_rows = cursor.fetchall()

            telemetry_dict = {}

            for name, ts, value in latest_rows:

                telemetry_dict[name] = {
                    "ts": ts,
                    "value": value
                }

            cursor.execute(
                f"""
                SELECT t.name, t.ts, t.value
                FROM telemetry t
                JOIN device d ON t.device_id = d.device_id
                WHERE d.device_name = ?
                AND DATE(t.ts / 1000, 'unixepoch', 'localtime')
                    = DATE('now', 'localtime')
                AND t.name IN ({",".join(["?"] * len(special_counters))})
                ORDER BY t.name, t.ts ASC
                """,
                [device_name] + special_counters
            )

            rows = cursor.fetchall()
            from collections import defaultdict
            grouped = defaultdict(list)
            for name, ts, value in rows:
                grouped[name].append(float(value))

            for name, values in grouped.items():
                if len(values) < 2:
                    consumption = 0
                else:
                    total = 0
                    prev = values[0]
                    for current in values[1:]:
                        delta = current - prev
                        if delta > 0:
                            total += delta
                        prev = current

                    consumption = total

                if name in telemetry_dict:
                    telemetry_dict[name]["daily_consumption"] = consumption

            return {
                device_name: telemetry_dict
            }

    def get_all_telemetry_status(self, device_id: str, telemetry_name: str, time_range: str):
        now = datetime.now()

        if time_range == "1h":
            start_time = now - timedelta(hours=1)
        elif time_range == "1d":
            start_time = now - timedelta(days=1)
        elif time_range == "7d":
            start_time = now - timedelta(days=7)
        elif time_range == "30d":
            start_time = now - timedelta(days=30)
        else:
            raise ValueError("time_range không hợp lệ")

        start_ms = int(start_time.timestamp() * 1000)
        end_ms   = int(now.timestamp() * 1000)

        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT ts, value
                FROM telemetry
                WHERE device_id = ?
                  AND name = ?
                  AND ts BETWEEN ? AND ?
                ORDER BY ts DESC
                """,
                (device_id, telemetry_name, start_ms, end_ms)
            )
            rows = cursor.fetchall()

        result = [{"ts": int(ts), "value": value} for ts, value in rows]

        return result

    def delete_time_out(self):
        now = datetime.now()

        cutoff_time = now - timedelta(days=1)
        cutoff_ms = int(cutoff_time.timestamp() * 1000)

        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM telemetry WHERE ts < ?",
                (cutoff_ms,)
            )
            conn.commit()

    def get_anomaly_score_low(self, field_id: str):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT anomaly_score_low
                FROM AI_management
                WHERE field_id = ?
            """, (field_id,))
            return [row[0] for row in cursor.fetchall()]

    def get_anomaly_score_high(self, field_id: str):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT anomaly_score_high
                FROM AI_management
                WHERE field_id = ?
            """, (field_id,))
            return [row[0] for row in cursor.fetchall()]

    def get_step(self, field_id: str):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT step
                FROM AI_management
                WHERE field_id = ?
            """, (field_id,))
            return [row[0] for row in cursor.fetchall()]

    def get_anomaly_status(self, field_id: str):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT anomaly_status
                FROM AI_management
                WHERE field_id = ?
            """, (field_id,))
            return [row[0] for row in cursor.fetchall()]

    def get_prediction_status(self, field_id: str):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT prediction_status
                FROM AI_management
                WHERE field_id = ?
            """, (field_id,))
            return [row[0] for row in cursor.fetchall()]
        
    def get_AI_Automation(self, field_id: str):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT AI_Automation
                FROM AI_management
                WHERE field_id = ?
            """, (field_id,))
            return [row[0] for row in cursor.fetchall()]


    def set_anomaly_score_low(self, field_id: str, value: float):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE AI_management
                SET anomaly_score_low = ?
                WHERE field_id = ?
            """, (value, field_id))
            conn.commit()

    def set_anomaly_score_high(self, field_id: str, value: float):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE AI_management
                SET anomaly_score_high = ?
                WHERE field_id = ?
            """, (value, field_id))
            conn.commit()

    def set_step(self, field_id: str, value: int):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE AI_management
                SET step = ?
                WHERE field_id = ?
            """, (value, field_id))
            conn.commit()

    def set_anomaly_status(self, field_id: str, value: str):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE AI_management
                SET anomaly_status = ?
                WHERE field_id = ?
            """, (value, field_id))
            conn.commit()

    def set_prediction_status(self, field_id: str, value: str):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE AI_management
                SET prediction_status = ?
                WHERE field_id = ?
            """, (value, field_id))
            conn.commit()

    def set_AI_automation(self, field_id: str, value: str):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE AI_management
                SET AI_automation = ?
                WHERE field_id = ?
            """, (value, field_id))
            conn.commit()

    def get_AI_telemetry_sample(self, device_id: str, sample: int):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT t.ts, t.value
                FROM telemetry t
                JOIN device d ON t.device_id = d.device_id
                WHERE d.device_id = ?
                AND t.name = 'status'
                ORDER BY t.ts DESC
                """,
                (device_id,)
            )

            rows = cursor.fetchall()

            limited_rows = rows[:sample]

            telemetry_list = [{"ts": ts, "value": value} for ts, value in limited_rows]
            return {device_id: telemetry_list}

    def delete_user(self, username: str):
        with self.connect() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                DELETE FROM field_user
                WHERE username = ?
                """,
                (username,)
            )

            cursor.execute(
                """
                DELETE FROM notification_management
                WHERE username = ?
                """,
                (username,)
            )

            cursor.execute(
                """
                DELETE FROM notification
                WHERE username = ?
                """,
                (username,)
            )

            conn.commit()

    def api_admin_greenhouses(self):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT f.field_id, f.field_name, fu.username
                FROM field f
                LEFT JOIN field_user fu ON f.field_id = fu.field_id
            """)
            result = cursor.fetchall()
            return result

    def clear_field(self, field_id: str):
        with self.connect() as conn:
            cursor = conn.cursor()
            try:
                # 1. Reset tên field (gán NULL)
                cursor.execute(
                    """
                    UPDATE field
                    SET field_name = NULL
                    WHERE field_id = ?
                    """,
                    (field_id,)
                )

                # 2. Xóa liên kết user bằng cách cập nhật thành NULL (thay vì xóa nguyên dòng)
                cursor.execute(
                    """
                    UPDATE field_user
                    SET username = NULL
                    WHERE field_id = ?
                    """,
                    (field_id,)
                )

                conn.commit()
                return {"success": True, "message": f"Đã dọn dẹp field {field_id} thành công"}
            except Exception as e:
                conn.rollback()
                return {"success": False, "message": str(e)}

    def create_AI_management_record(self, field_id: str):
        with self.connect() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO AI_management (
                        field_id,
                        anomaly_score_low,
                        anomaly_score_high,
                        step,
                        anomaly_status,
                        prediction_status,
                        AI_automation
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    field_id,
                    0,          
                    100,        
                    5,          
                    "OFF",      
                    "OFF",      
                    "OFF"       
                ))
                conn.commit()
                return {"success": True, "message": "Tạo record AI_management thành công"}
            except Exception as e:
                conn.rollback()
                return {"success": False, "message": str(e)}
    
    def create_notification_management(self, username: str):
        with self.connect() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO notification_management (status, username, email_status)
                    VALUES (?, ?, ?)
                """, ("OFF", username, "OFF"))  

                conn.commit()
                return {"success": True, "message": "Tạo notification_management thành công"}
            except Exception as e:
                conn.rollback()
                return {"success": False, "message": str(e)}
    
    def get_notifications_by_user(self, username: str):
        with self.connect() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    SELECT 
                        n.status, 
                        n.device_id, 
                        n.ts, 
                        n.is_read,
                        d.device_name, 
                        f.field_name
                    FROM notification n
                    LEFT JOIN device d ON n.device_id = d.device_id
                    LEFT JOIN field f ON d.field_id = f.field_id
                    WHERE n.username = ?
                    ORDER BY n.ts DESC
                    LIMIT 50
                """, (username,))
                
                rows = cursor.fetchall()
                data_list = []
                for r in rows:
                    data_list.append({
                        "status": r[0],
                        "device_id": r[1],
                        "ts": r[2],
                        "is_read": r[3],
                        "device_name": r[4] if r[4] else "Unknown Device",
                        "field_name": r[5] if r[5] else "Unknown Field"
                    })

                return {"success": True, "data": data_list}
            except Exception as e:
                return {"success": False, "message": str(e)}

    def mark_notification_as_read(self, ts: int, device_id: str, username: str):
        with self.connect() as conn:
            cursor = conn.cursor()
            try:

                cursor.execute("""
                    UPDATE notification
                    SET is_read = 1
                    WHERE ts = ? AND device_id = ? AND username = ?
                """, (ts, device_id, username))
                
                conn.commit()
                return {"success": True, "message": "Đã đánh dấu đã đọc"}
            except Exception as e:
                conn.rollback()
                return {"success": False, "message": str(e)} 

    def delete_notification(self, notifications_list):
        """
        notifications_list có thể là:
        - Một dict đơn lẻ: {"ts": 123, "device_id": "ABC", "username": "user1"}
        - Hoặc một danh sách các dict: [{"ts": 123, ...}, {"ts": 456, ...}]
        """
        # Nếu người dùng chỉ truyền vào 1 thông báo đơn lẻ, tự động bọc nó thành mảng list
        if isinstance(notifications_list, dict):
            notifications_list = [notifications_list]
            
        if not notifications_list:
            return {"success": True, "message": "Danh sách xóa trống"}

        with self.connect() as conn:
            cursor = conn.cursor()
            try:
                # Thực hiện xóa hàng loạt trong cùng một Transaction để tối ưu tốc độ
                for notif in notifications_list:
                    ts = notif.get('ts')
                    device_id = notif.get('device_id')
                    username = notif.get('username')
                    
                    cursor.execute("""
                        DELETE FROM notification
                        WHERE ts = ? AND device_id = ? AND username = ?
                    """, (ts, device_id, username))
                
                conn.commit()
                return {"success": True, "message": f"Đã xóa thành công {len(notifications_list)} thông báo"}
            except Exception as e:
                conn.rollback()
                return {"success": False, "message": str(e)}

    def get_notification_status(self, username: str):
        with self.connect() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    SELECT status, email_status
                    FROM notification_management
                    WHERE username = ?
                """, (username,))

                row = cursor.fetchone()

                if row:
                    return {
                        "success": True,
                        "data": {
                            "status": row[0],
                            "email_status": row[1]
                        }
                    }

                return {"success": False, "message": "Không tìm thấy user"}

            except Exception as e:
                return {"success": False, "message": str(e)}

    def set_notification_status(self, username: str, status: str):
        with self.connect() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    UPDATE notification_management
                    SET status = ?
                    WHERE username = ?
                """, (status, username))
                conn.commit()
                return {"success": True, "message": f"Đã cập nhật status = {status} cho {username}"}
            except Exception as e:
                conn.rollback()
                return {"success": False, "message": str(e)}

    def set_email_notification_status(self, username: str, email_status: str):
        with self.connect() as conn:
            cursor = conn.cursor()
            try:
                if email_status not in ["ON", "OFF"]:
                    return {"success": False, "message": "email_status phải là ON hoặc OFF"}

                cursor.execute("""
                    UPDATE notification_management
                    SET email_status = ?
                    WHERE username = ?
                """, (email_status, username))

                conn.commit()

                return {
                    "success": True,
                    "message": f"Đã cập nhật email_status = {email_status} cho {username}"
                }

            except Exception as e:
                conn.rollback()
                return {"success": False, "message": str(e)}
        
    def insert_notification(self, status: str, device_id: str, ts: int, username: str):
        with self.connect() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO notification (status, device_id, ts, username)
                    VALUES (?, ?, ?, ?)
                """, (status, device_id, ts, username))
                conn.commit()
                return {"success": True, "message": "Thêm notification thành công"}
            except Exception as e:
                conn.rollback()
                return {"success": False, "message": str(e)}

    def get_devices_controller_by_field(self, field_id: int):
        with self.connect() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    SELECT device_id, device_name, type, state, created_at, updated_at
                    FROM device_controller
                    WHERE field_id = ?
                """, (field_id,))
                rows = cursor.fetchall()
                return {"success": True, "devices": rows}
            except Exception as e:
                return {"success": False, "message": str(e)}

    def toggle_device_state(self, device_id: int):
        with self.connect() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT state FROM device_controller WHERE device_id = ?", (device_id,))
                current = cursor.fetchone()
                if not current:
                    return {"success": False, "message": "Device không tồn tại"}

                new_state = "DONE" if current[0] == "ON" else "ON"
                cursor.execute("""
                    UPDATE device_controller
                    SET state = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE device_id = ?
                """, (new_state, device_id))
                conn.commit()
                return {"success": True, "new_state": new_state}
            except Exception as e:
                conn.rollback()
                return {"success": False, "message": str(e)}

    def set_device_state(self, device_id: int, state: str):
        with self.connect() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    UPDATE device_controller
                    SET state = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE device_id = ?
                """, (state, device_id))

                conn.commit()

                return {
                    "success": True,
                    "device_id": device_id,
                    "new_state": state
                }

            except Exception as e:
                conn.rollback()
                return {
                    "success": False,
                    "message": str(e)
                }
            
    def get_type_and_state_by_field(self, field_id: int):
        with self.connect() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    SELECT type, state
                    FROM device_controller
                    WHERE field_id = ?
                """, (field_id,))
                rows = cursor.fetchall()
                return {"success": True, "data": rows}
            except Exception as e:
                return {"success": False, "message": str(e)}

    def get_device_controller_by_id(self, field_id: int, device_id: int):
        with self.connect() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    SELECT device_id, device_name, type, state, created_at, updated_at
                    FROM device_controller
                    WHERE field_id = ? AND device_id = ?
                """, (field_id, device_id))
                row = cursor.fetchone()
                if row:
                    return {"success": True, "device": row}
                else:
                    return {"success": False, "message": "Device not found"}
            except Exception as e:
                return {"success": False, "message": str(e)}

    def get_all_telemetry_status(self, device_name: str, telemetry_name: str, time_range: str):
        from datetime import datetime, timedelta
        now = datetime.now()

        # Tính toán mốc thời gian bắt đầu
        if time_range == "1h":
            start_time = now - timedelta(hours=1)
        elif time_range == "1d":
            start_time = now - timedelta(days=1)
        elif time_range == "7d":
            start_time = now - timedelta(days=7)
        elif time_range == "30d":
            start_time = now - timedelta(days=30)
        else:
            start_time = now - timedelta(days=1)

        start_ms = int(start_time.timestamp() * 1000)
        end_ms = int(now.timestamp() * 1000)

        # IN RA ĐỂ XEM JAVASCRIPT GỬI XUỐNG CÁI GÌ
        print(f"\n[DEBUG DB] Đang tìm thiết bị: '{device_name}'", flush=True)
        print(f"[DEBUG DB] Thông số: '{telemetry_name}'", flush=True)

        with self.connect() as conn:
            cursor = conn.cursor()
            # ĐÃ LẮP TRẢ LẠI BỘ LỌC THỜI GIAN
            cursor.execute(
                """
                SELECT t.ts, t.value
                FROM telemetry t
                JOIN device d ON t.device_id = d.device_id
                WHERE d.device_name = ?
                  AND t.name = ?
                  AND t.ts BETWEEN ? AND ?
                ORDER BY t.ts ASC
                """,
                (device_name, telemetry_name, start_ms, end_ms)
            )
            rows = cursor.fetchall()
            
            print(f"[DEBUG DB] TÌM THẤY {len(rows)} DÒNG DỮ LIỆU (Chưa lọc thời gian)!", flush=True)

        # Ép kiểu dữ liệu về dạng Dict
        result = [{"ts": int(ts), "value": float(value)} for ts, value in rows]
        
        return result

    def get_users_with_notifications_enabled(self):
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT username 
                    FROM notification_management 
                    WHERE status = 'ON'
                """)
                results = cursor.fetchall()
                if results:
                    return [row[0] for row in results]
                return []
                
        except Exception as e:
            print(f"[DB ERROR] Lỗi lấy danh sách user nhận thông báo: {e}")
            return []

    def check_anomaly(self, username):
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 
                        telemetry.value, 
                        device.device_name, 
                        field.field_name,
                        telemetry.device_id,
                        device.field_id
                    FROM telemetry
                    JOIN device ON telemetry.device_id = device.device_id
                    JOIN field ON device.field_id = field.field_id
                    WHERE telemetry.name = 'anomaly_score'
                    ORDER BY telemetry.ts DESC
                    LIMIT 1
                """)    
                result = cursor.fetchone()
                
                if result:
                    score, device_name, field_name, device_id, field_id = result
                    cursor.execute("""
                        SELECT anomaly_score_low, anomaly_score_high 
                        FROM AI_management 
                        WHERE field_id = ?
                    """, (field_id,))
                    thresholds = cursor.fetchone()
                    
                    if not thresholds:
                        return {"success": False}
                        
                    low, high = thresholds
                    current_status = None
                    
                    if score >= high:
                        current_status = "CRITICAL"
                    elif score >= low:
                        current_status = "WARNING"
                    
                    if not current_status:
                        return {"success": False}
                    
                    # THAY ĐỔI Ở ĐÂY: Bổ sung điều kiện username = ? vào truy vấn
                    cursor.execute("""
                        SELECT ts, status 
                        FROM notification 
                        WHERE device_id = ? AND username = ? 
                        ORDER BY ts DESC 
                        LIMIT 1
                    """, (device_id, username)) # THAY ĐỔI Ở ĐÂY: Truyền thêm biến username
                    
                    last_notif = cursor.fetchone()
                    
                    if last_notif:
                        last_ts, last_status = last_notif
                        
                        if last_ts > 10000000000:
                            last_ts = last_ts / 1000
                            
                        current_ts = int(time.time())
                        
                        if (current_ts - last_ts) < 900 and current_status == last_status:
                            return {"success": False}
                            
                    return {
                        "success": True,
                        "anomaly_score": score,
                        "device_name": device_name,
                        "field_name": field_name,
                        "device_id": device_id
                    }

            return {"success": False}
            
        except Exception as e:
            return {"success": False, "message": str(e)}

    def get_all_schedulers(self):
        with self.connect() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    SELECT
                        s.scheduler_id,
                        s.field_id,
                        f.field_name,
                        s.device_id,
                        s.name,
                        s.event_date,
                        s.end_date,
                        s.event_time,
                        s.event_type,
                        s.mode,
                        s.duration,
                        s.consumption,
                        s.repeat_enabled,
                        s.type_repeat,
                        s.repeat_value,
                        s.enabled,
                        s.created_at
                    FROM scheduler s
                    JOIN field f
                        ON s.field_id = f.field_id
                    ORDER BY s.scheduler_id DESC
                """)
                rows = cursor.fetchall()
                schedulers = []
                for row in rows:
                    schedulers.append({
                        "scheduler_id": row[0],
                        "field_id": row[1],
                        "field_name": row[2],
                        "device_id": row[3],   
                        "name": row[4],
                        "event_date": row[5],
                        "end_date": row[6],
                        "event_time": row[7],
                        "event_type": row[8],
                        "mode": row[9],
                        "duration": row[10],
                        "consumption": row[11],
                        "repeat_enabled": bool(row[12]) if row[12] is not None else False,
                        "type_repeat": row[13],
                        "repeat_value": row[14],
                        "enabled": bool(row[15]) if row[15] is not None else False,
                        "created_at": row[16]
                    })

                return {
                    "success": True,
                    "data": schedulers
                }

            except Exception as e:

                return {
                    "success": True,
                    "data": rows
                }
            
    def get_schedulers_by_field_id(self, field_id):
        with self.connect() as conn:
            cursor = conn.cursor()
            try:
                # Dùng LEFT JOIN để móc nối lấy dc.device_name
                cursor.execute("""
                    SELECT
                        s.scheduler_id,
                        s.field_id,
                        f.field_name,
                        s.device_id,
                        s.name,
                        s.event_date,
                        s.end_date,
                        s.event_time,
                        s.event_type,
                        s.mode,
                        s.duration,
                        s.consumption,
                        s.repeat_enabled,
                        s.type_repeat,
                        s.repeat_value,
                        s.enabled,
                        s.created_at,
                        dc.device_name   -- ✔ THÊM CỘT TÊN THIẾT BỊ (Index 17)
                    FROM scheduler s
                    JOIN field f ON s.field_id = f.field_id
                    LEFT JOIN device_controller dc ON s.device_id = dc.device_id
                    WHERE s.field_id = ?
                    ORDER BY s.scheduler_id DESC
                """, (field_id,))

                rows = cursor.fetchall()
                schedulers = []

                for row in rows:
                    schedulers.append({
                        "scheduler_id": row[0],
                        "field_id": row[1],
                        "field_name": row[2],
                        "device_id": row[3],
                        "name": row[4],
                        "event_date": row[5],
                        "end_date": row[6],
                        "event_time": row[7],
                        "event_type": row[8],
                        "mode": row[9],
                        "duration": row[10],
                        "consumption": row[11],
                        "repeat_enabled": bool(row[12]) if row[12] is not None else False,
                        "type_repeat": row[13],
                        "repeat_value": row[14],
                        "enabled": bool(row[15]) if row[15] is not None else False,
                        "created_at": row[16],
                        "device_name": row[17] if row[17] else "Unknown" # ✔ GÁN TÊN VÀO JSON
                    })

                return {
                    "success": True,
                    "data": schedulers
                }

            except Exception as e:
                return {
                    "success": False,
                    "message": str(e)
                }

    def create_scheduler(
        self,
        field_id,
        device_id,   
        name,
        event_date,
        end_date,        
        event_time,
        event_type,
        mode,
        duration=None,
        consumption=None,
        repeat_enabled=False,
        type_repeat=None,
        repeat_value=None
    ):
        with self.connect() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO scheduler (
                        field_id,
                        device_id,
                        name,
                        event_date,
                        end_date,
                        event_time,
                        event_type,
                        mode,
                        duration,
                        consumption,
                        repeat_enabled,
                        type_repeat,
                        repeat_value,
                        enabled
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                """, (
                    field_id,
                    device_id,   
                    name,
                    event_date,
                    end_date,     
                    event_time,
                    event_type,
                    mode,
                    duration,
                    consumption,
                    int(repeat_enabled),
                    type_repeat,
                    repeat_value
                ))
                conn.commit()
                return {
                    "success": True,
                    "message": "Scheduler created successfully"
                }
            except Exception as e:
                return {
                    "success": False,
                    "message": str(e)
                }

    def delete_scheduler(self, scheduler_id):
        with self.connect() as conn:
            cursor = conn.cursor()

            try:

                cursor.execute("""
                    DELETE FROM scheduler
                    WHERE scheduler_id = ?
                """, (scheduler_id,))

                conn.commit()

                return {
                    "success": True,
                    "message": "Scheduler deleted successfully"
                }

            except Exception as e:

                return {
                    "success": False,
                    "message": str(e)
                }

    def update_scheduler(
        self,
        scheduler_id,
        field_id,
        device_id,   
        name,
        event_date,
        end_date,         # ✔ Thêm end_date
        event_time,
        event_type,
        mode,
        duration=None,
        consumption=None,
        repeat_enabled=False,
        type_repeat=None,
        repeat_value=None,
        enabled=True
    ):
        with self.connect() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    UPDATE scheduler
                    SET
                        field_id = ?,
                        device_id = ?,   
                        name = ?,
                        event_date = ?,
                        end_date = ?,
                        event_time = ?,
                        event_type = ?,
                        mode = ?,
                        duration = ?,
                        consumption = ?,
                        repeat_enabled = ?,
                        type_repeat = ?,
                        repeat_value = ?,
                        enabled = ?
                    WHERE scheduler_id = ?
                """, (
                    field_id,
                    device_id,   
                    name,
                    event_date,
                    end_date,     
                    event_time,
                    event_type,
                    mode,
                    duration,
                    consumption,
                    int(repeat_enabled),
                    type_repeat,
                    repeat_value,
                    int(enabled),
                    scheduler_id
                ))
                conn.commit()
                return {
                    "success": True,
                    "message": "Scheduler updated successfully"
                }
            except Exception as e:
                return {
                    "success": False,
                    "message": str(e)
                }
            
    def disable_scheduler(self, scheduler_id):
        with self.connect() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    UPDATE scheduler
                    SET enabled = 0
                    WHERE scheduler_id = ?
                """, (scheduler_id,))
                conn.commit()
                return {
                    "success": True,
                    "message": "Scheduler disabled successfully",
                    "scheduler_id": scheduler_id
                }
            except Exception as e:
                return {
                    "success": False,
                    "message": str(e)
                }

    def get_scheduler_id_by_name(self, name: str):
        with self.connect() as conn:
            cursor = conn.cursor()
            try:
                # Tìm kiếm lịch trình theo tên
                cursor.execute("""
                    SELECT scheduler_id 
                    FROM scheduler 
                    WHERE name = ?
                    LIMIT 1
                """, (name,))
                row = cursor.fetchone()
                if row:
                    return {
                        "success": True, 
                        "scheduler_id": row[0]
                    }
                else:
                    return {
                        "success": False, 
                        "message": f"Không tìm thấy lịch trình nào có tên '{name}'."
                    }
            except Exception as e:
                return {
                    "success": False, 
                    "message": f"Lỗi truy vấn: {str(e)}"
                }

    def get_device_controller_by_device_id(self, device_id):
        with self.connect() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    SELECT
                        device_id,
                        field_id,
                        type
                    FROM device_controller
                    WHERE device_id = ?
                    LIMIT 1
                """, (device_id,))
                row = cursor.fetchone()
                if not row:
                    return {
                        "success": False,
                        "message": "Device not found"
                    }
                return {
                    "success": True,
                    "data": {
                        "device_id": row[0],
                        "field_id": row[1],
                        "type": row[2]
                    }
                }
            except Exception as e:
                return {
                    "success": False,
                    "message": str(e)
                }
            
    def update_scheduler_date(self, scheduler_id, next_date, next_time):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE scheduler
                SET event_date = ?, event_time = ?
                WHERE scheduler_id = ?
            """, (next_date, next_time, scheduler_id))
            conn.commit()

    def get_device_sensor_mapping(self, device_id):
        try:
            with self.connect() as conn:
                cursor = conn.cursor()

                query = """
                SELECT 
                    device_id,
                    type,
                    sensor_id
                FROM device_controller
                WHERE device_id = ?
                LIMIT 1
                """

                cursor.execute(query, (device_id,))
                row = cursor.fetchone()

                if not row:
                    return {
                        "success": False,
                        "message": "Device not found"
                    }

                return {
                    "success": True,
                    "data": {
                        "device_id": row[0],
                        "type": row[1],
                        "sensor_id": row[2]
                    }
                }

        except Exception as e:
            return {
                "success": False,
                "message": str(e)
            }
            
    def get_new_telemetry(self, device_id, last_ts):
        with self.connect() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT ts, value, name
                FROM telemetry
                WHERE device_id = ?
                AND CAST(ts AS INTEGER) > ?
                ORDER BY ts ASC
            """, (device_id, last_ts))

            return cursor.fetchall()
        
    def get_max_ts(self, device_id):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT MAX(ts)
                FROM telemetry
                WHERE device_id = ?
            """, (device_id,))
            return cursor.fetchone()[0] or 0
        
    def create_billing_item(self, field_id, title, amount):
        with self.connect() as conn:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO billing_items (
                        field_id,
                        title,
                        amount
                    )
                    VALUES (?, ?, ?)
                """, (field_id, title, amount))
                conn.commit()
                return {
                    "success": True,
                    "message": "Tạo billing item thành công"
                }
            except Exception as e:
                conn.rollback()
                return {
                    "success": False,
                    "message": str(e)
                }

    def get_unpaid_bills(self, field_ids):   
        with self.connect() as conn:
            try:
                cursor = conn.cursor()

                if isinstance(field_ids, str):
                    field_ids = [field_ids]

                field_ids = [str(fid).strip() for fid in field_ids]

                if not field_ids:
                    return {
                        "success": True,
                        "message": "Không có field nào",
                        "data": []
                    }

                placeholders = ",".join(["?"] * len(field_ids))

                cursor.execute(f"""
                    SELECT *
                    FROM billing_items
                    WHERE field_id IN ({placeholders})
                    AND status = 'unpaid'
                    ORDER BY created_at DESC, id DESC
                """, field_ids)

                rows = cursor.fetchall()

                return {
                    "success": True,
                    "message": "Lấy unpaid bills thành công",
                    "data": rows
                }

            except Exception as e:
                return {
                    "success": False,
                    "message": str(e),
                    "data": []
                }

    def mark_bills_as_paid(self, field_ids):
        with self.connect() as conn:
            try:
                cursor = conn.cursor()
                if isinstance(field_ids, str):
                    field_ids = field_ids.split(",")
                field_ids = [
                    str(fid).strip()
                    for fid in field_ids
                    if str(fid).strip()
                ]

                if not field_ids:
                    return {
                        "success": False,
                        "message": "Danh sách field_ids rỗng"
                    }

                placeholders = ",".join(["?"] * len(field_ids))

                cursor.execute(f"""
                    UPDATE billing_items
                    SET
                        status = 'paid',
                        paid_at = CURRENT_TIMESTAMP
                    WHERE field_id IN ({placeholders})
                    AND status = 'unpaid'
                """, field_ids)

                conn.commit()

                return {
                    "success": True,
                    "message": "Cập nhật bill thành paid thành công",
                    "updated": cursor.rowcount
                }

            except Exception as e:
                conn.rollback()
                return {
                    "success": False,
                    "message": str(e)
                }

    def mark_bill_as_unpaid(self, bill_id):
        with self.connect() as conn:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE billing_items
                    SET
                        status = 'unpaid',
                        paid_at = NULL
                    WHERE id = ?
                """, (bill_id,))
                conn.commit()
                return {
                    "success": True,
                    "message": "Đánh dấu bill về unpaid thành công",
                    "data": {
                        "bill_id": bill_id
                    }
                }
            except Exception as e:
                conn.rollback()
                return {
                    "success": False,
                    "message": "Lỗi khi cập nhật bill",
                    "error": str(e)
                }

    def delete_billing_item(self, bill_id):
        with self.connect() as conn:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM billing_items
                    WHERE id = ?
                """, (bill_id,))
                conn.commit()
                return {
                    "success": True,
                    "message": "Xoá billing item thành công",
                    "data": {
                        "bill_id": bill_id
                    }
                }
            except Exception as e:
                conn.rollback()
                return {
                    "success": False,
                    "message": "Lỗi khi xoá billing item",
                    "error": str(e)
                }
            
    def create_transaction(self, user_id, field_id, order_id, request_id, amount, status="pending"):
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO payment_transactions (
                    user_id,
                    field_id,
                    order_id,
                    request_id,
                    amount,
                    status
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                field_id,
                order_id,
                request_id,
                amount,
                status
            ))
            conn.commit()
    
        
    def get_transaction_by_order_id(self, order_id):
        with self.connect() as conn:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT *
                    FROM payment_transactions
                    WHERE order_id = ?
                """, (order_id,))
                row = cursor.fetchone()
                return {
                    "success": True,
                    "message": "Lấy transaction thành công",
                    "data": row
                }
            except Exception as e:
                return {
                    "success": False,
                    "message": "Lỗi lấy transaction",
                    "error": str(e)
                }
            
    def update_transaction_status(self, order_id, status):
        with self.connect() as conn:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE payment_transactions
                    SET
                        status = ?,
                        paid_at = CURRENT_TIMESTAMP
                    WHERE order_id = ?
                """, (
                    status,
                    order_id
                ))
                conn.commit()
                return {
                    "success": True,
                    "message": "Cập nhật transaction thành công",
                    "data": {
                        "order_id": order_id,
                        "status": status
                    }
                }
            except Exception as e:
                conn.rollback()
                return {
                    "success": False,
                    "message": "Lỗi update transaction",
                    "error": str(e)
                }
            
    def save_response(self, order_id, raw_response):
        with self.connect() as conn:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE payment_transactions
                    SET raw_response = ?
                    WHERE order_id = ?
                """, (
                    str(raw_response),
                    order_id
                ))
                conn.commit()
                return {
                    "success": True,
                    "message": "Lưu response thành công"
                }
            except Exception as e:
                conn.rollback()
                return {
                    "success": False,
                    "message": "Lỗi lưu response",
                    "error": str(e)
                }
    
    def get_transactions_by_field(self, field_id):
        with self.connect() as conn:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT *
                    FROM payment_transactions
                    WHERE field_id = ?
                    ORDER BY created_at DESC
                """, (field_id,))

                rows = cursor.fetchall()
                return {
                    "success": True,
                    "message": "Lấy danh sách transaction",
                    "data": rows
                }
            except Exception as e:
                return {
                    "success": False,
                    "message": "Lỗi lấy transaction theo field",
                    "error": str(e)
                }
    
    def create_service_plan(self, field_id, service_days, daily_price):
        with self.connect() as conn:
            cursor = conn.cursor()
            start_date = datetime.now().date()
            expired_date = start_date + timedelta(days=int(service_days))
            cursor.execute("""
                INSERT INTO field_service_plan (
                    field_id,
                    service_days,
                    daily_price,
                    start_date,
                    expired_date,
                    accumulated_amount,
                    status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                field_id,
                service_days,
                daily_price,
                start_date,
                expired_date,
                0,
                "active"
            ))
            conn.commit()
            return {
                "success": True,
                "message": "Tạo gói dịch vụ thành công"
            }
        
    def update_service_plan(self, plan_id, service_days, daily_price):
        with self.connect() as conn:
            cursor = conn.cursor()

            start_date = datetime.now().date()
            expired_date = start_date + timedelta(days=int(service_days))

            cursor.execute("""
                UPDATE field_service_plan
                SET
                    service_days = ?,
                    daily_price = ?,
                    start_date = ?,
                    expired_date = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                service_days,
                daily_price,
                start_date,
                expired_date,
                plan_id
            ))
            conn.commit()
            return {
                "success": True,
                "message": "Cập nhật gói dịch vụ thành công"
            }
        
    def delete_service_plan(self, plan_id):
        with self.connect() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                DELETE FROM field_service_plan
                WHERE id = ?
            """, (plan_id,))

            conn.commit()

            return {
                "success": True,
                "message": "Xóa gói dịch vụ thành công"
            }
        
    def get_active_service_plans(self):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    id,
                    field_id,
                    service_days,
                    daily_price,
                    start_date,
                    expired_date,
                    accumulated_amount,
                    status
                FROM field_service_plan
                WHERE status = 'active'
            """)
            rows = cursor.fetchall()

        return [
            {
                "id": row[0],
                "field_id": row[1],
                "service_days": row[2],
                "daily_price": row[3],
                "start_date": row[4],
                "expired_date": row[5],
                "accumulated_amount": row[6],
                "status": row[7]
            }
            for row in rows
        ]
    
    def update_accumulated_amount(self, plan_id, amount):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE field_service_plan
                SET
                    accumulated_amount = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (amount, plan_id))
            conn.commit()

    def update_accumulated_amount(self, plan_id, amount):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE field_service_plan
                SET
                    accumulated_amount = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (amount, plan_id))
            conn.commit()

    def expire_service_plan(self, plan_id):
        with self.connect() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE field_service_plan
                SET
                    status = 'expired',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (plan_id,))

            conn.commit()

    def get_service_plans_by_fields(self, field_ids):
        with self.connect() as conn:
            try:
                cursor = conn.cursor()

                if not field_ids:
                    return {
                        "success": True,
                        "data": []
                    }

                placeholders = ",".join(["?"] * len(field_ids))

                cursor.execute(f"""
                    SELECT 
                        id,
                        field_id,
                        service_days,
                        daily_price,
                        start_date,
                        expired_date,
                        accumulated_amount,
                        status
                    FROM field_service_plan
                    WHERE field_id IN ({placeholders})
                    ORDER BY id DESC
                """, field_ids)

                rows = cursor.fetchall()

                return {
                    "success": True,
                    "data": [
                        {
                            "id": row[0],
                            "field_id": row[1],
                            "service_days": row[2],
                            "daily_price": row[3],
                            "start_date": row[4],
                            "expired_date": row[5],
                            "accumulated_amount": row[6],
                            "status": row[7]
                        }
                        for row in rows
                    ]
                }

            except Exception as e:
                return {
                    "success": False,
                    "message": str(e),
                    "data": []
                }
    
    def handle_anomaly_automation(self):
        print("\n[DEBUG] Đang chạy vòng lặp kiểm tra AI...", flush=True)
        actions = []
        try:
            with self.connect() as conn:
                cur = conn.cursor()
                cur.execute("SELECT DISTINCT field_id FROM AI_management WHERE LOWER(AI_automation) = 'on'")
                active_fields = [r[0] for r in cur.fetchall()]

            print(f"[DEBUG] Số ruộng đang BẬT AI: {len(active_fields)} -> Danh sách: {active_fields}", flush=True)

            if not active_fields:
                return actions

            for field_id in active_fields:
                with self.connect() as conn:
                    cur = conn.cursor()

                    cur.execute("SELECT anomaly_score_high FROM AI_management WHERE field_id = ?", (field_id,))
                    row_threshold = cur.fetchone()
                    if not row_threshold:
                        print(f"[DEBUG] Lỗi: Không tìm thấy anomaly_score_high của ruộng {field_id}", flush=True)
                        continue
                    high_threshold = float(row_threshold[0])

                    cur.execute("""
                        SELECT telemetry.value
                        FROM telemetry
                        JOIN device ON telemetry.device_id = device.device_id
                        WHERE telemetry.name = 'anomaly_score' AND device.field_id = ?
                        ORDER BY telemetry.ts DESC LIMIT 1
                    """, (field_id,))
                    row_anomaly = cur.fetchone()

                    if not row_anomaly:
                        print(f"[DEBUG] CẢNH BÁO: Ruộng {field_id} CHƯA CÓ dữ liệu anomaly_score!", flush=True)
                        continue

                    current_score = float(row_anomaly[0])

                print(f"[QUÉT AI] Ruộng {field_id} | Điểm dị thường: {current_score} / Ngưỡng: {high_threshold}", flush=True)

                if current_score < high_threshold:
                    print(f"   -> AI đánh giá AN TOÀN. Bỏ qua.", flush=True)
                    continue

                print(f"[BÁO ĐỘNG ĐỎ] Ruộng {field_id} vượt ngưỡng CRITICAL! Quét cảm biến...", flush=True)

                devices = self.get_device_names(field_id)
                for device_name in devices:
                    latest_data = self.get_telemetry(device_name)
                    if not latest_data or device_name not in latest_data:
                        continue

                    telemetries = latest_data[device_name]

                    if "moisture" in telemetries and float(telemetries["moisture"]["value"]) < 40.0:
                        actions.append({"field_id": field_id, "target_type": "moisture", "action": "increase"})

                    if "temperature" in telemetries:
                        temp = float(telemetries["temperature"]["value"])
                        if temp > 35.0:
                            actions.append({"field_id": field_id, "target_type": "temperature", "action": "decrease"})
                        elif temp < 15.0:
                            actions.append({"field_id": field_id, "target_type": "temperature", "action": "increase"})
        except Exception as e:  
            print(f"\n[LỖI CRASH HỆ THỐNG AUTO] {str(e)}\n", flush=True)
        print(actions)
        return actions
    
    def get_all_bills(self):
        with self.connect() as conn:
            try:
                cur = conn.cursor()

                cur.execute("""
                    SELECT 
                        id, 
                        field_id, 
                        title, 
                        amount, 
                        status, 
                        created_at, 
                        paid_at
                    FROM billing_items
                    ORDER BY created_at DESC, id DESC
                """)

                rows = cur.fetchall()

                data = []
                for r in rows:
                    data.append({
                        "id": r[0],
                        "field_id": r[1],
                        "title": r[2],
                        "amount": r[3],
                        "status": r[4],
                        "created_at": r[5],
                        "paid_at": r[6]
                    })

                return {
                    "success": True,
                    "data": data
                }

            except Exception as e:
                return {
                    "success": False,
                    "message": str(e),
                    "data": []
                }