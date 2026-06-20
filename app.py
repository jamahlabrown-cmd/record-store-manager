
import sqlite3
import json
from pathlib import Path
from datetime import date, datetime
import pandas as pd
import streamlit as st
from urllib.parse import quote_plus, urlparse, parse_qs
from urllib.request import Request, urlopen

DB = Path("house_of_wax_v11.db")
MEDIA_DIR = Path("house_of_wax_media")
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "")


def conn():
    return sqlite3.connect(DB)


def q(sql, params=()):
    c = conn()
    c.execute(sql, params)
    c.commit()
    c.close()
    ensure_internet_media_schema()


def table(name):
    c = conn()
    df = pd.read_sql_query(f"SELECT * FROM {name}", c)
    c.close()
    return df


def get_store_setting(key, default=""):
    try:
        df = table("store_settings")
        if df.empty:
            return default
        row = df[df.setting_key == key]
        if row.empty:
            return default
        return str(row.iloc[0].setting_value or default)
    except Exception:
        return default

def set_store_setting(key, value):
    q("INSERT OR REPLACE INTO store_settings (setting_key, setting_value) VALUES (?, ?)", (key, str(value or "")))

def get_store_settings():
    return {
        "store_name": get_store_setting("store_name", "House Of Wax"),
        "tagline": get_store_setting("tagline", "Rare finds. Real records. Better digging."),
        "announcement": get_store_setting("announcement", "New arrivals added often. Request a hold if you see something you like."),
        "logo_url": get_store_setting("logo_url", ""),
        "banner_url": get_store_setting("banner_url", ""),
        "instagram_url": get_store_setting("instagram_url", ""),
        "contact_email": get_store_setting("contact_email", ""),
        "contact_phone": get_store_setting("contact_phone", ""),
        "pickup_note": get_store_setting("pickup_note", "Pickup and local hold options available."),
        "shipping_note": get_store_setting("shipping_note", "Shipping available on request."),
        "payment_link": get_store_setting("payment_link", ""),
    }

def save_brand_file(uploaded_file, label):
    MEDIA_DIR.mkdir(exist_ok=True)
    ext = Path(uploaded_file.name).suffix.lower()
    safe_name = f"branding_{label}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}{ext}"
    path = MEDIA_DIR / safe_name
    path.write_bytes(uploaded_file.getbuffer())
    return str(path)

def first_uploaded_picture(sku):
    media = get_media_for_sku(sku, public_only=True)
    if media.empty:
        return ""
    pics = media[media.media_type == "Picture"] if "media_type" in media.columns else media.iloc[0:0]
    if pics.empty:
        return ""
    p = str(pics.iloc[0].file_path)
    return p if Path(p).exists() else ""

def first_internet_thumbnail(sku):
    links = get_internet_media_links(sku, public_only=True)
    if links.empty:
        return ""
    for _, link in links.iterrows():
        thumb = infer_thumbnail_url(link.get("media_type", ""), link.get("source", ""), link.get("url", ""), link.get("thumbnail_url", ""))
        if thumb:
            return thumb
    return ""

def product_thumbnail(record):
    uploaded = first_uploaded_picture(record.sku)
    if uploaded:
        return uploaded
    internet = first_internet_thumbnail(record.sku)
    if internet:
        return internet
    image_url = str(getattr(record, "image_url", "") or "").strip()
    if image_url:
        return image_url
    return ""

def detect_media_source(url):
    u = str(url or "").lower()
    if "youtube.com" in u or "youtu.be" in u:
        return "YouTube", "Video"
    if "discogs.com" in u:
        return "Discogs", "Reference"
    if "bandcamp.com" in u:
        return "Bandcamp", "Audio"
    if "soundcloud.com" in u:
        return "SoundCloud", "Audio"
    if "archive.org" in u:
        return "Internet Archive", "Reference"
    if any(u.endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif"]):
        return "Direct Image", "Picture"
    if any(u.endswith(ext) for ext in [".mp4", ".mov", ".m4v", ".webm"]):
        return "Direct Video", "Video"
    if any(u.endswith(ext) for ext in [".mp3", ".wav", ".m4a", ".aac", ".ogg"]):
        return "Direct Audio", "Audio"
    return "Other", "Reference"

def normalize_barcode(value):
    return "".join(ch for ch in str(value or "") if ch.isdigit())

def barcode_search_links(barcode, catalog_number="", artist="", title=""):
    bc = normalize_barcode(barcode)
    cat = quote_plus(str(catalog_number or ""))
    text_query = quote_plus(" ".join([str(artist or ""), str(title or ""), str(catalog_number or "")]).strip())
    links = {}
    if bc:
        links["Discogs barcode search"] = f"https://www.discogs.com/search/?barcode={bc}&type=release"
        links["Discogs general UPC search"] = f"https://www.discogs.com/search/?q={bc}&type=release"
        links["MusicBrainz barcode search"] = f"https://musicbrainz.org/search?query=barcode%3A{bc}&type=release&method=advanced"
        links["Google UPC search"] = f"https://www.google.com/search?q={bc}+album+barcode+record"
    if catalog_number:
        links["Discogs catalog number search"] = f"https://www.discogs.com/search/?catno={cat}&type=release"
        links["MusicBrainz catalog search"] = f"https://musicbrainz.org/search?query=catno%3A{cat}&type=release&method=advanced"
    if text_query:
        links["Artist/title fallback search"] = f"https://www.discogs.com/search/?q={text_query}&type=release"
    return links

def musicbrainz_lookup_by_barcode(barcode):
    bc = normalize_barcode(barcode)
    if not bc:
        return []
    url = f"https://musicbrainz.org/ws/2/release/?query=barcode:{bc}&fmt=json&limit=5"
    try:
        req = Request(url, headers={"User-Agent": "HouseOfWaxInventory/1.0 (contact: admin@houseofwax.local)"})
        with urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        results = []
        for rel in data.get("releases", []):
            artist_credit = rel.get("artist-credit", [])
            artist = "".join([a.get("name", "") if isinstance(a, dict) else str(a) for a in artist_credit]).strip()
            labels = rel.get("label-info", []) or []
            label = ""
            catalog = ""
            if labels:
                label = ((labels[0].get("label") or {}).get("name") or "")
                catalog = labels[0].get("catalog-number") or ""
            media = rel.get("media", []) or []
            fmt = media[0].get("format", "") if media else ""
            results.append({
                "artist": artist,
                "title": rel.get("title", ""),
                "release_year": str(rel.get("date", ""))[:4],
                "label": label,
                "catalog_number": catalog,
                "format": fmt or "Vinyl/CD/Cassette",
                "barcode": bc,
                "external_release_url": "https://musicbrainz.org/release/" + rel.get("id", ""),
                "metadata_source": "MusicBrainz barcode lookup",
            })
        return results
    except Exception:
        return []

def save_purchase_request(record, request_type, name, email, phone, pickup_or_shipping, address, message):
    q("""INSERT INTO purchase_requests
    (request_date, sku, artist, title, request_type, customer_name, customer_email, customer_phone, pickup_or_shipping, address, message, status, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
    (date.today().isoformat(), record.sku, record.artist, record.title, request_type, name, email, phone, pickup_or_shipping, address, message, "New", datetime.now().isoformat(timespec="seconds")))

def render_hold_form(record, key_suffix=""):
    with st.form(f"hold_{record.sku}_{key_suffix}"):
        c1, c2 = st.columns(2)
        name = c1.text_input("Name")
        email = c2.text_input("Email")
        phone = st.text_input("Phone")
        message = st.text_area("Message", value=f"I am interested in {record.artist} — {record.title}.")
        submitted = st.form_submit_button("Request Hold / Ask About This Record", use_container_width=True)
        if submitted:
            if not name or not email:
                st.error("Name and email are required.")
            else:
                q("""INSERT INTO hold_requests
                (request_date, sku, artist, title, customer_name, customer_email, customer_phone, message, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (date.today().isoformat(), record.sku, record.artist, record.title, name, email, phone, message, "New", datetime.now().isoformat(timespec="seconds")))
                st.success("Request sent. We will follow up soon.")

def render_media_gallery(record):
    media = get_media_for_sku(record.sku, public_only=True)
    internet_links = get_internet_media_links(record.sku, public_only=True)
    if media.empty and internet_links.empty:
        return
    st.write("### Media")
    if not media.empty:
        render_media_assets(media)
    if not internet_links.empty:
        render_internet_media_links(internet_links)

def render_product_detail(record):
    st.button("← Back to all records", key="back_to_records", on_click=lambda: st.session_state.update({"selected_sku": ""}))
    c1, c2 = st.columns([1, 1.2])
    with c1:
        thumb = product_thumbnail(record)
        if thumb:
            st.image(thumb, use_container_width=True)
        render_media_gallery(record)
    with c2:
        st.header(f"{record.artist} — {record.title}")
        st.caption("House Of Wax inventory" if record.owner_type == "Store" else f"House Of Wax seller #{int(record.seller_id)}")
        st.markdown(f"## {money(record.price)}")
        st.write(f"**Format:** {record.format}")
        st.write(f"**Genre:** {record.genre}")
        st.write(f"**Condition:** {record.condition}")
        st.write(f"**Year:** {record.release_year}")
        if str(getattr(record, "catalog_number", "") or "").strip():
            st.write(f"**Catalog #:** {record.catalog_number}")
        if str(getattr(record, "barcode", "") or "").strip():
            st.write(f"**Barcode/UPC:** {record.barcode}")
        st.write(f"**Available:** {int(record.quantity)}")
        if str(record.bio or "").strip():
            st.write(record.bio)
        settings = get_store_settings()
        if settings.get("payment_link"):
            st.link_button("Pay / Checkout Link", settings["payment_link"], use_container_width=True)
        st.caption(settings.get("pickup_note", ""))
        st.caption(settings.get("shipping_note", ""))
        st.divider()
        render_hold_form(record, key_suffix="detail")

def render_product_card(record):
    with st.container(border=True):
        thumb = product_thumbnail(record)
        if thumb:
            st.image(thumb, use_container_width=True)
        else:
            st.markdown("### 🎵")
        st.markdown(f"**{record.artist} — {record.title}**")
        st.caption(f"{record.format} • {record.genre} • {record.condition}")
        st.markdown(f"### {money(record.price)}")
        if st.button("View / Reserve", key=f"view_{record.sku}", use_container_width=True):
            st.session_state.selected_sku = record.sku
            st.rerun()

def ensure_house_of_wax_schema():
    c = conn()
    cur = c.cursor()
    try:
        inv_cols = [row[1] for row in cur.execute("PRAGMA table_info(inventory)").fetchall()]
        for col in ["catalog_number", "matrix_runout", "external_release_url", "metadata_source"]:
            if col not in inv_cols:
                cur.execute(f"ALTER TABLE inventory ADD COLUMN {col} TEXT")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS purchase_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_date TEXT,
            sku TEXT,
            artist TEXT,
            title TEXT,
            request_type TEXT,
            customer_name TEXT,
            customer_email TEXT,
            customer_phone TEXT,
            pickup_or_shipping TEXT,
            address TEXT,
            message TEXT,
            status TEXT DEFAULT 'New',
            created_at TEXT
        )
        """)
        c.commit()
    except Exception:
        pass
    c.close()

def ensure_internet_media_schema():
    c = conn()
    cur = c.cursor()
    try:
        cols = [row[1] for row in cur.execute("PRAGMA table_info(internet_media_links)").fetchall()]
        if "thumbnail_url" not in cols:
            cur.execute("ALTER TABLE internet_media_links ADD COLUMN thumbnail_url TEXT")
            c.commit()
    except Exception:
        pass
    c.close()

def setup():
    MEDIA_DIR.mkdir(exist_ok=True)
    c = conn()
    cur = c.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sku TEXT UNIQUE,
        barcode TEXT,
        catalog_number TEXT,
        matrix_runout TEXT,
        external_release_url TEXT,
        metadata_source TEXT,
        artist TEXT NOT NULL,
        title TEXT NOT NULL,
        format TEXT DEFAULT 'Vinyl',
        genre TEXT,
        condition TEXT,
        label TEXT,
        release_year TEXT,
        pressing_notes TEXT,
        cost REAL DEFAULT 0,
        price REAL DEFAULT 0,
        quantity INTEGER DEFAULT 0,
        reorder_level INTEGER DEFAULT 2,
        location TEXT,
        bio TEXT,
        caption TEXT,
        hashtags TEXT,
        image_url TEXT,
        public_visible TEXT DEFAULT 'Yes',
        owner_type TEXT DEFAULT 'Store',
        seller_id INTEGER DEFAULT 0,
        commission_rate REAL DEFAULT 0,
        listing_fee REAL DEFAULT 0,
        listing_status TEXT DEFAULT 'Active',
        updated_at TEXT
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS media_assets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sku TEXT NOT NULL,
        media_type TEXT NOT NULL,
        file_name TEXT NOT NULL,
        file_path TEXT NOT NULL,
        public_visible TEXT DEFAULT 'Yes',
        caption TEXT,
        uploaded_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS internet_media_links (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sku TEXT NOT NULL,
        source TEXT,
        media_type TEXT,
        title TEXT,
        url TEXT NOT NULL,
        public_visible TEXT DEFAULT 'Yes',
        notes TEXT,
        thumbnail_url TEXT,
        saved_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS store_settings (
        setting_key TEXT PRIMARY KEY,
        setting_value TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS sellers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        store_name TEXT NOT NULL,
        seller_name TEXT,
        email TEXT UNIQUE,
        phone TEXT,
        commission_rate REAL DEFAULT 10,
        monthly_fee REAL DEFAULT 0,
        status TEXT DEFAULT 'Pending',
        created_at TEXT
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_date TEXT,
        sku TEXT,
        seller_id INTEGER,
        sale_price REAL,
        platform_fee REAL,
        seller_payout REAL,
        buyer_name TEXT,
        buyer_email TEXT,
        status TEXT DEFAULT 'New',
        created_at TEXT
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        expense_date TEXT,
        category TEXT,
        vendor TEXT,
        description TEXT,
        amount REAL,
        created_at TEXT
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS purchase_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        request_date TEXT,
        sku TEXT,
        artist TEXT,
        title TEXT,
        request_type TEXT,
        customer_name TEXT,
        customer_email TEXT,
        customer_phone TEXT,
        pickup_or_shipping TEXT,
        address TEXT,
        message TEXT,
        status TEXT DEFAULT 'New',
        created_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS hold_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        request_date TEXT,
        sku TEXT,
        artist TEXT,
        title TEXT,
        customer_name TEXT,
        customer_email TEXT,
        customer_phone TEXT,
        message TEXT,
        status TEXT DEFAULT 'New',
        created_at TEXT
    )
    """)
    c.commit()
    c.close()
    ensure_house_of_wax_schema()


def money(x):
    try:
        return f"${float(x):,.2f}"
    except Exception:
        return "$0.00"


def s(v):
    if pd.isna(v):
        return ""
    return str(v).strip()


def sku_for(artist, title, barcode=""):
    if barcode:
        return "BC-" + barcode[-8:]
    return (artist[:3] + "-" + title[:5] + "-" + str(int(datetime.now().timestamp()))[-5:]).upper().replace(" ", "")


def bio(row):
    artist = s(row.get("artist", ""))
    title = s(row.get("title", ""))
    genre = s(row.get("genre", ""))
    fmt = s(row.get("format", "Vinyl")) or "record"
    condition = s(row.get("condition", ""))
    year = s(row.get("release_year", ""))
    label = s(row.get("label", ""))
    pressing = s(row.get("pressing_notes", ""))
    catalog = s(row.get("catalog_number", ""))
    barcode = s(row.get("barcode", ""))

    parts = []
    opening = f"{artist} — {title}" if artist and title else title or artist or "This release"
    if year:
        opening += f" ({year})"
    opening += f" is a strong {fmt.lower()} listing for listeners, collectors, and anyone building a deeper music library."
    if genre:
        opening += f" The sound sits in the {genre} lane, making it a useful pick for both everyday listening and focused digging."
    parts.append(opening)

    detail = ""
    if label:
        detail += f" Released on {label},"
    else:
        detail += " This copy"
    if condition:
        detail += f" is listed in {condition} condition"
    else:
        detail += " is ready for review"
    if pressing:
        detail += f" with notes that may matter to buyers: {pressing}"
    if catalog:
        detail += f". Catalog number: {catalog}"
    if barcode:
        detail += f". Barcode/UPC: {barcode}"
    detail += "."
    parts.append(detail)

    parts.append("House Of Wax recommends checking the photos, media previews, and condition notes before requesting a hold or purchase. If this is a rare pressing, limited issue, import, clean used copy, or hard-to-find format, those details can make the listing more valuable and easier for the right buyer to find.")
    return " ".join(parts)


def caption(row):
    artist, title, genre = s(row.get("artist","")), s(row.get("title","")), s(row.get("genre",""))
    price = row.get("price", 0)
    txt = f"Now in stock: {artist} — {title}."
    if genre:
        txt += f" A great {genre} pick."
    try:
        if float(price) > 0:
            txt += f" Priced at ${float(price):.2f}."
    except Exception:
        pass
    return txt + " Message us or stop by before it is gone."


def tags(row):
    genre = s(row.get("genre","")).replace(" ","")
    artist = s(row.get("artist","")).replace(" ","")
    out = ["#HouseOfWax", "#RecordStore", "#VinylCommunity", "#NowSpinning", "#CrateDigging"]
    if genre:
        out.append("#" + genre)
    if artist and len(artist) < 25:
        out.append("#" + artist)
    return " ".join(out)


def save_inventory(row):
    row = {str(k).lower().strip(): v for k, v in row.items()}
    artist, title, barcode = s(row.get("artist","")), s(row.get("title","")), s(row.get("barcode",""))
    sku = s(row.get("sku","")) or sku_for(artist, title, barcode)
    data = {
        "sku": sku,
        "barcode": barcode,
        "catalog_number": s(row.get("catalog_number", "")) or s(row.get("catno", "")) or s(row.get("catalog", "")),
        "matrix_runout": s(row.get("matrix_runout", "")) or s(row.get("matrix", "")) or s(row.get("runout", "")),
        "external_release_url": s(row.get("external_release_url", "")) or s(row.get("discogs_url", "")) or s(row.get("musicbrainz_url", "")),
        "metadata_source": s(row.get("metadata_source", "")),
        "artist": artist,
        "title": title,
        "format": s(row.get("format","Vinyl")) or "Vinyl",
        "genre": s(row.get("genre","")),
        "condition": s(row.get("condition","")),
        "label": s(row.get("label","")),
        "release_year": s(row.get("release_year","")),
        "pressing_notes": s(row.get("pressing_notes","")),
        "cost": float(row.get("cost",0) or 0),
        "price": float(row.get("price",0) or 0),
        "quantity": int(float(row.get("quantity",0) or 0)),
        "reorder_level": int(float(row.get("reorder_level",2) or 2)),
        "location": s(row.get("location","")),
        "bio": s(row.get("bio","")),
        "caption": s(row.get("caption","")) or s(row.get("social_caption","")),
        "hashtags": s(row.get("hashtags","")),
        "image_url": s(row.get("image_url","")),
        "public_visible": s(row.get("public_visible","Yes")) or "Yes",
        "owner_type": s(row.get("owner_type","Store")) or "Store",
        "seller_id": int(float(row.get("seller_id",0) or 0)),
        "commission_rate": float(row.get("commission_rate",0) or 0),
        "listing_fee": float(row.get("listing_fee",0) or 0),
        "listing_status": s(row.get("listing_status","Active")) or "Active",
        "updated_at": datetime.now().isoformat(timespec="seconds")
    }
    if not data["bio"]:
        data["bio"] = bio(data)
    if not data["caption"]:
        data["caption"] = caption(data)
    if not data["hashtags"]:
        data["hashtags"] = tags(data)

    c = conn()
    c.execute("""
    INSERT INTO inventory
    (sku, barcode, catalog_number, matrix_runout, external_release_url, metadata_source, artist, title, format, genre, condition, label, release_year, pressing_notes,
    cost, price, quantity, reorder_level, location, bio, caption, hashtags, image_url, public_visible,
    owner_type, seller_id, commission_rate, listing_fee, listing_status, updated_at)
    VALUES
    (:sku, :barcode, :catalog_number, :matrix_runout, :external_release_url, :metadata_source, :artist, :title, :format, :genre, :condition, :label, :release_year, :pressing_notes,
    :cost, :price, :quantity, :reorder_level, :location, :bio, :caption, :hashtags, :image_url, :public_visible,
    :owner_type, :seller_id, :commission_rate, :listing_fee, :listing_status, :updated_at)
    ON CONFLICT(sku) DO UPDATE SET
    barcode=excluded.barcode, catalog_number=excluded.catalog_number, matrix_runout=excluded.matrix_runout, external_release_url=excluded.external_release_url, metadata_source=excluded.metadata_source, artist=excluded.artist, title=excluded.title, format=excluded.format,
    genre=excluded.genre, condition=excluded.condition, label=excluded.label, release_year=excluded.release_year,
    pressing_notes=excluded.pressing_notes, cost=excluded.cost, price=excluded.price, quantity=excluded.quantity,
    reorder_level=excluded.reorder_level, location=excluded.location, bio=excluded.bio, caption=excluded.caption,
    hashtags=excluded.hashtags, image_url=excluded.image_url, public_visible=excluded.public_visible,
    owner_type=excluded.owner_type, seller_id=excluded.seller_id, commission_rate=excluded.commission_rate,
    listing_fee=excluded.listing_fee, listing_status=excluded.listing_status, updated_at=excluded.updated_at
    """, data)
    c.commit()
    c.close()



def extract_youtube_id(url):
    try:
        parsed = urlparse(str(url))
        host = parsed.netloc.lower()
        if "youtu.be" in host:
            return parsed.path.strip("/")
        if "youtube.com" in host:
            if parsed.path == "/watch":
                return parse_qs(parsed.query).get("v", [None])[0]
            if parsed.path.startswith("/shorts/"):
                return parsed.path.split("/shorts/")[-1].split("/")[0]
            if parsed.path.startswith("/embed/"):
                return parsed.path.split("/embed/")[-1].split("/")[0]
    except Exception:
        return None
    return None

def infer_thumbnail_url(media_type, source, url, saved_thumb=""):
    saved_thumb = str(saved_thumb or "").strip()
    if saved_thumb:
        return saved_thumb
    url = str(url or "").strip()
    media_type = str(media_type or "")
    source = str(source or "")
    lower = url.lower()
    if media_type == "Picture":
        if any(lower.endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif"]):
            return url
    if media_type == "Video":
        yt_id = extract_youtube_id(url)
        if yt_id:
            return f"https://img.youtube.com/vi/{yt_id}/hqdefault.jpg"
    return ""

def render_internet_media_card(link):
    label = str(link.get("title", "") or link.get("url", "Media link"))
    media_type = str(link.get("media_type", "") or "Media")
    source = str(link.get("source", "") or "Internet")
    notes = str(link.get("notes", "") or "")
    url = str(link.get("url", "") or "")
    thumb = infer_thumbnail_url(media_type, source, url, link.get("thumbnail_url", ""))

    with st.container(border=True):
        st.markdown(f"**{media_type} — {source}**")
        if media_type == "Picture":
            if thumb:
                st.image(thumb, caption=label, use_container_width=True)
            st.link_button(f"Open {label}", url)
        elif media_type == "Video":
            yt_id = extract_youtube_id(url)
            if yt_id:
                st.image(f"https://img.youtube.com/vi/{yt_id}/hqdefault.jpg", caption=label, use_container_width=True)
            elif thumb:
                st.image(thumb, caption=label, use_container_width=True)
            elif url.lower().endswith((".mp4", ".mov", ".m4v", ".webm")):
                st.video(url)
            st.link_button(f"Watch {label}", url)
        elif media_type == "Audio":
            if url.lower().endswith((".mp3", ".wav", ".m4a", ".aac", ".ogg")):
                st.audio(url)
            st.link_button(f"Listen to {label}", url)
        else:
            if thumb:
                st.image(thumb, caption=label, use_container_width=True)
            st.link_button(f"Open {label}", url)
        if notes:
            st.caption(notes)

def build_media_search_links(artist, title, label="", year=""):
    base_query = " ".join([str(artist or ""), str(title or ""), str(label or ""), str(year or ""), "vinyl record"]).strip()
    qv = quote_plus(base_query)
    image_q = quote_plus(base_query + " album cover record")
    audio_q = quote_plus(str(artist or "") + " " + str(title or "") + " audio")
    video_q = quote_plus(str(artist or "") + " " + str(title or "") + " vinyl")
    return {
        "Discogs Release Search": f"https://www.discogs.com/search/?q={qv}&type=all",
        "Google Images": f"https://www.google.com/search?tbm=isch&q={image_q}",
        "YouTube": f"https://www.youtube.com/results?search_query={video_q}",
        "Internet Archive": f"https://archive.org/search?query={qv}",
        "Bandcamp": f"https://bandcamp.com/search?q={audio_q}",
        "SoundCloud": f"https://soundcloud.com/search?q={audio_q}",
        "General Web Search": f"https://www.google.com/search?q={qv}",
    }

def save_internet_media_link(sku, source, media_type, title, url, public_visible="Yes", notes="", thumbnail_url=""):
    q("""
    INSERT INTO internet_media_links
    (sku, source, media_type, title, url, public_visible, notes, thumbnail_url, saved_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        sku, source, media_type, title, url, public_visible, notes, thumbnail_url,
        datetime.now().isoformat(timespec="seconds")
    ))

def get_internet_media_links(sku, public_only=False):
    c = conn()
    if public_only:
        df = pd.read_sql_query(
            "SELECT * FROM internet_media_links WHERE sku = ? AND public_visible = 'Yes' ORDER BY saved_at DESC",
            c,
            params=(sku,)
        )
    else:
        df = pd.read_sql_query(
            "SELECT * FROM internet_media_links WHERE sku = ? ORDER BY saved_at DESC",
            c,
            params=(sku,)
        )
    c.close()
    return df

def delete_internet_media_link(link_id):
    q("DELETE FROM internet_media_links WHERE id = ?", (int(link_id),))

def render_internet_media_links(link_df):
    if link_df.empty:
        return
    cols = st.columns(2)
    for idx, (_, link) in enumerate(link_df.iterrows()):
        with cols[idx % 2]:
            render_internet_media_card(link)


def save_media_file(sku, uploaded_file, media_type, public_visible="Yes", caption_text=""):
    MEDIA_DIR.mkdir(exist_ok=True)
    safe_sku = "".join([ch for ch in str(sku) if ch.isalnum() or ch in ("-", "_")]) or "unknown"
    ext = Path(uploaded_file.name).suffix.lower()
    stamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    safe_name = f"{safe_sku}_{media_type}_{stamp}{ext}"
    path = MEDIA_DIR / safe_name
    path.write_bytes(uploaded_file.getbuffer())
    q("""
    INSERT INTO media_assets
    (sku, media_type, file_name, file_path, public_visible, caption, uploaded_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (sku, media_type, uploaded_file.name, str(path), public_visible, caption_text, datetime.now().isoformat(timespec="seconds")))


def get_media_for_sku(sku, public_only=False):
    c = conn()
    if public_only:
        df = pd.read_sql_query("SELECT * FROM media_assets WHERE sku = ? AND public_visible = 'Yes' ORDER BY uploaded_at DESC", c, params=(sku,))
    else:
        df = pd.read_sql_query("SELECT * FROM media_assets WHERE sku = ? ORDER BY uploaded_at DESC", c, params=(sku,))
    c.close()
    return df


def render_media_assets(media_df):
    if media_df.empty:
        return
    for _, m in media_df.iterrows():
        path = str(m.get("file_path", ""))
        cap = str(m.get("caption", "") or "")
        if not Path(path).exists():
            st.warning(f"Media file missing: {m.get('file_name', '')}")
            continue
        if m["media_type"] == "Picture":
            st.image(path, caption=cap or m.get("file_name", ""), use_container_width=True)
        elif m["media_type"] == "Audio":
            if cap:
                st.caption(cap)
            st.audio(path)
        elif m["media_type"] == "Video":
            if cap:
                st.caption(cap)
            st.video(path)


def delete_media_asset(media_id):
    assets = table("media_assets")
    row = assets[assets["id"] == int(media_id)] if not assets.empty else assets
    if not row.empty:
        file_path = Path(str(row.iloc[0]["file_path"]))
        if file_path.exists():
            try:
                file_path.unlink()
            except Exception:
                pass
    q("DELETE FROM media_assets WHERE id = ?", (int(media_id),))


def apply_storefront_css():
    st.markdown("""
    <style>
    .block-container {padding-top: 1.5rem;}
    div[data-testid="stVerticalBlockBorderWrapper"] {border-radius: 18px; box-shadow: 0 2px 14px rgba(0,0,0,0.06);}
    .how-hero {padding: 22px 26px; border-radius: 22px; background: linear-gradient(135deg, #111 0%, #3b2f2f 55%, #8a6f3d 100%); color: white; margin-bottom: 18px;}
    .how-hero h1 {margin-bottom: 4px;}
    .how-announcement {padding: 10px 14px; border-radius: 12px; background: rgba(255,255,255,0.12); margin-top: 12px;}
    </style>
    """, unsafe_allow_html=True)

setup()
st.set_page_config(page_title="House Of Wax", layout="wide")
st.sidebar.title("House Of Wax")
mode = st.sidebar.radio("Choose view", ["Public Storefront", "Seller Storefronts", "Admin Login"])

if mode == "Public Storefront":
    apply_storefront_css()
    settings = get_store_settings()
    if settings["logo_url"]:
        try:
            st.sidebar.image(settings["logo_url"], use_container_width=True)
        except Exception:
            pass
    st.markdown(f"""
    <div class="how-hero">
        <h1>{settings['store_name']}</h1>
        <div>{settings['tagline']}</div>
        <div class="how-announcement">{settings['announcement']}</div>
    </div>
    """, unsafe_allow_html=True)
    if settings["banner_url"]:
        st.image(settings["banner_url"], use_container_width=True)

    inv = table("inventory")
    if inv.empty:
        st.info("No public inventory yet.")
    else:
        public = inv[(inv.public_visible == "Yes") & (inv.quantity > 0) & (inv.listing_status == "Active")]
        if "selected_sku" not in st.session_state:
            st.session_state.selected_sku = ""

        if st.session_state.selected_sku:
            chosen = public[public.sku == st.session_state.selected_sku]
            if chosen.empty:
                st.session_state.selected_sku = ""
                st.rerun()
            else:
                render_product_detail(chosen.iloc[0])
        else:
            c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
            search = c1.text_input("Search records", placeholder="Artist, title, genre, barcode...")
            genres = sorted([g for g in public.genre.dropna().astype(str).unique().tolist() if g.strip()])
            genre_filter = c2.selectbox("Genre", ["All"] + genres)
            condition_filter = c3.selectbox("Condition", ["All"] + sorted([g for g in public.condition.dropna().astype(str).unique().tolist() if g.strip()]))
            sort_by = c4.selectbox("Sort", ["Newest", "Price low", "Price high", "Artist A-Z"])

            if search:
                public = public[public.astype(str).apply(lambda col: col.str.contains(search, case=False, na=False)).any(axis=1)]
            if genre_filter != "All":
                public = public[public.genre.astype(str) == genre_filter]
            if condition_filter != "All":
                public = public[public.condition.astype(str) == condition_filter]
            if sort_by == "Price low":
                public = public.sort_values("price", ascending=True)
            elif sort_by == "Price high":
                public = public.sort_values("price", ascending=False)
            elif sort_by == "Artist A-Z":
                public = public.sort_values(["artist", "title"], ascending=True)
            else:
                public = public.sort_values("updated_at", ascending=False) if "updated_at" in public.columns else public

            st.caption(f"Showing {len(public)} available record(s).")
            if public.empty:
                st.info("No records match that search.")
            else:
                cols = st.columns(3)
                for idx, (_, r) in enumerate(public.iterrows()):
                    with cols[idx % 3]:
                        render_product_card(r)

    st.caption("Customer view hides costs, expenses, sales reports, and admin tools.")

elif mode == "Seller Storefronts":
    apply_storefront_css()
    st.title("House Of Wax Seller Storefronts")
    sellers = table("sellers")
    inv = table("inventory")
    approved = sellers[sellers.status == "Approved"] if not sellers.empty else sellers
    if approved.empty:
        st.info("No approved seller storefronts yet.")
    else:
        choice = st.selectbox("Choose seller", [f"{r.id} | {r.store_name}" for _, r in approved.iterrows()])
        seller_id = int(choice.split("|")[0].strip())
        seller = approved[approved.id == seller_id].iloc[0]
        st.header(seller.store_name)
        items = inv[(inv.owner_type == "Marketplace Seller") & (inv.seller_id == seller_id) & (inv.quantity > 0)]
        if items.empty:
            st.info("This seller has no active listings.")
        else:
            cols = st.columns(3)
            for idx, (_, r) in enumerate(items.iterrows()):
                with cols[idx % 3]:
                    render_product_card(r)

else:
    if "auth" not in st.session_state:
        st.session_state.auth = False
    if not st.session_state.auth:
        st.title("House Of Wax Admin Login")
        pw = st.text_input("Password", type="password")
        if st.button("Login"):
            if ADMIN_PASSWORD and pw == ADMIN_PASSWORD:
                st.session_state.auth = True
                st.rerun()
            else:
                st.error("Wrong password or admin password not set in Streamlit Secrets.")
        if not ADMIN_PASSWORD:
            st.error("Admin password is not set yet. Add ADMIN_PASSWORD in Streamlit Secrets before using Admin Login.")
        else:
            st.info("Admin password is set securely in Streamlit Secrets.")
        st.stop()

    if st.sidebar.button("Logout"):
        st.session_state.auth = False
        st.rerun()

    tabs = st.tabs(['Dashboard', 'Barcode Scanner', 'Inventory', 'Upload CSV', 'Media Manager', 'Internet Media Finder', 'Sellers', 'Seller Listings', 'Marketplace Orders', 'Expenses', 'Hold Requests', 'Cleanup', 'Reports'])

    with tabs[0]:
        st.subheader("Dashboard")
        with st.expander("Storefront Branding & Sales Settings", expanded=False):
            settings = get_store_settings()
            st.write("Add your logo, banner, tagline, contact info, and announcement. These show on the public storefront.")
            with st.form("store_settings_form"):
                store_name = st.text_input("Store name", value=settings["store_name"])
                tagline = st.text_input("Tagline", value=settings["tagline"])
                announcement = st.text_area("Storefront announcement", value=settings["announcement"])
                logo_upload = st.file_uploader("Upload logo", type=["jpg", "jpeg", "png", "webp"], key="logo_upload")
                banner_upload = st.file_uploader("Upload banner / hero image", type=["jpg", "jpeg", "png", "webp"], key="banner_upload")
                logo_url = st.text_input("Logo URL or saved file path", value=settings["logo_url"])
                banner_url = st.text_input("Banner URL or saved file path", value=settings["banner_url"])
                instagram_url = st.text_input("Instagram URL", value=settings["instagram_url"])
                contact_email = st.text_input("Contact email", value=settings["contact_email"])
                contact_phone = st.text_input("Contact phone", value=settings["contact_phone"])
                pickup_note = st.text_input("Pickup note", value=settings.get("pickup_note", ""))
                shipping_note = st.text_input("Shipping note", value=settings.get("shipping_note", ""))
                payment_link = st.text_input("Optional payment/checkout link", value=settings.get("payment_link", ""))
                if st.form_submit_button("Save Storefront Settings"):
                    if logo_upload is not None:
                        logo_url = save_brand_file(logo_upload, "logo")
                    if banner_upload is not None:
                        banner_url = save_brand_file(banner_upload, "banner")
                    for k, v in {
                        "store_name": store_name, "tagline": tagline, "announcement": announcement,
                        "logo_url": logo_url, "banner_url": banner_url, "instagram_url": instagram_url,
                        "contact_email": contact_email, "contact_phone": contact_phone,
                        "pickup_note": pickup_note, "shipping_note": shipping_note, "payment_link": payment_link
                    }.items():
                        set_store_setting(k, v)
                    st.success("Storefront settings saved.")
        inv = table("inventory")
        sellers = table("sellers")
        orders = table("orders")
        expenses = table("expenses")
        media = table("media_assets")
        c1,c2,c3,c4,c5,c6 = st.columns(6)
        c1.metric("Units", int(inv.quantity.sum()) if not inv.empty else 0)
        c2.metric("Retail Value", money((inv.price * inv.quantity).sum()) if not inv.empty else "$0.00")
        c3.metric("Cost Value", money((inv.cost * inv.quantity).sum()) if not inv.empty else "$0.00")
        c4.metric("Sellers", len(sellers))
        c5.metric("Orders", len(orders))
        c6.metric("Media Files", len(media))
        if not inv.empty:
            st.subheader("Low Stock")
            st.dataframe(inv[inv.quantity <= inv.reorder_level][["sku","barcode","artist","title","quantity","reorder_level","location"]], use_container_width=True)

    with tabs[1]:
        st.subheader("Two-Way Barcode Scanner / Release Lookup")
        st.write("Use a USB/Bluetooth scanner, QRbot, or manually type the barcode from the back cover. The barcode can find an existing item in your inventory or help identify album metadata from MusicBrainz/Discogs.")
        barcode = st.text_input("Scan or type barcode / UPC / EAN")
        catalog_lookup = st.text_input("Optional catalog number from spine/back cover")
        inv = table("inventory")
        if barcode:
            clean_barcode = normalize_barcode(barcode)
            found = inv[inv.barcode.astype(str).str.replace(r"\\D", "", regex=True) == clean_barcode] if not inv.empty else inv
            if not found.empty:
                st.success("Barcode found in House Of Wax inventory.")
                st.dataframe(found, use_container_width=True)
            else:
                st.warning("Barcode not found in your inventory yet. Use lookup tools below to identify and add it.")

            st.write("### Fast web lookups")
            st.caption("Barcode is usually the first identifier to try. Catalog number and matrix/runout help narrow down exact pressings.")
            for name, url in barcode_search_links(clean_barcode, catalog_lookup).items():
                st.link_button(name, url)

            st.write("### Try MusicBrainz auto-lookup")
            if st.button("Lookup barcode metadata"):
                results = musicbrainz_lookup_by_barcode(clean_barcode)
                st.session_state["barcode_lookup_results"] = results
                if not results:
                    st.error("No automatic MusicBrainz results found. Try the Discogs barcode/catalog search buttons above.")

            results = st.session_state.get("barcode_lookup_results", [])
            if results:
                st.success(f"Found {len(results)} possible release match(es).")
                for i, res in enumerate(results):
                    with st.expander(f"Match {i+1}: {res.get('artist','')} — {res.get('title','')}", expanded=(i==0)):
                        st.json(res)
                        c1,c2,c3 = st.columns(3)
                        condition = c1.text_input("Condition", value="Used - Review", key=f"lookup_cond_{i}")
                        price = c2.number_input("Price", min_value=0.0, step=0.01, key=f"lookup_price_{i}")
                        quantity = c3.number_input("Quantity", min_value=1, value=1, key=f"lookup_qty_{i}")
                        if st.button("Add this match to inventory", key=f"add_lookup_{i}"):
                            item = dict(res)
                            item.update({"condition": condition, "price": price, "quantity": quantity, "public_visible": "No"})
                            save_inventory(item)
                            st.success("Added as private inventory. Review it, add media, then mark Public Visible = Yes when ready.")

            st.write("### Add manually from barcode")
            with st.form("barcode_add"):
                artist = st.text_input("Artist")
                title = st.text_input("Title")
                c1,c2,c3 = st.columns(3)
                fmt = c1.selectbox("Format", ["Vinyl","CD","Cassette","DVD","Merch","Other"])
                genre = c2.text_input("Genre")
                condition = c3.text_input("Condition")
                c4,c5,c6 = st.columns(3)
                cost = c4.number_input("Cost", min_value=0.0, step=0.01)
                price = c5.number_input("Price", min_value=0.0, step=0.01)
                quantity = c6.number_input("Quantity", min_value=1, value=1)
                label = st.text_input("Label")
                release_year = st.text_input("Release year")
                pressing_notes = st.text_area("Pressing / identifier notes", placeholder="Catalog number, matrix/runout, promo, club edition, country, etc.")
                if st.form_submit_button("Add Record From Barcode"):
                    save_inventory({"barcode": clean_barcode, "catalog_number": catalog_lookup, "artist": artist, "title": title, "format": fmt, "genre": genre, "condition": condition, "cost": cost, "price": price, "quantity": quantity, "label": label, "release_year": release_year, "pressing_notes": pressing_notes})
                    st.success("Record added.")

    with tabs[2]:
        st.subheader("Inventory")
        inv = table("inventory")
        st.dataframe(inv, use_container_width=True)
        with st.form("manual"):
            st.subheader("Add / Edit")
            c1,c2,c3 = st.columns(3)
            sku = c1.text_input("SKU")
            barcode = c2.text_input("Barcode / UPC / EAN")
            public_visible = c3.selectbox("Public Visible", ["Yes","No"])
            ccat1, ccat2 = st.columns(2)
            catalog_number = ccat1.text_input("Catalog number")
            matrix_runout = ccat2.text_input("Matrix/runout")
            c4,c5 = st.columns(2)
            artist = c4.text_input("Artist")
            title = c5.text_input("Title")
            c6,c7,c8 = st.columns(3)
            fmt = c6.selectbox("Format", ["Vinyl","CD","Cassette","DVD","Merch","Other"])
            genre = c7.text_input("Genre")
            condition = c8.text_input("Condition")
            c9,c10,c11,c12 = st.columns(4)
            cost = c9.number_input("Cost", min_value=0.0, step=0.01)
            price = c10.number_input("Price", min_value=0.0, step=0.01)
            quantity = c11.number_input("Quantity", min_value=0, step=1)
            reorder = c12.number_input("Reorder Level", min_value=0, value=2)
            location = st.text_input("Location")
            label = st.text_input("Label")
            release_year = st.text_input("Release year")
            pressing_notes = st.text_area("Pressing notes / identifiers")
            if st.form_submit_button("Save"):
                save_inventory({"sku":sku,"barcode":barcode,"artist":artist,"title":title,"format":fmt,"genre":genre,"condition":condition,"cost":cost,"price":price,"quantity":quantity,"reorder_level":reorder,"location":location,"public_visible":public_visible,"catalog_number":catalog_number,"matrix_runout":matrix_runout,"label":label,"release_year":release_year,"pressing_notes":pressing_notes})
                st.success("Saved.")

    with tabs[3]:
        st.subheader("Upload CSV")
        uploaded = st.file_uploader("Choose CSV", type=["csv"])
        if uploaded:
            df = pd.read_csv(uploaded)
            df.columns = [c.lower().strip() for c in df.columns]
            st.dataframe(df.head(20), use_container_width=True)
            if st.button("Import / Update Inventory"):
                if "artist" not in df.columns or "title" not in df.columns:
                    st.error("CSV must include artist and title.")
                else:
                    for _, row in df.iterrows():
                        save_inventory(row.to_dict())
                    st.success(f"Imported {len(df)} rows.")

    with tabs[4]:
        st.subheader("Media Manager")
        st.write("Attach pictures, audio clips, and videos to records. Public media appears on the customer storefront; private media stays admin-only.")
        inv = table("inventory")
        if inv.empty:
            st.info("Add inventory first, then upload media.")
        else:
            item_choice = st.selectbox("Choose record for media", [f"{r.sku} | {r.artist} - {r.title}" for _, r in inv.iterrows()])
            sku = item_choice.split("|")[0].strip()
            record = inv[inv.sku == sku].iloc[0]
            st.write(f"### {record.artist} — {record.title}")
            st.caption(f"SKU: {sku}")
            media_type = st.selectbox("Media Type", ["Picture", "Audio", "Video"])
            public_visible = st.selectbox("Show media on Public Storefront?", ["Yes", "No"])
            caption_text = st.text_input("Media Caption / Notes")
            if media_type == "Picture":
                files = st.file_uploader("Upload pictures", type=["jpg", "jpeg", "png", "webp"], accept_multiple_files=True)
            elif media_type == "Audio":
                files = st.file_uploader("Upload audio clips", type=["mp3", "wav", "m4a", "aac", "ogg"], accept_multiple_files=True)
            else:
                files = st.file_uploader("Upload videos", type=["mp4", "mov", "m4v", "webm"], accept_multiple_files=True)
            if st.button("Save Media"):
                if not files:
                    st.error("Choose at least one file first.")
                else:
                    for uploaded in files:
                        save_media_file(sku, uploaded, media_type, public_visible, caption_text)
                    st.success(f"Saved {len(files)} media file(s) to {record.artist} — {record.title}.")
            st.write("### Existing Media For This Record")
            current_media = get_media_for_sku(sku, public_only=False)
            if current_media.empty:
                st.info("No media uploaded for this record yet.")
            else:
                st.dataframe(current_media[["id", "media_type", "file_name", "public_visible", "caption", "uploaded_at"]], use_container_width=True)
                render_media_assets(current_media)
                delete_choice = st.selectbox("Delete media asset ID", [str(x) for x in current_media["id"].tolist()])
                if st.button("Delete Selected Media"):
                    delete_media_asset(delete_choice)
                    st.success("Media deleted. Refresh or change tabs to update.")


    with tabs[5]:
        st.subheader("Internet Media Finder")
        st.write("Use this to quickly attach official media links and thumbnails. Paste a URL, and the app will guess the source, media type, and thumbnail when possible.")

        inv = table("inventory")
        if inv.empty:
            st.info("Add inventory first, then use Internet Media Finder.")
        else:
            item_choice = st.selectbox("Choose record to search", [f"{r.sku} | {r.artist} - {r.title}" for _, r in inv.iterrows()])
            sku = item_choice.split("|")[0].strip()
            record = inv[inv.sku == sku].iloc[0]

            st.write(f"### {record.artist} — {record.title}")
            st.caption(f"SKU: {sku}")

            custom_query = st.text_input(
                "Optional custom search words",
                value=f"{record.artist} {record.title} {record.label or ''} {record.release_year or ''} vinyl record".strip()
            )

            links = build_media_search_links(record.artist, record.title, record.label, record.release_year)
            if custom_query:
                custom_q = quote_plus(custom_query)
                links["Custom Google Images"] = f"https://www.google.com/search?tbm=isch&q={custom_q}"
                links["Custom YouTube"] = f"https://www.youtube.com/results?search_query={custom_q}"
                links["Custom Web Search"] = f"https://www.google.com/search?q={custom_q}"

            st.write("### Search the internet")
            st.caption("Open these links, find the best legal/official media, copy the URL, then save it below.")
            for name, url in links.items():
                st.link_button(name, url)

            st.divider()
            st.write("### Save a media link to this record")
            media_url = st.text_input("Paste media/page URL")
            detected_source, detected_type = detect_media_source(media_url) if media_url else ("YouTube", "Video")
            csrc, ctype = st.columns(2)
            source = csrc.selectbox("Source", ["YouTube", "Discogs", "Google Images", "Internet Archive", "Bandcamp", "SoundCloud", "Official Website", "Direct Image", "Direct Video", "Direct Audio", "Other"], index=["YouTube", "Discogs", "Google Images", "Internet Archive", "Bandcamp", "SoundCloud", "Official Website", "Direct Image", "Direct Video", "Direct Audio", "Other"].index(detected_source) if detected_source in ["YouTube", "Discogs", "Google Images", "Internet Archive", "Bandcamp", "SoundCloud", "Official Website", "Direct Image", "Direct Video", "Direct Audio", "Other"] else 10)
            media_type = ctype.selectbox("Media Link Type", ["Picture", "Audio", "Video", "Reference"], index=["Picture", "Audio", "Video", "Reference"].index(detected_type) if detected_type in ["Picture", "Audio", "Video", "Reference"] else 3)
            link_title = st.text_input("Link title", value=f"{record.artist} - {record.title}")
            auto_thumb = infer_thumbnail_url(media_type, source, media_url, "") if media_url else ""
            public_visible = st.selectbox("Show this link on Public Storefront?", ["Yes", "No"], key="internet_public_visible")
            notes = st.text_area("Notes / usage rights / source details")
            thumbnail_url = st.text_input("Optional thumbnail URL (auto-filled for YouTube/direct images when possible)", value=auto_thumb)

            if st.button("Save Internet Media Link"):
                if not media_url.strip():
                    st.error("Paste a URL first.")
                else:
                    save_internet_media_link(sku, source, media_type, link_title, media_url.strip(), public_visible, notes, thumbnail_url.strip())
                    st.success("Saved internet media link to this record.")

            st.write("### Saved Internet Media Links")
            saved_links = get_internet_media_links(sku, public_only=False)
            if saved_links.empty:
                st.info("No internet media links saved for this record yet.")
            else:
                st.dataframe(saved_links[["id", "source", "media_type", "title", "url", "thumbnail_url", "public_visible", "saved_at"]], use_container_width=True)
                render_internet_media_links(saved_links)

                delete_link = st.selectbox("Delete internet media link ID", [str(x) for x in saved_links["id"].tolist()])
                if st.button("Delete Selected Internet Link"):
                    delete_internet_media_link(delete_link)
                    st.success("Internet media link deleted. Refresh or change tabs to update.")


    with tabs[6]:
        st.subheader("House Of Wax Sellers / Sub-Stores")
        with st.form("seller"):
            c1,c2 = st.columns(2)
            store_name = c1.text_input("Storefront Name")
            seller_name = c2.text_input("Seller Name")
            c3,c4 = st.columns(2)
            email = c3.text_input("Email")
            phone = c4.text_input("Phone")
            c5,c6,c7 = st.columns(3)
            commission = c5.number_input("Commission %", min_value=0.0, max_value=100.0, value=10.0)
            monthly = c6.number_input("Monthly Storefront Fee", min_value=0.0, value=0.0)
            status = c7.selectbox("Status", ["Pending","Approved","Suspended"])
            if st.form_submit_button("Save Seller"):
                q("""INSERT OR REPLACE INTO sellers
                (store_name,seller_name,email,phone,commission_rate,monthly_fee,status,created_at)
                VALUES (?,?,?,?,?,?,?,?)""",
                (store_name,seller_name,email,phone,commission,monthly,status,datetime.now().isoformat(timespec="seconds")))
                st.success("Seller saved.")
        st.dataframe(table("sellers"), use_container_width=True)

    with tabs[7]:
        st.subheader("Create Seller Listing")
        sellers = table("sellers")
        approved = sellers[sellers.status == "Approved"] if not sellers.empty else sellers
        if approved.empty:
            st.info("Approve a seller first.")
        else:
            with st.form("seller_listing"):
                seller_choice = st.selectbox("Seller", [f"{r.id} | {r.store_name} | {r.commission_rate}%" for _, r in approved.iterrows()])
                seller_id = int(seller_choice.split("|")[0].strip())
                seller = approved[approved.id == seller_id].iloc[0]
                c1,c2 = st.columns(2)
                barcode = c1.text_input("Barcode")
                sku = c2.text_input("SKU")
                c3,c4 = st.columns(2)
                artist = c3.text_input("Artist")
                title = c4.text_input("Title")
                c5,c6,c7 = st.columns(3)
                fmt = c5.selectbox("Format", ["Vinyl","CD","Cassette","DVD","Merch","Other"])
                genre = c6.text_input("Genre")
                condition = c7.text_input("Condition")
                c8,c9,c10 = st.columns(3)
                cost = c8.number_input("Seller/internal cost", min_value=0.0, step=0.01)
                price = c9.number_input("Listing price", min_value=0.0, step=0.01)
                quantity = c10.number_input("Quantity", min_value=1, value=1)
                listing_fee = st.number_input("Listing fee charged", min_value=0.0, value=0.0)
                if st.form_submit_button("Create Listing"):
                    save_inventory({"sku":sku,"barcode":barcode,"artist":artist,"title":title,"format":fmt,"genre":genre,"condition":condition,"cost":cost,"price":price,"quantity":quantity,"public_visible":"Yes","owner_type":"Marketplace Seller","seller_id":seller_id,"commission_rate":seller.commission_rate,"listing_fee":listing_fee})
                    st.success("Seller listing created.")
        inv = table("inventory")
        if not inv.empty:
            st.dataframe(inv[inv.owner_type == "Marketplace Seller"], use_container_width=True)

    with tabs[8]:
        st.subheader("Marketplace Orders / Payouts")
        inv = table("inventory")
        active = inv[(inv.owner_type == "Marketplace Seller") & (inv.quantity > 0)] if not inv.empty else inv
        if active.empty:
            st.info("No active seller listings.")
        else:
            with st.form("order"):
                item_choice = st.selectbox("Sold item", [f"{r.sku} | Seller {int(r.seller_id)} | {r.artist} - {r.title} | {money(r.price)}" for _, r in active.iterrows()])
                sku = item_choice.split("|")[0].strip()
                item = active[active.sku == sku].iloc[0]
                sale_price = st.number_input("Sale price", min_value=0.0, value=float(item.price), step=0.01)
                buyer_name = st.text_input("Buyer name")
                buyer_email = st.text_input("Buyer email")
                if st.form_submit_button("Record Sale"):
                    fee = sale_price * float(item.commission_rate) / 100
                    payout = sale_price - fee
                    q("""INSERT INTO orders
                    (order_date, sku, seller_id, sale_price, platform_fee, seller_payout, buyer_name, buyer_email, status, created_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (date.today().isoformat(), sku, int(item.seller_id), sale_price, fee, payout, buyer_name, buyer_email, "New", datetime.now().isoformat(timespec="seconds")))
                    q("UPDATE inventory SET quantity = MAX(quantity - 1, 0), updated_at = ? WHERE sku = ?", (datetime.now().isoformat(timespec="seconds"), sku))
                    st.success(f"Sale recorded. Platform fee: {money(fee)}. Seller payout: {money(payout)}.")
        orders = table("orders")
        st.dataframe(orders, use_container_width=True)

    with tabs[9]:
        st.subheader("Expenses")
        with st.form("expense"):
            c1,c2,c3 = st.columns(3)
            expense_date = c1.date_input("Date", value=date.today())
            category = c2.text_input("Category", value="Supplies")
            amount = c3.number_input("Amount", min_value=0.0, step=0.01)
            vendor = st.text_input("Vendor")
            description = st.text_area("Description")
            if st.form_submit_button("Add Expense"):
                q("INSERT INTO expenses (expense_date,category,vendor,description,amount,created_at) VALUES (?,?,?,?,?,?)",
                  (expense_date.isoformat(), category, vendor, description, amount, datetime.now().isoformat(timespec="seconds")))
                st.success("Expense added.")
        st.dataframe(table("expenses"), use_container_width=True)

    with tabs[10]:
        st.subheader("Hold Requests")
        st.dataframe(table("hold_requests"), use_container_width=True)
        st.subheader("Purchase / Reserve Requests")
        st.dataframe(table("purchase_requests"), use_container_width=True)

    with tabs[11]:
        st.subheader("Cleanup")
        if st.button("Delete sample inventory"):
            for sku in ["VIN-0001","VIN-0002","VIN-0003","CD-0001","MER-0001"]:
                q("DELETE FROM inventory WHERE sku = ?", (sku,))
            st.success("Samples deleted.")
        confirm = st.text_input("Type DELETE ALL to wipe all app data")
        if st.button("Reset entire app"):
            if confirm == "DELETE ALL":
                for t in ["inventory","media_assets","internet_media_links","sellers","orders","expenses","hold_requests","store_settings"]:
                    q(f"DELETE FROM {t}")
                st.success("App reset.")
            else:
                st.error("Type DELETE ALL exactly.")

    with tabs[12]:
        st.subheader("Reports")
        report = st.selectbox("Report", ["inventory","media_assets","sellers","orders","expenses","hold_requests"])
        df = table(report)
        st.dataframe(df, use_container_width=True)
        if not df.empty:
            st.download_button("Download CSV", df.to_csv(index=False), f"{report}.csv", "text/csv")
