from flask import Flask
from controllers.model import db

app=None

def setup():

    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///QUIZ_Master.db'
    db.init_app(app)
    app.app_context().push() #Direct access to other modules
    app.debug=True
    print("QUIZ MASTER IS ACTIVATED")

setup()


# def home():

from controllers.controller import *

if __name__ == "__main__":
    app.run()