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
import random
import read_value

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

    def clear_reset_session(self):
        self.pop_reset_session()
        return ("", 204)
    
    def control_device(self):
        # Yêu cầu phải đăng nhập mới được điều khiển
        if 'username' not in session:
            return jsonify({"success": False, "message": "Bạn chưa đăng nhập"}), 401
            
        username = session.get('username')
        data = request.get_json()
        
        field_id = data.get('field_id')
        device_name = data.get('device_name')
        action = data.get('action') # 'ON' hoặc 'OFF'

        # Kiểm tra xem User này có quyền điều khiển Field này không
        if not self.field.find_username(field_id, username):
            return jsonify({"success": False, "message": "Bạn không có quyền điều khiển ruộng này"}), 403

        print(f"User {username} ra lệnh: {action} thiết bị {device_name} tại {field_id}")

        # ==========================================================
        # TODO: GỌI API CỦA COREIOT/THINGSBOARD TẠI ĐÂY ĐỂ ĐIỀU KHIỂN
        # Ví dụ: self.sensor.send_rpc(device_name, action)
        # ==========================================================

        # Giả lập thành công (Bạn sẽ thay bằng kết quả thật từ IoT)
        is_success = True 
        
        if is_success:
            return jsonify({"success": True, "message": f"Đã {action} {device_name}"})
        else:
            return jsonify({"success": False, "message": "Thiết bị không phản hồi"})
        
    def management_page(self):
        resp = self.require_login()
        if resp:
            return resp
            
        # Kiểm tra, chặn user thường truy cập
        username = session.get('username')
        role = self.auth.get_role(username)
        if role != 'administrator' and role != 'admin':
            return redirect('/') 

        return render_template('admin_management.html')
    
    # 1. TRANG RENDER HTML
    def user_management_page(self):
        resp = self.require_login()
        if resp: return resp
        role = self.auth.get_role(session.get('username'))
        if role not in ['administrator', 'admin']: return redirect('/')
        
        # Đã gọi qua file config
        return render_template(config.user_management_page)

    # 2. API LẤY DANH SÁCH USER VÀ RUỘNG
    def api_admin_users(self):
        import sqlite3
        # Lấy danh sách user từ userdata.db
        conn_user = sqlite3.connect('userdata.db')
        cur_user = conn_user.cursor()
        cur_user.execute("SELECT id, username, email FROM user_data WHERE role='user'")
        users = cur_user.fetchall()
        conn_user.close()

        # Lấy danh sách field từ field.db
        conn_field = sqlite3.connect('field.db')
        cur_field = conn_field.cursor()
        
        result_list = []
        for u in users:
            user_id = u[0]
            username = u[1]
            email = u[2]
            
            # Tìm các field_id thuộc về username này
            cur_field.execute("SELECT field_id FROM field_user WHERE username=?", (username,))
            fields = [row[0] for row in cur_field.fetchall()]
            
            result_list.append({
                "id": user_id,
                "username": username,
                "email": email,
                "fields": fields
            })
            
        conn_field.close()
        return jsonify(result_list)

    # 3. API XÓA USER
    def api_admin_delete_users(self):
        data = request.get_json()
        user_ids = data.get('user_ids', [])
        
        import sqlite3
        conn = sqlite3.connect('userdata.db')
        cur = conn.cursor()
        
        try:
            for uid in user_ids:
                cur.execute("DELETE FROM user_data WHERE id=?", (uid,))
            conn.commit()
            success = True
            msg = "Đã xóa thành công"
        except Exception as e:
            conn.rollback()
            success = False
            msg = str(e)
        finally:
            conn.close()
            
        return jsonify({"success": success, "message": msg})
    
    # 1. Render trang HTML
    def greenhouse_management_page(self):
        resp = self.require_login()
        if resp: return resp
        role = self.auth.get_role(session.get('username'))
        if role not in ['administrator', 'admin']: return redirect('/')
        return render_template(config.greenhouse_management_page)

    # 2. API lấy danh sách Field
    def api_admin_greenhouses(self):
        import sqlite3
        conn = sqlite3.connect('field.db')
        cur = conn.cursor()
        
        # LEFT JOIN bảng field với bảng field_user để tìm chủ nhân
        cur.execute("""
            SELECT f.field_id, f.field_name, fu.username 
            FROM field f 
            LEFT JOIN field_user fu ON f.field_id = fu.field_id
        """)
        rows = cur.fetchall()
        conn.close()
        
        result_list = []
        for row in rows:
            field_name = row[1] if row[1] and str(row[1]).strip() != "" else "---"
            username = row[2] if row[2] and str(row[2]).strip() != "" else "---"
            
            result_list.append({
                "field_id": row[0],
                "plant": field_name,
                "username": username
            })
            
        return jsonify(result_list)    

    # API THÊM FIELD MỚI (GREENHOUSE)
    def api_admin_add_greenhouse(self):
        data = request.get_json()
        field_id = data.get('field_id', '').strip()

        if not field_id:
            return jsonify({"success": False, "message": "Field ID không hợp lệ"})

        import sqlite3
        conn = sqlite3.connect('field.db')
        cur = conn.cursor()

        try:
            # Chỉ thêm vào bảng field, field_name = NULL để tự động hiện "---" trên web
            cur.execute("INSERT INTO field (field_id, field_name) VALUES (?, ?)", (field_id, None))
            conn.commit()
            success = True
            msg = "Thêm thành công"
        except sqlite3.IntegrityError:
            conn.rollback()
            success = False
            msg = f"Field ID '{field_id}' đã tồn tại trong hệ thống!"
        except Exception as e:
            conn.rollback()
            success = False
            msg = str(e)
        finally:
            conn.close()

        return jsonify({"success": success, "message": msg})
    
    # API DỌN DẸP DỮ LIỆU FIELD (CLEAR)
    def api_admin_clear_fields(self):
        data = request.get_json()
        field_ids = data.get('field_ids', [])

        if not field_ids:
            return jsonify({"success": False, "message": "Không có field nào được chọn"})

        import sqlite3
        conn = sqlite3.connect('field.db')
        cur = conn.cursor()

        try:
            for fid in field_ids:
                # 1. Cập nhật bảng field: Xóa tên Plant (Gán thành NULL)
                cur.execute("UPDATE field SET field_name = NULL WHERE field_id = ?", (fid,))
                
                # 2. Xóa liên kết người dùng trong bảng field_user
                cur.execute("DELETE FROM field_user WHERE field_id = ?", (fid,))
            
            conn.commit()
            success = True
            msg = "Đã dọn dẹp thành công"
        except Exception as e:
            conn.rollback()
            success = False
            msg = str(e)
        finally:
            conn.close()

        return jsonify({"success": success, "message": msg})
    
    # API CẬP NHẬT FIELD (EDIT GREENHOUSE)
    def api_admin_edit_greenhouse(self):
        data = request.get_json()
        field_id = data.get('field_id', '').strip()
        username = data.get('username', '').strip()
        plant = data.get('plant', '').strip()

        if not field_id:
            return jsonify({"success": False, "message": "Field ID không hợp lệ"})

        import sqlite3
        conn = sqlite3.connect('field.db')
        cur = conn.cursor()

        try:
            # 1. Cập nhật bảng field (Tên Plant)
            plant_val = plant if plant else None
            cur.execute("UPDATE field SET field_name = ? WHERE field_id = ?", (plant_val, field_id))

            # 2. Cập nhật bảng field_user (Username)
            # Xóa liên kết cũ trước để làm sạch
            cur.execute("DELETE FROM field_user WHERE field_id = ?", (field_id,))
            
            # Nếu admin chọn 1 user, thì thêm liên kết mới vào
            if username:
                cur.execute("INSERT INTO field_user (field_id, username) VALUES (?, ?)", (field_id, username))

            conn.commit()
            success = True
            msg = "Cập nhật thành công"
        except Exception as e:
            conn.rollback()
            success = False
            msg = str(e)
        finally:
            conn.close()

        return jsonify({"success": success, "message": msg})
    
    # API XÓA HOÀN TOÀN FIELD (DELETE GREENHOUSE)
    def api_admin_delete_greenhouse_fields(self):
        data = request.get_json()
        field_ids = data.get('field_ids', [])

        if not field_ids:
            return jsonify({"success": False, "message": "Không có field nào được chọn"})

        import sqlite3
        conn = sqlite3.connect('field.db')
        cur = conn.cursor()

        try:
            for fid in field_ids:
                # Nhờ ON DELETE CASCADE, chỉ cần xóa ở bảng gốc 'field' là đủ
                cur.execute("DELETE FROM field WHERE field_id = ?", (fid,))
            
            conn.commit()
            success = True
            msg = "Đã xóa field thành công"
        except Exception as e:
            conn.rollback()
            success = False
            msg = str(e)
        finally:
            conn.close()

        return jsonify({"success": success, "message": msg})

# HOME PAGE
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
            
            # --- KIỂM TRA ROLE ĐỂ PHÂN LUỒNG CHUYỂN TRANG ---
            role = self.auth.get_role(username)
            
            # Kiểm tra nếu là admin (tuỳ vào chữ bạn lưu trong DB là admin hay administrator)
            if role == 'admin':
                redirect_url = "/admin_management"  # Đẩy Admin vào thẳng trang Quản lý
            else:
                redirect_url = "/"        # Đẩy User thường vào trang Home giám sát
            # ------------------------------------------------

            return jsonify({
                "success": result['success'],
                "message": result['message'],
                "role": role,
                "redirect": redirect_url
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
        
    # def resend_otp(self):   # Gửi lại OTP nếu người dùng yêu cầu
    #     username = session.get('username')
    #     if not username:
    #         return jsonify({"success": False, "message": "Không tìm thấy người dùng trong session."})

    #     email = self.auth.user_manager.get_email(username)
    #     self.otp.update_otp(email)
    #     self.otp.send_otp_email(email)

    #     return jsonify({"success": True, "message": "OTP đã được gửi lại."})

        
#################################################################################################################################

 # RESET PASSWORD PAGE

    def reset_password(self):
        username = session.get('username')
        expire_at = session.get(f"{username}_allow_reset")

        if not username or not expire_at or datetime.utcnow().timestamp() > expire_at:
            self.pop_reset_session()
            return redirect('/forgot-password')

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
    def dashboard_page(self):
        resp = self.require_login()
        if resp:
            return resp
        return render_template(config.dashboard_page)
    def control_page(self):
        resp = self.require_login()
        if resp:
            return resp
        return render_template(config.control_page)
    def manage_page(self):
        resp = self.require_login()
        if resp:
            return resp
            
        # --- CHẶN USER THƯỜNG TRUY CẬP TRANG ADMIN ---
        username = session.get('username')
        role = self.auth.get_role(username)
        if role != 'administrator' and role != 'admin':
            return redirect('/') # Nếu không phải admin, đá về trang Home
        # ---------------------------------------------

        return render_template(config.manage_page)
    def add_field(self):
        field_id =  request.form.get("field_id")
        field_name =  request.form.get("field_name")
        username = session.get('username')
        result = self.field.add_field(field_id, field_name, username)

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
        print(self.field.get_fields(username))
        return jsonify(self.field.get_fields(username))
    
    def delete_field(self):
        field_id = request.get_json().get("field_id")
        username = session.get('username')
        self.field.delete_field()
        self.logger.log_delete_field(field_id)
        return jsonify(self.field.get_fields(username))
    
    def rename_field_id(self):
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
        
    def rename_field_name(self):
        field_id =  request.get_json().get("field_id")
        new_field_name =  request.get_json().get("new_field_name")
        result = self.field.rename_field_name(field_id,new_field_name)
        
        if result:
            self.logger.log_rename_field(field_id,new_field_name)
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
        if data:
            for entry in data:
                self.field.insert_telemetry(entry)
                id = self.sensor.find_id(entry)
                self.sensor.delete(id)
    
    def update_out_date_status(self):
        self.field.delete_time_out()

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

        if not data:
            return []

        df = pd.DataFrame(data)
        df["ts"] = pd.to_datetime(df["ts"], unit="ms")
        df = df.set_index("ts")

        df["filtered"] = df["value"].rolling(window=median_window, min_periods=1).median()
        resampled = df["filtered"].resample(freq).mean().dropna()

        result = [
            {"ts": int(ts.timestamp() * 1000),
            "value": round(val, 2) if pd.notnull(val) else None}
            for ts, val in resampled.items()
        ]
        return result

    def send_chart(self):
        device_name = request.get_json().get("device_name")
        telemetry = request.get_json().get("telemetry")
        time_mode = request.get_json().get("time")
        #device_name = "SI Soil Moisture 5"
        #telemetry="temperature"
        #time_mode = "7d"

        freq_map = {
            "1h": "10min",   
            "1d": "1h",      
            "7d": "6h",      
            "30d": "1d"      
        }

        raw_data = self.field.get_all_telemetry_status(device_name, telemetry, time_mode)   

        resampled = self.resample_mean(raw_data, freq=freq_map[time_mode])

        return jsonify(resampled)
    
    # def get_data(self):
    #     fake_temp = round(random.uniform(10.0, 45.0), 1)
    #     fake_humid = random.randint(30, 100)
    #     fake_light = random.randint(100, 500)
    #     soil_moisture = 0
    #     test = routes.send_telemetry()
    #     for item in test:
    #         for device_name, telemetry in item.items():
    #             if 'moisture' in telemetry:
    #                 moisture_data = telemetry['moisture']
    #                 soil_moisture = moisture_data.get('value')
    #     return jsonify({
    #         "temperature": fake_temp,
    #         "humidity": fake_humid,
    #         "light": fake_light,
    #         "moisture": soil_moisture
    # })

    def get_current_user(self):
        # Kiểm tra xem user có trong session (đã đăng nhập) chưa
        if 'username' in session:
            username = session['username']
            role = self.auth.get_role(username) # Gọi hàm lấy role từ Authentication
            return jsonify({"success": True, "username": username, "role": role})
        else:
            return jsonify({"success": False, "message": "Chưa đăng nhập"}), 401
#################################################################################################################################


from webserver import FlaskServer
from user_manager import UserManager
from logger import UserLogger
from email_otp import OTPManager
from sensor_API import Sensor_API
from field_manager import FieldDB
from logger import UserLogger
from apscheduler.schedulers.background import BackgroundScheduler

manager = UserManager()
log = UserLogger()
otp = OTPManager(manager)
auth = Authentication(manager,log,otp)
server = FlaskServer()
sensor = Sensor_API()
field = FieldDB()
log = UserLogger()
routes = Routes(auth,otp,sensor,field,log)
scheduler = BackgroundScheduler()
server.add_route('/', routes.home_page, methods=['GET'])
server.add_route('/login', routes.login_page, methods=['GET'])
server.add_route('/login', routes.login, methods=['POST'])
server.add_route('/logout', routes.logout, methods=['POST'])
server.add_route('/signup', routes.signup_page, methods=['GET'])
server.add_route('/signup', routes.signup, methods=['POST'])
server.add_route('/forgot-password', routes.forgot_password_page, methods=['GET'])
server.add_route('/forgot-password', routes.send_otp, methods=['POST'])
server.add_route('/verify-otp', routes.verify_otp, methods=['POST'])
# server.add_route('/resend-otp', routes.resend_otp, methods=['POST'])
server.add_route('/reset-password', routes.reset_password_page, methods=['GET'])
server.add_route('/reset-password', routes.reset_password, methods=['POST'])
server.add_route('/control', routes.control_page, methods=['GET'])
server.add_route('/dashboard', routes.dashboard_page, methods=['GET'])
server.add_route('/manage', routes.manage_page, methods=['GET'])
server.add_route('/api/data', routes.send_telemetry, methods=['POST','GET'])
server.add_route('/api/fields', routes.get_field, methods=['POST','GET'])
server.add_route('/api/rename_device', routes.rename_device, methods=['POST'])
server.add_route('/api/rename_field', routes.rename_field_name, methods=['POST'])
server.add_route('/api/send_chart', routes.send_chart, methods=['POST'])
server.add_route('/api/current_user', routes.get_current_user, methods=['GET'])
server.add_route('/api/control_device', routes.control_device, methods=['POST'])

server.add_route('/admin_management', routes.management_page, methods=['GET'])
server.add_route('/admin_management/users', routes.user_management_page, methods=['GET'])
server.add_route('/api/admin/users', routes.api_admin_users, methods=['GET'])
server.add_route('/api/admin/delete_users', routes.api_admin_delete_users, methods=['POST'])
server.add_route('/admin_management/greenhouses', routes.greenhouse_management_page, methods=['GET'])
server.add_route('/api/admin/greenhouses', routes.api_admin_greenhouses, methods=['GET'])
server.add_route('/api/admin/add_greenhouse', routes.api_admin_add_greenhouse, methods=['POST'])
server.add_route('/api/admin/clear_fields', routes.api_admin_clear_fields, methods=['POST'])
server.add_route('/api/admin/edit_greenhouse', routes.api_admin_edit_greenhouse, methods=['POST'])
server.add_route('/api/admin/delete_greenhouse_fields', routes.api_admin_delete_greenhouse_fields, methods=['POST'])

scheduler.add_job(routes.update_status, 'interval', seconds=10)
# scheduler.add_job(routes.update_out_date_status, 'interval', seconds=5)


if __name__ == '__main__':
    scheduler.start()
    server.run()

