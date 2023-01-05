import os

from flask import Flask, render_template, request, flash,make_response, render_template_string
from flask_mail import Message, Mail
import datetime

from forms import ContactForm, InputForm
from flask_cors import CORS

mail = Mail()

app = Flask(__name__)
CORS(app)


app.secret_key = '****************'

app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 465
app.config["MAIL_USE_SSL"] = True
app.config["MAIL_USERNAME"] = 'your_email@gmail.com'
app.config[
    "MAIL_PASSWORD"] = '****************'  # password generated in Google Account Settings under 'Security',
# 'App passwords',
# choose 'other' in the app menu, create a name (here: 'FlaskMail'),
# and generate password. The password has 16 characters.
# Copy/paste it under app.config["MAIL_PASSWORD"].
# It will give you access to your gmail when you have two steps verification.
mail.init_app(app)

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


@app.context_processor
def inject_today_date():
    return {'year': datetime.date.today().year}


# @app.route('/')
# def home():
#     return render_template('home.html')


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    form = ContactForm()

    if request.method == 'POST':
        if not form.validate():
            flash('All fields are required.')
            return render_template('contact.html', form=form)
        else:
            msg = Message(form.subject.data, sender='contact@example.com', recipients=['your_email@gmail.com'])
            msg.body = """
            From: %s <%s>
            %s
            """ % (form.name.data, form.email.data, form.message.data)
            mail.send(msg)
            return render_template('contact.html', success=True)

    elif request.method == 'GET':
        return render_template('contact.html', form=form)


@app.route("/input")
def input():
    form = InputForm()
    return render_template('input.html', form=form)


@app.route('/')
def test():

    return render_template("station_info_window.html")

@app.route('/map')
def show_map():

    return render_template("map.html")

@app.route("/window", methods = ["POST"])
def window():
    if request.method == "POST":
        # datafromjs = request.form['mydata']
        result = "return this"
        resp = make_response('{"response": ' + result + '}')
        resp.headers['Content-Type'] = "application/json"
        return resp


if __name__ == '__main__':
    # app.run(debug=True)
    app.run("0.0.0.0", port=80, debug=False)  # added host parameters for docker container
