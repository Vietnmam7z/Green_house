import sqlite3
import json
import config 

class FieldDB:
    def __init__(self, field_db_path = config.field_db_path):
        self.field_db_path = field_db_path

    def connect(self):
        conn = sqlite3.connect(self.field_db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    
    def add_field(self, field_id: str, username: str):
        with self.connect() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT 1 FROM field WHERE field_id = ?", (field_id,))
            if cursor.fetchone():
                return {"success": False, "message": "Ruộng đã tồn tại."} 

            cursor.execute("INSERT INTO field (field_id) VALUES (?)", (field_id,))
         
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
                SELECT field_id FROM field_user
                WHERE username = ?
            """, (username,))
            return [row[0] for row in cursor.fetchall()]

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
            
    def get_device_ids(self, field_id: int):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT device_id
                FROM device
                WHERE field_id = ?
                """,
                (field_id,)
            )
            return [row[0] for row in cursor.fetchall()]
        
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

    def get_device_name_by_id(self, device_id: str) -> str:
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT device_name
                FROM device
                WHERE device_id = ?
            """, (device_id,))
            row = cursor.fetchone()
            return row[0] if row else None

    def get_field_by_device_name(self, device_name: str) -> str:
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT field_id
                FROM device
                WHERE device_name = ?
            """, (device_name,))
            row = cursor.fetchone()
            return row[0] if row else None

    def insert_telemetry(self, data: dict):
        device_id = data.get("device")   
        ts = data.get("ts")
        telemetry = data.get("telemetry", {})

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

    def get_all_telemetry_status(self, device_name: str, telemetry_name: str):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT t.ts, t.value
                FROM telemetry t
                JOIN device d ON t.device_id = d.device_id
                WHERE d.device_name = ? AND t.name = ?
                ORDER BY t.ts ASC
                """,
                (device_name, telemetry_name)
            )

            rows = cursor.fetchall()
            result = [{ "ts": ts, "value": value } for ts, value in rows]
            return result





