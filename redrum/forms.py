from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, EmailField
from wtforms.validators import DataRequired, length, EqualTo, ValidationError
from redrum.models import Users
from flask_login import current_user


class RegistrationForm(FlaskForm):
    username = StringField("نام کاربری", validators=[DataRequired(), length(min=4, max=25, message='نام کاربری باید دارای 4 تا 25 کرکتر باشد')])
    email = EmailField("ایمیل", validators=[DataRequired()])
    mobile_number = StringField("شماره موبایل", validators=[DataRequired(), length(min=11, max=11, message='شماره موبایل باید ۱۱ رقم باشد')])
    password = PasswordField("رمز عبور", validators=[DataRequired()])
    confirm_password = PasswordField("تکرار رمز عبور", validators=[DataRequired(), EqualTo('password', message='رمز عبور با تکرار آن یکسان نیست')])

    def validate_username(self, username):
        user = Users.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError("این نام کاربری قبلاً ثبت شده است")

    def validate_mobile_number(self, mobile_number):
        if not mobile_number.data.isdigit():
            raise ValidationError("شماره موبایل باید فقط عدد باشد")
        if not mobile_number.data.startswith('09'):
            raise ValidationError("شماره موبایل باید با ۰۹ شروع شود")
        user = Users.query.filter_by(mobile_number=mobile_number.data).first()
        if user:
            raise ValidationError("این شماره موبایل قبلاً ثبت شده است")

    def validate_email(self, email):
        user = Users.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError("این ایمیل قبلاً ثبت شده است")


class LoginForm(FlaskForm):
    username = StringField("نام کاربری یا شماره موبایل", validators=[DataRequired()])
    password = PasswordField("رمز عبور", validators=[DataRequired()])
    remember = BooleanField("مرا به خاطر داشته باش")
