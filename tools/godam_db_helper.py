#!/usr/bin/env python3
import sqlite3
import sys
import json
import os
import datetime

DB_PATH = '/root/GoDaam/backend/warehouse.db'

def get_db_connection():
    if not os.path.exists(DB_PATH):
        # Fallback to local path for testing if needed
        local_path = './warehouse.db'
        if os.path.exists(local_path):
            return sqlite3.connect(local_path)
        raise FileNotFoundError(f"GoDaam database not found at {DB_PATH}")
    return sqlite3.connect(DB_PATH)

def insert_demo_order():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Count existing demo orders to generate a unique sequential number
    cursor.execute("SELECT COUNT(*) FROM outbound_orders WHERE outbound_number LIKE 'OR26101%'")

    num_count = cursor.fetchone()[0]
    outbound_num = f"OR26101{num_count:02d}"
    
    # Check if we already have this specific sequential number
    cursor.execute("SELECT id FROM outbound_orders WHERE outbound_number = ?", (outbound_num,))
    row = cursor.fetchone()
    if row:
        conn.close()
        return {"status": "exists", "id": row[0], "number": outbound_num}
        
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    
    # Insert a customer first to maintain relational integrity if needed
    cursor.execute("SELECT id FROM customers WHERE company_name = 'CompuTech Company'")
    cust_row = cursor.fetchone()
    if not cust_row:
        cursor.execute("""
            INSERT INTO customers (customer_number, company_name, city_name, address, contact_person, contact_person_number, created_at, updated_at)
            VALUES ('CUST9001', 'CompuTech Company', 'Riyadh', 'Deepak Industrial Area, Riyadh, KSA', 'Deepak', '+966500000000', ?, ?)
        """, (now, now))
        conn.commit()
    
    # Insert order
    cursor.execute("""
        INSERT INTO outbound_orders (
            outbound_number, sales_order_number, customer_po_number, customer_name, 
            status, total_cases, gross_weight, volume, delivery_address, 
            contact_person, created_at, updated_at
        ) VALUES (
            ?, 'SO-9921', 'PO-8822', 'CompuTech Company', 
            'Pending', 150, 1250.5, 4.2, 'Deepak Industrial Area, Riyadh, KSA', 
            'Deepak', ?, ?
        )
    """, (outbound_num, now, now))

    
    order_id = cursor.lastrowid
    
    # Insert some items for the order using exact schema columns
    cursor.execute("""
        INSERT INTO outbound_items (outbound_id, part_number, description, required_qty, picked_qty, status)
        VALUES (?, 'ITEM-A', 'High-Grade Copper Terminal Cables', 100, 0, 'Pending')
    """, (order_id,))
    
    cursor.execute("""
        INSERT INTO outbound_items (outbound_id, part_number, description, required_qty, picked_qty, status)
        VALUES (?, 'ITEM-B', 'Industrial Distribution Rails 2m', 50, 0, 'Pending')
    """, (order_id,))
    
    conn.commit()
    conn.close()
    return {"status": "inserted", "id": order_id}

def get_pending_orders():
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Check count first, if 0 let's auto-seed the demo order so the user has data to test!
    cursor.execute("SELECT COUNT(*) FROM outbound_orders WHERE status IN ('Pending', 'uploaded', 'new', 'PENDING')")
    count = cursor.fetchone()[0]
    if count == 0:
        insert_demo_order()

        
    cursor.execute("""
        SELECT id, outbound_number, sales_order_number, customer_name, 
               status, total_cases, gross_weight, delivery_address, contact_person, created_at 
        FROM outbound_orders 
        WHERE status IN ('Pending', 'uploaded', 'new', 'PENDING')
    """)
    rows = cursor.fetchall()
    
    result = []
    for r in rows:
        result.append(dict(r))
        
    conn.close()
    return result

def get_order_details(order_ref):
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Search by order number or id
    cursor.execute("""
        SELECT * FROM outbound_orders 
        WHERE outbound_number = ? OR id = ?
    """, (order_ref, order_ref))
    order_row = cursor.fetchone()
    
    if not order_row:
        conn.close()
        return None
        
    order = dict(order_row)
    
    # Fetch related items using outbound_id column
    try:
        cursor.execute("""
            SELECT * FROM outbound_items 
            WHERE outbound_id = ?
        """, (order['id'],))
        items_rows = cursor.fetchall()
        order['items'] = [dict(i) for i in items_rows]
    except Exception:
        order['items'] = []
        
    conn.close()
    return order


def confirm_order(order_ref, confirm_notes=""):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Find the order
    cursor.execute("SELECT id, outbound_number, customer_name FROM outbound_orders WHERE outbound_number = ? OR id = ?", (order_ref, order_ref))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return {"status": "error", "message": f"Order {order_ref} not found."}
        
    order_id, order_num, cust_name = row
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Update status to Confirmed
    cursor.execute("""
        UPDATE outbound_orders 
        SET status = 'Confirmed', updated_at = ?
        WHERE id = ?
    """, (now, order_id))
    
    # Log the action in AI agent logs if table exists
    try:
        cursor.execute("""
            INSERT INTO ai_agent_logs (user_id, username, role, command, tool_name, tool_args_json, status, created_at)
            VALUES (0, 'Hermes Bot', 'AI Agent', ?, 'confirm-order', ?, 'SUCCESS', ?)
        """, (f"Confirm order {order_num}", json.dumps({"order_id": order_id, "notes": confirm_notes}), now))
    except Exception:
        pass
        
    conn.commit()
    conn.close()
    
    return {
        "status": "success", 
        "order_id": order_id, 
        "order_number": order_num, 
        "customer_name": cust_name,
        "message": f"Order {order_num} for {cust_name} has been successfully CONFIRMED in the database."
    }

def print_help():
    print("""GoDaam Database Helper Utility for Hermes
Usage:
  python3 godam_db_helper.py get-pending
  python3 godam_db_helper.py get-details <order_number_or_id>
  python3 godam_db_helper.py confirm <order_number_or_id> [confirm_notes]
  python3 godam_db_helper.py insert-demo
""")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print_help()
        sys.exit(1)
        
    action = sys.argv[1].lower()
    
    try:
        if action == 'get-pending':
            orders = get_pending_orders()
            print(json.dumps(orders, indent=2))
        elif action == 'get-details':
            if len(sys.argv) < 3:
                print("Error: Missing order reference argument.")
                sys.exit(1)
            details = get_order_details(sys.argv[2])
            if details:
                print(json.dumps(details, indent=2))
            else:
                print(json.dumps({"error": f"Order {sys.argv[2]} not found."}))
        elif action == 'confirm':
            if len(sys.argv) < 3:
                print("Error: Missing order reference argument.")
                sys.exit(1)
            notes = sys.argv[3] if len(sys.argv) > 3 else "Confirmed via Hermes Agent Gateway."
            res = confirm_order(sys.argv[2], notes)
            print(json.dumps(res, indent=2))
        elif action == 'insert-demo':
            res = insert_demo_order()
            print(json.dumps(res, indent=2))
        else:
            print(f"Unknown action: {action}")
            print_help()
            sys.exit(1)
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        sys.exit(1)
