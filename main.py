
from flask import Flask, request, jsonify
import os
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

@app.route("/", methods=["GET"])
def index():
    return "EDI Bridge is running"

@app.route("/incoming/850", methods=["POST"])
def receive_850():
    try:
        data = request.get_json()
        logging.info("Received 850 EDI data: %s", data)

        # Simulated processing - extend this for Odoo integration
        po_number = data.get("po_number")
        customer = data.get("customer", {}).get("name")

        logging.info("Processing PO %s for customer %s", po_number, customer)

        return jsonify({"status": "success", "message": f"PO {po_number} received for {customer}"}), 200
    except Exception as e:
        logging.exception("Error processing 850:")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
