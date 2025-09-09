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
        