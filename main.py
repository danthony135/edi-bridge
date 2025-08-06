def create_sale_order(po_data):
    try:
        db = os.getenv("ODOO_DB")
        common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
        uid = common.authenticate(db, ODOO_USERNAME, ODOO_PASSWORD, {})

        models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')

        # Find or create the customer
        customer = po_data['customer']
        partner_ids = models.execute_kw(db, uid, ODOO_PASSWORD,
            'res.partner', 'search', [[['email', '=', customer['email']]]])
        if not partner_ids:
            partner_id = models.execute_kw(db, uid, ODOO_PASSWORD,
                'res.partner', 'create', [{
                    'name': customer['name'],
                    'email': customer['email']
                }])
        else:
            partner_id = partner_ids[0]

        # Prepare order lines
        order_lines = []
        for item in po_data['lines']:
            product_ids = models.execute_kw(db, uid, ODOO_PASSWORD,
                'product.product', 'search', [[['default_code', '=', item['sku']]]], {'limit': 1})
            if not product_ids:
                raise Exception(f"Product not found: {item['sku']}")
            order_lines.append((0, 0, {
                'product_id': product_ids[0],
                'product_uom_qty': item['qty'],
                'price_unit': item['price']
            }))

        # Create the sale order
        order_id = models.execute_kw(db, uid, ODOO_PASSWORD,
            'sale.order', 'create', [{
                'partner_id': partner_id,
                'origin': po_data['po_number'],
                'date_order': po_data['order_date'],
                'order_line': order_lines
            }])
        return order_id
    except Exception as e:
        return str(e)
