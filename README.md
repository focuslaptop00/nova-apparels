# Nova Apparels — Meesho Business & Hisab Portal

A simple, all-in-one local dashboard for **Nova Apparels** (**Arsh**, **Kiran**, and **Anurag**) to track every Meesho order, status change, cancellation reason, return/RTO reason, business expense, partner investment, and bank payout schedule in one place.

## How to Open the Portal
1. Double-click **`start_portal.bat`** in `c:\Users\admin\Desktop\Meesho`, OR run:
   ```powershell
   python app.py
   ```
2. Open **http://127.0.0.1:8765** in Chrome.

## What's Inside
- **Home Overview**: Total orders till date, COD vs Prepaid split, Received in Bank vs Pending Payments (with next payout date), Cancelled count, Returns & RTO count, Total Expenses, 14-day sales chart, and Team Hisab summary.
- **All Orders**: Search/filter by Order ID, Date, Product, COD/Prepaid, Current Status, or Payment Status. Shows both **Started Status → Current Status** and full timestamped **Order History**.
- **Cancellations**: Every cancelled order with cancel date, who cancelled (Customer / Seller / Meesho), exact reason, and top reason breakdown.
- **Returns & RTO**: Track Customer Returns vs Courier RTO, exact return reasons, parcel status (In Transit / Received / Claim Raised), and return fee deductions.
- **Payments & Bank**: Clear split between **Settled in Bank (Account Ch Agi)** and **Pending (Kdo Augi)** with live day countdowns and a 1-click **Mark Settled in Bank** button.
- **Expenses & Capital**: Track Stock, Packaging, Ads, Tech, and Misc expenses along with Partner Capital Investments and Withdrawals — showing who paid (`Arsh`, `Kiran`, `Anurag`, or `Company Bank`).
- **Team (Arsh, Kiran, Anurag)**: View and edit roles, profit shares, invested capital, pocket expenses, and orders handled.
- **Import CSV & Backup**: Bulk import Meesho Orders CSV files or export Excel-ready CSV and full JSON backups. All data is saved locally in `nova_apparels.db`.
