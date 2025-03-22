from flask import Flask
from flask_cors import CORS

app = Flask(__name__, instance_path='/tmp')
CORS(app)  

app.secret_key = 'secret_key'


import routes

app.instance_path = '/tmp'

if __name__ == '__main__':
    app.run()