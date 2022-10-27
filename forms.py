from flask_wtf import FlaskForm
import wtforms as wtf


class ContactForm(FlaskForm):
    name = wtf.StringField("Name",  [wtf.validators.data_required()])
    email = wtf.StringField("Email",  [wtf.validators.data_required(
        "Please enter your email address."), wtf.validators.Email("Please enter your email address.")])
    subject = wtf.StringField("Subject",  [wtf.validators.data_required()])
    message = wtf.TextAreaField("Message",  [wtf.validators.data_required()])
    submit = wtf.SubmitField("Send")

class InputForm(FlaskForm):
    rangefield = wtf.IntegerRangeField()
    filefield = wtf.FileField()
    submitfield = wtf.SubmitField("submitfield")
