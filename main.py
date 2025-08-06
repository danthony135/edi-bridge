from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/incoming/850', methods=['POST'])
def handle_850():
    data = request.json
    return jsonify({"status": "received", "po_number": data.get("po_number")})

@app.route('/incoming/860', methods=['POST'])
def handle_860():
    data = request.json
    return jsonify({"status": "received", "change_request": data.get("po_number")})

@app.route('/outgoing/855', methods=['POST'])
def send_855():
    return jsonify({"status": "sent", "ack": True})

@app.route('/outgoing/856', methods=['POST'])
def send_856():
    return jsonify({"status": "sent", "asn": True})

@app.route('/outgoing/810', methods=['POST'])
def send_810():
    return jsonify({"status": "sent", "invoice": True})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)