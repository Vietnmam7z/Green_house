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
        role = request.form.get('role')
        
        result = self.auth.register_user(username, password, email, role)

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

    def forgot_password(self):
        email = request.form.get('email')
        result = self.auth.forget_password(email)

        if result and result['success']:
            return jsonify({
                "success": result['success'],
                "message": "Mã OTP đã được gửi đến email của bạn.",
                "redirect": "/reset-password"
            })
    
        else:
            return jsonify({
                "success": False,
                "message": "Email không tồn tại."
            })

#################################################################################################################################

 # SEND OTP PAGE
    def reset_password_page(self):
        if self.redirect_if_logged_in():
            return self.redirect_if_logged_in()
        else:
            return render_template(config.reset_password_page)

    def reset_password(self):
        email = request.form.get('email')
        otp = request.form.get('otp')
        new_password = request.form.get('new_password')
        
        result = self.auth.reset_password(email, otp, new_password)

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


