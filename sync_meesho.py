"""
Nova Apparels - Automated Meesho Sync Engine
Syncs Meesho orders, shipments, returns, and payout settlements into nova_apparels.db.
Always creates an automatic timestamped database backup before any changes.
"""

import os
import sys
import csv
import json
import sqlite3
import datetime
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "nova_apparels.db")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")


def create_backup():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    if os.path.exists(DB_PATH) and os.path.getsize(DB_PATH) > 0:
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = os.path.join(BACKUP_DIR, f"nova_apparels_backup_{ts}.db")
        shutil.copy2(DB_PATH, dest)
        print(f"[OK] Automatic database backup created: {os.path.basename(dest)}")
        
        # Keep last 30 backups
        backups = sorted([os.path.join(BACKUP_DIR, f) for f in os.listdir(BACKUP_DIR) if f.startswith("nova_apparels_backup_") and f.endswith(".db")])
        if len(backups) > 30:
            for old in backups[:-30]:
                try:
                    os.remove(old)
                except OSError:
                    pass


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def sync_from_csv(csv_path, handled_by="Arsh"):
    if not os.path.exists(csv_path):
        print(f"[ERROR] File not found: {csv_path}")
        return 0, 0
    
    create_backup()
    conn = get_db()
    cur = conn.cursor()
    
    inserted = 0
    updated = 0
    
    with open(csv_path, "r", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sub_id = row.get("Sub Order No") or row.get("Sub-order No") or row.get("Sub Order ID") or ""
            sub_id = sub_id.strip()
            if not sub_id:
                continue
            
            order_id = sub_id.split("_")[0] if "_" in sub_id else sub_id
            order_date = row.get("Order Date", "")[:10] or datetime.date.today().strftime("%Y-%m-%d")
            product_name = row.get("Product Name", "Meesho Product").strip()
            sku = row.get("SKU") or row.get("Supplier SKU") or ""
            qty = int(row.get("Quantity", 1) or 1)
            price = float(row.get("Supplier Discounted Price (Incl GST and Commision)") or row.get("Supplier Listed Price (Incl. GST + Commission)") or row.get("Price") or 0)
            status = row.get("Live Order Status") or row.get("Order Status") or "Pending"
            
            # Map meesho status
            if "deliver" in status.lower():
                cur_status = "Delivered"
            elif "ship" in status.lower():
                cur_status = "Shipped"
            elif "ready" in status.lower():
                cur_status = "Ready to Ship"
            elif "cancel" in status.lower():
                cur_status = "Cancelled"
            elif "return" in status.lower() or "rto" in status.lower():
                cur_status = "Returned"
            else:
                cur_status = status.strip()
            
            existing = cur.execute("SELECT id, current_status FROM orders WHERE sub_order_id = ? OR order_id = ?", (sub_id, order_id)).fetchone()
            if existing:
                cur.execute(
                    """
                    UPDATE orders
                    SET current_status = ?, sku = COALESCE(NULLIF(?, ''), sku),
                        product_name = COALESCE(NULLIF(?, ''), product_name),
                        order_amount = CASE WHEN order_amount = 0 THEN ? ELSE order_amount END,
                        status_updated_at = ?
                    WHERE id = ?
                    """,
                    (cur_status, sku, product_name, price, datetime.datetime.now().isoformat(), existing["id"])
                )
                updated += 1
            else:
                cur.execute(
                    """
                    INSERT INTO orders (
                        order_id, sub_order_id, order_date, product_name, sku, quantity,
                        payment_mode, order_amount, initial_status, current_status,
                        status_updated_at, handled_by, is_demo
                    ) VALUES (?, ?, ?, ?, ?, ?, 'Unified (Meesho)', ?, ?, ?, ?, ?, 0)
                    """,
                    (
                        order_id, sub_order_id, order_date, product_name, sku, qty,
                        price, cur_status, cur_status, datetime.datetime.now().isoformat(),
                        handled_by
                    )
                )
                inserted += 1
                
    conn.commit()
    conn.close()
    print(f"[SUCCESS] Sync completed: {inserted} new orders added, {updated} orders updated.")
    return inserted, updated


if __name__ == "__main__":
    if len(sys.argv) > 1:
        sync_from_csv(sys.argv[1])
    else:
        create_backup()
        print("[INFO] Run with CSV path to import: python sync_meesho.py <file.csv>")
