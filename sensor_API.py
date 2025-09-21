import config

class Sensor_API:
    def __init__(self):
        self.token = ""
        self.urls = []
        self.header ={}

    def get_token(self) -> str:
        return self.token

    def set_token(self, value: str):
        self.token = value.strip()

    def get_urls(self):
        return self.urls

    def get_headers(self) -> str:
        return self.headers

    def update(self, device_ids):
        self.urls = []
        self.headers = {"Authorization": f"{self.token}"}

        for device_id in device_ids:
            url = f"https://app.coreiot.io/api/plugins/telemetry/DEVICE/{device_id}/values/timeseries"
            self.urls.append(url)
            
    def read_all_sensor_values(self, data: dict) -> dict:
        result = {}
        try:
            for key, values in data.items():
                if isinstance(values, list) and len(values) > 0:
                    try:
                        value = float(values[0]["value"])
                        result[key] = value
                    except Exception as inner_e:
                        print(f"Không đọc được giá trị cho '{key}': {str(inner_e)}")
                        result[key] = None
                else:
                    print(f"Không có dữ liệu cho '{key}'")
                    result[key] = None
            return result
        except Exception as e:
            print(f"Lỗi khi đọc dữ liệu telemetry: {str(e)}")
            return {}