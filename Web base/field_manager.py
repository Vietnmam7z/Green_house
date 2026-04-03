import sqlite3
import json
import config 
from datetime import datetime, timedelta

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

            conn.commit()
            return {"success": True, "message": "Thêm ruộng thành công."}
                            
    def get_fields(self, username: str):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT f.field_id, f.field_name
                FROM field_user fu
                JOIN field f ON fu.field_id = f.field_id
                WHERE fu.username = ?
            """, (username,))
            return [{"field_id": row[0], "field_name": row[1]} for row in cursor.fetchall()]
        
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
            cursor.execute("DELETE FROM field WHERE field_id = ?", (field_id,))
            conn.commit()

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
                    WHERE device_id = t.device_id AND name = t.name
                )
                """,
                (device_name,)
            )

            rows = cursor.fetchall()
            telemetry_dict = {}
            for name, ts, value in rows:
                telemetry_dict[name] = {"ts": ts, "value": value}

            return {device_name: telemetry_dict}

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

    def get_anomoly_score_low(self, field_id: str):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT anomoly_score_low
                FROM AI_management
                WHERE field_id = ?
            """, (field_id,))
            return [row[0] for row in cursor.fetchall()]

    def get_anomoly_score_high(self, field_id: str):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT anomoly_score_high
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

    def get_anomoly_status(self, field_id: str):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT anomoly_status
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

    def get_anomoly_prediction_status(self, field_id: str):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT anomoly_prediction_status
                FROM AI_management
                WHERE field_id = ?
            """, (field_id,))
            return [row[0] for row in cursor.fetchall()]

    def set_anomoly_score_low(self, field_id: str, value: float):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE AI_management
                SET anomoly_score_low = ?
                WHERE field_id = ?
            """, (value, field_id))
            conn.commit()

    def set_anomoly_score_high(self, field_id: str, value: float):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE AI_management
                SET anomoly_score_high = ?
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

    def set_anomoly_status(self, field_id: str, value: str):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE AI_management
                SET anomoly_status = ?
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

    def set_anomoly_prediction_status(self, field_id: str, value: str):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE AI_management
                SET anomoly_prediction_status = ?
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
                        anomoly_score_low,
                        anomoly_score_high,
                        step,
                        anomoly_status,
                        prediction_status,
                        anomoly_prediction_status
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
                    INSERT INTO notification_management (status, username)
                    VALUES (?, ?)
                """, ("OFF", username))
                conn.commit()
                return {"success": True, "message": "Tạo notification_management thành công"}
            except Exception as e:
                conn.rollback()
                return {"success": False, "message": str(e)}
    
    def get_notification_status(self, username: str):
        with self.connect() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    SELECT status
                    FROM notification_management
                    WHERE username = ?
                """, (username,))
                row = cursor.fetchone()
                
                if row:
                    return {"status": row[0]}

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


