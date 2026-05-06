import paho.mqtt.client as mqtt
import time, json, config

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected successfully!!")
    else:
        print("Connection failed with code", rc)

def send_state(field_id: int, new_state: str):
    client = mqtt.Client("DEVICE_CONTROLLER")
    client.username_pw_set(config.ACCESS_TOKEN)
    client.on_connect = on_connect
    client.connect(config.BROKER_ADDRESS, config.PORT, 60)
    client.loop_start()

    payload = {
        f"SI Field {field_id}": {
            "state": new_state
        }
    }
    client.publish("v1/devices/me/telemetry", json.dumps(payload), qos=1)
    print(f"Published {new_state}:", payload)

    time.sleep(1)
    client.disconnect()

