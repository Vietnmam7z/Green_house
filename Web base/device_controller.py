import paho.mqtt.client as mqtt
import time, json, config

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected successfully!!")
    else:
        print("Connection failed with code", rc)

def send_state(field_id: str, new_state: str, device_type: str):
    field_num = int(field_id)

    client = mqtt.Client("DEVICE_CONTROLLER")
    client.username_pw_set(config.ACCESS_TOKEN)
    client.on_connect = on_connect
    client.connect(config.BROKER_ADDRESS, config.PORT, 60)
    client.loop_start()

    payload = {
        f"{device_type}{field_num}": {
            "field": f"SI Field {field_num}",
            "state": new_state,
            "type": device_type
        }
    }

    client.publish("v1/devices/me/telemetry", json.dumps(payload), qos=1)
    print(f"Published {new_state} for {device_type}{field_num}:", payload)

    time.sleep(1)
    client.disconnect()

def send_device_command(field_id: str, device_type: int, state: str):
    print("[DEBUG CALL]", field_id, device_type, state)
    field_num = int(field_id)

    client = mqtt.Client("DEVICE_CONTROLLER")
    client.username_pw_set(config.ACCESS_TOKEN)
    client.on_connect = on_connect
    client.connect(config.BROKER_ADDRESS, config.PORT, 60)
    client.loop_start()

    payload = {
        f"{device_type}{field_num}": {
            "field": f"SI Field {field_num}",
            "state": state,
            "type": device_type
        }
    }
    client.publish(
        "v1/devices/me/telemetry",
        json.dumps(payload),
        qos=1
    )
    print(f"[MQTT] {state} sent:", payload)
    time.sleep(1)
    client.disconnect()