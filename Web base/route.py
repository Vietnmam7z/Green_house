from dataclasses import Field
from flask import Flask, request, session, current_app, redirect, render_template, jsonify
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
import subprocess
import sys
import sqlite3
import json
import device_controller

class Routes:
    def __init__(self, auth: Authentication, otp: OTPManager, sensor: Sensor_API, field: FieldDB, logger: UserLogger):
        self.auth = auth
        self.otp = otp
        self.sensor = sensor
        self.field = field
        self.logger = logger
        self.running_jobs = {}
        self.executed_keys = set()
        
    def require_login(self):
        if 'username' not in session:
            return redirect('/login')
        
    def redirect_if_logged_in(self):
        if 'username' in session:
            username = session.get('username')
            role = self.auth.get_role(username) # Lấy role để kiểm tra
            
            # Phân luồng: Admin về trang quản lý, User về trang chủ
            if role in ['administrator', 'admin']:
                return redirect('/admin_management')
            else:            
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
        role = self.auth.get_role(username)
        data = request.get_json()
        
        field_id = data.get('field_id')
        device_name = data.get('device_name')
        action = data.get('action') # 'ON' hoặc 'OFF'

        # 1. KIỂM TRA QUYỀN
        if role not in ['administrator', 'admin']:
            if not self.field.find_user_id(field_id, username):
                return jsonify({"success": False, "message": "Bạn không có quyền điều khiển ruộng này"}), 403

        print(f"User {username} ra lệnh: {action} thiết bị {device_name} tại {field_id}")

        # 2. LƯU TRẠNG THÁI VÀO DATABASE ĐỂ ĐỒNG BỘ
        try:
            # Thêm timeout=5.0 để nếu DB bị khóa, nó sẽ chờ tối đa 5 giây thay vì báo lỗi ngay
            conn = sqlite3.connect('field.db', timeout=5.0)
            cur = conn.cursor()
            
            # KHÓA ĐỘC QUYỀN (EXCLUSIVE LOCK): Ngăn luồng khác đọc/ghi xen ngang
            cur.execute("BEGIN EXCLUSIVE")
            
            # Lấy trạng thái hiện tại (nếu có)
            cur.execute("SELECT status FROM field_status WHERE field_id = ?", (field_id,))
            row = cur.fetchone()

            states = {}
            if row and row[0]:
                try:
                    states = json.loads(row[0])
                except json.JSONDecodeError:
                    pass

            # Cập nhật trạng thái của thiết bị vừa được bấm
            states[device_name] = action

            # Lưu ngược lại vào database
            if row is not None:
                cur.execute("UPDATE field_status SET status = ? WHERE field_id = ?", (json.dumps(states), field_id))
            else:
                cur.execute("INSERT INTO field_status (field_id, status) VALUES (?, ?)", (field_id, json.dumps(states)))
                
            conn.commit()
            conn.close()
            
        except sqlite3.OperationalError as e:
            # Nếu 2 người bấm thật sự cùng lúc và timeout không cứu được, báo cho Web biết
            print(f"Lỗi khóa DB: {e}")
            return jsonify({"success": False, "message": "Hệ thống đang bận xử lý lệnh khác, vui lòng thử lại!"}), 503
        except Exception as e:
            print(f"Lỗi Database trong control_device: {e}")
            return jsonify({"success": False, "message": f"Lỗi server: {e}"}), 500

        # ==========================================================
        # 3. TRẢ VỀ KẾT QUẢ CHO FRONTEND
        # CHÚ Ý: Các dòng dưới đây phải thẳng hàng với chữ 'try' phía trên
        # ==========================================================
        is_success = True 
        
        if is_success:
            return jsonify({"success": True, "message": f"Đã {action} {device_name}"})
        else:
            return jsonify({"success": False, "message": "Thiết bị không phản hồi"})
	
    # API CHO TRANG CONTROL
    def get_control_status(self):
        field_id = request.args.get('field_id')
        if not field_id:
            return jsonify({"success": False, "message": "Thiếu field_id"})
        import sqlite3
        import json
        conn = sqlite3.connect('field.db')
        cur = conn.cursor()
        cur.execute("SELECT status FROM field_status WHERE field_id = ?", (field_id,))
        row = cur.fetchone()
        conn.close()
        states = {}
        if row and row[0]:
            try:
                states = json.loads(row[0])
            except json.JSONDecodeError:
                pass
        return jsonify({"success": True, "states": states})
            
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

    def get_devices_controller(self):
        field_id = request.args.get("field_id") 
        result = self.field.get_devices_controller_by_field(field_id)

        if result["success"]:
            return jsonify({
                "success": True,
                "devices": result["devices"]
            })
        else:
            return jsonify({
                "success": False,
                "message": result["message"]
            })

    def toggle_and_send(self):
        field_id = request.args.get("field_id")
        device_id = request.args.get("device_id")

        result = self.field.toggle_device_state(int(device_id))
        if not result["success"]:
            return jsonify(result)

        new_state = result["new_state"]
        
        device_info = self.field.get_device_controller_by_id(field_id, device_id)
        print(f"DEBUG: Lấy type cho field_id {field_id}, device_id {device_id} => {device_info}")

        if device_info["success"]:
            device = device_info["device"]
            type = device[2]  
            device_controller.send_state(field_id, new_state, type)
            self.logger.log_set_device_state(field_id, device_id, new_state)

        return jsonify({"success": True, "new_state": new_state})

    def get_schedulers_by_field(self):
        field_id = request.args.get("field_id")
        if not field_id:
            return jsonify({
                "success": False,
                "message": "Missing field_id"
            })
        try:
            result = self.field.get_schedulers_by_field_id(field_id)
            return jsonify(result)
        except Exception as e:
            return jsonify({
                "success": False,
                "message": str(e)
            })

    def create_scheduler(self):
        data = request.json
        try:
            result = self.field.create_scheduler(
                field_id=data.get("field_id"),
                device_id=data.get("device_id"),
                name=data.get("name"),
                event_date=data.get("event_date"),
                end_date=data.get("end_date"),
                event_time=data.get("event_time"),
                event_type=data.get("event_type"),
                mode=data.get("mode"),
                duration=data.get("duration"),
                consumption=data.get("consumption"),
                repeat_enabled=data.get("repeat_enabled", False),
                type_repeat=data.get("type_repeat"),
                repeat_value=data.get("repeat_value")
            )

            if result["success"]:
                scheduler_id = result.get("scheduler_id")
                if data.get("mode") == "time":
                    self.logger.log_create_job_no_threshold(
                        scheduler_id,
                        data.get("field_id"),
                        data.get("device_id"),
                        data.get("duration"),
                        data.get("event_date"),
                        data.get("event_time")
                    )
                else: 
                    self.logger.log_create_job(
                        scheduler_id,
                        data.get("field_id"),
                        data.get("device_id"),
                        data.get("consumption"),
                        data.get("event_date"),
                        data.get("event_time")
                    )
                
            return jsonify(result)
        except Exception as e:
            return jsonify({
                "success": False,
                "message": str(e)
            })

    def update_scheduler(self):
        data = request.json
        try:
            result = self.field.update_scheduler(
                scheduler_id=data.get("scheduler_id"),
                field_id=data.get("field_id"),
                device_id=data.get("device_id"),
                name=data.get("name"),
                event_date=data.get("event_date"),
                end_date=data.get("end_date"),
                event_time=data.get("event_time"),
                event_type=data.get("event_type"),
                mode=data.get("mode"),
                duration=data.get("duration"),
                consumption=data.get("consumption"),
                repeat_enabled=data.get("repeat_enabled", False),
                type_repeat=data.get("type_repeat"),
                repeat_value=data.get("repeat_value"),
                enabled=data.get("enabled", True)
            )
            if result["success"]:
                scheduler_id = data.get("scheduler_id")
                if data.get("mode") == "time":
                    self.logger.log_update_job_no_threshold(
                        scheduler_id,
                        data.get("field_id"),
                        data.get("device_id"),
                        data.get("duration"),
                        data.get("event_date"),
                        data.get("event_time")
                    )
                else: 
                    self.logger.log_update_job(
                        scheduler_id,
                        data.get("field_id"),
                        data.get("device_id"),
                        data.get("consumption"),
                        data.get("event_date"),
                        data.get("event_time")
                    )

            return jsonify(result)
        except Exception as e:
            return jsonify({
                "success": False,
                "message": str(e)
            })
    
    def delete_scheduler(self):
        data = request.json
        scheduler_id = data.get("scheduler_id")
        try:
            result = self.field.delete_scheduler(scheduler_id)
            if result["success"]:
                self.logger.log_delete_job(scheduler_id)
            return jsonify(result)
        except Exception as e:
            return jsonify({
                "success": False,
                "message": str(e)
            })
        
    def execute_scheduler(self, device_id, state):
        device_info = self.field.get_device_controller_by_device_id(device_id)
        if not device_info["success"]:
            print(f"[EXEC ERROR] Device not found: {device_id}")
            return

        device = device_info["data"]
        field_id = device["field_id"]
        device_type = device["type"]
        self.field.set_device_state(device_id, state)
        device_controller.send_device_command(field_id, device_type, state)
        print(f"[EXEC] {state} -> {device_type} (field {field_id})")

    def calculate_next_date(self, row):
        event_date_str = row["event_date"]
        event_time_str = row["event_time"]
        repeat_type = row["type_repeat"]
        repeat_value = row.get("repeat_value") or 1

        # Kết hợp ngày và giờ hiện tại thành đối tượng datetime
        current_run = datetime.strptime(f"{event_date_str} {event_time_str[:5]}", "%Y-%m-%d %H:%M")
        
        next_run = current_run # Mặc định

        if repeat_type == "daily":
            next_run = current_run + timedelta(days=1)
        elif repeat_type == "every_n_days":
            next_run = current_run + timedelta(days=int(repeat_value))
        elif repeat_type == "weekly":
            next_run = current_run + timedelta(days=7)
        elif repeat_type == "every_n_weeks":
            next_run = current_run + timedelta(weeks=int(repeat_value))

        # Trả về cùng lúc (Ngày, Giờ)
        return next_run.strftime("%Y-%m-%d"), next_run.strftime("%H:%M:%S")
        
    def check_and_run_schedulers(self):
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        current_date = now.strftime("%Y-%m-%d")

        try:
            result = self.field.get_all_schedulers()
            if not result["success"]:
                return

            rows = result["data"]

            if not hasattr(self, "executed_keys"):
                self.executed_keys = set()

            if not hasattr(self, "running_jobs"):
                self.running_jobs = {}

            for row in rows:
                scheduler_id = row["scheduler_id"]
                mode = row.get("mode")
                event_time = (row.get("event_time") or "")[:5]
                event_date = row.get("event_date")

                if not event_date:
                    continue

                event_date = str(event_date).split(" ")[0].strip()
                if event_date != current_date:
                    continue

                if event_time and event_time[:5] != current_time[:5]:
                    continue

                job = None
                if mode == "time":

                    base_key = f"{scheduler_id}_{event_date}_{event_time}"
                    if base_key in self.executed_keys:
                        continue

                    job = self.handle_time_scheduler(row, now, current_date, current_time)
                    if job:
                        self.executed_keys.add(base_key)

                elif mode == "consumption":
                    base_key = f"{scheduler_id}_{event_date}_{event_time}"
                    if base_key in self.executed_keys:
                        continue

                    job = self.handle_consumption_scheduler(row, now, current_date, current_time)
                    if job:
                        self.executed_keys.add(base_key) 

                if job:
                    self.running_jobs[job["scheduler_id"]] = job

            self.handle_done_jobs(now)
            if len(self.executed_keys) > 10000:
                self.executed_keys.clear()

        except Exception as e:
            print(f"[SCHEDULER ERROR] {str(e)}")

    def handle_consumption_scheduler(self, row, now, current_date, current_time):
        scheduler_id = row["scheduler_id"]
        device_id = row["device_id"]
        if not row["enabled"]:
            return None

        device_info = self.field.get_device_sensor_mapping(device_id)
        if not device_info["success"]:
            return None

        device_type = (device_info["data"]["type"] or "").strip().lower()
        sensor_id = device_info["data"]["sensor_id"]
        if device_type not in ("valve", "co2_valve", "fertilizer"):
            return None

        event_time = row.get("event_time", "")

        if event_time and event_time[:5] != current_time[:5]:
            return None

        if scheduler_id in self.running_jobs:
            return None

        initial_value = None
        telemetry_name = "fertilizerCounter" if device_type == "fertilizer" else "pulseCounter"
        try:
            current_data = self.field.get_telemetry(sensor_id)
            if current_data and sensor_id in current_data:
                if telemetry_name in current_data[sensor_id]:
                    initial_value = float(current_data[sensor_id][telemetry_name]["value"])
        except Exception as e:
            print(f"Lỗi lấy giá trị ban đầu: {e}")

        if initial_value is None:
            initial_value = 0.0

        start_ts = int(now.timestamp() * 1000)
        self.execute_scheduler(device_id, "ON")
        
        return {
            "scheduler_id": scheduler_id,
            "device_id": device_id,
            "sensor_id": sensor_id,
            "device_type": device_type,  # Thêm dòng này để dùng ở hàm dưới
            "start_time": now,
            "last_ts": start_ts,
            "prev_value": initial_value, # Nạp số mốc vào đây
            "row": row,
            "type": "consumption"
        }
    
    def handle_time_scheduler(self, row, now, current_date, current_time):

        scheduler_id = row["scheduler_id"]
        device_id = row["device_id"]
        event_time = row["event_time"]

        if not row["enabled"]:
            return None

        if event_time[:5] != current_time[:5]:
            return None

        exec_key = f"{scheduler_id}_{current_date}_{event_time[:5]}"

        if exec_key in self.executed_keys:
            return None

        self.executed_keys.add(exec_key)

        self.execute_scheduler(device_id, "ON")

        return {
            "scheduler_id": scheduler_id,
            "device_id": device_id,
            "start_time": now,
            "duration": row.get("duration") or 60,
            "row": row,
            "type": "time"
        }   
     
    def handle_done_jobs(self, now):
        for scheduler_id in list(self.running_jobs.keys()):
            job = self.running_jobs[scheduler_id]
            
            # --- PHẦN XỬ LÝ THEO THỜI GIAN (TIME) ---
            if job.get("type") == "time":
                elapsed = (now - job["start_time"]).total_seconds()
                if elapsed < (job.get("duration", 0) * 60):
                    continue

                device_id = job["device_id"]
                self.execute_scheduler(device_id, "DONE")
                
                # SỬA LẠI ĐÚNG 2 DÒNG NÀY:
                next_date, next_time = self.calculate_next_date(job["row"])
                self.field.update_scheduler_date(scheduler_id, next_date, next_time)
                
                del self.running_jobs[scheduler_id]
                continue

            # --- PHẦN XỬ LÝ THEO LƯU LƯỢNG (CONSUMPTION) MỚI SỬA ---
            if job.get("type") != "consumption":
                continue

            sensor_id = job["sensor_id"]
            device_type = job.get("device_type", "valve")
            # [VÁ LỖI 2A]: Xác định đúng tên tín hiệu cần nghe
            telemetry_name = "fertilizerCounter" if device_type == "fertilizer" else "pulseCounter"

            db_max_ts = self.field.get_max_ts(sensor_id)
            last_ts = job.get("last_ts", 0)
            if last_ts > db_max_ts:
                last_ts = db_max_ts
            rows = self.field.get_new_telemetry(sensor_id, last_ts)

            if not rows:
                continue

            total_delta = 0
            max_ts = last_ts
            prev_value = job.get("prev_value")

            for row in rows:
                ts = row[0]
                value_str = row[1]
                name = row[2]

                # [VÁ LỖI 2B]: Lọc BỎ TẤT CẢ tín hiệu rác (như pin, sóng...), chỉ nghe đồng hồ nước
                if name != telemetry_name:
                    continue

                try:
                    value = float(value_str)
                except:
                    continue
                
                if prev_value is not None:
                    delta = value - prev_value
                    if delta > 0:
                        total_delta += delta

                prev_value = value
                job["prev_value"] = prev_value

                if ts > max_ts:
                    max_ts = ts

            job["last_ts"] = max_ts
            job["total_consumption"] = job.get("total_consumption", 0) + total_delta

            threshold = float(job["row"].get("consumption") or 0)

            print(f"[CONS] Cảm biến {sensor_id} | Chảy thêm: {total_delta}L | Tổng đã tưới: {job['total_consumption']}L / Mục tiêu: {threshold}L")

            # NẾU ĐÃ TƯỚI ĐỦ (HOẶC VƯỢT) NGƯỠNG
            if threshold > 0 and job["total_consumption"] >= threshold:
                device_id = job["device_id"]
                self.execute_scheduler(device_id, "DONE") # Tắt máy bơm
                
                # Tính ngày lặp lại tiếp theo và lưu vào DB
                next_date, next_time = self.calculate_next_date(job["row"])
                self.field.update_scheduler_date(scheduler_id, next_date, next_time)
                
                del self.running_jobs[scheduler_id] # Kết thúc tiến trình
                
    def reset_daily_cache(self):
        self.executed_keys.clear()

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
        users = self.auth.get_all_user_information()
        result_list = []
        for u in users:
            user_id = u["user_id"]
            username = u["username"]
            email = u["email"]

            # BỔ SUNG 1: Lấy role của user hiện tại
            role = self.auth.get_role(username)

            # get_fields trả về list dict => lấy ra danh sách field_id
            fields_data = self.field.get_fields(username)   # [{'field_id': '001', 'field_name': 'Plant A'}, ...]
            field_ids = [f["field_id"] for f in fields_data]

            fields = self.field.get_field_ids(field_ids)

            result_list.append({
                "id": user_id,
                "username": username,
                "email": email,
                "fields": fields,
                "role": role  # BỔ SUNG 2: Thêm role vào JSON gửi về Frontend
            })
        
        return jsonify(result_list)

    # 3. API XÓA USER
    def api_admin_delete_users(self):
        data = request.get_json()
        user_ids = data.get('user_ids', [])
        for user_id in user_ids:
            username = self.auth.get_username(user_id)
            self.auth.delete_user(username)
            self.field.delete_user(username)
            self.logger.log_delete_user(username)
        return jsonify({"success": True, "message": "Người dùng đã được xóa thành công"})
    
    # 1. Render trang HTML
    def greenhouse_management_page(self):
        resp = self.require_login()
        if resp: return resp
        role = self.auth.get_role(session.get('username'))
        if role not in ['administrator', 'admin']: return redirect('/')
        return render_template(config.greenhouse_management_page)

    # 2. API lấy danh sách Field
    def api_admin_greenhouses(self):
        rows = self.field.api_admin_greenhouses();
        result_list = []
        for field_id, field_name, username in rows:
            field_name = field_name if field_name and str(field_name).strip() != "" else "---"
            username = username if username else "---"

            result_list.append({
                "field_id": field_id,
                "plant": field_name,
                "username": username
            })

        return jsonify(result_list)
            
    # API THÊM FIELD MỚI (GREENHOUSE)
    def api_admin_add_greenhouse(self):
        data = request.get_json()
        field_id = data.get('field_id', '').strip()
        result = field.add_field(field_id, None, None)
        self.logger.log_add_field(field_id)
        self.field.create_AI_management_record(field_id)
        return jsonify(result)

    # API DỌN DẸP DỮ LIỆU FIELD (CLEAR)
    def api_admin_clear_fields(self):
        data = request.get_json()
        field_ids = data.get('field_ids', [])
        for field_id in field_ids:
            result = self.field.clear_field(field_id)
            self.logger.log_clear_field(field_id)
        return jsonify(result)

    # API CẬP NHẬT FIELD (EDIT GREENHOUSE)
    def api_admin_edit_greenhouse(self):
        data = request.get_json()
        field_id = data.get('field_id', '').strip()
        username = data.get('username', '').strip()
        plant = data.get('plant', '').strip()

        if not field_id:
            return jsonify({"success": False, "message": "Field ID không hợp lệ"})

        self.field.rename_field_name(field_id, plant if plant else None)
        if username:
            self.field.add_user_to_field(field_id, username)
            self.logger.log_add_user_to_field(field_id, username)

        return jsonify({"success": True, "message": "Cập nhật thành công"})
    
    # API XÓA HOÀN TOÀN FIELD (DELETE GREENHOUSE)
    def api_admin_delete_greenhouse_fields(self):
        data = request.get_json()
        field_ids = data.get('field_ids', [])

        if not field_ids:
            return jsonify({"success": False, "message": "Không có field nào được chọn"})
        for field_id in field_ids:
            self.field.delete_field(field_id)
            self.logger.log_delete_field(field_id)
        return jsonify({"success": True, "message": "Đã xóa field thành công"})          

# HOME PAGE
################################################################################################################################        
 
 # HOME PAGE  
     
    def home_page(self):
        resp = self.require_login()
        if resp:  # Nếu require_login trả về một response (redirect hoặc render)
            return resp

        username = session.get('username')
        role = self.auth.get_role(username)
        # Nếu là Admin vô tình vào trang "/", tự động đẩy về "/admin_management"
        if role in ['administrator', 'admin']:
            return redirect('/admin_management')
        # Nếu là User thường thì cho vào trang Home giám sát
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
            session.permanent = True
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
            self.field.create_notification_management(username)
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
        role = self.auth.get_role(username) # Lấy quyền của người dùng hiện tại
        
        # Nếu là Admin -> Lấy toàn bộ ruộng
        if role in ['administrator', 'admin']:
            fields = self.field.get_all_fields()
        # Nếu là User thường -> Chỉ lấy ruộng của mình
        else:
            fields = self.field.get_fields(username)
            
        return jsonify(fields)
    
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
   
    def get_ai_settings(self):
        field_id = request.args.get('field_id')
        if not field_id:
            return jsonify({"success": False, "message": "Missing field_id"}), 400
            
        try:
            return jsonify({
                "success": True, 
                "data": {
                    "anomoly_score_low": self.field.get_anomoly_score_low(field_id)[0],
                    "anomoly_score_high": self.field.get_anomoly_score_high(field_id)[0],
                    "step": self.field.get_step(field_id)[0],
                    "anomoly_status": self.field.get_anomoly_status(field_id)[0],
                    "prediction_status": self.field.get_prediction_status(field_id)[0],
                    "anomoly_prediction_status": self.field.get_anomoly_prediction_status(field_id)[0]
                }
            }), 200
        except Exception as e:
            print(f"Lỗi lấy cấu hình AI: {e}")
            return jsonify({"success": False, "message": "Server error"}), 500    
    
    def update_ai_settings(self):
        data = request.get_json()
        field_id = data.get('field_id')
        anomoly_score_low = float(data.get('anomoly_score_low', 0))
        anomoly_score_high = float(data.get('anomoly_score_high', 100))
        step = int(data.get('step', 5))
        anomoly_status = data.get('anomoly_status', 'OFF')
        prediction_status = data.get('prediction_status', 'OFF')
        anomoly_prediction_status = data.get('anomoly_prediction_status', 'OFF')

        # Kiểm tra field_id hợp lệ
        if not field_id:
            return jsonify({"success": False, "message": "Thiếu mã khu vực (field_id)."}), 400

        self.field.set_anomoly_score_low(field_id, anomoly_score_low)
        self.field.set_anomoly_score_high(field_id, anomoly_score_high)
        self.field.set_step(field_id, step)
        self.field.set_anomoly_status(field_id, anomoly_status)
        self.field.set_prediction_status(field_id, prediction_status)
        self.field.set_anomoly_prediction_status(field_id, anomoly_prediction_status)

        return jsonify({
            "success": True, 
            "message": "Đã lưu cấu hình AI thành công!"
        }), 200
 
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
        device_id = request.args.get('device_id')
        name = request.args.get('name')
        

        if not device_id or not name:
            return jsonify({"success": False, "message": "Thiếu tham số device_id hoặc name"}), 400
        result = self.field.send_chart(device_id, name)
        if isinstance(result, dict):
            return jsonify(result)
        return result

    def check_anomaly(self):
        result = self.field.check_anomaly()
        if isinstance(result, dict):
            return jsonify(result)
        return result
    
    def save_notification(self):
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "Không nhận được dữ liệu"})

        status = data.get('status')
        device_id = data.get('device_id')
        ts = data.get('ts')
        username = data.get('username')
        result = self.field.insert_notification(status, device_id, ts, username)
        return jsonify(result)

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

app = Flask(__name__)


def job_update_status():
    with app.app_context():
        routes.update_status()

def job_check_scheduler():
    with app.app_context():
        routes.check_and_run_schedulers()

def job_update_out_date_status():
    with app.app_context():
        routes.update_out_date_status()

def job_reset_daily_cache():
    with app.app_context():
        routes.reset_daily_cache()
    
server.add_route('/api/get_devices_controller', routes.toggle_and_send, methods=['POST'])
server.add_route('/api/devices_list', routes.get_devices_controller, methods=['GET'])
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
server.add_route('/api/send_chart', routes.send_chart, methods=['GET'])
server.add_route('/api/current_user', routes.get_current_user, methods=['GET'])
server.add_route('/api/control_device', routes.control_device, methods=['POST'])
#server.add_route('/api/get_control_status', routes.get_control_status, methods=['GET'])
server.add_route('/api/save_notification', routes.save_notification, methods=['POST'])
server.add_route('/api/update_ai_settings', routes.update_ai_settings, methods=['POST'])
server.add_route('/api/get_ai_settings', routes.get_ai_settings, methods=['GET'])
server.add_route('/api/check_anomaly', routes.check_anomaly, methods=['GET'])
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

server.add_route('/api/get_schedulers', routes.get_schedulers_by_field, methods=['GET'])
server.add_route('/api/create_scheduler', routes.create_scheduler, methods=['POST'])
server.add_route('/api/update_scheduler', routes.update_scheduler, methods=['POST'])
server.add_route('/api/delete_scheduler', routes.delete_scheduler, methods=['POST'])

scheduler.add_job(job_reset_daily_cache, 'cron', hour=0, minute=0)
scheduler.add_job(job_update_status, 'interval', seconds=10)
scheduler.add_job(job_check_scheduler,'interval',seconds=1,max_instances=1,coalesce=True)


#scheduler.add_job(job_update_out_date_status, 'interval', seconds=5)


if __name__ == '__main__':
    import os
    os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
    import sys
    import subprocess
    
    # Khởi tạo biến lưu tiến trình AI để dễ dàng quản lý
    ai_process = None
    
    # TRẠM KIỂM SOÁT: Chỉ khởi động AI và Scheduler nếu đây là tiến trình con của Reloader
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        scheduler.start()
        print("Đang khởi động Server AI ngầm...")
        try:
            ai_process = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "LSTM_AI:app", "--host", "0.0.0.0", "--port", "8000"]
            )
            print("Đã bật Server AI tại cổng 8000!")
        except Exception as e:
            print(f"Lỗi không thể khởi động Server AI: {e}")
            
    try:
        # Lệnh chạy Web Server
        server.run()
    except KeyboardInterrupt:
        # Bắt sự kiện khi bạn nhấn Ctrl + C
        print("\n[HỆ THỐNG] Nhận lệnh tắt từ người dùng...")
    finally:
        # 1. Dọn dẹp Scheduler (Tắt các tiến trình cập nhật ngầm)
        try:
            if scheduler.running:
                scheduler.shutdown(wait=False)
                print("[HỆ THỐNG] Đã tắt Scheduler an toàn.")
        except Exception:
            pass # Bỏ qua nếu scheduler chưa kịp chạy

        # 2. Dọn dẹp sạch sẽ tiến trình Server AI
        if ai_process is not None:
            ai_process.terminate()
            ai_process.wait() # Chờ tiến trình AI tắt hẳn
            print("[HỆ THỐNG] Đã đóng Server AI (cổng 8000) an toàn.")
            
        print("[HỆ THỐNG] Tạm biệt!")