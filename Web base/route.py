from dataclasses import Field
from flask import Flask, request, session, current_app, redirect, render_template, jsonify
from datetime import datetime, time, timedelta
from authentication import Authentication
from email_otp import OTPManager
from sensor_API import Sensor_API
from notification import NotificationManager
from field_manager import FieldDB
from logger import UserLogger
import payment
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
    
    def profile_page(self):
        resp = self.require_login()
        if resp:
            return resp
        return render_template('profile.html')
    
    def control_device(self):
        # Yêu cầu phải đăng nhập mới được điều khiển
        if 'username' not in session:
            return jsonify({"success": False, "message": "Bạn chưa đăng nhập"}), 401
            
        username = session.get('username')
        role = self.auth.get_role(username)
        data = request.get_json()
        
        field_id = data.get('field_id')
        device_name = data.get('device_name') # VD: 'Light', 'Irrigation' từ UI
        action = data.get('action') # 'ON' hoặc 'OFF'

        # 1. KIỂM TRA QUYỀN
        if role not in ['administrator', 'admin']:
            if not self.field.find_user_id(field_id, username):
                return jsonify({"success": False, "message": "Bạn không có quyền điều khiển ruộng này"}), 403

        print(f"User {username} ra lệnh: {action} thiết bị {device_name} tại {field_id}")

        # 2. BẢN ĐỒ MAP GIAO DIỆN (UI) SANG TYPE TRONG DATABASE
        ui_to_db_type = {
            "Light": "light",
            "Vent": "vent",
            "Irrigation": "valve",
            "Cooling pad": "cooling_pad",
            "Heater": "heater",
            "CO2 valve": "co2_valve",
            "Fan": "fan",
            "Fertigation": "fertilizer"
        }
        
        db_type = ui_to_db_type.get(device_name)
        if not db_type:
            return jsonify({"success": False, "message": "Thiết bị không hợp lệ"}), 400

        # Chuyển đổi trạng thái cho khớp với DB (OFF tương đương với DONE)
        db_state = "ON" if action == "ON" else "DONE"

        # 3. LƯU VÀO BẢNG DEVICE_CONTROLLER & GỬI MQTT
        try:
            conn = sqlite3.connect('field.db', timeout=5.0)
            cur = conn.cursor()
            cur.execute("BEGIN EXCLUSIVE")
            
            # Tìm ID của thiết bị theo type
            cur.execute("SELECT device_id FROM device_controller WHERE field_id = ? AND type = ?", (field_id, db_type))
            row = cur.fetchone()
            
            if row:
                device_id = row[0]
                # Cập nhật trạng thái
                cur.execute("UPDATE device_controller SET state = ?, updated_at = CURRENT_TIMESTAMP WHERE device_id = ?", (db_state, device_id))
                conn.commit()
                
                # Gửi lệnh MQTT xuống phần cứng
                device_controller.send_device_command(field_id, db_type, db_state)

                if db_state == "DONE":
                    jobs_to_remove = []
                    # Tìm xem có lịch nào của thiết bị này đang chạy ngầm không
                    for sched_id, job in self.running_jobs.items():
                        if str(job["device_id"]) == str(device_id):
                            row = job["row"]
                            end_date_str = row.get("end_date") # Lấy ngày kết thúc
                            
                            # Tính chu kỳ lặp kế tiếp
                            next_date, next_time = self.calculate_next_date(row)
                            
                            # KIỂM TRA HẾT HẠN KHI TẮT THỦ CÔNG
                            if end_date_str and next_date > end_date_str:
                                self.field.delete_scheduler(sched_id)
                                print(f"[MANUAL OFF - EXPIRED] Lịch {sched_id} đã hết hạn. Đã xóa.")
                            else:
                                self.field.update_scheduler_date(sched_id, next_date, next_time)
                                print(f"[MANUAL OFF] Đã đóng sớm lịch {sched_id} do người dùng tắt tay.")
                                
                            jobs_to_remove.append(sched_id)
                    
                    # Dọn dẹp bộ nhớ
                    for sched_id in jobs_to_remove:
                        del self.running_jobs[sched_id]
                # ========================================================

            else:
                conn.rollback()
                return jsonify({"success": False, "message": "Không tìm thấy thiết bị này trong CSDL"}), 404
                
            conn.close()
            return jsonify({"success": True, "message": f"Đã {action} {device_name}"})
            
        except sqlite3.OperationalError as e:
            print(f"Lỗi khóa DB: {e}")
            return jsonify({"success": False, "message": "Hệ thống đang bận, vui lòng thử lại!"}), 503
        except Exception as e:
            print(f"Lỗi hệ thống: {e}")
            return jsonify({"success": False, "message": f"Lỗi server: {e}"}), 500
	
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
        start = data.get("event_date")
        end = data.get("end_date")
        
        if end and start and end < start:
            return jsonify({"success": False, "message": "End date must be >= Start date"})
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
            row = job["row"]
            end_date_str = row.get("end_date") # Lấy ngày kết thúc từ Database

            # --- PHẦN XỬ LÝ THEO THỜI GIAN (TIME) ---
            if job.get("type") == "time":
                elapsed = (now - job["start_time"]).total_seconds()
                if elapsed < (job.get("duration", 0) * 60):
                    continue

                device_id = job["device_id"]
                self.execute_scheduler(device_id, "DONE")
                
                # 1. Tính ngày giờ lặp lại
                next_date, next_time = self.calculate_next_date(row)
                
                # 2. KIỂM TRA HẾT HẠN
                if end_date_str and next_date > end_date_str:
                    self.field.delete_scheduler(scheduler_id)
                    print(f"[EXPIRED] Lịch {scheduler_id} (Time) đã hết hạn (Next: {next_date} > End: {end_date_str}). Đã xóa.")
                else:
                    self.field.update_scheduler_date(scheduler_id, next_date, next_time)
                
                del self.running_jobs[scheduler_id]
                continue

            # --- PHẦN XỬ LÝ THEO LƯU LƯỢNG (CONSUMPTION) ---
            if job.get("type") != "consumption":
                continue

            sensor_id = job["sensor_id"]
            device_type = job.get("device_type", "valve")
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

            for r in rows:
                ts = r[0]
                value_str = r[1]
                name = r[2]

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

            threshold = float(row.get("consumption") or 0)

            print(f"[CONS] Cảm biến {sensor_id} | Chảy thêm: {total_delta}L | Tổng đã tưới: {job['total_consumption']}L / Mục tiêu: {threshold}L")

            # NẾU ĐÃ TƯỚI ĐỦ (HOẶC VƯỢT) NGƯỠNG
            if threshold > 0 and job["total_consumption"] >= threshold:
                device_id = job["device_id"]
                self.execute_scheduler(device_id, "DONE") # Tắt máy bơm
                
                # 1. Tính ngày lặp lại tiếp theo
                next_date, next_time = self.calculate_next_date(row)
                
                # 2. KIỂM TRA HẾT HẠN
                if end_date_str and next_date > end_date_str:
                    self.field.delete_scheduler(scheduler_id)
                    print(f"[EXPIRED] Lịch {scheduler_id} (Cons) đã hết hạn (Next: {next_date} > End: {end_date_str}). Đã xóa.")
                else:
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

    # 1. Render trang HTML cho Billing Management
    def billing_management_page(self):
        resp = self.require_login()
        if resp: return resp
        role = self.auth.get_role(session.get('username'))
        if role not in ['administrator', 'admin']: return redirect('/')
        
        # Gọi tên file HTML từ config
        return render_template(config.billing_management_page)

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
        result = self.field.add_field(field_id, None, None)

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
    def notifications_page(self):
        resp = self.require_login()
        if resp:
            return resp
        return render_template(config.notification_page)
    
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
    
    def remove_users_from_field(self):
        """API: Xóa danh sách user cụ thể khỏi một ruộng."""
        # 1. Kiểm tra xem người dùng đã đăng nhập chưa
        if 'username' not in session:
            return jsonify({"success": False, "message": "Bạn chưa đăng nhập."}), 401
            
        # 2. Lấy role từ database để kiểm tra quyền Admin (Giống logic các hàm khác)
        username = session['username']
        role = self.auth.get_role(username)
        if role not in ['admin', 'administrator']:
            return jsonify({"success": False, "message": "Bạn không có quyền thực hiện hành động này."}), 403
        
        # 3. Xử lý logic xóa user
        data = request.get_json()
        field_id = data.get('field_id')
        usernames = data.get('usernames') # Đây là một list các username từ JS gửi lên
        
        if not field_id or not usernames:
            return jsonify({"success": False, "message": "Thiếu thông tin Field ID hoặc danh sách User."})
        
        try:
            # Gọi hàm xóa trong field_manager.py
            result = self.field.remove_users_from_field(field_id, usernames)
            return jsonify(result)
        except Exception as e:
            return jsonify({"success": False, "message": f"Lỗi hệ thống: {str(e)}"})
        
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
                    "anomaly_score_low": self.field.get_anomaly_score_low(field_id)[0],
                    "anomaly_score_high": self.field.get_anomaly_score_high(field_id)[0],
                    "step": self.field.get_step(field_id)[0],
                    "anomaly_status": self.field.get_anomaly_status(field_id)[0],
                    "prediction_status": self.field.get_prediction_status(field_id)[0],
                    "AI_automation": self.field.get_AI_Automation(field_id)[0],
                }
            }), 200
        except Exception as e:
            print(f"Lỗi lấy cấu hình AI: {e}")
            return jsonify({"success": False, "message": "Server error"}), 500    
    
    def update_ai_settings(self):
        data = request.get_json()
        field_id = data.get('field_id')
        anomaly_score_low = float(data.get('anomaly_score_low', 0))
        anomaly_score_high = float(data.get('anomaly_score_high', 100))
        step = int(data.get('step', 5))
        anomaly_status = data.get('anomaly_status', 'OFF')
        prediction_status = data.get('prediction_status', 'OFF')
        AI_automation = data.get('AI_automation','OFF')

        # Kiểm tra field_id hợp lệ
        if not field_id:
            return jsonify({"success": False, "message": "Thiếu mã khu vực (field_id)."}), 400

        self.field.set_anomaly_score_low(field_id, anomaly_score_low)
        self.field.set_anomaly_score_high(field_id, anomaly_score_high)
        self.field.set_step(field_id, step)
        self.field.set_anomaly_status(field_id, anomaly_status)
        self.field.set_prediction_status(field_id, prediction_status)
        self.field.set_AI_automation(field_id, AI_automation)

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

    def check_anomaly(self,username):
        result = self.field.check_anomaly(username)
        if isinstance(result, dict):
            return jsonify(result)
        return result
    
    def get_notification_status(self):
        username = session.get('username')
        return jsonify(self.field.get_notification_status(username))
    
    def set_notification_status(self):
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "Không nhận được dữ liệu"})

        status = data.get('status')
        username = session.get('username')
        self.logger.log_set_notification_status(username, status)
        result = self.field.set_notification_status(username, status)
        return jsonify(result)
    
    def set_notification_email_status(self):
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "Không nhận được dữ liệu"})

        status = data.get('status')
        username = session.get('username')
        self.logger.log_set_notification_email_status(username, status)
        result = self.field.set_email_notification_status(username, status)
        return jsonify(result)
    
    def api_get_notifications(self):
        username = request.args.get('username')
        if not username:
            return jsonify({"success": False, "message": "Thiếu username"}), 400
        result = self.field.get_notifications_by_user(username)
        return jsonify(result)
    
    

    def api_mark_read(self):
        data = request.get_json()
        ts = data.get('ts')
        device_id = data.get('device_id')
        username = data.get('username')
        result = self.field.mark_notification_as_read(ts, device_id, username)
        return jsonify(result)

    def api_delete_notification(self):
        from flask import request, jsonify
        data = request.get_json()
        if isinstance(data, list):
            result = self.field.delete_notification(data)
        else:
            # Nếu frontend gửi lên một đối tượng đơn lẻ
            result = self.field.delete_notification(data)
            
        return jsonify(result)
    
    def save_notification(self):
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "Không nhận được dữ liệu"})

        status = data.get('status')
        device_id = data.get('device_id')
        ts = data.get('ts')
        username = data.get('username')
        result = self.field.insert_notification(status, device_id, ts, username)
        notif = self.field.get_notification_status(username)
        if notif["data"]["email_status"] == "ON":
            email = self.auth.get_email(username)
            self.otp.send_notification_email(email, device_id, status, ts, username)
        return jsonify(result)

    def get_current_user(self):
        # Kiểm tra xem user có trong session (đã đăng nhập) chưa
        if 'username' in session:
            username = session['username']
            role = self.auth.get_role(username) 
            
            # Truy vấn thêm email từ userdata.db
            email = "Chưa cập nhật"
            try:
                with sqlite3.connect('userdata.db') as conn:
                    cur = conn.cursor()
                    cur.execute("SELECT email FROM user_data WHERE username = ?", (username,))
                    row = cur.fetchone()
                    if row and row[0]:
                        email = row[0]
            except Exception as e:
                print("Lỗi lấy email:", e)
                
            return jsonify({"success": True, "username": username, "role": role, "email": email})
        else:
            return jsonify({"success": False, "message": "Chưa đăng nhập"}), 401
        
    def change_password(self):
        if 'username' not in session:
            return jsonify({"success": False, "message": "Vui lòng đăng nhập lại"}), 401
        
        data = request.get_json()
        username = session['username']
        old_pw = data.get('old_password')
        new_pw = data.get('new_password')
        
        # 1. Tái sử dụng hàm login để xác thực mật khẩu cũ
        check_login = self.auth.login_user(username, old_pw)
        if not check_login['success']:
            return jsonify({"success": False, "message": "Mật khẩu hiện tại không chính xác!"})
            
        # 2. Tái sử dụng hàm reset_password để lưu mật khẩu mới
        result = self.auth.reset_password(username, new_pw)
        return jsonify(result)
        
# FIELD BILLING & PAYMENT
    def create_billing(self):
        data = request.get_json()
        field_id = data.get("field_id")
        title = data.get("title")
        amount = data.get("amount")
        return self.field.create_billing_item(field_id, title, amount)

    def api_admin_get_all_bills(self):
        role = self.auth.get_role(session.get('username'))

        if role not in ['administrator', 'admin']:
            return jsonify({
                "success": False,
                "message": "Không có quyền truy cập"
            }), 403

        result = self.field.get_all_bills()

        status_code = 200 if result.get("success") else 500
        return jsonify(result), status_code
        
    def get_unpaid_bills(self):
        field_ids = request.get_json().get("field_ids", [])
        return self.field.get_unpaid_bills(field_ids)
    
    def mark_bills_paid(self):
        field_id = request.get_json().get("field_id")
        return self.field.mark_bills_as_paid(field_id)
    
    def delete_bill(self):
        bill_id = request.get_json().get("bill_id")
        return self.field.delete_billing_item(bill_id)
    
    def create_payment(self):
        username = session.get("username")
        field_id = request.get_json().get("field_id")
        user_id = self.auth.get_user_id(username)
        bills_result = self.field.get_unpaid_bills(field_id)
        bills = bills_result["data"]

        if not bills:
            return {
                "success": False,
                "message": "Không có hóa đơn chưa thanh toán"
            }
        total = sum([b[3] for b in bills])
        momo_data, order_id, request_id = payment.create_momo_payment(total)
        if momo_data.get("resultCode") != 0:
            return {
                "success": False,
                "message": "Tạo thanh toán MoMo thất bại",
                "data": momo_data
            }
        self.field.create_transaction(
            user_id,
            field_id,
            order_id,
            request_id,
            total
        )
        return {
            "success": True,
            "order_id": order_id,
            "amount": total,
            "payUrl": momo_data.get("payUrl")
        }
    
    def get_payment_status(self):
        order_id = request.get_json().get("order_id")
        return self.field.get_transaction_by_order_id(order_id)
    
    def update_payment_status(self):
        data = request.get_json()
        order_id = data.get("order_id")
        status = data.get("status")
        raw_response = data.get("raw_response")
        result = self.field.update_transaction_status(order_id, status)
        if status == "success":
            txn = self.field.get_transaction_by_order_id(order_id)
            transaction = txn["data"] if txn["success"] else None
            if transaction:
                field_id = transaction[1]
                request_id = transaction[3]
                amount = transaction[4]
                username = session.get("username")
                user_id = self.auth.get_user_id(username)
                bills = self.field.get_unpaid_bills(field_id)["data"]
                self.auth.save_payment_history(user_id, field_id, order_id, request_id, amount, bills, raw_response)
                self.field.mark_bills_as_paid(field_id)
        return result
      
    def momo_ipn(self):
        data = request.json or {}

        order_id = data.get("orderId")
        result_code = data.get("resultCode")

        status = "success" if result_code == 0 else "failed"

        return self.update_payment_status_internal(order_id, status, data)
    
    def update_payment_status_internal(self, order_id, status, raw_response=None):
        result = self.field.update_transaction_status(order_id, status)
        
        if status == "success":
            txn = self.field.get_transaction_by_order_id(order_id)
            
            # Xử lý an toàn: Lấy dữ liệu giao dịch dù trả về là List hay Tuple
            transaction = txn["data"]
            if isinstance(transaction, list) and len(transaction) > 0:
                transaction = transaction[0]
                
            print("Dữ liệu Transaction an toàn:", transaction)
            
            if transaction:
                user_id = transaction[10]    
                field_id = transaction[1]
                # SỬA LỖI 1: Lấy đúng vị trí số 3 thay vì 4
                request_id = transaction[3]  
                amount = transaction[5]
                
                bills = self.field.get_unpaid_bills(field_id)["data"]
                
                # SỬA LỖI 2: Ép kiểu raw_response thành chuỗi (String) trước khi lưu
                if isinstance(raw_response, dict):
                    response_str = json.dumps(raw_response)
                else:
                    response_str = str(raw_response)
                
                # Lưu vào userdata.db
                self.auth.save_payment_history(user_id, field_id, order_id, request_id, amount, bills, response_str)
                
                self.field.mark_bills_as_paid(field_id)
                self.logger.log_payment_transaction(user_id, field_id, order_id, request_id, amount, bills, response_str)
                
        return result

# USER TRANSACTION HISTORY
################################################################################################################################        
    
    def get_transactions_of_user(self):
        username = session.get('username')
        user_id = self.auth.get_user_id(username)
        
        with self.field.connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM payment_transactions WHERE user_id = ? AND status = 'success' ORDER BY paid_at DESC", (user_id,))
            db_rows = cur.fetchall()

        # Hàm phụ trợ: Chuyển đổi chuỗi thời gian từ GMT+0 sang GMT+7
        def to_gmt7(time_str):
            if not time_str:
                return ""
            try:
                # Cắt chuỗi lấy đúng định dạng YYYY-MM-DD HH:MM:SS (bỏ phần mili-giây nếu có)
                clean_str = str(time_str).strip()[:19]
                dt = datetime.strptime(clean_str, "%Y-%m-%d %H:%M:%S")
                # Cộng thêm 7 tiếng
                dt_gmt7 = dt + timedelta(hours=7)
                return dt_gmt7.strftime("%Y-%m-%d %H:%M:%S")
            except:
                return time_str # Trả về nguyên bản nếu bị lỗi parse

        rows = []
        for r in db_rows:
            mapped = [
                r[0],             # 0: id
                r[10],            # 1: user_id
                r[1],             # 2: field_id
                r[2],             # 3: order_id
                r[3],             # 4: request_id
                r[5],             # 5: amount
                r[6],             # 6: status
                r[9],             # 7: raw_response
                to_gmt7(r[7]),    # 8: created_at (Đã +7)
                to_gmt7(r[8]),    # 9: updated_at/paid_at (Đã +7)
                to_gmt7(r[8])     # 10: paid_at (Đã +7)
            ]
            rows.append(mapped)

        return jsonify({"success": True, "data": rows})
    
    def get_transactions_items(self):
        data = request.get_json()
        transaction_id = data.get("transaction_id")
        
        try:
            rows = []
            # Truy vấn trực tiếp bảng user_payment_transaction_items
            # Lấy billing_title (tên hóa đơn) và billing_amount (số tiền)
            with self.auth.user_manager.connect() as conn: # Lưu ý: kiểm tra xem bảng này nằm ở userdata.db hay field.db để gọi conn cho đúng
                cur = conn.cursor()
                cur.execute("""
                    SELECT id, transaction_id, billing_title, billing_amount 
                    FROM user_payment_transaction_items 
                    WHERE transaction_id = ?
                """, (transaction_id,))
                db_rows = cur.fetchall()
                
                for r in db_rows:
                    rows.append([r[0], r[1], r[2], r[3]])
                    
            return jsonify({"success": True, "data": rows})
        except Exception as e:
            print(f"Lỗi API lấy chi tiết giao dịch: {e}")
            return jsonify({"success": False, "message": "Không tìm thấy chi tiết"})

# FIELD SERVICE PLAN BILLING
################################################################################################################################ 

    def run_service_plan_billing(self):
        plans = self.field.get_active_service_plans()
        today = datetime.now().date()
        for plan in plans:
            plan_id = plan["id"]
            field_id = plan["field_id"]
            daily_price = plan["daily_price"]
            expired_date = datetime.strptime(plan["expired_date"], "%Y-%m-%d").date()
            new_amount = plan["accumulated_amount"] + daily_price
            self.field.update_accumulated_amount(plan_id, new_amount)
            if today >= expired_date:
                self.field.create_billing_item(
                    field_id,
                    "Phí dịch vụ tự động",
                    new_amount
                )
                self.field.expire_service_plan(plan_id)
        return {
            "success": True,
            "message": "Đã chạy tính phí dịch vụ"
        }
    
    def create_service_plan(self):
        data = request.get_json()

        field_id = data.get("field_id")
        service_days = data.get("service_days")
        daily_price = data.get("daily_price")
        self.logger.log_create_service_plan(field_id, service_days, daily_price)
        return self.field.create_service_plan(
            field_id,
            service_days,
            daily_price
        )
    
    def update_service_plan(self):
        data = request.get_json()
        plan_id = data.get("plan_id")
        service_days = data.get("service_days")
        daily_price = data.get("daily_price")
        self.logger.log_update_service_plan(plan_id, service_days, daily_price)
        return self.field.update_service_plan(
            plan_id,
            service_days,
            daily_price
        )
    
    def delete_service_plan(self):
        data = request.get_json()
        plan_id = data.get("plan_id")
        self.logger.log_delete_service_plan(plan_id)
        return self.field.delete_service_plan(plan_id)
    
    def get_service_plans(self):
        data = request.get_json()
        field_ids = data.get("field_ids", [])
        if not field_ids:
            return jsonify({
                "success": False,
                "message": "Thiếu mã ruộng (field_ids)"
            })
        result = self.field.get_service_plans_by_fields(field_ids)
        return jsonify(result)
    



# AI AUTOMATION
################################################################################################################################ 
    
    def create_automation_field(self, field_id, target_type, action):
        selected = self.select_event_type(field_id, target_type, action)
        if not selected:
            return {
                "success": False,
                "message": "Không tìm thấy thiết bị phù hợp để tạo automation"
            }
        device_id = selected["device_id"]
        event_type = selected["event_type"]
        now = datetime.now()
        event_date = now.strftime("%Y-%m-%d")
        end_date = event_date
        event_time = now.strftime("%H:%M:%S")
        name = f"{field_id}_automation"
        self.field.create_scheduler(field_id, device_id, name, event_date, end_date, event_time, event_type, "time", duration=1)
        result  = self.field.get_scheduler_id_by_name(name)
        scheduler_id = None
        if result.get("success"):
            scheduler_id = result.get("scheduler_id")
        return {
            "success": True,
            "message": "Tạo automation scheduler thành công",
            "data": {
                "field_id": field_id,
                "device_id": device_id,
                "scheduler_id": scheduler_id,
                "target_type": target_type,
                "action": action
            }
        }

    def select_event_type(self, field_id, target_type, action):
        result = self.field.get_devices_controller_by_field(field_id)
        if not result["success"]:
            return None
        devices = result["devices"]
        device_priority = []

        if target_type == "temperature" and action == "decrease":
            device_priority = ["cooling_pad", "vent", "fan"]
        elif target_type == "temperature" and action == "increase":
            device_priority = ["heater"]
        elif target_type == "moisture" and action == "increase":
            device_priority = ["valve"]
        else:
          return None

        for device_type in device_priority:
            for device in devices:
                if device[2] == device_type:
                    return {
                        "device_id": device[0],
                        "event_type": device_type
                    }
        return None
    
    def automation_trigger(self):
        actions = self.field.handle_anomaly_automation()
        running_device_ids = {str(j["device_id"]) for j in self.running_jobs.values()}

        for action in actions:
            field_id = action["field_id"]
            target_type = action["target_type"]
            act = action["action"]

            # Tìm thiết bị phù hợp
            selected = self.select_event_type(field_id, target_type, act)
            if not selected: continue

            
            device_id = str(selected["device_id"])
            if device_id in running_device_ids: continue

            # Kiểm tra thiết bị đang rảnh
            dev_info = self.field.get_device_controller_by_id(field_id, device_id)
            if not dev_info.get("success") or dev_info["device"][3] != "DONE": continue

            self.create_automation_field(field_id,target_type,act)

    
#################################################################################################################################

from notification import NotificationManager
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
notifier = NotificationManager(field_db=field, auth_manager=auth, email_manager=otp)
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

def job_reset_daily():
    with app.app_context():
        routes.reset_daily_cache()
        routes.run_service_plan_billing()

def job_service_plan_billing():
    with app.app_context():
        routes.run_service_plan_billing()

def job_anomaly_trigger():
    print("[DEBUG] ---> Tiến trình quét dị thường (5s) vừa thức dậy!")
    with app.app_context():
        try:
            active_users = field.get_users_with_notifications_enabled() 
            
            if not active_users:
                print("[DEBUG] Không có user nào bật thông báo. Bỏ qua quét.")
                return 

            # 2. Duyệt qua từng user để check dị thường
            for username in active_users:
                data = field.check_anomaly(username) 
                
                if not data or not data.get("success"):
                    continue
                    
                print(f"[DEBUG] Cảnh báo mới cho {username} - Dữ liệu: {data}")
                
                data['username'] = username 
                notifier.trigger_anomaly_alert(data)
                print(f"[DEBUG] Đã đẩy dữ liệu của {username} vào NotificationManager.")
                
        except Exception as e:
            print(f"[BACKGROUND ERROR] Lỗi quét dị thường: {e}")

def automation():
    with app.app_context():
        routes.automation_trigger()

server.add_route('/api/billing/create', routes.create_billing, methods=['POST'])
server.add_route('/api/admin/all_bills', routes.api_admin_get_all_bills, methods=['GET'])
server.add_route('/api/billing/unpaid', routes.get_unpaid_bills, methods=['POST'])
server.add_route('/api/billing/mark_paid', routes.mark_bills_paid, methods=['POST'])
server.add_route('/api/billing/delete', routes.delete_bill, methods=['POST'])
server.add_route('/api/payment/create', routes.create_payment, methods=['POST'])
server.add_route('/api/payment/status', routes.get_payment_status, methods=['POST'])
server.add_route('/api/payment/update', routes.update_payment_status, methods=['POST'])
server.add_route('/ipn', routes.momo_ipn, methods=['POST'])
server.add_route('/api/payment/history', routes.get_transactions_of_user, methods=['GET'])
server.add_route('/api/payment/items', routes.get_transactions_items, methods=['POST'])
server.add_route('/api/user/transactions', routes.get_transactions_of_user, methods=['GET', 'POST'])

server.add_route('/api/service_plan/create', routes.create_service_plan, methods=['POST'])
server.add_route('/api/service_plan/update', routes.update_service_plan, methods=['POST'])
server.add_route('/api/service_plan/delete', routes.delete_service_plan, methods=['POST'])
server.add_route('/api/service_plan/list', routes.get_service_plans, methods=['POST'])
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
server.add_route('/api/user/change_password', routes.change_password, methods=['POST'])
server.add_route('/profile', routes.profile_page, methods=['GET'])
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
server.add_route('/api/get_notifications', routes.api_get_notifications, methods=['GET'])
server.add_route('/notifications', routes.notifications_page, methods=['GET'])
server.add_route('/api/mark_read', routes.api_mark_read, methods=['POST'])
server.add_route('/api/delete_notifications', routes.api_delete_notification, methods=['POST'])
server.add_route('/api/get_notification_settings', routes.get_notification_status, methods=['GET'])
server.add_route('/api/set_notification_status', routes.set_notification_status, methods=['POST'])
server.add_route('/api/set_notification_email_status', routes.set_notification_email_status, methods=['POST'])

server.add_route('/api/update_ai_settings', routes.update_ai_settings, methods=['POST'])
server.add_route('/api/get_ai_settings', routes.get_ai_settings, methods=['GET'])
server.add_route('/api/check_anomaly', routes.check_anomaly, methods=['GET'])
server.add_route('/admin_management', routes.management_page, methods=['GET'])
server.add_route('/admin_management/users', routes.user_management_page, methods=['GET'])
server.add_route('/api/admin/users', routes.api_admin_users, methods=['GET'])
server.add_route('/api/admin/delete_users', routes.api_admin_delete_users, methods=['POST'])
server.add_route('/admin_management/greenhouses', routes.greenhouse_management_page, methods=['GET'])
server.add_route('/admin_management/billing', routes.billing_management_page, methods=['GET'])
server.add_route('/api/admin/greenhouses', routes.api_admin_greenhouses, methods=['GET'])
server.add_route('/api/admin/add_greenhouse', routes.api_admin_add_greenhouse, methods=['POST'])
server.add_route('/api/admin/clear_fields', routes.api_admin_clear_fields, methods=['POST'])
server.add_route('/api/admin/edit_greenhouse', routes.api_admin_edit_greenhouse, methods=['POST'])
server.add_route('/api/admin/delete_greenhouse_fields', routes.api_admin_delete_greenhouse_fields, methods=['POST'])
server.add_route('/api/admin/remove_users_from_field', routes.remove_users_from_field, methods=['POST'])

server.add_route('/api/get_schedulers', routes.get_schedulers_by_field, methods=['GET'])
server.add_route('/api/create_scheduler', routes.create_scheduler, methods=['POST'])
server.add_route('/api/update_scheduler', routes.update_scheduler, methods=['POST'])
server.add_route('/api/delete_scheduler', routes.delete_scheduler, methods=['POST'])

scheduler.add_job(job_reset_daily, 'cron', hour=0, minute=0)
scheduler.add_job(job_update_status, 'interval', seconds=10)
scheduler.add_job(job_check_scheduler,'interval',seconds=1,max_instances=1,coalesce=True)
scheduler.add_job(job_service_plan_billing,trigger='cron',hour=0,minute=0,id='service_plan_billing_job',replace_existing=True)
scheduler.add_job(automation, 'interval', seconds=10)
scheduler.add_job(job_anomaly_trigger, 'interval', seconds=5)
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
        server.run(port=5000)
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