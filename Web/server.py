from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# Trang login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        # TODO: check trong DB
        if email == "test@gmail.com" and password == "1234":
            return redirect(url_for("home"))
        else:
            return "Login failed!"
    return render_template("login.html")

# Trang signup
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        # TODO: lưu DB
        return redirect(url_for("login"))
    return render_template("signup.html")

@app.route("/home")
def home():
    return render_template("home.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
