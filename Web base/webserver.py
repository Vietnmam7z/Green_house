from flask import Flask, request, session
from datetime import timedelta
import socket
import config 
import os

class FlaskServer:
    def __init__(self):
        self.app = Flask(__name__, template_folder=config.template_folder, static_folder=config.static_folder)
        self.app.secret_key = os.urandom(24)
        self.app.permanent_session_lifetime = timedelta(days=1)
        self.routes = []

    def add_route(self, path, handler, methods=['GET']):
        self.app.add_url_rule(path, view_func=handler, methods=methods)

    def run(self, host='0.0.0.0', port=80):
        hostname = socket.gethostname()
        ip_address = socket.gethostbyname(hostname)
        print(f"Hostname: {hostname}")
        print(f"IP Address: {ip_address}")
        print(f"Server đang chạy tại http://{ip_address}:{port}")
        self.app.run(
            host=host,
            port=port,
            debug=True
        )
