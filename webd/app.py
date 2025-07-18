from flask import Flask
from flask_cors import CORS

import sys
import io
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

app = Flask(__name__, instance_path='/tmp')
CORS(app)  

import routes

app.instance_path = '/tmp'

if __name__ == '__main__':
    app.run()