from redrum import db, Login_manager
from redrum import app
import datetime
from flask_login import UserMixin

class Users(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(30), unique=True, nullable = False)
    email = db.Column(db.String(60), unique=True)
    mobile_number = db.Column(db.String(20), unique=True, nullable = False)
    password = db.Column(db.String(60), nullable = False)
    is_confirmed = db.Column(db.Boolean, default=False)
    confirmed_on = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.id}, {self.username})"
    
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50))
    image_url = db.Column(db.String(200))
    is_active = db.Column(db.Boolean, default=True)
    
    

    def __repr__(self):
        return f"{self.__class__.__name__}({self.id}, {self.product_name})"
    
class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    order_date = db.Column(db.DateTime, default=db.func.now())
    shipping_address = db.Column(db.String(200))
    payment_status = db.Column(db.String(20))

    user = db.relationship('Users', backref='orders')
    
    product = db.relationship('Product', backref='orders')


class PostalCard(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text)
    image_filename = db.Column(db.String(200))
    audio_filename = db.Column(db.String(200))
    qr_filename = db.Column(db.String(200))


    def __repr__(self):
        return f"{self.__class__.__name__}({self.id}, {self.user_id}, {self.product_id}"

@Login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))
    
    


    