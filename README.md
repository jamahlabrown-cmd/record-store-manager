# House Of Wax V25 Release Database

You should see:

`Running V25 HOUSE OF WAX RELEASE DATABASE`

## What changed

V25 turns barcode lookup into the beginning of House Of Wax's own internal release database.

## Added tables

- `how_releases`
- `how_release_sources`
- `how_release_corrections`

## Flow

1. Seller scans or enters barcode
2. House Of Wax checks internal release database first
3. If no internal match exists, it checks Discogs/MusicBrainz
4. Lookup result is saved into House Of Wax release database
5. Seller can auto-fill listing draft
6. Seller can suggest corrections
7. Admin can review, edit, approve, reject, or mark releases as needs review

## Purpose

Over time, House Of Wax can build its own verified music product database with:
- barcode
- artist
- title
- format
- label
- year
- genre/style
- catalog number
- cover image
- Discogs ID
- MusicBrainz ID
- GS1 validation status
- confidence score
- approval status
- seller corrections
