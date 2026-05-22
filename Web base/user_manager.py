import sqlite3
import hashlib
import datetime
import config 
import json

class UserManager:
    def __init__(self, user_db_path = config.user_db_path):
        self.user_db_path = user_db_path

    def connect(self):
        return sqlite3.connect(self.user_db_path)

    def add_user(self, username: str, password: str, email: str, role="user"):
        hashed = hashlib.sha256(password.encode()).hexdigest()
        now = datetime.datetime.now().isoformat()
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO user_data (username, password, email, role, is_online, last_active)
                VALUES (?, ?, ?, ?, 0, ?)
            """, (username, hashed, email, role, now))
            conn.commit()

    def delete_user(self, username: str):
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM user_data WHERE username = ?", (username,))

    def find_user(self, username: str):
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM user_data WHERE username = ?", (username,))
            return cur.fetchone() is not None

    def get_password(self, username: str):
        return self.get_field(username, "password")
    
    def set_password(self, username, hashed_password):
        conn = sqlite3.connect(self.user_db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE user_data SET password = ? WHERE username = ?", (hashed_password, username))
        conn.commit()
        conn.close()
            
    def get_role(self, username: str):
        return self.get_field(username, "role")

    def get_status(self, username: str, is_online=True):
        status = self._get_field(username, "is_online")
        return bool(status) if status is not None else None
    
    def set_status(self, username: str, is_online=True):
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE user_data SET is_online = ? WHERE username = ?", (int(is_online), username))

    def get_last_active(self, username: str):
        return self._get_field(username, "last_active")

    def set_last_active(self, username: str):
        now = datetime.datetime.now().isoformat()
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE user_data SET last_active = ? WHERE username = ?", (now, username))
            
    def get_all_usernames(self):
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT username FROM user_data")
            rows = cur.fetchall()
        return [row[0] for row in rows]
    
    def find_email(self, email: str):
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT username FROM user_data WHERE email = ? LIMIT 1", (email,))
            result = cur.fetchone()
        return result[0] if result else False
    
    def get_email_by_username(self, username: str):
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT email FROM user_data WHERE username = ? LIMIT 1", (username,))
            result = cur.fetchone()
        return result[0] if result else None

    def set_email(self, old_email: str, new_email: str):
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE user_data SET email = ? WHERE email = ?", (new_email, old_email))
            conn.commit()

    def get_field(self, username: str, field):
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute(f"SELECT {field} FROM user_data WHERE username = ?", (username,))
            result = cur.fetchone()
            return result[0] if result else None

    def add_otp(self, email: str, otp, expires_at):
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO otp_codes (email, otp, expires_at, used)
                VALUES (?, ?, ?, 0)
                ON CONFLICT(email) DO UPDATE SET
                    otp = excluded.otp,
                    expires_at = excluded.expires_at,
                    used = 0
            """, (email, otp, expires_at))
            conn.commit()
            
    def get_otp(self, email: str):
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT otp FROM otp_codes
                WHERE email = ? AND used = 0
                ORDER BY expires_at DESC LIMIT 1
            """, (email,))
            result = cur.fetchone()

        return result[0] if result else None
    
    def get_otp_used(self, otp):
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT used FROM otp_codes
                WHERE otp = ?
                ORDER BY expires_at DESC LIMIT 1
            """, (otp,))
            result = cur.fetchone()

        return bool(result[0]) if result else None

    def set_otp_used(self, otp: str):
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE otp_codes SET used = 1
                WHERE otp = ? AND used = 0
            """, (otp,))
            conn.commit()
            
    def get_expire(self, otp: str):
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT expires_at FROM otp_codes
                WHERE otp = ?
                ORDER BY expires_at DESC LIMIT 1
            """, (otp,))
            result = cur.fetchone()

        return result[0] if result else None

    def get_all_user_information(self):
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, username, email, role FROM user_data")
            rows = cur.fetchall()

        # Trả về danh sách dict để dễ dùng hơn
        return [
            {
                "user_id": row[0],
                "username": row[1],
                "email": row[2],
            }
            for row in rows
        ]
    
    def get_username(self, user_id: int):
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT username FROM user_data WHERE id = ?", (user_id,))
            result = cur.fetchone()
        return result[0] if result else None
    
    def get_user_id(self, username: str):
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM user_data WHERE username = ?", (username,))
            result = cur.fetchone()
        return result[0] if result else None

    def save_payment_history(self, user_id, field_id, order_id, request_id, amount, bills, raw_response=None):
        with self.connect() as conn:
            cur = conn.cursor()

            cur.execute("""
                INSERT INTO user_payment_transactions (
                    user_id,
                    field_id,
                    order_id,
                    request_id,
                    amount,
                    status,
                    raw_response,
                    paid_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                user_id,
                field_id,
                order_id,
                request_id,
                amount,
                "success",
                json.dumps(raw_response)
            ))

            transaction_id = cur.lastrowid

            for bill in bills:
                cur.execute("""
                    INSERT INTO user_payment_transaction_items (
                        transaction_id,
                        billing_title,
                        billing_amount
                    )
                    VALUES (?, ?, ?)
                """, (
                    transaction_id,
                    bill[2],
                    bill[3]
                ))

            conn.commit()

    def get_transaction_detail_by_user_id(self, user_id):
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT 
                    id,
                    user_id,
                    field_id,
                    order_id,
                    request_id,
                    amount,
                    status,
                    raw_response,
                    created_at,
                    paid_at
                FROM user_payment_transactions
                WHERE user_id = ?
                ORDER BY created_at DESC
            """, (user_id,))

            rows = cur.fetchall()

            transactions = []

            for row in rows:
                transactions.append({
                    "transaction_id": row[0],
                    "user_id": row[1],
                    "field_id": row[2],
                    "order_id": row[3],
                    "request_id": row[4],
                    "amount": row[5],
                    "status": row[6],
                    "raw_response": row[7],
                    "created_at": row[8],
                    "paid_at": row[9]
                })

            return transactions
        
    def get_transaction_items(self, transaction_id):
        with self.connect() as conn:
            cur = conn.cursor()

            cur.execute("""
                SELECT 
                    id,
                    billing_title,
                    billing_amount
                FROM user_payment_transaction_items
                WHERE transaction_id = ?
            """, (transaction_id,))

            rows = cur.fetchall()

            items = [
                {
                    "item_id": r[0],
                    "title": r[1],
                    "amount": r[2]
                }
                for r in rows
            ]

            return items