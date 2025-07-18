from flask import Flask, jsonify
from flask_cors import CORS
import subprocess
import sys
import os

import sys
import io
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
except Exception:
    pass

app = Flask(__name__)
CORS(app)

@app.route('/generate', methods=['POST'])
def generate_output():
    """
    Runs model/master.py and returns its output as JSON.
    """
    try:
        script_path = os.path.join(os.path.dirname(__file__), 'model', 'master.py')
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            check=True,
            encoding='utf-8'
        )
        return jsonify({'output': result.stdout})
    except subprocess.CalledProcessError as e:
        return jsonify({'error': f"Model script failed: {e.stderr}"}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
