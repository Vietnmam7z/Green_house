from mistralai import Mistral
from prompts import EditPrompts
import json
import config  
import os
import sqlite3

# Sử dụng SQLite để lưu trữ vĩnh viễn các đoạn chat.
class ChatHistoryManager:
    def __init__(self, db_path=config.db_path):
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_box (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                role TEXT CHECK(role IN ('user', 'assistant')) NOT NULL,
                content TEXT NOT NULL
            )
        """)
        self.conn.commit()

    # Lấy toàn bộ lịch sử trò chuyện của một username cụ thể, sắp xếp theo thứ tự thời gian.
    def get_history(self, username: str) -> list:
        cursor = self.conn.execute(
            "SELECT role, content FROM chat_box WHERE username = ? ORDER BY id ASC",
            (username,)
        )
        return [{"role": row[0], "content": row[1]} for row in cursor.fetchall()]

    # Thêm một dòng tin nhắn mới (của người dùng hoặc của AI) vào cơ sở dữ liệu.
    def add_message(self, username: str, role: str, content: str):
        self.conn.execute(
            "INSERT INTO chat_box (username, role, content) VALUES (?, ?, ?)",
            (username, role, content)
        )
        self.conn.commit()

    # Xóa toàn bộ lịch sử chat của một người dùng khi cần "reset" lại cuộc trò chuyện.
    def clear_message(self, username: str):
        self.conn.execute("DELETE FROM chat_box WHERE username = ?", (username,))
        self.conn.commit()

        
# Quản lý kết nối tới Mistral AI và xử lý luồng tin nhắn.
class Mistral_API: 
    def __init__(self, api_key: str = config.api_key, model: str = config.model_small , json_path: str = config.json_path):
        self.api_key = api_key
        self.model = model
        self.json_path = json_path
        self.client = Mistral(api_key=self.api_key)

    # Cho phép chuyển đổi qua lại giữa các phiên bản model lớn/nhỏ (model_medium, model_small) tùy vào nhu cầu cần phản hồi nhanh hay cần suy luận phức tạp.
    def model_medium(self):
        self.model = config.model_medium

    def model_small(self):
        self.model = config.model_small
        
    def send_message(self, prompt: str, username: str, history_manager: ChatHistoryManager) -> dict:
        try:
            messages = history_manager.get_history(username)[-20:]  # Tải lịch sử chat của người dùng

            messages.append({"role": "user", "content": prompt})    # Nối thêm câu hỏi mới (prompt) của người dùng vào danh sách.

            response = self.client.chat.complete(                   # Gửi toàn bộ danh sách ngữ cảnh này lên Mistral AI để xin câu trả lời.
                model=self.model,
                messages=messages
            )

            reply = response.choices[0].message.content

            history_manager.add_message(username, "user", prompt)   # Lưu lại cả câu hỏi của người dùng và câu trả lời của AI vào database để làm dữ liệu cho các câu hỏi tiếp theo.
            history_manager.add_message(username, "assistant", reply)

            return {"message": reply}

        except Exception as e:
            return {"message": f"Lỗi khi gọi API: {str(e)}"}


