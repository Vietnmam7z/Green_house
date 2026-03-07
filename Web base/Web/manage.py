from flask import Blueprint,render_template

manage = Blueprint('manage',__name__)

@manage.route('/')
def home():
    return render_template("manage.html")



