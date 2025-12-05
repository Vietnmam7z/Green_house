from mistralai import Mistral
from prompts import EditPrompts
import json
import config  
import os
import sqlite3

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

    def get_history(self, username: str) -> list:
        cursor = self.conn.execute(
            "SELECT role, content FROM chat_box WHERE username = ? ORDER BY id ASC",
            (username,)
        )
        return [{"role": row[0], "content": row[1]} for row in cursor.fetchall()]

    def add_message(self, username: str, role: str, content: str):
        self.conn.execute(
            "INSERT INTO chat_box (username, role, content) VALUES (?, ?, ?)",
            (username, role, content)
        )
        self.conn.commit()

    def clear_message(self, username: str):
        self.conn.execute("DELETE FROM chat_box WHERE username = ?", (username,))
        self.conn.commit()

        

class Mistral_API:
    def __init__(self, api_key: str = config.api_key, model: str = config.model_small , json_path: str = config.json_path):
        self.api_key = api_key
        self.model = model
        self.json_path = json_path
        self.client = Mistral(api_key=self.api_key)

    def model_medium(self):
        self.model = config.model_medium

    def model_small(self):
        self.model = config.model_small
        
    def send_message(self, prompt: str, username: str, history_manager: ChatHistoryManager) -> dict:
        try:
            messages = history_manager.get_history(username)[-20:]

            messages.append({"role": "user", "content": prompt})

            response = self.client.chat.complete(
                model=self.model,
                messages=messages
            )

            reply = response.choices[0].message.content

            history_manager.add_message(username, "user", prompt)
            history_manager.add_message(username, "assistant", reply)

            return {"message": reply}

        except Exception as e:
            return {"message": f"Lỗi khi gọi API: {str(e)}"}


