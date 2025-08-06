
from flask import Flask, request, jsonify
import os
import xmlrpc.client

app = Flask(__name__)

# Environment variables
ODOO_URL = os.getenv("ODOO_URL")
ODOO_DB = os.getenv("ODOO_DB")
ODOO_USER = os.getenv("ODOO_USER")
ODOO_API_KEY = os.getenv("ODOO_API_KEY")

def get_odoo_client():
    common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
    uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_API_KEY, {})
    models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")
    return uid, models

@app.route("/")
def health():
    return jsonify({"status": "ok"})

@app.route("/incoming/850", methods=["POST"])
def receive_850():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON"}), 400

        po_number = data.get("po_number")
        customer_info = data.get("customer", {})
        line_items = data.get("line_items", [])

        if not po_number or not customer_info.get("name") or not line_items:
            return jsonify({"error": "Missing PO data"}), 400

        uid, models = get_odoo_client()

        # Check if customer exists
        customer_name = customer_info["name"]
        customer_ids = models.execute_kw(ODOO_DB, uid, ODOO_API_KEY,
            'res.partner', 'search', [[['name', '=', customer_name]]])
        if customer_ids:
            customer_id = customer_ids[0]
        else:
            # Create customer
            customer_id = models.execute_kw(ODOO_DB, uid, ODOO_API_KEY,
                'res.partner', 'create', [{
                    'name': customer_name,
                    'email': customer_info.get("email"),
                    'phone': customer_info.get("phone"),
                    'street': customer_info.get("address", {}).get("street"),
                    'city': customer_info.get("address", {}).get("city"),
                    'state_id': None,
                    'zip': customer_info.get("address", {}).get("zip"),
                    'country_id': None,
                }])

        # Create sale order
        order_lines = []
        for item in line_items:
            order_lines.append((0, 0, {
                'name': item.get("description", item["sku"]),
                'product_uom_qty': item["quantity"],
                'price_unit': item["price"],
            }))

        sale_order_id = models.execute_kw(ODOO_DB, uid, ODOO_API_KEY,
            'sale.order', 'create', [{
                'partner_id': customer_id,
                'client_order_ref': po_number,
                'order_line': order_lines
            }])

        return jsonify({
            "status": "success",
            "sale_order_id": sale_order_id,
            "po_number": po_number
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
