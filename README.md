# House Of Wax V16.1 Settings Startup Fix

This fixes the startup crash caused by an old/corrupt `settings` table in Streamlit's SQLite database.

You should see:

`Running V16.1 SETTINGS STARTUP FIX`

## Fixed

- App no longer writes to the old `settings` table.
- New safe table: `app_settings`
- Startup settings cannot crash the app if an old database exists.
- Keeps the V16 full testing features:
  - buyer dashboard
  - seller dashboard
  - seller stores
  - barcode scanner/input
  - barcode/catalog/matrix product fields
  - public seller feedback
  - public buyer trust profiles
  - product upload
  - bulk import
  - messages
  - announcements
  - events/drops
  - badges
  - auctions
  - admin reports

## Upload

Upload only these first:

- app.py
- requirements.txt
- runtime.txt

Then reboot Streamlit.
