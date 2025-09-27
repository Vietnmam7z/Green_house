from dataclasses import Field
from flask import request, session, redirect, render_template, jsonify
from datetime import datetime, timedelta
from authentication import Authentication
from email_otp import OTPManager
from sensor_API import Sensor_API
from field_manager import FieldDB
from logger import UserLogger
import requests
import config
import pandas as pd

class Routes:
    def __init__(self, auth: Authentication, otp: OTPManager, sensor: Sensor_API, field: FieldDB, logger: UserLogger):
        self.auth = auth
        self.otp = otp
        self.sensor = sensor
        self.field = field
        self.logger = logger
        
    def require_login(self):
        if 'username' not in session:
            return redirect('/login')
        
    def redirect_if_logged_in(self):
        if 'username' in session:
            return redirect('/')   

    def reset_password_page(self):
        username = session.get('username')
        if not username or not session.get(f"{username}_allow_reset"):
            return redirect('/forgot-password')

        return render_template(config.reset_password_page)

    def pop_reset_session(self):
        username = session.get('username')
        if username:
            session.pop('username', None)
            session.pop(f"{username}_allow_reset", None)


################################################################################################################################        
 
 # HOME PAGE  
     
    def home_page(self):
        resp = self.require_login()
        if resp:  # Nếu require_login trả về một response (redirect hoặc render)
            return resp

        username = session.get('username')
        return render_template(config.home_page, username=username)

    def logout(self):
        username = session.get('username')
        if username:
            # Cập nhật trạng thái offline và thời gian hoạt động cuối
            self.auth.logout_user(username)
            self.auth.user_manager.set_last_active(username)

            # Xoá session
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
        return render_template(config.forgot_password_page)

    def send_otp(self):
        email = request.json.get('email')
        print("Yêu cầu gửi OTP cho:", email)

        username = self.auth.user_manager.find_email(email)
        if not username:
            print("Email không tồn tại:", email)
            return jsonify({"success": False, "message": "Email không tồn tại."}), 200

        self.otp.update_otp(email)
        self.otp.send_otp_email(email)
        session['username'] = username

        print("OTP đã gửi thành công cho:", email)
        return jsonify({"success": True, "message": "OTP đã được gửi"}), 200

    def verify_otp(self):   # Xác thực OTP người dùng nhập vào
        otp_code = request.json.get('otp')
        username = session.get('username')
        if not username:
            return jsonify({"success": False, "message": "Không tìm thấy người dùng trong session."})

        result = self.otp.confirm_otp(otp_code, username)
        if result['success']:
            session[f"{username}_allow_reset"] = (datetime.utcnow() + timedelta(minutes=15)).timestamp()
            return jsonify({"success": True, "message": result['message'], "redirect": "/reset-password"})
        else:
            return jsonify({"success": False, "message": result['message']})
        
    def resend_otp(self):   # Gửi lại OTP nếu người dùng yêu cầu
        username = session.get('username')
        if not username:
            return jsonify({"success": False, "message": "Không tìm thấy người dùng trong session."})

        email = self.auth.user_manager.get_email(username)
        self.otp.update_otp(email)
        self.otp.send_otp_email(email)

        return jsonify({"success": True, "message": "OTP đã được gửi lại."})

        
#################################################################################################################################

 # RESET PASSWORD PAGE

    def reset_password(self):
        username = session.get('username')
        expire_at = session.get(f"{username}_allow_reset")

        if not username or not expire_at or datetime.utcnow().timestamp() > expire_at:
            self.pop_reset_session()
            return jsonify({
                "success": False,
                "message": "Hết thời gian đổi mật khẩu"
            })

        data = request.get_json()
        new_password = data.get('new_password')

        result = self.auth.reset_password(username, new_password)

        if result['success']:
            self.pop_reset_session()
            return jsonify({
                "success": True,
                "message": result['message'],
                "redirect": "/login"
            })
        else:
            return jsonify({
                "success": False,
                "message": result['message']
            })
        
#################################################################################################################################

 # DASHBOARD_PAGE

    def add_field(self):
        field_id =  request.form.get("field_id")
        username = session.get('username')
        result = self.field.add_field(field_id, username)

        if result:
            self.logger.log_add_field(field_id)
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
        self.logger.log_delete_field(field_id)
        return jsonify(self.field.get_fields(username))
    
    def rename_field(self):
        old_field_id =  request.get_json().get("old_field_id")
        new_field_id =  request.get_json().get("new_field_id")
        result = self.field.rename_field_id(old_field_id,new_field_id)
        
        if result:
            self.logger.log_rename_field(old_field_id,new_field_id)
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
            self.logger.log_add_device(device_id)
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
        self.logger.log_delete_device(device_id)
        return jsonify(self.field.get_devices(field_id))
    
    def rename_device(self):
        old_name_device =  request.get_json().get("old_name")
        new_name_device =  request.get_json().get("new_name")
        result = self.field.rename_device(old_name_device,new_name_device)
        
        if result:
            self.logger.log_rename_device(old_name_device,new_name_device)
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
        field_id =  request.get_json().get("field_id")

        if result:
                     
            return jsonify({
                "success": False,
                "message": "Người dùng không cần cấp quyền",
            })
        else:
            self.field.add_user_to_field(field_id,username)
            self.logger.log_add_user_to_field(field_id,username)  
            return jsonify({
                "success": True,
                "message": "Người dùng đã được cấp quyền",
            })
     
    def update_status(self):
        data = self.sensor.update()
        for entry in data:
            self.field.insert_telemetry(entry)
            id = self.sensor.find_id(entry)
            self.sensor.delete(id)

    def send_all_field(self):
        username = session.get('username')
        result = self.field.get_fields(username)
        print(result)
        return jsonify(result)

    def send_telemetry(self):
        field_id =  request.get_json().get("field_id")
        devices = self.field.get_device_names(field_id)

        result = []
        for device in devices:
            result.append(self.field.get_telemetry(device))

        return jsonify(result)

    def resample_mean(self, data, freq="10min", median_window=5):

        df = pd.DataFrame(data)
        df["ts"] = pd.to_datetime(df["ts"], unit="ms")  
        df = df.set_index("ts")

        df["filtered"] = df["value"].rolling(window=median_window, min_periods=1).median()       
        resampled = df["filtered"].resample(freq).mean().dropna()
        
        result = [
            {"ts": int(ts.timestamp() * 1000), "value": round(val, 2) if pd.notnull(val) else None}
            for ts, val in resampled.items()
        ]
        return result

    def send_chart(self):
        device_name = request.get_json().get("device_name")
        telemetry = request.get_json().get("telemetry")
        time_mode = request.get_json().get("time")
        #device_name = "Moisture 5"
        #telemetry_name="temperature"
        #time_mode = "1h"

        raw_data = self.field.get_all_telemetry_status(device_name, telemetry)

        print(raw_data)
        
        freq_map = {
            "1h": "10min",   
            "1d": "1H",      
            "7d": "6H",      
            "30d": "1D"      
        }

        resampled = self.resample_mean(raw_data, freq=freq_map[time_mode])

        return resampled

#################################################################################################################################






