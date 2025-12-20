from flask import Blueprint,render_template

control = Blueprint('control',__name__)

@control.route('/')
def home():
    return render_template("control.html")