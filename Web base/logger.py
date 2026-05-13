import logging
from logging.handlers import RotatingFileHandler
import config

class UserLogger:
    def __init__(self, log_file=config.log_file, max_bytes=1_000_000, backup_count=3):
        self.logger = logging.getLogger("UserActivity")
        self.logger.setLevel(logging.INFO)

        handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,       
            backupCount=backup_count, 
            encoding="utf-8"
        )

        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)

        if not self.logger.hasHandlers():
            self.logger.addHandler(handler)

    def log_login(self, username: str):
        self.logger.info(f"Đăng nhập: {username}")

    def log_register(self, username: str):
        self.logger.info(f"Đăng ký: {username}")

    def log_logout(self, username: str):
        self.logger.info(f"Đăng xuất: {username}")

    def log_offline(self, username: str):
        self.logger.info(f"Offline: {username}")

    def log_delete_user(self, username: str):
        self.logger.warning(f"Xóa tài khoản: {username}")

    def log_change_password(self, username: str):
        self.logger.info(f"Đổi mật khẩu: {username}")

    def log_reset_password(self, username: str):
        self.logger.warning(f"Đặt lại mật khẩu: {username}")

    def log_add_field(self, field_id: str):
        self.logger.warning(f"Tạo ruộng: {field_id}")

    def log_delete_field(self, field_id: str):
        self.logger.warning(f"Xóa ruộng: {field_id}")

    def log_rename_field(self, old_field_id: str, new_field_id: str):
        self.logger.warning(f"Đổi tên ruộng {old_field_id} thành {new_field_id}")

    def log_add_device(self, device_name: str):
        self.logger.warning(f"Tạo thiết bị: {device_name}")

    def log_delete_device(self, device_name: str):
        self.logger.warning(f"Xóa thiết bị: {device_name}")

    def log_rename_device(self, old_device_name: str, new_device_name: str):
        self.logger.warning(f"Đổi tên thiết bị {old_device_name} thành {new_device_name}")

    def log_add_user_to_field(self, field_id: str,  username: str,):
        self.logger.warning(f"Thêm user {username} vào ruộng {field_id}")
    
    def log_remove_user_from_field(self, field_id: str, username: str): 
        self.logger.warning(f"Xóa user {username} khỏi ruộng {field_id}")

    def log_clear_field(self, field_id: str):
        self.logger.warning(f"Dọn dẹp dữ liệu ruộng {field_id}")

    def log_set_anomoly_score_low(self, field_id: str):
        self.logger.warning(f"Đặt điểm bất thường thấp cho ruộng {field_id}")
    
    def log_set_anomoly_score_high(self, field_id: str):
        self.logger.warning(f"Đặt điểm bất thường cao cho ruộng {field_id}")

    def log_set_prediction_status(self, field_id: str, status: str):
        self.logger.warning(f"Đặt trạng thái dự đoán cho ruộng {field_id} thành {status}")

    def log_set_anomoly_prediction_status(self, field_id: str, status: str):
        self.logger.warning(f"Đặt trạng thái dự đoán bất thường cho ruộng {field_id} thành {status}")   

    def log_set_notification_status(self, field_id: str, status: str):
        self.logger.warning(f"Đặt trạng thái thông báo cho ruộng {field_id} thành {status}")

    def log_set_device_state(self, field_id: str, device_type: str, state: str):
        self.logger.warning(f"Đặt trạng thái thiết bị {device_type} của ruộng {field_id} thành {state}")

    def log_create_job(self, job_id: str, field_id: str, device_id: str, threshold: float, event_date: str, event_time: str):
        self.logger.warning(f"Tạo công việc {job_id} cho ruộng {field_id} vào ngày {event_date} lúc {event_time} với thiết bị {device_id} và ngưỡng {threshold}")

    def log_create_job_no_threshold(self, job_id: str, field_id: str, device_id: str, duration: int, event_date: str, event_time: str):
        self.logger.warning(f"Tạo công việc {job_id} cho ruộng {field_id} vào ngày {event_date} lúc {event_time} với thiết bị {device_id} trong {duration} giây")

    def log_delete_job(self, job_id: str):
        self.logger.warning(f"Xóa công việc {job_id}")
    
    def log_update_job(self, job_id: str, field_id: str, device_id: str, threshold: float, event_date: str, event_time: str):
        self.logger.warning(f"Cập nhật công việc {job_id} cho ruộng {field_id} vào ngày {event_date} lúc {event_time} với thiết bị {device_id} và ngưỡng {threshold}")

    def log_update_job_no_threshold(self, job_id: str, field_id: str, device_id: str, duration: int, event_date: str, event_time: str):
        self.logger.warning(f"Cập nhật công việc {job_id} cho ruộng {field_id} vào ngày {event_date} lúc {event_time} với thiết bị {device_id} trong {duration} giây")   

    def log_set_notification_email_status(self, username: str, status: str):
        self.logger.warning(f"Đặt trạng thái email thông báo cho user {username} thành {status}")
    
    def log_set_automatic_status(self, field_id: str, status: str):
        self.logger.warning(f"Đặt trạng thái tự động cho ruộng {field_id} thành {status}")

    def log_payment_transaction(self, user_id: int, field_id: str, order_id: str, request_id: str, amount: float, bills: list, raw_response=None):
        self.logger.info(f"Giao dịch thanh toán - User ID: {user_id}, Field ID: {field_id}, Order ID: {order_id}, Request ID: {request_id}, Amount: {amount}, Bills: {bills}, Raw Response: {raw_response}")

    def log_create_service_plan(self, field_id: str, service_days: int, daily_price: float):
        self.logger.info(f"Tạo gói dịch vụ - Field ID: {field_id}, Service Days: {service_days}, Daily Price: {daily_price}")

    def log_update_service_plan(self, field_id: str, service_days: int, daily_price: float):
        self.logger.info(f"Cập nhật gói dịch vụ - Field ID: {field_id}, Service Days: {service_days}, Daily Price: {daily_price}")

    def log_delete_service_plan(self, field_id: str):
        self.logger.info(f"Xóa gói dịch vụ - Field ID: {field_id}")