import os
import sys
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
from printer import pos_print

if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
else:
    application_path = os.path.dirname(os.path.abspath(__file__))

env_path = os.path.join(application_path, '.env')
load_dotenv(env_path)

app = Flask(__name__)

frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
port = int(os.getenv("PORT", "5050"))
CORS(app, origins=[frontend_url])

@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "healthy"}), 200

@app.route("/print", methods=["POST"])
def print_invoice():
    invoice_data = request.get_json()
    pos_print(invoice_data)
    return "", 204

if __name__ == "__main__":
    print(f"Starting Edu Printer System on port {port}...")
    print(f"Health check: http://localhost:{port}/")
    print("Press Ctrl+C to stop")
    app.run(debug=False, host="0.0.0.0", port=port)

