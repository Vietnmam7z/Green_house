import config
import requests

class Sensor_API:
    def __init__(self):
        pass
    
    def update(self):
        try:
            response = requests.get(config.api_sensor)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Lỗi khi gọi API: {e}")
            return None

    def find_id(self, data):
        return data.get("id") if isinstance(data, dict) else None
         
    def delete(self, item):
        try:
            url = f"{config.api_sensor}/{item}"
            response = requests.delete(url)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"Lỗi khi gọi API DELETE cho {item}: {e}")
            return None
        




