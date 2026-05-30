from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_mail import Mail
from itsdangerous import URLSafeTimedSerializer


app = Flask(__name__)
app.config['SECRET_KEY'] = '87bfb447b21f18a081d337c088e52763'
app.config["SQLALCHEMY_DATABASE_URI"]='mysql://root:root@localhost/janus'
app.config["SQLALCHEMY_TRACK_MODIFICATION"]= False

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USERNAME'] = "janusartshop@gmail.com"
app.config['MAIL_PASSWORD'] = "pqkmpzcpmiujejsw"
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False

s = URLSafeTimedSerializer(app.config['SECRET_KEY'])

mail = Mail(app)
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
Login_manager = LoginManager(app)


app.app_context().push()

from redrum import routes
