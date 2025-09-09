from user_manager import UserManager
from email.message import EmailMessage
import secrets
import datetime
import smtplib
import config

class OTPManager:
    def __init__(self, user_manager: UserManager):
        self.user_manager = user_manager  

    def generate_otp(self):
        otp = str(secrets.randbelow(1000000)).zfill(6)
        expires_at = datetime.datetime.utcnow() + datetime.timedelta(minutes=5)
        return otp, expires_at

    def update_otp(self, email: str):
        otp, expires_at = self.generate_otp()
        self.user_manager.add_otp(email,otp,expires_at)
        
    def send_otp_email(self, receiver_email: str):
        sender_email = config.sender_email
        app_password = config.app_password
        otp_code = self.user_manager.get_otp(receiver_email)
        
        subject = "🔐 Mã xác nhận OTP của bạn"
        body = f"""
        Xin chào,

        Đây là mã OTP của bạn: {otp_code}
        Mã này có hiệu lực trong vòng 5 phút.

        Nếu bạn không yêu cầu mã này, vui lòng bỏ qua email này.

        Trân trọng,
        Hệ thống xác thực
        """


        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = sender_email
        msg["To"] = receiver_email
        msg.set_content(body)


        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
                smtp.login(sender_email, app_password)
                smtp.send_message(msg)
            return True
        except Exception as e:
            print("Lỗi gửi email:", e)
            return False

    def confirm_otp(self, otp: str):
        used = self.user_manager.get_otp_used(otp)
        if used is None:
            return {"success": False, "message": "Mã OTP không tồn tại."}
        if used:
            return {"success": False, "message": "Mã OTP đã được sử dụng."}

        expires_at = datetime.datetime.fromisoformat(self.user_manager.get_expire(otp))
        now = datetime.datetime.utcnow()
        if expires_at <= now:
            return {"success": False, "message": "Mã OTP đã hết hạn."}

        self.user_manager.set_otp_used(otp)

        return {"success": True, "message": "Mã OTP hợp lệ và đã được xác nhận."}

