# House Of Wax V25.3 Missing Import Fix

You should see:

`Running V25.3 MISSING IMPORT FIX`

## Fixed

This fixes the NameError crash:

`NameError: name 're' is not defined`

The barcode cleanup function uses `re.sub()`, so the app needed `import re`.

## Keeps

- V25 Release Database
- V25.2 barcode widget unique key fixes
- MusicBrainz lookup
- Discogs token support
- House Of Wax release database admin
- Seller release correction system
