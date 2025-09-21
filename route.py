from dataclasses import Field
from flask import request, session, redirect, render_template, jsonify
from datetime import datetime, timedelta
from authentication import Authentication
from email_otp import OTPManager
from sensor_API import Sensor_API
from field_manager import FieldDB
import requests
import config

class Routes:
    def __init__(self, auth: Authentication, otp: OTPManager, sensor: Sensor_API, field: FieldDB):
        self.auth = auth
        self.otp = otp
        self.sensor = sensor
        self.field = field
        
    def require_login(self):
        if 'username' not in session:
            return redirect('/login')
        
    def redirect_if_logged_in(self):
        if 'username' in session:
            return redirect('/')   

    def reset_password_page(self):
        username = session.get('username')
        if not session.get(f"{username}_allow_reset"):
            return redirect('/forgot-password')  

    def pop_reset_session(self):
        username = session.get('username')
        session.pop(f"{username}_allow_reset", None)

# HOME PAGE
################################################################################################################################        
        
    def home_page(self):
        if self.require_login():
            return self.require_login() 
        username = session.get('username')
        return render_template(config.home_page, username=username)
    
    def logout(self):
        username = session.get('username')
        self.auth.logout_user(username)
        if username:
            session.pop('username', None)
            return jsonify({
                "success": True,
                "redirect": "/login"
            })
        else:
            return jsonify({
                "success": False,
                "message": "Không tìm thấy người dùng trong session"
            })
            
################################################################################################################################
    
 # LOGIN PAGE   
    def login_page(self):
        if self.redirect_if_logged_in():
            return self.redirect_if_logged_in()
        else:
            return render_template(config.login_page)

    def login(self):
        username = request.form.get('username')
        password = request.form.get('password')
        result = self.auth.login_user(username, password)

        if result['success']:
            session['username'] = username
            return jsonify({
                "success": result['success'],
                "message": result['message'],
                "role": self.auth.get_role(username),
                "redirect": "/"
            })
    
        else:
            return jsonify({
                "success": result['success'],
                "message": result['message']
            })

#################################################################################################################################
        
 # SIGNUP PAGE   
    def signup_page(self):
        if self.redirect_if_logged_in():
            return self.redirect_if_logged_in()
        else:
            return render_template(config.signup_page)

    def signup(self):
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')
        
        result = self.auth.register_user(username, password, email)

        if result['success']:
            return jsonify({
                "success": result['success'],
                "message": result['message'],
                "redirect": "/login"
            })
    
        else:
            return jsonify({
                "success": result['success'],
                "message": result['message']
            })

#################################################################################################################################

 # FORGOT PASSWORD PAGE
    def forgot_password_page(self):
        if self.redirect_if_logged_in():
            return self.redirect_if_logged_in()
        else:
            return render_template(config.forgot_password_page)

    def forgot_password(self, OTP: str):
        username = session.get('username')
        session[f"{username}_allow_reset"] = (datetime.utcnow() + timedelta(minutes=15)).timestamp()
        result = self.otp.confirm_otp(OTP, username)
        
        if result['success']:
            return jsonify({
                "success": result['success'],
                "message": result['message'],
                "redirect": "/reset-password"
            })
    
        else:
            return jsonify({
                "success": result['success'],
                "message": result['message']
            })
#################################################################################################################################

 # SEND OTP PAGE
    def reset_password_page(self):
        if self.redirect_if_logged_in():
            return self.redirect_if_logged_in()
        else:
            return render_template(config.reset_password_page)
        
        
    def reset_password(self):
        username = session.get('username')
        expire_at = session.get(f"{username}_allow_reset")
        if not expire_at or datetime.utcnow().timestamp() > expire_at:
            self.pop_reset_session()
            return jsonify({
                "success": False,
                "message": "Hết thời gian đổi mật khẩu"
            })            
        new_password = request.form.get('new_password')
        
        result = self.auth.reset_password(username, new_password)

        if result['success']:
            self.pop_reset_session()
            return jsonify({
                "success": result['success'],
                "message": result['message'],
                "redirect": "/login"
            })
    
        else:
            return jsonify({
                "success": result['success'],
                "message": result['message']
            })
        
#################################################################################################################################

 # DASHBOARD_PAGE
    def add_field(self):
        field_id =  request.form.get("field_id")
        username = session.get('username')
        result = self.field.add_field(field_id, username)

        if result:
            return jsonify({
                "success": result['success'],
                "message": result['message'],
            })
        else:
            return jsonify({
                "success": result['success'],
                "message": result['message'],
            })

    def get_field(self):
        username = session.get('username')
        return jsonify(self.field.get_fields(username))
    
    def delete_field(self):
        field_id = request.get_json().get("field_id")
        username = session.get('username')
        self.field.delete_field()
        return jsonify(self.field.get_fields(username))
    
    def rename_field(self):
        old_field_id =  request.get_json().get("old_field_id")
        new_field_id =  request.get_json().get("new_field_id")
        result = self.field.rename_field_id(old_field_id,new_field_id)
        
        if result:
            return jsonify({
                "success": result['success'],
                "message": result['message'],
            })
        else:
            return jsonify({
                "success": result['success'],
                "message": result['message'],
            })
        
    def get_device(self):
        field_id =  request.get_json().get("field_id")
        return jsonify(self.field.get_devices(field_id))
    
    def add_device(self):
        field_id =  request.get_json().get("field_id")
        device_id =  request.get_json().get("device_id")
        device_name =  request.get_json().get("device_name")
        result = self.field.add_device(field_id,device_id,device_name)

        if result:
            return jsonify({
                "success": result['success'],
                "message": result['message'],
            })
        else:
            return jsonify({
                "success": result['success'],
                "message": result['message'],
            })
        
    def delete_device(self):
        device_id = request.get_json().get("device_id")
        field_id = request.get_json().get("field_id")
        self.field.delete_device()
        return jsonify(self.field.get_devices(field_id))
    
    def rename_device(self):
        old_name =  request.get_json().get("old_name")
        new_name =  request.get_json().get("new_name")
        result = self.field.rename_device(old_name,new_name)
        
        if result:
            return jsonify({
                "success": result['success'],
                "message": result['message'],
            })
        else:
            return jsonify({
                "success": result['success'],
                "message": result['message'],
            })
       
    def add_user(self):
        username = session.get('username')
        result = self.field.find_username(username)
        if result:              
            return jsonify({
                "success": False,
                "message": "Người dùng không cần cấp quyền",
            })
        else:
            return jsonify({
                "success": True,
                "message": "Người dùng đã được cấp quyền",
            })
     
    def get_status(self):
        try:
            username = session.get('username')
            device_ids = self.field.get_device_ids(username)
            self.sensor.update(device_ids)
            all_telemetries = {}
            
            for device_id, url in zip(device_ids, self.sensor.get_urls()):
                try:
                    response = requests.get(url, headers=self.sensor.get_headers())
                    data = response.json()
                    telemetries = self.sensor.read_all_sensor_values(data)

                    device_name = self.field.get_device_name_by_id(device_id)
                    if not device_name:
                        device_name = device_id  

                    all_telemetries[device_name] = telemetries

                except Exception as inner_e:
                    all_telemetries[device_name] = {"error": str(inner_e)}

            return jsonify(all_telemetries), 200

        except Exception as e:
            return jsonify({"error": str(e)}), 500



        
   