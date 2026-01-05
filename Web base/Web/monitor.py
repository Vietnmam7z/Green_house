from flask import Blueprint,render_template,jsonify
import random
import read_value
monitor = Blueprint('monitor',__name__)

@monitor.route('/')
def home():
    return render_template("monitor.html")

@monitor.route('/api/data')
def get_data():
    while(1):
        fake_temp = round(random.uniform(10.0, 45.0), 1)
        fake_humid = random.randint(30, 100)
        fake_light = random.randint(100, 500)
        soil_moisture = read_value.get_sensor_value("moisture")
        return jsonify({
            "temperature": fake_temp,
            "humidity": fake_humid,
            "light": fake_light,
            "soil_moisture": soil_moisture
    })