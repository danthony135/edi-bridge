from flask import Flask, request, jsonify
import os
import requests
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

ODOO_URL = os.getenv("ODOO_URL")
ODOO_DB = os.getenv("ODOO_DB")
ODOO_USER = os.getenv("ODOO_USER")
ODOO_API_KEY = os.getenv("ODOO_API_KEY")

@app.route("/", methods=["GET"])
def index():
    return "EDI Bridge is running"

@app.route("/incoming/850", methods=["POST"])
def receive_850():
    auth = request.headers.get("Authorization")
    if auth != "Bearer test1234":
        return jsonify({"error": "Unauthorized"}), 401

    try:
        data = request.get_json()
        po_number = data.get("po_number")
        customer_name = data.get("customer", {}).get("name")
        items = data.get("line_items", [])

        logging.info(f"Received 850: PO {po_number} for {customer_name}")

        # Step 1: Create or find customer
        customer = create_or_find_partner(customer_name)

        # Step 2: Create order lines
        order_lines = []
        for item in items:
            product = find_product_by_sku(item.get("sku"))
            if not product:
                continue
            order_lines.append((0, 0, {
                "product_id": product["id"],
                "product_uom_qty": item.get("quantity", 1),
                "price_unit": item.get("price", 0.0),
                "name": item.get("description", product["display_name"]),
            }))

        if not order_lines:
            return jsonify({"error": "No valid products found"}), 400

        # Step 3: Create sale order
        order = create_sale_order(po_number, customer["id"], order_lines)

        return jsonify({"status": "success", "sale_order_id": order["id"]})
    except Exception as e:
        logging.exception("Error processing 850")
        return jsonify({"error": str(e)}), 500

def odoo_rpc(model, method, args, kwargs=None):
    url = f"{ODOO_URL}/jsonrpc"
    headers = {"Content-Type": "application/json"}
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "service": "object",
            "method": "execute_kw",
            "args": [ODOO_DB, ODOO_USER, ODOO_API_KEY, model, method, args, kwargs or {}]
        },
        "id": 1,
    }
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    return response.json()["result"]

def create_or_find_partner(name):
    partners = odoo_rpc("res.partner", "search_read", [[["name", "=", name]]], {"limit": 1})
    if partners:
        return partners[0]
    partner_id = odoo_rpc("res.partner", "create", [{"name": name}])
    return {"id": partner_id, "name": name}

def find_product_by_sku(sku):
    products = odoo_rpc("product.product", "search_read", [[["default_code", "=", sku]]], {"limit": 1})
    return products[0] if products else None

def create_sale_order(po_number, partner_id, lines):
    return odoo_rpc("sale.order", "create", [{
        "partner_id": partner_id,
        "client_order_ref": po_number,
        "order_line": lines
    }])

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
