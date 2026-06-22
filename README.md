# House Of Wax V25.5 Search Fallback Upgrade

You should see:

`Running V25.5 SEARCH FALLBACK UPGRADE`

## What changed

Barcode-only lookup can miss popular artists if the exact barcode is not in MusicBrainz or if Discogs is not connected.

V25.5 adds:
- artist/title fallback search
- Discogs text search
- MusicBrainz text search
- standalone Barcode Diagnostics with artist/title search
- better fallback when barcode lookup returns nothing

## Recommended test

Try:
- Artist: Lady Gaga
- Title: The Fame

or:
- Artist: Lady Gaga
- Title: Born This Way

Then choose a release candidate and auto-fill the listing draft.
