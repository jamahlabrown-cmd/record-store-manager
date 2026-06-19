# House Of Wax V7 Media

This version adds a Media Manager to House Of Wax.

## New media features

Attach media to each record by SKU:

- Pictures: JPG, JPEG, PNG, WEBP
- Audio: MP3, WAV, M4A, AAC, OGG
- Video: MP4, MOV, M4V, WEBM

Each file can be public or private.

Public media appears on the Public Storefront under the record.
Private media stays inside Admin.

## How to use

1. Log into Admin.
2. Go to Media Manager.
3. Choose a record.
4. Pick Picture, Audio, or Video.
5. Upload one or more files.
6. Choose whether the media is public.
7. Click Save Media.

## Admin password

This secure version uses Streamlit Secrets:

```toml
ADMIN_PASSWORD = "your-private-password"
```

Go to Streamlit > Manage app > Settings > Secrets to set it.

## Important media storage note

This version stores uploaded media in the Streamlit app file system. That is okay for testing but may reset later on Streamlit Cloud.

For real business use, media should eventually move to cloud storage like Supabase Storage, Cloudinary, Amazon S3, Google Drive, or Firebase Storage.



# V8 Internet Media Finder

House Of Wax V8 adds an Internet Media Finder.

This feature helps you find photos, audio, video, and reference links for each record. It does not automatically download copyrighted media. Instead, it creates search buttons and lets the admin save useful links to the record.

## Search sources included

- Discogs
- Google Images
- YouTube
- Internet Archive
- Bandcamp
- SoundCloud
- General web search

## How to use

1. Log into Admin.
2. Go to `Internet Media Finder`.
3. Choose a record.
4. Open the search buttons.
5. Find the best official/legal media source.
6. Copy the URL.
7. Paste the URL into `Save a media link to this record`.
8. Choose whether the link is public.
9. Save it.

## Important copyright note

Do not automatically download or reuse album art, videos, or audio clips unless you have permission, it is your own media, it is from the artist/label with permission, or it is clearly licensed for reuse.

For the public storefront, the safest options are:

- your own photos of the record
- your own condition videos
- official YouTube links
- official Bandcamp/SoundCloud links
- Discogs reference links
- label/artist official website links


## Thumbnail previews

House Of Wax V9 adds thumbnail-style previews for saved internet media links.

- Picture links can display the image directly when the URL is a direct image link.
- YouTube links automatically show a video thumbnail.
- Other video/image links can use an optional `thumbnail_url` so the storefront shows a preview image.
- Audio links still show a direct open/listen button, and direct audio files can be previewed in the app.
