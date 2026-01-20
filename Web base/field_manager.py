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
        
    def find_username(self, field_id: str, username: str):
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
            cursor.execute("""
                INSERT INTO field_user (field_id, username)
                VALUES (?, ?)
            """, (field_id, username))
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


