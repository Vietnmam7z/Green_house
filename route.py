from flask import request, session, redirect, render_template, jsonify
from authentication import Authentication
from email_otp import OTPManager
import config

class Routes:
    def __init__(self, auth: Authentication, otp: OTPManager):
        self.auth = auth
        self.otp = otp
        
    def require_login(self):
        if 'username' not in session:
            return redirect('/login')
        
    def redirect_if_logged_in(self):
        if 'username' in session:
            return redirect('/')   

    def reset_password_page(self):
        username = session.get('username')
        if not session.get(f"{username}_allow_reset"):
            return redirect('/forgot-password')  

    def pop_reset_session(self):
        username = session.get('username')
        session.pop(f"{username}_allow_reset", None)

# HOME PAGE
################################################################################################################################        
        
    def home_page(self):
        if self.require_login():
            return self.require_login() 
        username = session.get('username')
        return render_template(config.home_page, username=username)
    
    def logout(self):
        username = session.get('username')
        self.auth.logout_user(username)
        if username:
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
        else:
            return render_template(config.forgot_password_page)

    def forgot_password(self, email: str):
        
        result = self.auth.confirm_email(email)

        if result['success'] is True:           
            username = session.get('user_name')
            session[f"{username}_allow_reset"] = True
            self.otp.update_otp(email)  
            self.otp.send_otp_email(email)
            

        return jsonify({
        "success": result['success'],
        "message": result['message'],
        "redirect": "/login"
    })
#################################################################################################################################

 # SEND OTP PAGE
    def reset_password_page(self):
        if self.redirect_if_logged_in():
            return self.redirect_if_logged_in()
        else:
            return render_template(config.reset_password_page)
        
            
    def comfirm_OTP(self, OTP: str):

        username = session.get('username')
        result = otp.confirm_otp(OTP, username)
        
        if result['success']:
            return jsonify({
                "success": result['success'],
                "message": result['message'],
                "redirect": "/reset-password"
            })
    
        else:
            return jsonify({
                "success": result['success'],
                "message": result['message']
            })
        
    def reset_password(self):
        username = session.get('username')
        new_password = request.form.get('new_password')
        
        result = self.auth.reset_password(username, new_password)

        if result['success']:
            self.pop_reset_session()
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


from webserver import FlaskServer
from user_manager import UserManager
from logger import UserLogger

manager = UserManager()
log = UserLogger()
otp = OTPManager(manager)
auth = Authentication(manager,log,otp)
server = FlaskServer()
routes = Routes(auth,otp)

server.add_route('/', routes.home_page, methods=['GET'])
server.add_route('/login', routes.login_page, methods=['GET'])
server.add_route('/login', routes.login, methods=['POST'])
server.add_route('/logout', routes.logout, methods=['POST'])
server.add_route('/signup', routes.signup_page, methods=['GET'])
server.add_route('/signup', routes.signup, methods=['POST'])
server.add_route('/forgot-password', routes.forgot_password_page, methods=['GET'])
server.add_route('/forgot-password', routes.forgot_password, methods=['POST'])
server.add_route('/reset-password', routes.reset_password_page, methods=['GET'])
server.add_route('/reset-password', routes.reset_password, methods=['POST'])

if __name__ == '__main__':
    server.run()