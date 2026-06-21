# House Of Wax V15.8.2 No Buyer Blocker Fix

This patch removes the repeated testing blocker:

`Buyer not found. Use Test Setup`

You should see:

`Running V15.8.2 NO BUYER BLOCKER FIX`

## Fixed

- Buyer Dashboard no longer fails just because an exact email is missing.
- Buyer Dashboard lets you choose an existing buyer.
- Buyer Dashboard can create/open a buyer by email instantly.
- If no buyer exists, the app creates a demo buyer automatically.
- Buyer pickers throughout the app no longer block the flow.
- The old “Buyer not found. Use Test Setup” message was removed.

## Demo Buyer

`buyer@test.com`

## What to test

1. Go to Buyer Dashboard.
2. Choose existing buyer or create/open by email.
3. Go to Marketplace.
4. Open a product.
5. Submit Request to Buy.
6. Confirm it does not block on buyer missing.
