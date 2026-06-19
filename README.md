
# House Of Wax

V5 adds two major foundations:

1. Barcode scanner / barcode lookup
2. House Of Wax Marketplace seller storefronts similar to an early Discogs-style platform

## Barcode Scanner

This version supports USB and Bluetooth barcode scanners.

Most barcode scanners act like a keyboard. Use it like this:

1. Open Admin Login.
2. Go to Barcode Scanner.
3. Click inside the barcode field.
4. Scan the record barcode.
5. The barcode number appears automatically.
6. If it exists, the app shows the record.
7. If it does not exist, the app lets you add the record.

## Phone Camera Scanner

This version does not yet decode barcodes from the phone camera.

That should be a future upgrade using:
- a custom Streamlit camera barcode component,
- a separate mobile scanner app,
- or Discogs/API lookup after barcode entry.

## House Of Wax Marketplace / Sub-Stores

This version adds:

- Seller profiles
- Seller approval
- Seller storefronts
- Seller listings
- Commission percentage
- Listing fee tracking
- House Of Wax Marketplace order recording
- Platform fee calculation
- Seller payout calculation
- Public seller storefront preview

## Still needed for a real Discogs-style marketplace

- Seller login
- Buyer checkout
- Stripe or PayPal payments
- Shipping labels
- Tax settings
- Seller payout automation
- Seller terms and agreements
- Product grading rules
- Cloud database such as Supabase or PostgreSQL

## Admin Password

Default:

changeme123

Change this in app.py before sharing publicly:

ADMIN_PASSWORD = "changeme123"

## Deploy

Upload these files to GitHub:

- app.py
- requirements.txt
- README.md
- QUICK_START.md
- sample_inventory_house_of_wax.csv

Then redeploy/reboot Streamlit.


# House Of Wax Improvement Roadmap

Based on similar tools like Discogs, Square for Retail, Shopify POS, and barcode inventory apps, the strongest next upgrades are:

## 1. Discogs-style barcode lookup
The current app can store and search barcodes. The next major step is connecting a music database/API so scanning a barcode can automatically pull:
- artist
- album title
- label
- release year
- format
- genre
- pressing/version notes
- market value estimate

## 2. True phone-camera barcode scanner
Right now the app works best with a USB/Bluetooth scanner or QRbot copy/paste. A future upgrade should add in-app phone camera scanning.

## 3. Permanent cloud database
The current Streamlit version is good for testing, but business data should move to Supabase/PostgreSQL before real public use.

## 4. Seller accounts
The marketplace foundation exists, but sellers eventually need their own login so they can:
- add records
- manage prices
- see orders
- see payouts
- edit their storefront

## 5. Listing fees and commissions
The app already tracks commission rate and listing fee fields. The next step is automating invoices and payout reports.

## 6. Checkout and payment processing
To become a true marketplace, House Of Wax will eventually need Stripe, PayPal, or Shopify checkout.

## 7. Record grading workflow
A Discogs-style marketplace needs standard grading:
- Media condition
- Sleeve condition
- Pressing notes
- Photos
- Return policy
- Seller notes

## 8. Shipping and local pickup
Add shipping cost rules, local pickup, hold requests, and seller shipping responsibility.

## 9. Barcode label printing
For records without barcodes, House Of Wax should be able to create internal barcodes and printable shelf labels.

## 10. Audit trail
Track who changed inventory, who adjusted stock, and why.
