from notification import NotificationManager
from webserver import FlaskServer
from user_manager import UserManager
from logger import UserLogger
from email_otp import OTPManager
from sensor_API import Sensor_API
from field_manager import FieldDB
from logger import UserLogger
from apscheduler.schedulers.background import BackgroundScheduler
from authentication import Authentication
from route import Routes
from flask import Flask

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
server.add_route('/admin_management/rental_service', routes.rental_service_page, methods=['GET'])
server.add_route('/api/admin/all_service_plans', routes.api_admin_get_all_service_plans, methods=['GET'])

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
server.add_route('/api/send_chart', routes.send_chart, methods=['POST'])
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