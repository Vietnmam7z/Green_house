import requests
import time

url = "https://app.coreiot.io/api/plugins/telemetry/DEVICE/2a5293c0-ce91-11f0-b238-bd8a9470eef2/values/timeseries"
headers = {"Authorization": f"Bearer eyJhbGciOiJIUzUxMiJ9.eyJzdWIiOiJ0aGVpbnNwaXJlcjIwMDRAZ21haWwuY29tIiwidXNlcklkIjoiNzBjMWZmNDAtYzUyMS0xMWYwLWE1NjItZDk2MzlmMDI1Njg0Iiwic2NvcGVzIjpbIlRFTkFOVF9BRE1JTiJdLCJzZXNzaW9uSWQiOiJmMjU2N2FiNS04MTEyLTQ1ZDEtOWY0OS1mMmRhNDdkMjczY2EiLCJleHAiOjE3NjYyMzI5NTksImlzcyI6InRoaW5nc2JvYXJkLmNsb3VkIiwiaWF0IjoxNzY2MjA0MTU5LCJmaXJzdE5hbWUiOiJJbnNwaXJlciIsImVuYWJsZWQiOnRydWUsImlzUHVibGljIjpmYWxzZSwiaXNCaWxsaW5nU2VydmljZSI6ZmFsc2UsInByaXZhY3lQb2xpY3lBY2NlcHRlZCI6dHJ1ZSwidGVybXNPZlVzZUFjY2VwdGVkIjp0cnVlLCJ0ZW5hbnRJZCI6IjcwOGZmMmMwLWM1MjEtMTFmMC1hNTYyLWQ5NjM5ZjAyNTY4NCIsImN1c3RvbWVySWQiOiIxMzgxNDAwMC0xZGQyLTExYjItODA4MC04MDgwODA4MDgwODAifQ.dU4_FDwuzfmYv1O_-TKhuwHnZuNW03abD1zfdFKMupSv2ehZfWNCfD0c-jPgIQbOinW4RBwiILkgc5OFdVqW8A"}


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

def get_sensor_value(key: str):
    response = requests.get(url, headers=headers)
    data = response.json()
    # battery = read_sensor_value(data, "battery")
    # print(battery)
    value_to_get = read_sensor_value(data, key)
    return value_to_get
