import time
from datetime import datetime

class NotificationManager:
    def __init__(self, field_db, auth_manager, email_manager=None):
        self.field = field_db
        self.auth = auth_manager
        self.email_manager = email_manager

    def trigger_anomaly_alert(self, anomaly_data):
        print(f"[DEBUG-NOTIFY] 1. Nhận dữ liệu kiểm tra: {anomaly_data}")
        
        if not anomaly_data or not isinstance(anomaly_data, dict) or not anomaly_data.get("success"):
            return

        score = float(anomaly_data.get("anomaly_score", 0))
        device_id = anomaly_data.get("device_id")
        
        # Chỉ nhận 1 username duy nhất
        target_field_id, target_field_name, target_username = self._resolve_target_info(
            anomaly_data.get("field_id"), 
            device_id,
            anomaly_data.get("username"),
            anomaly_data.get("field_name")
        )

        print(f"[DEBUG-NOTIFY] 2. Phân tích: field_id={target_field_id}, user={target_username}")

        # Kiểm tra chuỗi rỗng thay vì mảng
        if not target_username:
            print("[DEBUG-NOTIFY] -> Không tìm được Username nào. Dừng!")
            return

        low_score = 0.25
        high_score = 0.85
        if target_field_id:
            low_val = self.field.get_anomaly_score_low(target_field_id)
            high_val = self.field.get_anomaly_score_high(target_field_id)
            low_score = float(low_val[0]) if low_val else 0.25
            high_score = float(high_val[0]) if high_val else 0.85

        status = None
        if score >= high_score:
            status = "CRITICAL"
        elif score >= low_score:
            status = "WARNING"

        print(f"[DEBUG-NOTIFY] 3. Điểm AI: {score} | Ngưỡng: {low_score}-{high_score} | Trạng thái: {status}")

        # Xử lý trực tiếp cho 1 người
        if status:
            self._process_alert(device_id, target_field_name, target_username, status)

    def _process_alert(self, device_id, field_name, username, status):
        print(f"[DEBUG-NOTIFY] 4. Bắt đầu xử lý cho User: {username}")
        ts = int(time.time() * 1000)
        
        # 1. Lấy toàn bộ cấu hình thông báo của người dùng
        notif_setting = self.field.get_notification_status(username)
        print(f"[DEBUG-NOTIFY] 5. Cấu hình gửi thông báo của user: {notif_setting}")
        
        web_status = "OFF"
        email_status = "OFF"
        
        if notif_setting:
            if "data" in notif_setting and isinstance(notif_setting["data"], dict):
                web_status = notif_setting["data"].get("status", "OFF")
                email_status = notif_setting["data"].get("email_status", "OFF")
            else:
                web_status = notif_setting.get("status", "OFF")
                email_status = notif_setting.get("email_status", "OFF")

        # =========================================================
        # 2. XỬ LÝ THÔNG BÁO WEB (Kiểm tra nút gạt Web)
        # =========================================================
        if web_status == "ON":
            try:
                self.field.insert_notification(status, device_id, ts, username)
                print(f"[DEBUG-NOTIFY] -> Đã lưu thành công vào Database (Web Alert: ON)")
            except Exception as e:
                print(f"[DEBUG-NOTIFY] -> LỖI khi lưu Database: {e}")
        else:
            print(f"[DEBUG-NOTIFY] -> BỎ QUA LƯU DB: User đã tắt nhận thông báo trên Web.")

        # =========================================================
        # 3. XỬ LÝ GỬI EMAIL (Kiểm tra nút gạt Email)
        # =========================================================
        if email_status == "ON":
            email = None
            try:
                email = self.auth.user_manager.get_email_by_username(username)
            except Exception as e:
                print(f"[DEBUG-NOTIFY] -> Lỗi lấy email: {e}")

            print(f"[DEBUG-NOTIFY] 6. Chuẩn bị gửi email tới: {email}")
            
            if email and self.email_manager and hasattr(self.email_manager, 'send_field_alert_email'):
                success = self.email_manager.send_field_alert_email(
                    receiver_email=email,
                    field_name=field_name,
                    device_name=device_id,
                    status=status,
                    username=username
                )
                if success:
                    print(f"[DEBUG-NOTIFY] -> THÀNH CÔNG: Đã gửi email")
                else:
                    print(f"[DEBUG-NOTIFY] -> THẤT BẠI: Hàm gửi mail lỗi")
            else:
                print(f"[DEBUG-NOTIFY] -> THẤT BẠI: Thiếu email hoặc chưa cấu hình email_manager")
        else:
            print(f"[DEBUG-NOTIFY] -> BỎ QUA GỬI MAIL: User đã tắt tính năng nhận Email.")

    def _resolve_target_info(self, field_id, device_id, username_from_data=None, field_name_from_data=None):
        field_name = field_name_from_data if field_name_from_data else "Khu vực không tên"
        
        # Khởi tạo biến lưu ĐÚNG 1 username
        target_username = username_from_data 

        all_fields = []
        if hasattr(self.field, 'api_admin_greenhouses'):
            all_fields = self.field.api_admin_greenhouses()

        if not field_id and field_name_from_data:
            for f_id, f_name, u_name in all_fields:
                if f_name and str(f_name).strip() == str(field_name_from_data).strip():
                    field_id = f_id
                    break 

        if not field_id:
            if hasattr(self.field, 'get_device_sensor_mapping'):
                sensor_info = self.field.get_device_sensor_mapping(device_id)
                if sensor_info and isinstance(sensor_info, dict) and sensor_info.get("success"):
                    field_id = sensor_info.get("data", {}).get("field_id")
            
            if not field_id and hasattr(self.field, 'get_device_controller_by_device_id'):
                dev_info = self.field.get_device_controller_by_device_id(device_id)
                if dev_info and isinstance(dev_info, dict) and dev_info.get("success"):
                    field_id = dev_info.get("data", {}).get("field_id")

        if field_id:
            for f_id, f_name, u_name in all_fields:
                if str(f_id) == str(field_id):
                    if not field_name_from_data and f_name and str(f_name).strip() != "":
                        field_name = f_name
                    # Nếu chưa có target_username thì gán giá trị u_name tìm được (chỉ gán 1 lần)
                    if not target_username and u_name:
                        target_username = u_name

        return field_id, field_name, target_username