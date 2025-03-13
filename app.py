from flask import Flask
from controllers.model import db
from flask_migrate import Migrate
import os
from controllers.api_controller import api

app=None

def setup():
    global app

    app = Flask(__name__)
    api.init_app(app)
    app.secret_key = "The admin's power"
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///Quiz_Master.db' #+         #os.path.join(app.instance_path, 'QUIZ_Master.db')
    print('Database path:', os.path.join(app.instance_path, 'Quiz_Master.db'))
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