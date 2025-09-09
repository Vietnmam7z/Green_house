import json
from mistralai import Mistral
import config  
from prompts import EditPrompts

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
        
    def send_message(self, prompt: str) -> dict:
        try:
            response = self.client.chat.complete(
                model= self.model,
                messages = [
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ]
            )
            return {"message": response.choices[0].message.content}
        except Exception as e:
            return {"message": f"Lỗi khi gọi API: {str(e)}"}



