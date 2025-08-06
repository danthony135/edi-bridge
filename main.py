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

def create_odoo_connection():
    common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
    uid = common.authenticate(ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD, {})
    models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")
    return uid, models

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
    try:
        uid, models = create_odoo_connection()
        order_id = request.json.get("order_id")
        order = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, "sale.order", "read", [order_id], {"fields": ["name", "date_order", "order_line"]})[0]
        line_ids = order["order_line"]
        lines = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, "sale.order.line", "read", [line_ids], {"fields": ["product_id", "product_uom_qty"]})
        items = [{"sku": l["product_id"][1], "qty": l["product_uom_qty"], "status": "accepted"} for l in lines]
        payload = {
            "po_number": order["name"],
            "acknowledged": True,
            "order_date": order["date_order"],
            "items": items
        }
        return jsonify(payload)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/outgoing/856", methods=["POST"])
def send_856():
    if not verify_token():
        return jsonify({"error": "Unauthorized"}), 401
    try:
        uid, models = create_odoo_connection()
        picking_id = request.json.get("picking_id")
        picking = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, "stock.picking", "read", [picking_id], {"fields": ["name", "carrier_id", "scheduled_date", "move_ids_without_package"]})[0]
        lines = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, "stock.move", "read", [picking["move_ids_without_package"]], {"fields": ["product_id", "product_uom_qty"]})
        items = [{"sku": l["product_id"][1], "qty": l["product_uom_qty"]} for l in lines]
        payload = {
            "shipment_id": picking["name"],
            "carrier": picking["carrier_id"][1] if picking["carrier_id"] else "N/A",
            "ship_date": picking["scheduled_date"],
            "items": items
        }
        return jsonify(payload)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/outgoing/810", methods=["POST"])
def send_810():
    if not verify_token():
        return jsonify({"error": "Unauthorized"}), 401
    try:
        uid, models = create_odoo_connection()
        invoice_id = request.json.get("invoice_id")
        invoice = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, "account.move", "read", [invoice_id], {"fields": ["name", "invoice_date", "amount_total", "invoice_line_ids", "invoice_origin"]})[0]
        lines = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, "account.move.line", "read", [invoice["invoice_line_ids"]], {"fields": ["product_id", "quantity", "price_unit"]})
        items = [{"sku": l["product_id"][1], "qty": l["quantity"], "price": l["price_unit"]} for l in lines if l["product_id"]]
        payload = {
            "invoice_number": invoice["name"],
            "po_number": invoice["invoice_origin"],
            "date": invoice["invoice_date"],
            "total": invoice["amount_total"],
            "items": items
        }
        return jsonify(payload)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
