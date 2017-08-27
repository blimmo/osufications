import os

import flask

app = flask.Flask(__name__)

@app.route('/')
def hello_world():
    return 'Waking up bot...\nYou can send it messages after it comes online'

app.run(host='0.0.0.0', port=int(os.environ.get('PORT')))
