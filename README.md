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
