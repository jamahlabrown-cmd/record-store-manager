
import sqlite3
from pathlib import Path
from datetime import date, datetime
import pandas as pd
import streamlit as st

DB = Path("house_of_wax_v7.db")
MEDIA_DIR = Path("house_of_wax_media")
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "")


def conn():
    return sqlite3.connect(DB)


def q(sql, params=()):
    c = conn()
    c.execute(sql, params)
    c.commit()
    c.close()


def table(name):
    c = conn()
    df = pd.read_sql_query(f"SELECT * FROM {name}", c)
    c.close()
    return df


def setup():
    MEDIA_DIR.mkdir(exist_ok=True)
    c = conn()
    cur = c.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sku TEXT UNIQUE,
        barcode TEXT,
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
    artist, title, genre, fmt = s(row.get("artist","")), s(row.get("title","")), s(row.get("genre","")), s(row.get("format","Vinyl"))
    condition, year = s(row.get("condition","")), s(row.get("release_year",""))
    text = f"{artist}'s {title}"
    if year:
        text += f" ({year})"
    text += f" is a standout {genre.lower()} release on {fmt.lower()}." if genre else f" is a standout release on {fmt.lower()}."
    if condition:
        text += f" This copy is listed in {condition} condition."
    return text + " A strong pickup for collectors, DJs, and music lovers."


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
    (sku, barcode, artist, title, format, genre, condition, label, release_year, pressing_notes,
    cost, price, quantity, reorder_level, location, bio, caption, hashtags, image_url, public_visible,
    owner_type, seller_id, commission_rate, listing_fee, listing_status, updated_at)
    VALUES
    (:sku, :barcode, :artist, :title, :format, :genre, :condition, :label, :release_year, :pressing_notes,
    :cost, :price, :quantity, :reorder_level, :location, :bio, :caption, :hashtags, :image_url, :public_visible,
    :owner_type, :seller_id, :commission_rate, :listing_fee, :listing_status, :updated_at)
    ON CONFLICT(sku) DO UPDATE SET
    barcode=excluded.barcode, artist=excluded.artist, title=excluded.title, format=excluded.format,
    genre=excluded.genre, condition=excluded.condition, label=excluded.label, release_year=excluded.release_year,
    pressing_notes=excluded.pressing_notes, cost=excluded.cost, price=excluded.price, quantity=excluded.quantity,
    reorder_level=excluded.reorder_level, location=excluded.location, bio=excluded.bio, caption=excluded.caption,
    hashtags=excluded.hashtags, image_url=excluded.image_url, public_visible=excluded.public_visible,
    owner_type=excluded.owner_type, seller_id=excluded.seller_id, commission_rate=excluded.commission_rate,
    listing_fee=excluded.listing_fee, listing_status=excluded.listing_status, updated_at=excluded.updated_at
    """, data)
    c.commit()
    c.close()


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


setup()
st.set_page_config(page_title="House Of Wax", layout="wide")
st.sidebar.title("House Of Wax")
mode = st.sidebar.radio("Choose view", ["Public Storefront", "Seller Storefronts", "Admin Login"])

if mode == "Public Storefront":
    st.title("House Of Wax")
    st.caption("Browse records, view media, and request a hold.")
    inv = table("inventory")
    if inv.empty:
        st.info("No public inventory yet.")
    else:
        public = inv[(inv.public_visible == "Yes") & (inv.quantity > 0) & (inv.listing_status == "Active")]
        search = st.text_input("Search artist, title, genre, or barcode")
        if search:
            public = public[public.astype(str).apply(lambda col: col.str.contains(search, case=False, na=False)).any(axis=1)]
        for _, r in public.iterrows():
            with st.container(border=True):
                st.subheader(f"{r.artist} — {r.title}")
                st.caption("House Of Wax inventory" if r.owner_type == "Store" else f"House Of Wax seller #{int(r.seller_id)}")
                st.write(f"{r.format} | {r.genre} | {r.condition} | {r.release_year}")
                st.write(r.bio)
                st.write(f"**Price:** {money(r.price)}")
                st.write(f"**Available:** {int(r.quantity)}")
                media = get_media_for_sku(r.sku, public_only=True)
                if not media.empty:
                    with st.expander("View photos, audio, and video"):
                        render_media_assets(media)
                with st.expander("Request hold"):
                    with st.form(f"hold_{r.sku}"):
                        name = st.text_input("Name")
                        email = st.text_input("Email")
                        phone = st.text_input("Phone")
                        message = st.text_area("Message", value=f"I am interested in {r.artist} — {r.title}.")
                        if st.form_submit_button("Send Request"):
                            if not name or not email:
                                st.error("Name and email are required.")
                            else:
                                q("""INSERT INTO hold_requests
                                (request_date, sku, artist, title, customer_name, customer_email, customer_phone, message, status, created_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                                (date.today().isoformat(), r.sku, r.artist, r.title, name, email, phone, message, "New", datetime.now().isoformat(timespec="seconds")))
                                st.success("Request sent.")
    st.warning("Public view hides costs, expenses, sales reports, customers, and admin tools.")

elif mode == "Seller Storefronts":
    st.title("House Of Wax Seller Storefronts")
    sellers = table("sellers")
    inv = table("inventory")
    approved = sellers[sellers.status == "Approved"] if not sellers.empty else sellers
    if approved.empty:
        st.info("No approved seller storefronts yet.")
    else:
        choice = st.selectbox("Choose seller", [f"{r.id} | {r.store_name}" for _, r in approved.iterrows()])
        seller_id = int(choice.split("|")[0].strip())
        st.header(approved[approved.id == seller_id].iloc[0].store_name)
        items = inv[(inv.owner_type == "Marketplace Seller") & (inv.seller_id == seller_id) & (inv.quantity > 0)]
        if items.empty:
            st.info("This seller has no active listings.")
        else:
            for _, r in items.iterrows():
                with st.container(border=True):
                    st.subheader(f"{r.artist} — {r.title}")
                    st.write(f"{r.format} | {r.genre} | {r.condition}")
                    st.write(f"**Price:** {money(r.price)}")
                    media = get_media_for_sku(r.sku, public_only=True)
                    if not media.empty:
                        with st.expander("View media"):
                            render_media_assets(media)

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

    tabs = st.tabs(["Dashboard", "Barcode Scanner", "Inventory", "Upload CSV", "Media Manager", "Sellers", "Seller Listings", "Marketplace Orders", "Expenses", "Hold Requests", "Cleanup", "Reports"])

    with tabs[0]:
        st.subheader("Dashboard")
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
        st.subheader("Barcode Scanner / Barcode Entry")
        st.write("Use QRbot, a USB scanner, or a Bluetooth scanner. Paste or scan the barcode below.")
        barcode = st.text_input("Scan or type barcode")
        inv = table("inventory")
        if barcode:
            found = inv[inv.barcode.astype(str) == str(barcode)] if not inv.empty else inv
            if not found.empty:
                st.success("Barcode found.")
                st.dataframe(found, use_container_width=True)
            else:
                st.warning("Barcode not found. Add it below.")
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
                    if st.form_submit_button("Add Record From Barcode"):
                        save_inventory({"barcode": barcode, "artist": artist, "title": title, "format": fmt, "genre": genre, "condition": condition, "cost": cost, "price": price, "quantity": quantity})
                        st.success("Record added.")

    with tabs[2]:
        st.subheader("Inventory")
        inv = table("inventory")
        st.dataframe(inv, use_container_width=True)
        with st.form("manual"):
            st.subheader("Add / Edit")
            c1,c2,c3 = st.columns(3)
            sku = c1.text_input("SKU")
            barcode = c2.text_input("Barcode")
            public_visible = c3.selectbox("Public Visible", ["Yes","No"])
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
            if st.form_submit_button("Save"):
                save_inventory({"sku":sku,"barcode":barcode,"artist":artist,"title":title,"format":fmt,"genre":genre,"condition":condition,"cost":cost,"price":price,"quantity":quantity,"reorder_level":reorder,"location":location,"public_visible":public_visible})
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

    with tabs[6]:
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

    with tabs[7]:
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

    with tabs[8]:
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

    with tabs[9]:
        st.subheader("Hold Requests")
        st.dataframe(table("hold_requests"), use_container_width=True)

    with tabs[10]:
        st.subheader("Cleanup")
        if st.button("Delete sample inventory"):
            for sku in ["VIN-0001","VIN-0002","VIN-0003","CD-0001","MER-0001"]:
                q("DELETE FROM inventory WHERE sku = ?", (sku,))
            st.success("Samples deleted.")
        confirm = st.text_input("Type DELETE ALL to wipe all app data")
        if st.button("Reset entire app"):
            if confirm == "DELETE ALL":
                for t in ["inventory","media_assets","sellers","orders","expenses","hold_requests"]:
                    q(f"DELETE FROM {t}")
                st.success("App reset.")
            else:
                st.error("Type DELETE ALL exactly.")

    with tabs[11]:
        st.subheader("Reports")
        report = st.selectbox("Report", ["inventory","media_assets","sellers","orders","expenses","hold_requests"])
        df = table(report)
        st.dataframe(df, use_container_width=True)
        if not df.empty:
            st.download_button("Download CSV", df.to_csv(index=False), f"{report}.csv", "text/csv")
