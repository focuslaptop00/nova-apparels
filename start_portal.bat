@echo off
title Nova Apparels - Meesho Portal & Shareable Link
cd /d "%~dp0"

echo =======================================================
echo          NOVA APPARELS - MEESHO BUSINESS PORTAL
echo =======================================================
echo.
echo 1. Creating automatic safety backup of database...
python -c "import shutil, datetime, os; os.makedirs('backups', exist_ok=True); shutil.copy2('nova_apparels.db', f'backups/nova_apparels_backup_{datetime.datetime.now().strftime(\"%%Y%%m%%d_%%H%%M%%S\")}.db'); print('[OK] Database Backup Saved!')"

echo.
echo 2. Starting portal web server...
start /b python app.py

echo.
echo 3. Opening your local dashboard in Chrome...
start "" http://127.0.0.1:8765

echo.
echo 4. Starting Cloudflare Public Link for Kiran & Anurag...
python start_tunnel.py

pause
