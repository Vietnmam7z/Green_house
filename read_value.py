import requests
import time

url = "https://app.coreiot.io/api/plugins/telemetry/DEVICE/21aa2280-9320-11f0-a934-bb34844744f7/values/timeseries"
headers = {"Authorization": f"Bearer eyJhbGciOiJIUzUxMiJ9.eyJzdWIiOiJHZW5raTQwMDBAZ21haWwuY29tIiwidXNlcklkIjoiZWMzNDU3MTAtNDczNC0xMWYwLWFhNzItYWZjN2ZhMjI3Mjk5Iiwic2NvcGVzIjpbIlRFTkFOVF9BRE1JTiJdLCJzZXNzaW9uSWQiOiI3NGRlNTRlYy01YWNhLTQxNDAtOTI0NC03Y2NhOWVmMmQ5ZTQiLCJleHAiOjE3NTg4NzE2NDUsImlzcyI6ImNvcmVpb3QuaW8iLCJpYXQiOjE3NTg4NjI2NDUsImZpcnN0TmFtZSI6IlRydW5nIE7DtG5nIiwiZW5hYmxlZCI6dHJ1ZSwiaXNQdWJsaWMiOmZhbHNlLCJ0ZW5hbnRJZCI6ImVjMTEzZWIwLTQ3MzQtMTFmMC1hYTcyLWFmYzdmYTIyNzI5OSIsImN1c3RvbWVySWQiOiIxMzgxNDAwMC0xZGQyLTExYjItODA4MC04MDgwODA4MDgwODAifQ.8Tr12DiXuZa7DZe7-2Spekf2pSrrKdra_DRjTI2FwBSwWatJ7AQ4TsxA29md6u5l81Wouz9lcHDmLZXsygLqQQ"}


def read_sensor_value(data: dict, key: str):
    try:
        if key in data and len(data[key]) > 0:
            value = float(data[key][0]["value"])
            return value
        else:
            print(f"Không có dữ liệu cho '{key}'.")
            return None
    except Exception as e:
        print(f"Lỗi khi xử lý '{key}': {str(e)}")
        return None


while True:
    response = requests.get(url, headers=headers)
    data = response.json()
    battery = read_sensor_value(data, "battery")
    print(battery)
    time.sleep(1)