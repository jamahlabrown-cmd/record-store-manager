# V25.7 Search Strategy

## How broad is this?

The app now uses both automatic APIs and manual fallback links.

Automatic:
1. House Of Wax internal database
2. Barcode cache
3. Discogs broad release search
4. Apple/iTunes album search
5. MusicBrainz broad release search

Manual links:
1. Discogs
2. MusicBrainz
3. Apple Music/iTunes
4. Google
5. Wikipedia
6. Wikidata
7. Barcode Lookup
8. UPCitemdb
9. Go-UPC
10. GS1

## Why manual seed exists

If APIs fail or the app cannot reach them from Streamlit, the seller/admin can still find the item manually and seed the House Of Wax internal database.
That is how House Of Wax builds its own reference database over time.
