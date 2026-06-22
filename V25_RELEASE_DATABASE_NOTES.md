# V25 Release Database Notes

## Lookup order

1. House Of Wax internal release database
2. Barcode lookup cache
3. Discogs if DISCOGS_TOKEN exists
4. MusicBrainz fallback
5. Manual seller entry

## Verification statuses

- Unverified
- Needs Review
- Approved
- Rejected

## Why this matters

House Of Wax can become smarter over time by saving barcode scans and seller corrections into its own database.

Eventually, this supports:
- verified releases
- duplicate barcode handling
- better listing quality
- source confidence
- marketplace trust
- internal pricing/condition intelligence
