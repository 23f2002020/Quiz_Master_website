from flask import Flask
from controllers.model import db
from flask_migrate import Migrate

app=None

def setup():
    global app

    app = Flask(__name__)
    app.secret_key = "The admin's power"
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///QUIZ_Master.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    migrate = Migrate(app, db)
    app.app_context().push() #Direct access to other modules
    app.debug=True
    print("QUIZ MASTER IS ACTIVATED")

setup()


# def home():

from controllers.controller import *

if __name__ == "__main__":
    app.run()