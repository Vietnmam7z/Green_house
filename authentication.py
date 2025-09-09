from user_manager import UserManager
from logger import UserLogger
from email_otp import OTPManager
import hashlib
import datetime

class Authentication:
    def __init__(self, user_manager: UserManager, logger: UserLogger, email_otp: OTPManager):
        self.user_manager = user_manager
        self.logger = logger
        self.email_otp = email_otp

    def login_user(self, username: str, password: str):
        if not self.user_manager.find_user(username):
            return {"success": False, "message": "Người dùng không tồn tại."}

        hashed_input = hashlib.sha256(password.encode()).hexdigest()
        stored_password = self.user_manager.get_password(username)

        if hashed_input != stored_password:
            return {"success": False, "message": "Sai mật khẩu."}

        self.user_manager.set_status(username, True)
        self.user_manager.set_last_active(username)
        self.logger.log_login(username)
        
        return {"success": True, "message": f"Đăng nhập thành công: {username}"}
    
    def register_user(self, username: str, password: str, email: str, role="user"):
        if self.user_manager.find_user(username):
            return {"success": False, "message": "Tên người dùng đã tồn tại."}
        
        if self.user_manager.find_email(email):
            return {"success": False, "message": "Email đã được sử dụng."}
                    
        self.user_manager.add_user(username, password, email, role)
        self.logger.log_register(username)
        
        return {"success": True, "message": f"Đăng ký thành công"}

    def change_password(self, username: str, old_password: str, new_password: str):
        if not self.user_manager.find_user(username):
            return {"success": False, "message": "Người dùng không tồn tại."}
        
        current_hashed = self.user_manager.get_password(username)
        input_hashed = hashlib.sha256(old_password.encode()).hexdigest()

        if input_hashed != current_hashed:
            return {"success": False, "message": "Mật khẩu cũ không đúng."}

        new_hashed = hashlib.sha256(new_password.encode()).hexdigest()
        self.user_manager.set_password(username, new_password)
        self.logger.log_change_password(username)
        
        return {"success": True, "message": "Đổi mật khẩu thành công."}

    def reset_password(self, username: str, new_password: str):
        self.logger.log_reset_password(username)
        return self.user_manager.set_password(username, new_password)

    def delete_user(self, username: str):
        self.user_manager.delete_user(username)
        self.logger.log_delete_user(username)
        return self.user_manager.get_all_usernames()

    def offline_user(self, username: str):
        self.logger.log_offline(username)
        self.user_manager.set_status(username, False)
       
    def forget_password(self, email: str):
        username = self.user_manager.find_email(email)
        if not username:
            return {"success": False, "message": "Email không tồn tại."}
        self.email_otp.update_otp(email)
        self.email_otp.send_otp_email(email)
        
    def change_email(self, email: str):
        username = self.user_manager.find_email(email)
        if not username:
            return {"success": False, "message": "Email không tồn tại."}
        self.email_otp.update_otp(email)
        self.email_otp.send_otp_email(email)         
        
    def confirm_otp(self, otp: str):
        return self.email_otp.confirm_otp(otp)
        

