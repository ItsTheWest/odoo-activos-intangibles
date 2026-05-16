import xmlrpc.client
import random
from datetime import datetime, timedelta

# ==========================================
# CONFIGURATION
# ==========================================
URL = 'http://localhost:8069'
DB = 'odoo'
USER = 'admin'
PASSWORD = 'admin'

# ==========================================
# DATA POOLS
# ==========================================
ASSET_TYPES = [
    {'name': 'Licencia de Software', 'code': 'SW', 'lifespan_days': 365},
    {'name': 'Marca Registrada', 'code': 'MR', 'lifespan_days': 3650},
    {'name': 'Patente de Invención', 'code': 'PT', 'lifespan_days': 7300},
    {'name': 'Dominio Web', 'code': 'WEB', 'lifespan_days': 365},
    {'name': 'Franquicia', 'code': 'FR', 'lifespan_days': 1825},
]

COMPANIES = ['Polar', 'Microsoft', 'Adobe', 'Oracle', 'Amazon', 'SAP', 'Google', 'IBM', 'Cisco', 'Odoo']
PRODUCTS = ['ERP', 'CRM', 'Cloud', 'Analytics', 'Engine', 'Platform', 'Suite', 'Pro', 'Max', 'Hub']

def main():
    print(f"Connecting to Odoo at {URL}...")
    try:
        common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
        uid = common.authenticate(DB, USER, PASSWORD, {})
        if not uid:
            print("Authentication failed. Check your DB, USER, and PASSWORD.")
            return
        
        models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
        print("Connected successfully!")
        
        # ---------------------------------------------------------
        # PRE-REQUISITES (Partners, Employees, Products)
        # ---------------------------------------------------------
        print("Ensuring dependencies exist (Partner, Employee, Product)...")
        # 1. Partner for Invoicing
        partner_ids = models.execute_kw(DB, uid, PASSWORD, 'res.partner', 'search', [[('name', '=', 'Proveedor de Intangibles Demo')]])
        partner_id = partner_ids[0] if partner_ids else models.execute_kw(DB, uid, PASSWORD, 'res.partner', 'create', [{'name': 'Proveedor de Intangibles Demo', 'is_company': True}])
        
        # 2. Employee for Expenses
        employee_ids = models.execute_kw(DB, uid, PASSWORD, 'hr.employee', 'search', [[('name', '=', 'Empleado Demo')]])
        employee_id = employee_ids[0] if employee_ids else models.execute_kw(DB, uid, PASSWORD, 'hr.employee', 'create', [{'name': 'Empleado Demo'}])
        
        # 3. Product for Expenses (Service type)
        product_ids = models.execute_kw(DB, uid, PASSWORD, 'product.product', 'search', [[('name', '=', 'Mantenimiento de Intangible')]])
        product_id = product_ids[0] if product_ids else models.execute_kw(DB, uid, PASSWORD, 'product.product', 'create', [{'name': 'Mantenimiento de Intangible', 'type': 'service', 'can_be_expensed': True}])

        # ---------------------------------------------------------
        # 1. Create or Fetch Asset Types
        # ---------------------------------------------------------
        type_ids = []
        for t in ASSET_TYPES:
            existing = models.execute_kw(DB, uid, PASSWORD, 'activo.intangible.type', 'search', [[('name', '=', t['name'])]])
            if existing:
                type_ids.append(existing[0])
            else:
                new_id = models.execute_kw(DB, uid, PASSWORD, 'activo.intangible.type', 'create', [t])
                type_ids.append(new_id)
                print(f"Created Asset Type: {t['name']}")
                
        # ---------------------------------------------------------
        # 2. Generate Assets (with connected Invoices and Expenses)
        # ---------------------------------------------------------
        total_to_generate = 50 # Lowered to 50 because generating 3 records per loop takes longer
        print(f"\nGenerating {total_to_generate} assets with connected Vendor Bills and Expenses...")
        
        created_count = 0
        for i in range(total_to_generate):
            try:
                type_id = random.choice(type_ids)
                type_info = models.execute_kw(DB, uid, PASSWORD, 'activo.intangible.type', 'read', [[type_id]], {'fields': ['name', 'lifespan_days']})[0]
                
                name = f"{type_info['name']} - {random.choice(COMPANIES)} {random.choice(PRODUCTS)} {random.randint(2020, 2026)}"
                concession_date = (datetime.now() - timedelta(days=random.randint(10, 450))).strftime('%Y-%m-%d')
                
                rand_state = random.randint(1, 100)
                if rand_state <= 10:
                    renewal_date = (datetime.now() - timedelta(days=random.randint(1, 30))).strftime('%Y-%m-%d')
                elif rand_state <= 25:
                    renewal_date = (datetime.now() + timedelta(days=random.randint(1, 55))).strftime('%Y-%m-%d')
                else:
                    renewal_date = (datetime.now() + timedelta(days=random.randint(70, type_info['lifespan_days'] or 365))).strftime('%Y-%m-%d')
                    
                valor_contable = round(random.uniform(500.0, 25000.0), 2)
                
                print(f"[{i+1}/{total_to_generate}] Processing: {name}...")

                # STEP A: Create Vendor Bill (Facturación)
                invoice_vals = {
                    'move_type': 'in_invoice',
                    'partner_id': partner_id,
                    'invoice_date': concession_date,
                    'invoice_line_ids': [
                        (0, 0, {
                            'name': f"Adquisición: {name}",
                            'price_unit': valor_contable,
                            'quantity': 1,
                        })
                    ]
                }
                invoice_id = models.execute_kw(DB, uid, PASSWORD, 'account.move', 'create', [invoice_vals])
                print(f"   -> Facturación creada (ID: {invoice_id})")
                
                # STEP B: Create Expense (Gastos)
                expense_vals = {
                    'name': f"Mantenimiento anual de {name}",
                    'employee_id': employee_id,
                    'product_id': product_id,
                    'total_amount': round(valor_contable * 0.1, 2),
                    'date': concession_date,
                }
                expense_id = models.execute_kw(DB, uid, PASSWORD, 'hr.expense', 'create', [expense_vals])
                print(f"   -> Gasto creado (ID: {expense_id})")
                
                # STEP C: Create Intangible Asset and link them!
                asset_vals = {
                    'name': name,
                    'asset_type_id': type_id,
                    'registration_number': f"REG-{random.randint(10000, 99999)}",
                    'concession_date': concession_date,
                    'renewal_date': renewal_date,
                    'valor_contable': valor_contable,
                    'invoice_id': invoice_id,
                    'expense_id': expense_id,
                }
                asset_id = models.execute_kw(DB, uid, PASSWORD, 'activo.intangible', 'create', [asset_vals])
                print(f"   -> Activo Intangible finalizado (ID: {asset_id})")
                
                created_count += 1
                    
            except Exception as e:
                print(f"   [!] Error creating ecosystem for {name}: {e}")
                
        print("-" * 50)
        print(f"PROCESS FINISHED: {created_count} assets created successfully.")
        print("-" * 50)

    except Exception as e:
        print(f"Connection error: {e}")

if __name__ == "__main__":
    main()
