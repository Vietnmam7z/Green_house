from flask import request, session, redirect, render_template, jsonify
from authentication import Authentication
import config

class Routes:
    def __init__(self, auth: Authentication):
        self.auth = auth
        
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
                "redirect": "/"
            })
    
        else:
            return jsonify({
                "success": result['success'],
                "message": result['message']
            })
        
#################################################################################################################################
        
