import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
from printer import pos_print

load_dotenv()

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
    app.run(debug=True, host="0.0.0.0", port=port)

