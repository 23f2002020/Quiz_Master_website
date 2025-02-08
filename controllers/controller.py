from flask import Flask, render_template, request
from .model import *
from datetime import datetime
from flask import current_app as app


@app.route("/")
def home():
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("user_name")
        password = request.form.get("password")
        user = User_Info.query.filter_by(email=username, password=password).first()
        if user and user.role==0:
           return render_template("admin_dashboard.html")
        elif user and user.role==1:
            return render_template("user_interface.html")
        else:
            return render_template("login.html", err_msg="Invalid username or password")
    
    return render_template("login.html",err_msg="")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        uname=request.form.get("full_name")
        email=request.form.get("user_name")
        password=request.form.get("password")
        qualification=request.form.get("qualification")
        dob1=request.form.get("dob")
        
        try:
            dob = datetime.strptime(dob1, '%d-%m-%Y').date()
        except ValueError:
            return "Invalid Date"
        user = User_Info.query.filter_by(email=email).first()
        if user:
            return render_template("signup.html",err_msg="User already exists")
        user=User_Info(email=email,password=password,fullname=uname,qualification=qualification,dob=dob)
        db.session.add(user)
        db.session.commit()
        return render_template("login.html",err_msg="Registration Successful, try login now")
    return render_template("signup.html",err_msg="")   

if __name__ == "__main__":
    app.run(debug=True)