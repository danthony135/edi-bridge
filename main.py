
from flask import Flask, request, jsonify
import os

app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return "EDI Bridge is running"

@app.route("/incoming/850", methods=["POST"])
def receive_850():
    data = request.get_json()
    print("Received 850:", data)
    return jsonify({"status": "success", "message": "850 received"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
