import csv
import datetime
import io
import json
import mimetypes
import os
import sqlite3
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "nova_apparels.db")
STATIC_DIR = os.path.join(BASE_DIR, "static")
PORT = int(os.environ.get("PORT", "8765"))


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def now_iso():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def today_str():
    return datetime.date.today().strftime("%Y-%m-%d")


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS members (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            role TEXT NOT NULL,
            is_investor INTEGER NOT NULL DEFAULT 0,
            share_percent REAL NOT NULL DEFAULT 0,
            phone TEXT DEFAULT '',
            notes TEXT DEFAULT ''
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT UNIQUE NOT NULL,
            sub_order_id TEXT DEFAULT '',
            order_date TEXT NOT NULL,
            product_name TEXT NOT NULL,
            sku TEXT DEFAULT '',
            quantity INTEGER NOT NULL DEFAULT 1,
            customer_name TEXT DEFAULT '',
            customer_city TEXT DEFAULT '',
            payment_mode TEXT NOT NULL DEFAULT 'COD',
            order_amount REAL NOT NULL DEFAULT 0,
            product_cost REAL NOT NULL DEFAULT 0,
            packaging_cost REAL NOT NULL DEFAULT 0,
            initial_status TEXT NOT NULL DEFAULT 'Pending',
            current_status TEXT NOT NULL DEFAULT 'Pending',
            status_updated_at TEXT DEFAULT '',
            cancel_reason TEXT DEFAULT '',
            cancelled_by TEXT DEFAULT '',
            cancel_date TEXT DEFAULT '',
            return_type TEXT DEFAULT '',
            return_reason TEXT DEFAULT '',
            return_date TEXT DEFAULT '',
            return_status TEXT DEFAULT '',
            return_deduction REAL NOT NULL DEFAULT 0,
            payment_status TEXT NOT NULL DEFAULT 'Pending',
            expected_payout_date TEXT DEFAULT '',
            settled_date TEXT DEFAULT '',
            settled_amount REAL NOT NULL DEFAULT 0,
            utr_reference TEXT DEFAULT '',
            handled_by TEXT DEFAULT 'Arsh',
            notes TEXT DEFAULT '',
            is_demo INTEGER NOT NULL DEFAULT 0,
            created_at TEXT DEFAULT '',
            updated_at TEXT DEFAULT ''
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS order_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_pk INTEGER NOT NULL,
            old_status TEXT DEFAULT '',
            new_status TEXT NOT NULL,
            changed_by TEXT DEFAULT 'Arsh',
            note TEXT DEFAULT '',
            changed_at TEXT NOT NULL,
            FOREIGN KEY (order_pk) REFERENCES orders(id) ON DELETE CASCADE
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            expense_date TEXT NOT NULL,
            entry_type TEXT NOT NULL DEFAULT 'Expense',
            category TEXT NOT NULL,
            title TEXT NOT NULL,
            amount REAL NOT NULL DEFAULT 0,
            paid_by TEXT NOT NULL DEFAULT 'Arsh',
            payment_method TEXT DEFAULT 'UPI / Bank',
            notes TEXT DEFAULT '',
            order_pk INTEGER DEFAULT NULL,
            is_demo INTEGER NOT NULL DEFAULT 0,
            created_at TEXT DEFAULT ''
        )
        """
    )

    exp_cols = [r[1] for r in cur.execute("PRAGMA table_info(expenses)").fetchall()]
    if "order_pk" not in exp_cols:
        cur.execute("ALTER TABLE expenses ADD COLUMN order_pk INTEGER DEFAULT NULL")

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS supplier_products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT NOT NULL,
            sku TEXT DEFAULT '',
            unit_price REAL NOT NULL DEFAULT 0,
            supplier_name TEXT NOT NULL DEFAULT 'Supplier Ajay Sir',
            paid_by TEXT NOT NULL DEFAULT 'Arsh',
            notes TEXT DEFAULT ''
        )
        """
    )

    sp_count = cur.execute("SELECT COUNT(*) FROM supplier_products").fetchone()[0]
    if sp_count == 0:
        cur.executemany(
            "INSERT INTO supplier_products (product_name, sku, unit_price, supplier_name, paid_by, notes) VALUES (?, ?, ?, ?, ?, ?)",
            [
                ("LED Board", "", 299.0, "Supplier Ajay Sir", "Arsh", "Notebook rate Rs.299"),
                ("Adaptor", "", 120.0, "Supplier Ajay Sir", "Arsh", "Notebook rate Rs.120"),
                ("Verti. Drawer / Drawer", "", 500.0, "Supplier Ajay Sir", "Arsh", "Notebook rate Rs.500"),
            ],
        )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS partner_transfers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transfer_date TEXT NOT NULL,
            from_member TEXT NOT NULL DEFAULT 'Anurag',
            to_member TEXT NOT NULL DEFAULT 'Arsh',
            amount REAL NOT NULL DEFAULT 0,
            payment_mode TEXT DEFAULT 'Cash',
            notes TEXT DEFAULT '',
            created_at TEXT DEFAULT ''
        )
        """
    )

    tr_count = cur.execute("SELECT COUNT(*) FROM partner_transfers").fetchone()[0]
    if tr_count == 0:
        ts = now_iso()
        cur.executemany(
            "INSERT INTO partner_transfers (transfer_date, from_member, to_member, amount, payment_mode, notes, created_at) VALUES (?, 'Anurag', 'Arsh', ?, 'Cash', ?, ?)",
            [
                (today_str(), 500.0, "Anurag paid Rs.500 cash to Arsh (Meesho payout recovery)", ts),
                (today_str(), 300.0, "Anurag paid Rs.300 cash to Arsh (Meesho payout recovery)", ts),
            ],
        )

    # Seed the 3 Nova Apparels members if table is empty
    member_count = cur.execute("SELECT COUNT(*) FROM members").fetchone()[0]
    if member_count == 0:
        cur.executemany(
            "INSERT INTO members (id, name, role, is_investor, share_percent, notes) VALUES (?, ?, ?, ?, ?, ?)",
            [
                ("arsh", "Arsh", "Investor + Manager", 1, 50.0, "Co-founder, Orders & Overall Hisab"),
                ("kiran", "Kiran", "Investor + Manager", 1, 50.0, "Co-founder, Operations & Finance"),
                ("anurag", "Anurag", "Technical Manager", 0, 0.0, "Catalog, Tech, Listing & Dispatch Support"),
            ],
        )

    # Automatic timestamped backup on every startup so no record is EVER lost
    conn.commit()
    conn.close()
    auto_backup_db()


def auto_backup_db():
    try:
        bdir = os.path.join(BASE_DIR, "backups")
        os.makedirs(bdir, exist_ok=True)
        if os.path.exists(DB_PATH) and os.path.getsize(DB_PATH) > 0:
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            dst = os.path.join(bdir, f"nova_apparels_backup_{ts}.db")
            shutil.copy2(DB_PATH, dst)
            all_b = sorted([os.path.join(bdir, f) for f in os.listdir(bdir) if f.startswith("nova_apparels_backup_") and f.endswith(".db")])
            if len(all_b) > 30:
                for old in all_b[:-30]:
                    try:
                        os.remove(old)
                    except OSError:
                        pass
    except Exception as e:
        print("Auto backup notice:", e)


def seed_demo_data(conn):
    pass
    today = datetime.date.today()

    def d(offset_days):
        return (today + datetime.timedelta(days=offset_days)).strftime("%Y-%m-%d")

    sample_orders = [
        # Settled Delivered Orders
        {
            "order_id": "MSH-90451201",
            "sub_order_id": "90451201_1",
            "order_date": d(-14),
            "product_name": "Nova Cotton Oversized T-Shirt (Black, L)",
            "sku": "NA-TS-BLK-L",
            "quantity": 1,
            "customer_name": "Rohit Sharma",
            "customer_city": "Ludhiana, PB",
            "payment_mode": "Prepaid",
            "order_amount": 499,
            "product_cost": 220,
            "packaging_cost": 18,
            "initial_status": "Pending",
            "current_status": "Delivered",
            "payment_status": "Settled",
            "expected_payout_date": d(-7),
            "settled_date": d(-7),
            "settled_amount": 462,
            "utr_reference": "UTR4112098731",
            "handled_by": "Arsh",
            "notes": "Delivered on time, bank settlement received.",
        },
        {
            "order_id": "MSH-90451202",
            "sub_order_id": "90451202_1",
            "order_date": d(-12),
            "product_name": "Nova Women Co-ord Set (Olive, M)",
            "sku": "NA-CRD-OLV-M",
            "quantity": 1,
            "customer_name": "Simran Kaur",
            "customer_city": "Chandigarh",
            "payment_mode": "COD",
            "order_amount": 799,
            "product_cost": 380,
            "packaging_cost": 22,
            "initial_status": "Ready to Ship",
            "current_status": "Delivered",
            "payment_status": "Settled",
            "expected_payout_date": d(-5),
            "settled_date": d(-4),
            "settled_amount": 745,
            "utr_reference": "UTR4112099412",
            "handled_by": "Kiran",
            "notes": "COD collected & settled in bank.",
        },
        # Delivered but Payment Pending (upcoming payout)
        {
            "order_id": "MSH-90451203",
            "sub_order_id": "90451203_1",
            "order_date": d(-6),
            "product_name": "Nova Fleece Hoodie (Navy, XL)",
            "sku": "NA-HD-NVY-XL",
            "quantity": 2,
            "customer_name": "Aman Verma",
            "customer_city": "Jaipur, RJ",
            "payment_mode": "COD",
            "order_amount": 1398,
            "product_cost": 680,
            "packaging_cost": 30,
            "initial_status": "Pending",
            "current_status": "Delivered",
            "payment_status": "Pending",
            "expected_payout_date": d(2),
            "settled_date": "",
            "settled_amount": 1310,
            "utr_reference": "",
            "handled_by": "Arsh",
            "notes": "Delivered 4 days ago, Meesho 7-day cycle payout due soon.",
        },
        {
            "order_id": "MSH-90451204",
            "sub_order_id": "90451204_1",
            "order_date": d(-4),
            "product_name": "Nova Cargo Joggers (Charcoal, M)",
            "sku": "NA-JOG-CHR-M",
            "quantity": 1,
            "customer_name": "Priya Patel",
            "customer_city": "Ahmedabad, GJ",
            "payment_mode": "Prepaid",
            "order_amount": 649,
            "product_cost": 310,
            "packaging_cost": 20,
            "initial_status": "Pending",
            "current_status": "Delivered",
            "payment_status": "Pending",
            "expected_payout_date": d(4),
            "settled_date": "",
            "settled_amount": 608,
            "utr_reference": "",
            "handled_by": "Anurag",
            "notes": "Prepaid order delivered, awaiting settlement.",
        },
        # Shipped / In-Transit Orders
        {
            "order_id": "MSH-90451205",
            "sub_order_id": "90451205_1",
            "order_date": d(-2),
            "product_name": "Nova Winter Sweatshirt (Maroon, L)",
            "sku": "NA-SW-MAR-L",
            "quantity": 1,
            "customer_name": "Vikas Yadav",
            "customer_city": "Lucknow, UP",
            "payment_mode": "COD",
            "order_amount": 599,
            "product_cost": 270,
            "packaging_cost": 18,
            "initial_status": "Pending",
            "current_status": "Shipped",
            "payment_status": "Pending",
            "expected_payout_date": d(8),
            "settled_date": "",
            "settled_amount": 555,
            "utr_reference": "",
            "handled_by": "Kiran",
            "notes": "Picked up by Delhivery, in transit.",
        },
        # Ready to Ship / Pending Today
        {
            "order_id": "MSH-90451206",
            "sub_order_id": "90451206_1",
            "order_date": d(0),
            "product_name": "Nova Cotton Polo T-Shirt (White, M)",
            "sku": "NA-PL-WHT-M",
            "quantity": 1,
            "customer_name": "Harpreet Singh",
            "customer_city": "Amritsar, PB",
            "payment_mode": "Prepaid",
            "order_amount": 449,
            "product_cost": 195,
            "packaging_cost": 15,
            "initial_status": "Pending",
            "current_status": "Ready to Ship",
            "payment_status": "Pending",
            "expected_payout_date": d(10),
            "settled_date": "",
            "settled_amount": 418,
            "utr_reference": "",
            "handled_by": "Anurag",
            "notes": "Label downloaded, next-day dispatch ready.",
        },
        # Cancelled Orders
        {
            "order_id": "MSH-90451207",
            "sub_order_id": "90451207_1",
            "order_date": d(-8),
            "product_name": "Nova Denim Jacket (Blue, L)",
            "sku": "NA-JKT-BLU-L",
            "quantity": 1,
            "customer_name": "Neha Gupta",
            "customer_city": "Delhi",
            "payment_mode": "COD",
            "order_amount": 999,
            "product_cost": 480,
            "packaging_cost": 0,
            "initial_status": "Pending",
            "current_status": "Cancelled",
            "cancel_reason": "Customer changed mind / ordered wrong size",
            "cancelled_by": "Customer",
            "cancel_date": d(-7),
            "payment_status": "Not Applicable",
            "expected_payout_date": "",
            "settled_date": "",
            "settled_amount": 0,
            "handled_by": "Arsh",
            "notes": "Cancelled before dispatch, no shipping loss.",
        },
        {
            "order_id": "MSH-90451208",
            "sub_order_id": "90451208_1",
            "order_date": d(-5),
            "product_name": "Nova Printed Kurta Set (Pink, S)",
            "sku": "NA-KRT-PNK-S",
            "quantity": 1,
            "customer_name": "Pooja Rani",
            "customer_city": "Panipat, HR",
            "payment_mode": "Prepaid",
            "order_amount": 699,
            "product_cost": 320,
            "packaging_cost": 0,
            "initial_status": "Pending",
            "current_status": "Cancelled",
            "cancel_reason": "Out of stock in size S (Inventory mismatch)",
            "cancelled_by": "Seller",
            "cancel_date": d(-4),
            "payment_status": "Not Applicable",
            "expected_payout_date": "",
            "settled_date": "",
            "settled_amount": 0,
            "handled_by": "Anurag",
            "notes": "Need to update Meesho stock count for S size.",
        },
        # Returned / RTO Orders
        {
            "order_id": "MSH-90451209",
            "sub_order_id": "90451209_1",
            "order_date": d(-11),
            "product_name": "Nova Women Co-ord Set (Black, L)",
            "sku": "NA-CRD-BLK-L",
            "quantity": 1,
            "customer_name": "Meera Joshi",
            "customer_city": "Pune, MH",
            "payment_mode": "COD",
            "order_amount": 799,
            "product_cost": 380,
            "packaging_cost": 22,
            "initial_status": "Shipped",
            "current_status": "Returned",
            "return_type": "Customer Return",
            "return_reason": "Size issue - fitting was slightly tight",
            "return_date": d(-3),
            "return_status": "Received",
            "return_deduction": 145,
            "payment_status": "Not Applicable",
            "expected_payout_date": "",
            "settled_date": "",
            "settled_amount": 0,
            "handled_by": "Kiran",
            "notes": "Parcel received back in good condition, restocked.",
        },
        {
            "order_id": "MSH-90451210",
            "sub_order_id": "90451210_1",
            "order_date": d(-9),
            "product_name": "Nova Fleece Hoodie (Grey, M)",
            "sku": "NA-HD-GRY-M",
            "quantity": 1,
            "customer_name": "Sandeep Kumar",
            "customer_city": "Patna, BR",
            "payment_mode": "COD",
            "order_amount": 699,
            "product_cost": 340,
            "packaging_cost": 18,
            "initial_status": "Shipped",
            "current_status": "RTO",
            "return_type": "Courier RTO",
            "return_reason": "Customer unreachable / phone switched off at delivery",
            "return_date": d(-2),
            "return_status": "In Transit",
            "return_deduction": 0,
            "payment_status": "Not Applicable",
            "expected_payout_date": "",
            "settled_date": "",
            "settled_amount": 0,
            "handled_by": "Arsh",
            "notes": "RTO returning back to warehouse (usually 0 fee on Meesho RTO).",
        },
    ]

    cur = conn.cursor()
    ts = now_iso()
    for o in sample_orders:
        cur.execute(
            """
            INSERT INTO orders (
                order_id, sub_order_id, order_date, product_name, sku, quantity,
                customer_name, customer_city, payment_mode, order_amount, product_cost, packaging_cost,
                initial_status, current_status, status_updated_at,
                cancel_reason, cancelled_by, cancel_date,
                return_type, return_reason, return_date, return_status, return_deduction,
                payment_status, expected_payout_date, settled_date, settled_amount, utr_reference,
                handled_by, notes, is_demo, created_at, updated_at
            ) VALUES (
                :order_id, :sub_order_id, :order_date, :product_name, :sku, :quantity,
                :customer_name, :customer_city, :payment_mode, :order_amount, :product_cost, :packaging_cost,
                :initial_status, :current_status, :status_updated_at,
                :cancel_reason, :cancelled_by, :cancel_date,
                :return_type, :return_reason, :return_date, :return_status, :return_deduction,
                :payment_status, :expected_payout_date, :settled_date, :settled_amount, :utr_reference,
                :handled_by, :notes, 1, :created_at, :updated_at
            )
            """,
            {
                "order_id": o["order_id"],
                "sub_order_id": o.get("sub_order_id", ""),
                "order_date": o["order_date"],
                "product_name": o["product_name"],
                "sku": o.get("sku", ""),
                "quantity": o.get("quantity", 1),
                "customer_name": o.get("customer_name", ""),
                "customer_city": o.get("customer_city", ""),
                "payment_mode": o["payment_mode"],
                "order_amount": o["order_amount"],
                "product_cost": o.get("product_cost", 0),
                "packaging_cost": o.get("packaging_cost", 0),
                "initial_status": o["initial_status"],
                "current_status": o["current_status"],
                "status_updated_at": ts,
                "cancel_reason": o.get("cancel_reason", ""),
                "cancelled_by": o.get("cancelled_by", ""),
                "cancel_date": o.get("cancel_date", ""),
                "return_type": o.get("return_type", ""),
                "return_reason": o.get("return_reason", ""),
                "return_date": o.get("return_date", ""),
                "return_status": o.get("return_status", ""),
                "return_deduction": o.get("return_deduction", 0),
                "payment_status": o["payment_status"],
                "expected_payout_date": o.get("expected_payout_date", ""),
                "settled_date": o.get("settled_date", ""),
                "settled_amount": o.get("settled_amount", 0),
                "utr_reference": o.get("utr_reference", ""),
                "handled_by": o.get("handled_by", "Arsh"),
                "notes": o.get("notes", ""),
                "created_at": ts,
                "updated_at": ts,
            },
        )
        pk = cur.lastrowid
        cur.execute(
            "INSERT INTO order_history (order_pk, old_status, new_status, changed_by, note, changed_at) VALUES (?, ?, ?, ?, ?, ?)",
            (pk, "", o["initial_status"], o.get("handled_by", "Arsh"), "Order received", o["order_date"] + " 10:00:00"),
        )
        if o["current_status"] != o["initial_status"]:
            cur.execute(
                "INSERT INTO order_history (order_pk, old_status, new_status, changed_by, note, changed_at) VALUES (?, ?, ?, ?, ?, ?)",
                (pk, o["initial_status"], o["current_status"], o.get("handled_by", "Arsh"), o.get("notes", "Status updated"), ts),
            )

    sample_expenses = [
        (d(-20), "Investment", "Capital Investment", "Initial Nova Apparels Stock Capital", 25000, "Arsh", "Bank Transfer", "Arsh initial investment share"),
        (d(-20), "Investment", "Capital Investment", "Initial Nova Apparels Stock Capital", 25000, "Kiran", "Bank Transfer", "Kiran initial investment share"),
        (d(-18), "Expense", "Stock / Inventory", "Winter Hoodies & Co-ord Wholesale Lot", 18500, "Company Bank", "Bank Transfer", "Bought 50 pcs assorted apparel"),
        (d(-15), "Expense", "Packaging", "Meesho Branded Polybags + Thermal Labels + Tape", 1650, "Kiran", "UPI", "500 polybags + 2 thermal rolls"),
        (d(-10), "Expense", "Ads & Marketing", "Meesho Catalog Boost Ads Wallet Recharge", 1200, "Arsh", "UPI", "Ad budget for top 5 catalogs"),
        (d(-7), "Expense", "Tech / Software", "Thermal Printer Setup & Internet Recharge", 899, "Anurag", "UPI", "Handled by Anurag for dispatch station"),
        (d(-3), "Expense", "Shipping / Logistics", "Local Transport Auto from Market to Warehouse", 350, "Kiran", "Cash", "Stock pickup transport"),
    ]
    for exp in sample_expenses:
        cur.execute(
            """
            INSERT INTO expenses (expense_date, entry_type, category, title, amount, paid_by, payment_method, notes, is_demo, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
            """,
            (*exp, ts),
        )


def rows_to_dicts(rows):
    return [dict(r) for r in rows]


def find_supplier_product(conn, sku, product_name):
    products = rows_to_dicts(conn.execute("SELECT * FROM supplier_products ORDER BY id ASC").fetchall())
    sku_low = (sku or "").strip().lower()
    name_low = (product_name or "").strip().lower()
    if sku_low:
        for p in products:
            p_skus = [s.strip().lower() for s in (p.get("sku") or "").split(",") if s.strip()]
            if sku_low in p_skus:
                return p
    if name_low:
        for p in products:
            pname = (p.get("product_name") or "").strip().lower()
            if pname and (pname in name_low or name_low in pname):
                return p
    return None


def sync_order_supplier_expense(conn, order_pk):
    o = conn.execute("SELECT * FROM orders WHERE id = ?", (order_pk,)).fetchone()
    if not o:
        return
    if o["order_id"] == "PRIOR-SHIPPED-BULK":
        return

    shipped_states = ("Shipped", "Delivered", "Returned", "RTO")
    sp = find_supplier_product(conn, o["sku"], o["product_name"])
    unit_price = float(o["product_cost"] or 0)
    supplier_name = sp["supplier_name"] if sp else "Supplier Ajay Sir"
    paid_by = sp["paid_by"] if sp else "Arsh"
    item_label = sp["product_name"] if sp else o["product_name"]

    if unit_price <= 0 and sp:
        unit_price = float(sp["unit_price"] or 0)
        if unit_price > 0:
            conn.execute("UPDATE orders SET product_cost = ? WHERE id = ?", (unit_price, order_pk))

    if o["current_status"] in shipped_states and unit_price > 0:
        # Notebook already covers historical supplier payments up to 2026-11-04
        if o["order_date"] <= "2026-11-04":
            return
        total_amt = round(unit_price * max(1, int(o["quantity"] or 1)), 2)
        title = f"Paid to {supplier_name} — {item_label} (Order {o['order_id']})"
        existing_exp = conn.execute("SELECT id FROM expenses WHERE order_pk = ?", (order_pk,)).fetchone()
        if existing_exp:
            conn.execute(
                """
                UPDATE expenses
                SET expense_date = ?, title = ?, amount = ?, paid_by = ?, notes = ?
                WHERE id = ?
                """,
                (
                    o["order_date"],
                    title,
                    total_amt,
                    paid_by,
                    f"Auto-synced on {o['current_status']} | SKU: {o['sku'] or '-'}",
                    existing_exp["id"],
                ),
            )
        else:
            conn.execute(
                """
                INSERT INTO expenses (
                    expense_date, entry_type, category, title, amount, paid_by,
                    payment_method, notes, order_pk, is_demo, created_at
                ) VALUES (?, 'Expense', 'Stock / Inventory', ?, ?, ?, 'Supplier Hisab', ?, ?, 0, ?)
                """,
                (
                    o["order_date"],
                    title,
                    total_amt,
                    paid_by,
                    f"Auto-created when order became {o['current_status']} | SKU: {o['sku'] or '-'}",
                    order_pk,
                    now_iso(),
                ),
            )
    elif o["current_status"] in ("Pending", "Ready to Ship", "Cancelled"):
        conn.execute("DELETE FROM expenses WHERE order_pk = ?", (order_pk,))


def compute_summary(conn):
    orders = rows_to_dicts(conn.execute("SELECT * FROM orders").fetchall())
    expenses = rows_to_dicts(conn.execute("SELECT * FROM expenses").fetchall())
    members = rows_to_dicts(conn.execute("SELECT * FROM members").fetchall())
    transfers = rows_to_dicts(conn.execute("SELECT * FROM partner_transfers").fetchall())

    total_orders = len(orders)
    cod_orders = sum(1 for o in orders if o["payment_mode"].upper() == "COD")
    prepaid_orders = sum(1 for o in orders if o["payment_mode"].upper() == "PREPAID")
    unverified_mode_orders = total_orders - cod_orders - prepaid_orders

    status_counts = {}
    for o in orders:
        st = o["current_status"]
        status_counts[st] = status_counts.get(st, 0) + 1

    cancelled_orders = [o for o in orders if o["current_status"] == "Cancelled"]
    returned_orders = [o for o in orders if o["current_status"] in ("Returned", "RTO")]
    delivered_orders = [o for o in orders if o["current_status"] == "Delivered"]
    active_orders = [o for o in orders if o["current_status"] in ("Pending", "Ready to Ship", "Shipped")]

    # Payment & financial metrics
    gross_sales = sum(o["order_amount"] for o in orders if o["current_status"] not in ("Cancelled", "Returned", "RTO"))
    settled_amount = sum(o["settled_amount"] for o in orders if o["payment_status"] == "Settled")
    pending_payout_amount = sum(
        (o["settled_amount"] if o["settled_amount"] > 0 else o["order_amount"])
        for o in orders
        if o["payment_status"] in ("Pending", "On Hold") and o["current_status"] not in ("Cancelled", "Returned", "RTO")
    )
    return_deductions = sum(o["return_deduction"] for o in orders)
    cogs_delivered = sum(
        (o["product_cost"] + o["packaging_cost"])
        for o in orders
        if o["current_status"] == "Delivered"
    )

    total_investments = sum(e["amount"] for e in expenses if e["entry_type"] == "Investment")
    total_expenses = sum(e["amount"] for e in expenses if e["entry_type"] == "Expense")
    total_withdrawals = sum(e["amount"] for e in expenses if e["entry_type"] == "Withdrawal")

    # Arsh out-of-pocket investment & Anurag bank recovery hisab
    arsh_invested = sum(
        e["amount"] for e in expenses
        if e["entry_type"] in ("Investment", "Expense") and (e["paid_by"] or "").lower() == "arsh"
    )
    anurag_paid_to_arsh = sum(
        t["amount"] for t in transfers
        if (t["from_member"] or "").lower() == "anurag" and (t["to_member"] or "").lower() == "arsh"
    )
    balance_with_anurag = round(settled_amount - anurag_paid_to_arsh, 2)
    arsh_to_recover = round(arsh_invested - anurag_paid_to_arsh, 2)

    # Per-member financial breakdown
    member_stats = []
    for m in members:
        name = m["name"]
        invested = sum(e["amount"] for e in expenses if e["entry_type"] == "Investment" and e["paid_by"].lower() == name.lower())
        spent = sum(e["amount"] for e in expenses if e["entry_type"] == "Expense" and e["paid_by"].lower() == name.lower())
        withdrawn = sum(e["amount"] for e in expenses if e["entry_type"] == "Withdrawal" and e["paid_by"].lower() == name.lower())
        orders_handled = sum(1 for o in orders if (o["handled_by"] or "").lower() == name.lower())
        member_stats.append({
            **m,
            "invested": round(invested, 2),
            "expenses_paid": round(spent, 2),
            "withdrawn": round(withdrawn, 2),
            "net_contribution": round(invested + spent - withdrawn, 2),
            "orders_handled": orders_handled,
        })

    # Upcoming payout schedule (pending payments sorted by expected_payout_date)
    upcoming_payouts = [
        {
            "id": o["id"],
            "order_id": o["order_id"],
            "product_name": o["product_name"],
            "current_status": o["current_status"],
            "payment_mode": o["payment_mode"],
            "payment_status": o["payment_status"],
            "expected_payout_date": o["expected_payout_date"],
            "amount": o["settled_amount"] if o["settled_amount"] > 0 else o["order_amount"],
        }
        for o in orders
        if o["payment_status"] in ("Pending", "On Hold") and o["current_status"] not in ("Cancelled", "Returned", "RTO")
    ]
    upcoming_payouts.sort(key=lambda x: x["expected_payout_date"] or "9999-99-99")

    # Scheduled upcoming payout dates (including return deductions scheduled on those dates)
    # E.g. 2026-11-13 has Delivered (+252.48) and 2 Returns (-157, -157) => Net -61.52
    # 2026-11-16 has 1 Return (-175) => Net -175.00
    payout_dates_map = {}
    for o in orders:
        dt = o["expected_payout_date"]
        if not dt or dt in ("2026-11-02", "2026-11-03"):
            continue
        if dt not in payout_dates_map:
            payout_dates_map[dt] = {
                "date": dt,
                "credits": 0.0,
                "deductions": 0.0,
                "net": 0.0,
                "bank_transfer": 0.0,
                "items": [],
            }
        grp = payout_dates_map[dt]
        if o["current_status"] in ("Returned", "RTO"):
            fee = float(o["return_deduction"] or 0)
            grp["deductions"] += fee
            grp["net"] -= fee
            grp["items"].append({
                "sub_order_id": o["sub_order_id"],
                "product_name": o["product_name"],
                "sku": o["sku"],
                "type": "Return Fee",
                "amount": -fee,
            })
        elif o["current_status"] == "Delivered":
            amt = float(o["settled_amount"] if o["settled_amount"] > 0 else o["order_amount"])
            grp["credits"] += amt
            grp["net"] += amt
            grp["items"].append({
                "sub_order_id": o["sub_order_id"],
                "product_name": o["product_name"],
                "sku": o["sku"],
                "type": "Delivered Payout",
                "amount": amt,
            })

    upcoming_schedule = []
    for dt in sorted(payout_dates_map.keys()):
        grp = payout_dates_map[dt]
        grp["credits"] = round(grp["credits"], 2)
        grp["deductions"] = round(grp["deductions"], 2)
        grp["net"] = round(grp["net"], 2)
        grp["bank_transfer"] = max(0.0, grp["net"])
        upcoming_schedule.append(grp)

    upcoming_net_7days = round(sum(grp["net"] for grp in upcoming_schedule), 2)

    # Reason breakdowns for cancellations & returns
    cancel_reasons = {}
    for o in cancelled_orders:
        r = (o["cancel_reason"] or "Not specified").strip()
        cancel_reasons[r] = cancel_reasons.get(r, 0) + 1

    return_reasons = {}
    for o in returned_orders:
        r = (o["return_reason"] or "Not specified").strip()
        return_reasons[r] = return_reasons.get(r, 0) + 1

    # Daily chart data (last 14 days)
    today = datetime.date.today()
    daily_series = []
    for i in range(13, -1, -1):
        day = (today - datetime.timedelta(days=i)).strftime("%Y-%m-%d")
        day_orders = [o for o in orders if o["order_date"] == day]
        day_sales = sum(o["order_amount"] for o in day_orders if o["current_status"] not in ("Cancelled", "Returned", "RTO"))
        daily_series.append({
            "date": day,
            "label": (today - datetime.timedelta(days=i)).strftime("%d %b"),
            "orders": len(day_orders),
            "sales": round(day_sales, 2),
        })

    has_demo = any(o["is_demo"] == 1 for o in orders) or any(e["is_demo"] == 1 for e in expenses)

    # Net cash & estimated net profit
    # Cash in company pool = investments + settled bank payouts - expenses - withdrawals
    company_bank_expenses = sum(
        e["amount"] for e in expenses if e["entry_type"] == "Expense" and e["paid_by"] == "Company Bank"
    )
    net_profit_est = settled_amount - cogs_delivered - return_deductions - (
        sum(e["amount"] for e in expenses if e["entry_type"] == "Expense" and e["category"] != "Stock / Inventory")
    )

    return {
        "total_orders": total_orders,
        "cod_orders": cod_orders,
        "prepaid_orders": prepaid_orders,
        "unverified_mode_orders": unverified_mode_orders,
        "status_counts": status_counts,
        "delivered_count": len(delivered_orders),
        "settled_count": len([o for o in orders if o["payment_status"] == "Settled"]),
        "active_count": len(active_orders),
        "cancelled_count": len(cancelled_orders),
        "returned_count": len(returned_orders),
        "gross_sales": round(gross_sales, 2),
        "settled_amount": round(settled_amount, 2),
        "pending_payout_amount": round(pending_payout_amount, 2),
        "return_deductions": round(return_deductions, 2),
        "total_investments": round(total_investments, 2),
        "total_expenses": round(total_expenses, 2),
        "total_withdrawals": round(total_withdrawals, 2),
        "arsh_invested": round(arsh_invested, 2),
        "anurag_paid_to_arsh": round(anurag_paid_to_arsh, 2),
        "balance_with_anurag": balance_with_anurag,
        "arsh_to_recover": arsh_to_recover,
        "company_bank_expenses": round(company_bank_expenses, 2),
        "net_profit_est": round(net_profit_est, 2),
        "upcoming_payouts": upcoming_payouts,
        "upcoming_schedule": upcoming_schedule,
        "upcoming_net_7days": upcoming_net_7days,
        "cancel_reasons": cancel_reasons,
        "return_reasons": return_reasons,
        "member_stats": member_stats,
        "daily_series": daily_series,
        "has_demo": has_demo,
    }


class PortalHandler(BaseHTTPRequestHandler):
    server_version = "NovaApparelsPortal/1.0"

    def log_message(self, format, *args):
        # Quiet clean logging
        pass

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def read_json_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw)

    def serve_static(self, rel_path):
        if rel_path == "" or rel_path == "/":
            rel_path = "index.html"
        rel_path = rel_path.lstrip("/")
        safe_path = os.path.normpath(os.path.join(STATIC_DIR, rel_path))
        if not safe_path.startswith(os.path.abspath(STATIC_DIR)) or not os.path.isfile(safe_path):
            self.send_error(404, "File not found")
            return
        mime, _ = mimetypes.guess_type(safe_path)
        with open(safe_path, "rb") as f:
            content = f.read()
        self.send_response(200)
        self.send_header("Content-Type", f"{mime or 'application/octet-stream'}; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/dashboard":
            conn = get_conn()
            try:
                summary = compute_summary(conn)
                orders = rows_to_dicts(conn.execute("SELECT * FROM orders ORDER BY order_date DESC, id DESC").fetchall())
                expenses = rows_to_dicts(conn.execute("SELECT * FROM expenses ORDER BY expense_date DESC, id DESC").fetchall())
                transfers = rows_to_dicts(conn.execute("SELECT * FROM partner_transfers ORDER BY transfer_date DESC, id DESC").fetchall())
                supplier_products = rows_to_dicts(conn.execute("SELECT * FROM supplier_products ORDER BY id ASC").fetchall())
                history = rows_to_dicts(conn.execute("SELECT * FROM order_history ORDER BY changed_at DESC, id DESC").fetchall())
                history_map = {}
                for h in history:
                    history_map.setdefault(h["order_pk"], []).append(h)
                for o in orders:
                    o["history"] = history_map.get(o["id"], [])

                # Collect unique SKUs from active/shipped orders for easy mapping
                sku_rows = rows_to_dicts(
                    conn.execute(
                        "SELECT DISTINCT sku, product_name FROM orders WHERE sku != '' AND order_id != 'PRIOR-SHIPPED-BULK' ORDER BY sku ASC"
                    ).fetchall()
                )
                self.send_json({
                    "summary": summary,
                    "orders": orders,
                    "expenses": expenses,
                    "transfers": transfers,
                    "supplier_products": supplier_products,
                    "order_skus": sku_rows,
                })
            finally:
                conn.close()
            return

        if path == "/api/export/csv":
            conn = get_conn()
            try:
                orders = rows_to_dicts(conn.execute("SELECT * FROM orders ORDER BY order_date DESC, id DESC").fetchall())
                buf = io.StringIO()
                if orders:
                    writer = csv.DictWriter(buf, fieldnames=list(orders[0].keys()))
                    writer.writeheader()
                    writer.writerows(orders)
                else:
                    buf.write("order_id,order_date,product_name,payment_mode,order_amount,initial_status,current_status,payment_status\n")
                data = buf.getvalue().encode("utf-8-sig")
                self.send_response(200)
                self.send_header("Content-Type", "text/csv; charset=utf-8")
                self.send_header("Content-Disposition", f'attachment; filename="nova_apparels_orders_{today_str()}.csv"')
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            finally:
                conn.close()
            return

        if path == "/api/export/backup":
            conn = get_conn()
            try:
                payload = {
                    "exported_at": now_iso(),
                    "store": "Nova Apparels",
                    "members": rows_to_dicts(conn.execute("SELECT * FROM members").fetchall()),
                    "orders": rows_to_dicts(conn.execute("SELECT * FROM orders").fetchall()),
                    "order_history": rows_to_dicts(conn.execute("SELECT * FROM order_history").fetchall()),
                    "expenses": rows_to_dicts(conn.execute("SELECT * FROM expenses").fetchall()),
                }
                data = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Disposition", f'attachment; filename="nova_apparels_backup_{today_str()}.json"')
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            finally:
                conn.close()
            return

        self.serve_static(path)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        try:
            body = self.read_json_body()
        except Exception as exc:
            self.send_json({"error": f"Invalid JSON: {exc}"}, status=400)
            return

        conn = get_conn()
        try:
            if path == "/api/orders":
                order_id = (body.get("order_id") or "").strip()
                product_name = (body.get("product_name") or "").strip()
                order_date = (body.get("order_date") or today_str()).strip()
                if not order_id or not product_name:
                    self.send_json({"error": "Order ID and Product Name are required."}, status=400)
                    return

                existing = conn.execute("SELECT id FROM orders WHERE order_id = ?", (order_id,)).fetchone()
                if existing:
                    self.send_json({"error": f"Order ID '{order_id}' already exists!"}, status=409)
                    return

                ts = now_iso()
                init_st = body.get("initial_status") or body.get("current_status") or "Pending"
                curr_st = body.get("current_status") or init_st
                handled_by = body.get("handled_by") or "Arsh"
                pay_status = body.get("payment_status")
                if not pay_status:
                    pay_status = "Not Applicable" if curr_st in ("Cancelled", "Returned", "RTO") else "Pending"

                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO orders (
                        order_id, sub_order_id, order_date, product_name, sku, quantity,
                        customer_name, customer_city, payment_mode, order_amount, product_cost, packaging_cost,
                        initial_status, current_status, status_updated_at,
                        cancel_reason, cancelled_by, cancel_date,
                        return_type, return_reason, return_date, return_status, return_deduction,
                        payment_status, expected_payout_date, settled_date, settled_amount, utr_reference,
                        handled_by, notes, is_demo, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
                    """,
                    (
                        order_id,
                        (body.get("sub_order_id") or "").strip(),
                        order_date,
                        product_name,
                        (body.get("sku") or "").strip(),
                        int(body.get("quantity") or 1),
                        (body.get("customer_name") or "").strip(),
                        (body.get("customer_city") or "").strip(),
                        body.get("payment_mode") or "COD",
                        float(body.get("order_amount") or 0),
                        float(body.get("product_cost") or 0),
                        float(body.get("packaging_cost") or 0),
                        init_st,
                        curr_st,
                        ts,
                        (body.get("cancel_reason") or "").strip(),
                        (body.get("cancelled_by") or "").strip(),
                        (body.get("cancel_date") or "").strip(),
                        (body.get("return_type") or "").strip(),
                        (body.get("return_reason") or "").strip(),
                        (body.get("return_date") or "").strip(),
                        (body.get("return_status") or "").strip(),
                        float(body.get("return_deduction") or 0),
                        pay_status,
                        (body.get("expected_payout_date") or "").strip(),
                        (body.get("settled_date") or "").strip(),
                        float(body.get("settled_amount") or 0),
                        (body.get("utr_reference") or "").strip(),
                        handled_by,
                        (body.get("notes") or "").strip(),
                        ts,
                        ts,
                    ),
                )
                pk = cur.lastrowid
                cur.execute(
                    "INSERT INTO order_history (order_pk, old_status, new_status, changed_by, note, changed_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (pk, "", init_st, handled_by, "Order added", ts),
                )
                if curr_st != init_st:
                    cur.execute(
                        "INSERT INTO order_history (order_pk, old_status, new_status, changed_by, note, changed_at) VALUES (?, ?, ?, ?, ?, ?)",
                        (pk, init_st, curr_st, handled_by, body.get("notes") or "Current status recorded", ts),
                    )
                sync_order_supplier_expense(conn, pk)
                conn.commit()
                self.send_json({"ok": True, "id": pk}, status=201)
                return

            if path == "/api/orders/import":
                rows = body.get("rows") or []
                handled_by = body.get("handled_by") or "Arsh"
                if not isinstance(rows, list) or not rows:
                    self.send_json({"error": "No rows provided to import."}, status=400)
                    return

                ts = now_iso()
                inserted = 0
                updated = 0
                cur = conn.cursor()
                for r in rows:
                    oid = (r.get("order_id") or "").strip()
                    if not oid:
                        continue
                    existing = cur.execute("SELECT id, current_status FROM orders WHERE order_id = ?", (oid,)).fetchone()
                    curr_st = (r.get("current_status") or "Pending").strip()
                    pay_st = (r.get("payment_status") or "").strip()
                    if not pay_st:
                        pay_st = "Not Applicable" if curr_st in ("Cancelled", "Returned", "RTO") else "Pending"

                    if existing:
                        old_st = existing["current_status"]
                        cur.execute(
                            """
                            UPDATE orders SET
                                product_name = COALESCE(NULLIF(?, ''), product_name),
                                current_status = ?,
                                status_updated_at = ?,
                                cancel_reason = COALESCE(NULLIF(?, ''), cancel_reason),
                                return_reason = COALESCE(NULLIF(?, ''), return_reason),
                                return_type = COALESCE(NULLIF(?, ''), return_type),
                                payment_status = ?,
                                expected_payout_date = COALESCE(NULLIF(?, ''), expected_payout_date),
                                settled_date = COALESCE(NULLIF(?, ''), settled_date),
                                settled_amount = CASE WHEN ? > 0 THEN ? ELSE settled_amount END,
                                utr_reference = COALESCE(NULLIF(?, ''), utr_reference),
                                updated_at = ?
                            WHERE id = ?
                            """,
                            (
                                (r.get("product_name") or "").strip(),
                                curr_st,
                                ts,
                                (r.get("cancel_reason") or "").strip(),
                                (r.get("return_reason") or "").strip(),
                                (r.get("return_type") or "").strip(),
                                pay_st,
                                (r.get("expected_payout_date") or "").strip(),
                                (r.get("settled_date") or "").strip(),
                                float(r.get("settled_amount") or 0),
                                float(r.get("settled_amount") or 0),
                                (r.get("utr_reference") or "").strip(),
                                ts,
                                existing["id"],
                            ),
                        )
                        if old_st != curr_st:
                            cur.execute(
                                "INSERT INTO order_history (order_pk, old_status, new_status, changed_by, note, changed_at) VALUES (?, ?, ?, ?, ?, ?)",
                                (existing["id"], old_st, curr_st, handled_by, "Updated via CSV import", ts),
                            )
                        sync_order_supplier_expense(conn, existing["id"])
                        updated += 1
                    else:
                        init_st = (r.get("initial_status") or curr_st).strip()
                        cur.execute(
                            """
                            INSERT INTO orders (
                                order_id, sub_order_id, order_date, product_name, sku, quantity,
                                customer_name, customer_city, payment_mode, order_amount, product_cost, packaging_cost,
                                initial_status, current_status, status_updated_at,
                                cancel_reason, cancelled_by, cancel_date,
                                return_type, return_reason, return_date, return_status, return_deduction,
                                payment_status, expected_payout_date, settled_date, settled_amount, utr_reference,
                                handled_by, notes, is_demo, created_at, updated_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
                            """,
                            (
                                oid,
                                (r.get("sub_order_id") or "").strip(),
                                (r.get("order_date") or today_str()).strip(),
                                (r.get("product_name") or "Meesho Product").strip(),
                                (r.get("sku") or "").strip(),
                                int(r.get("quantity") or 1),
                                (r.get("customer_name") or "").strip(),
                                (r.get("customer_city") or "").strip(),
                                (r.get("payment_mode") or "COD").strip(),
                                float(r.get("order_amount") or 0),
                                float(r.get("product_cost") or 0),
                                float(r.get("packaging_cost") or 0),
                                init_st,
                                curr_st,
                                ts,
                                (r.get("cancel_reason") or "").strip(),
                                (r.get("cancelled_by") or "").strip(),
                                (r.get("cancel_date") or "").strip(),
                                (r.get("return_type") or "").strip(),
                                (r.get("return_reason") or "").strip(),
                                (r.get("return_date") or "").strip(),
                                (r.get("return_status") or "").strip(),
                                float(r.get("return_deduction") or 0),
                                pay_st,
                                (r.get("expected_payout_date") or "").strip(),
                                (r.get("settled_date") or "").strip(),
                                float(r.get("settled_amount") or 0),
                                (r.get("utr_reference") or "").strip(),
                                handled_by,
                                (r.get("notes") or "Imported from CSV").strip(),
                                ts,
                                ts,
                            ),
                        )
                        pk = cur.lastrowid
                        cur.execute(
                            "INSERT INTO order_history (order_pk, old_status, new_status, changed_by, note, changed_at) VALUES (?, ?, ?, ?, ?, ?)",
                            (pk, "", curr_st, handled_by, "Imported from CSV", ts),
                        )
                        sync_order_supplier_expense(conn, pk)
                        inserted += 1
                conn.commit()
                self.send_json({"ok": True, "inserted": inserted, "updated": updated})
                return

            if path == "/api/expenses":
                title = (body.get("title") or "").strip()
                category = (body.get("category") or "Other").strip()
                amount = float(body.get("amount") or 0)
                if not title or amount <= 0:
                    self.send_json({"error": "Title and positive Amount are required."}, status=400)
                    return

                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO expenses (expense_date, entry_type, category, title, amount, paid_by, payment_method, notes, is_demo, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
                    """,
                    (
                        (body.get("expense_date") or today_str()).strip(),
                        (body.get("entry_type") or "Expense").strip(),
                        category,
                        title,
                        amount,
                        (body.get("paid_by") or "Arsh").strip(),
                        (body.get("payment_method") or "UPI / Bank").strip(),
                        (body.get("notes") or "").strip(),
                        now_iso(),
                    ),
                )
                conn.commit()
                self.send_json({"ok": True, "id": cur.lastrowid}, status=201)
                return

            if path == "/api/transfers":
                amount = float(body.get("amount") or 0)
                if amount <= 0:
                    self.send_json({"error": "Positive amount is required."}, status=400)
                    return
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO partner_transfers (transfer_date, from_member, to_member, amount, payment_mode, notes, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        (body.get("transfer_date") or today_str()).strip(),
                        (body.get("from_member") or "Anurag").strip(),
                        (body.get("to_member") or "Arsh").strip(),
                        amount,
                        (body.get("payment_mode") or "Cash").strip(),
                        (body.get("notes") or "").strip(),
                        now_iso(),
                    ),
                )
                conn.commit()
                self.send_json({"ok": True, "id": cur.lastrowid}, status=201)
                return

            if path == "/api/supplier-products":
                pname = (body.get("product_name") or "").strip()
                sku = (body.get("sku") or "").strip()
                unit_price = float(body.get("unit_price") or 0)
                supplier_name = (body.get("supplier_name") or "Supplier Ajay Sir").strip()
                paid_by = (body.get("paid_by") or "Arsh").strip()
                notes = (body.get("notes") or "").strip()
                if not pname or unit_price <= 0:
                    self.send_json({"error": "Product name and positive price are required."}, status=400)
                    return

                sp_id = body.get("id")
                if sp_id:
                    conn.execute(
                        "UPDATE supplier_products SET product_name = ?, sku = ?, unit_price = ?, supplier_name = ?, paid_by = ?, notes = ? WHERE id = ?",
                        (pname, sku, unit_price, supplier_name, paid_by, notes, int(sp_id)),
                    )
                else:
                    conn.execute(
                        "INSERT INTO supplier_products (product_name, sku, unit_price, supplier_name, paid_by, notes) VALUES (?, ?, ?, ?, ?, ?)",
                        (pname, sku, unit_price, supplier_name, paid_by, notes),
                    )
                # Sync all shipped/delivered orders so any matching SKU gets its expense auto-created
                for row in conn.execute("SELECT id FROM orders").fetchall():
                    sync_order_supplier_expense(conn, row["id"])
                conn.commit()
                self.send_json({"ok": True})
                return

            if path == "/api/supplier-products/map-sku":
                sku = (body.get("sku") or "").strip()
                sp_id = int(body.get("supplier_product_id") or 0)
                sp = conn.execute("SELECT * FROM supplier_products WHERE id = ?", (sp_id,)).fetchone()
                if not sku or not sp:
                    self.send_json({"error": "SKU and valid Supplier Product are required."}, status=400)
                    return
                # Remove SKU from any other product first, then attach to chosen product
                for row in conn.execute("SELECT id, sku FROM supplier_products").fetchall():
                    existing_skus = [s.strip() for s in (row["sku"] or "").split(",") if s.strip() and s.strip().lower() != sku.lower()]
                    if row["id"] == sp_id:
                        existing_skus.append(sku)
                    conn.execute("UPDATE supplier_products SET sku = ? WHERE id = ?", (", ".join(existing_skus), row["id"]))
                # Re-sync matching orders
                for row in conn.execute("SELECT id FROM orders WHERE LOWER(sku) = LOWER(?)", (sku,)).fetchall():
                    conn.execute("UPDATE orders SET product_cost = ? WHERE id = ?", (sp["unit_price"], row["id"]))
                    sync_order_supplier_expense(conn, row["id"])
                conn.commit()
                self.send_json({"ok": True})
                return

            if path == "/api/demo/clear":
                conn.execute("DELETE FROM orders WHERE is_demo = 1")
                conn.execute("DELETE FROM expenses WHERE is_demo = 1")
                conn.commit()
                self.send_json({"ok": True})
                return

            if path == "/api/demo/restore":
                conn.execute("DELETE FROM orders WHERE is_demo = 1")
                conn.execute("DELETE FROM expenses WHERE is_demo = 1")
                seed_demo_data(conn)
                conn.commit()
                self.send_json({"ok": True})
                return

            self.send_json({"error": "Endpoint not found"}, status=404)
        finally:
            conn.close()

    def do_PUT(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        try:
            body = self.read_json_body()
        except Exception as exc:
            self.send_json({"error": f"Invalid JSON: {exc}"}, status=400)
            return

        conn = get_conn()
        try:
            if path.startswith("/api/orders/"):
                try:
                    pk = int(path.split("/api/orders/")[1])
                except ValueError:
                    self.send_json({"error": "Invalid order ID"}, status=400)
                    return

                existing = conn.execute("SELECT * FROM orders WHERE id = ?", (pk,)).fetchone()
                if not existing:
                    self.send_json({"error": "Order not found"}, status=404)
                    return

                ts = now_iso()
                old_status = existing["current_status"]
                new_status = (body.get("current_status") or old_status).strip()
                changed_by = (body.get("handled_by") or body.get("changed_by") or existing["handled_by"] or "Arsh").strip()

                fields = [
                    "order_id", "sub_order_id", "order_date", "product_name", "sku", "quantity",
                    "customer_name", "customer_city", "payment_mode", "order_amount", "product_cost", "packaging_cost",
                    "initial_status", "current_status", "cancel_reason", "cancelled_by", "cancel_date",
                    "return_type", "return_reason", "return_date", "return_status", "return_deduction",
                    "payment_status", "expected_payout_date", "settled_date", "settled_amount", "utr_reference",
                    "handled_by", "notes"
                ]

                updates = {}
                for f in fields:
                    if f in body:
                        updates[f] = body[f]
                    else:
                        updates[f] = existing[f]

                conn.execute(
                    """
                    UPDATE orders SET
                        order_id = ?, sub_order_id = ?, order_date = ?, product_name = ?, sku = ?, quantity = ?,
                        customer_name = ?, customer_city = ?, payment_mode = ?, order_amount = ?, product_cost = ?, packaging_cost = ?,
                        initial_status = ?, current_status = ?, status_updated_at = ?,
                        cancel_reason = ?, cancelled_by = ?, cancel_date = ?,
                        return_type = ?, return_reason = ?, return_date = ?, return_status = ?, return_deduction = ?,
                        payment_status = ?, expected_payout_date = ?, settled_date = ?, settled_amount = ?, utr_reference = ?,
                        handled_by = ?, notes = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        str(updates["order_id"]).strip(),
                        str(updates["sub_order_id"] or "").strip(),
                        str(updates["order_date"]).strip(),
                        str(updates["product_name"]).strip(),
                        str(updates["sku"] or "").strip(),
                        int(updates["quantity"] or 1),
                        str(updates["customer_name"] or "").strip(),
                        str(updates["customer_city"] or "").strip(),
                        str(updates["payment_mode"] or "COD").strip(),
                        float(updates["order_amount"] or 0),
                        float(updates["product_cost"] or 0),
                        float(updates["packaging_cost"] or 0),
                        str(updates["initial_status"] or "Pending").strip(),
                        new_status,
                        ts if new_status != old_status else existing["status_updated_at"],
                        str(updates["cancel_reason"] or "").strip(),
                        str(updates["cancelled_by"] or "").strip(),
                        str(updates["cancel_date"] or "").strip(),
                        str(updates["return_type"] or "").strip(),
                        str(updates["return_reason"] or "").strip(),
                        str(updates["return_date"] or "").strip(),
                        str(updates["return_status"] or "").strip(),
                        float(updates["return_deduction"] or 0),
                        str(updates["payment_status"] or "Pending").strip(),
                        str(updates["expected_payout_date"] or "").strip(),
                        str(updates["settled_date"] or "").strip(),
                        float(updates["settled_amount"] or 0),
                        str(updates["utr_reference"] or "").strip(),
                        changed_by,
                        str(updates["notes"] or "").strip(),
                        ts,
                        pk,
                    ),
                )

                if new_status != old_status:
                    note = body.get("status_note") or body.get("cancel_reason") or body.get("return_reason") or "Status updated"
                    conn.execute(
                        "INSERT INTO order_history (order_pk, old_status, new_status, changed_by, note, changed_at) VALUES (?, ?, ?, ?, ?, ?)",
                        (pk, old_status, new_status, changed_by, str(note).strip(), ts),
                    )
                sync_order_supplier_expense(conn, pk)
                conn.commit()
                self.send_json({"ok": True})
                return

            if path.startswith("/api/members/"):
                mid = path.split("/api/members/")[1].strip()
                existing = conn.execute("SELECT * FROM members WHERE id = ?", (mid,)).fetchone()
                if not existing:
                    self.send_json({"error": "Member not found"}, status=404)
                    return
                conn.execute(
                    "UPDATE members SET role = ?, share_percent = ?, phone = ?, notes = ? WHERE id = ?",
                    (
                        body.get("role", existing["role"]),
                        float(body.get("share_percent", existing["share_percent"])),
                        body.get("phone", existing["phone"]),
                        body.get("notes", existing["notes"]),
                        mid,
                    ),
                )
                conn.commit()
                self.send_json({"ok": True})
                return

            self.send_json({"error": "Endpoint not found"}, status=404)
        finally:
            conn.close()

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        conn = get_conn()
        try:
            if path.startswith("/api/orders/"):
                pk = int(path.split("/api/orders/")[1])
                conn.execute("DELETE FROM expenses WHERE order_pk = ?", (pk,))
                conn.execute("DELETE FROM orders WHERE id = ?", (pk,))
                conn.commit()
                self.send_json({"ok": True})
                return

            if path.startswith("/api/expenses/"):
                pk = int(path.split("/api/expenses/")[1])
                conn.execute("DELETE FROM expenses WHERE id = ?", (pk,))
                conn.commit()
                self.send_json({"ok": True})
                return

            if path.startswith("/api/transfers/"):
                pk = int(path.split("/api/transfers/")[1])
                conn.execute("DELETE FROM partner_transfers WHERE id = ?", (pk,))
                conn.commit()
                self.send_json({"ok": True})
                return

            if path.startswith("/api/supplier-products/"):
                pk = int(path.split("/api/supplier-products/")[1])
                conn.execute("DELETE FROM supplier_products WHERE id = ?", (pk,))
                conn.commit()
                self.send_json({"ok": True})
                return

            self.send_json({"error": "Endpoint not found"}, status=404)
        except ValueError:
            self.send_json({"error": "Invalid ID"}, status=400)
        finally:
            conn.close()


def main():
    init_db()
    server = ThreadingHTTPServer(("0.0.0.0", PORT), PortalHandler)
    print(f"Nova Apparels Portal running at http://0.0.0.0:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down Nova Apparels Portal.")
        server.server_close()


if __name__ == "__main__":
    main()
