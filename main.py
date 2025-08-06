from flask import Flask, request, jsonify
import os
import xmlrpc.client

app = Flask(__name__)

# Load environment variables
API_TOKEN = os.getenv("API_TOKEN")
ODOO_URL = os.getenv("ODOO_URL")
ODOO_USERNAME = os.getenv("ODOO_USERNAME")
ODOO_PASSWORD = os.getenv("ODOO_PASSWORD")
ODOO_DB = os.getenv("ODOO_DB")

def verify_token():
    auth_header = request.headers.get("Authorization", "")
    return auth_header == f"Bearer {API_TOKEN}"

def create_sale_order(po_data):
    try:
        common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
        uid = common.authenticate(ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD, {})
        if not uid:
            return "Authentication with Odoo failed."

        models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")

        # Find or create customer
        customer = po_data.get("customer", {})
        partner_ids = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD,
            "res.partner", "search", [[["email", "=", customer.get("email")]]])
        if not partner_ids:
            partner_id = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD,
                "res.partner", "create", [{
                    "name": customer.get("name"),
                    "email": customer.get("email")
                }])
        else:
            partner_id = partner_ids[0]

        # Build order lines
        lines = []
        for item in po_data.get("lines", []):
            sku = item.get("sku")
            product_ids = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD,
                "product.product", "search", [[["default_code", "=", sku]]], {"limit": 1})
            if not product_ids:
                raise Exception(f"Product not found: {sku}")
            lines.append((0, 0, {
                "product_id": product_ids[0],
                "product_uom_qty": item.get("qty"),
                "price_unit": item.get("price")
            }))

        # Create the sale order
        order_id = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD,
            "sale.order", "create", [{
                "partner_id": partner_id,
                "origin": po_data.get("po_number"),
                "date_order": po_data.get("order_date"),
                "order_line": lines
            }])
        return order_id
    except Exception as e:
        return f"Error: {str(e)}"

@app.route("/incoming/850", methods=["POST"])
def handle_850():
    if not verify_token():
        return jsonify({"error": "Unauthorized"}), 401
    data = request.json
    result = create_sale_order(data)
    return jsonify({"status": "processed", "result": result})

@app.route("/incoming/860", methods=["POST"])
def handle_860():
    if not verify_token():
        return jsonify({"error": "Unauthorized"}), 401
    data = request.json
    return jsonify({"status": "received", "change_request": data.get("po_number")})

@app.route("/outgoing/855", methods=["POST"])
def send_855():
    if not verify_token():
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify({"status": "sent", "ack": True})

@app.route("/outgoing/856", methods=["POST"])
def send_856():
    if not verify_token():
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify({"status": "sent", "asn": True})

@app.route("/outgoing/810", methods=["POST"])
def send_810():
    if not verify_token():
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify({"status": "sent", "invoice": True})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
