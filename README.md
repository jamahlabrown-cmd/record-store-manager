
# Record Store Manager V3

This version adds the six suggested marketing/operations upgrades.

## New features added

### 1. Post This Item button
Select a record and instantly create several post styles:
- Collector-focused
- Casual
- Sales-focused
- Storytelling

### 2. Best time to post field
When scheduling a post, the app recommends a good posting window based on platform and post type.

### 3. Post status tracker
Every scheduled post can be marked:
- Scheduled
- Posted
- Skipped
- Needs Edit
- Sold Out - Do Not Post

### 4. Sold-item protection
If a record quantity is zero, the app warns you before posting or scheduling that record.

### 5. Wishlist matching
The app checks customer wishlists and favorite genres against inventory.

Example:
If a customer wants jazz or Miles Davis, and you upload Miles Davis, the system shows a match and gives you a copy-ready customer message.

### 6. Weekly marketing plan
The app generates a 7-day marketing plan with:
- Daily theme
- Recommended record
- Suggested action
- Draft caption
- Hashtags

## Other core features

- Inventory tracking
- CSV inventory upload
- Record bios
- Auto-generated captions and hashtags
- Social media scheduler
- Content calendar download
- Expense tracking
- Daily operations tracking
- Customer wishlist database
- Reports

## How to run

Unzip this folder.

Open Terminal inside the folder and run:

```bash
pip3 install -r requirements.txt
streamlit run app.py
```

If that does not work, run:

```bash
python3 -m streamlit run app.py
```

## Upload file

Use `sample_inventory_v3.csv` to test the upload feature.

Supported CSV columns:

```csv
sku,artist,title,format,genre,condition,label,release_year,pressing_notes,cost,price,quantity,reorder_level,location,bio,social_caption,hashtags,image_url
```

Required:
- artist
- title

Recommended:
- sku
- format
- genre
- condition
- cost
- price
- quantity
- reorder_level
- location

## Important note about social posting

This app helps you create, schedule, organize, and track posts.

It does not directly auto-post to Instagram, Facebook, or TikTok yet.

Direct posting would require official API setup or a tool like Buffer, Later, Hootsuite, Zapier, Shopify, Square, or Meta Business Suite.
