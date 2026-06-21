
import sqlite3
from pathlib import Path
from datetime import datetime
import shutil
import pandas as pd
import streamlit as st

st.set_page_config(page_title="House Of Wax Marketplace", page_icon="🎧", layout="wide")

APP_VERSION = "V15.7 TESTING UNLOCKED"
APP_NAME = "House Of Wax"
TEST_MODE = True

# IMPORTANT:
# Stable database name going forward so buyer/seller profiles do not disappear every version.
DB = Path("house_of_wax.db")

# Try to recover old test databases if the new stable DB does not exist yet.
OLD_DBS = [
    "house_of_wax_v15_6.db",
    "house_of_wax_v15_5.db",
    "house_of_wax_v15_4.db",
    "house_of_wax_v15_3.db",
    "house_of_wax_v15_2.db",
]

if not DB.exists():
    for old in OLD_DBS:
        old_path = Path(old)
        if old_path.exists():
            shutil.copy(old_path, DB)
            break

MEDIA_DIR = Path("house_of_wax_uploads")
MEDIA_DIR.mkdir(exist_ok=True)

try:
    ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "")
except Exception:
    ADMIN_PASSWORD = ""


# -----------------------------
# Helpers
# -----------------------------
def now():
    return datetime.now().isoformat(timespec="seconds")


def money(value):
    try:
        return f"${float(value):,.2f}"
    except Exception:
        return "$0.00"


def safe(value, fallback=""):
    if value is None:
        return fallback
    try:
        if pd.isna(value):
            return fallback
    except Exception:
        pass
    text = str(value)
    if text.lower() in ["nan", "none"]:
        return fallback
    return text


def connect():
    return sqlite3.connect(DB)


def run_sql(sql, params=()):
    conn = connect()
    cur = conn.cursor()
    cur.execute(sql, params)
    conn.commit()
    conn.close()


def get_df(sql, params=()):
    conn = connect()
    df = pd.read_sql_query(sql, conn, params=params)
    conn.close()
    return df


def get_table(table_name):
    try:
        return get_df(f"SELECT * FROM {table_name}")
    except Exception:
        return pd.DataFrame()


def add_column_if_missing(table_name, column_name, column_type):
    try:
        existing = get_df(f"PRAGMA table_info({table_name})")
        if column_name not in existing["name"].tolist():
            run_sql(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
    except Exception:
        pass


def get_setting(key, default=""):
    try:
        df = get_df("SELECT value FROM settings WHERE key = ?", (key,))
        if df.empty:
            return default
        return safe(df.iloc[0]["value"], default)
    except Exception:
        return default


def save_setting(key, value):
    run_sql("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))


def email_exists(table_name, email):
    if not email:
        return False
    try:
        df = get_df(f"SELECT id FROM {table_name} WHERE lower(email)=lower(?)", (email.strip(),))
        return not df.empty
    except Exception:
        return False


def save_uploaded_file(uploaded_file, folder_name):
    if uploaded_file is None:
        return ""
    folder = MEDIA_DIR / folder_name
    folder.mkdir(parents=True, exist_ok=True)
    safe_name = uploaded_file.name.replace(" ", "_").replace("/", "_")
    path = folder / f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{safe_name}"
    path.write_bytes(uploaded_file.getbuffer())
    return str(path)


def delete_by_id(table_name, row_id):
    run_sql(f"DELETE FROM {table_name} WHERE id = ?", (int(row_id),))


def calculate_fee(total, auction=False):
    key = "auction_commission_percent" if auction else "platform_commission_percent"
    pct = float(get_setting(key, "9"))
    return round(float(total) * pct / 100, 2)


# -----------------------------
# Database setup
# -----------------------------
def setup_database():
    conn = connect()
    cur = conn.cursor()

    cur.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sellers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_name TEXT NOT NULL,
            owner_name TEXT,
            email TEXT UNIQUE,
            phone TEXT,
            city TEXT,
            state TEXT,
            website TEXT,
            instagram TEXT,
            store_bio TEXT,
            seller_story TEXT,
            specialties TEXT,
            logo_url TEXT,
            banner_url TEXT,
            status TEXT DEFAULT 'Pending',
            seller_level TEXT DEFAULT 'Starter Seller',
            rating REAL DEFAULT 100,
            completed_sales INTEGER DEFAULT 0,
            disputes INTEGER DEFAULT 0,
            strikes INTEGER DEFAULT 0,
            auction_override TEXT DEFAULT 'No',
            access_code TEXT,
            created_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS seller_policies (
            seller_id INTEGER PRIMARY KEY,
            shipping_policy TEXT,
            return_policy TEXT,
            grading_policy TEXT,
            customer_service_policy TEXT,
            bundle_policy TEXT,
            auction_policy TEXT,
            buyer_requirements TEXT,
            local_pickup_policy TEXT,
            international_shipping_policy TEXT,
            processing_time TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS buyers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT UNIQUE,
            phone TEXT,
            city TEXT,
            status TEXT DEFAULT 'New Buyer',
            rating REAL DEFAULT 100,
            completed_purchases INTEGER DEFAULT 0,
            unpaid_orders INTEGER DEFAULT 0,
            disputes INTEGER DEFAULT 0,
            strikes INTEGER DEFAULT 0,
            created_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            seller_id INTEGER,
            sku TEXT,
            barcode TEXT,
            catalog_number TEXT,
            matrix_runout TEXT,
            category TEXT,
            artist TEXT,
            title TEXT,
            format TEXT,
            label TEXT,
            release_year TEXT,
            genre TEXT,
            media_grade TEXT,
            sleeve_grade TEXT,
            condition_notes TEXT,
            description TEXT,
            price REAL DEFAULT 0,
            quantity INTEGER DEFAULT 1,
            shipping_price REAL DEFAULT 0,
            image_url TEXT,
            video_url TEXT,
            audio_url TEXT,
            external_release_url TEXT,
            listing_status TEXT DEFAULT 'Active',
            listing_type TEXT DEFAULT 'Fixed Price',
            created_at TEXT,
            updated_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS product_gallery (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            image_url TEXT,
            caption TEXT,
            created_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            seller_id INTEGER,
            buyer_id INTEGER,
            order_type TEXT,
            status TEXT DEFAULT 'New',
            item_price REAL DEFAULT 0,
            shipping_price REAL DEFAULT 0,
            platform_fee REAL DEFAULT 0,
            seller_payout REAL DEFAULT 0,
            buyer_message TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            reviewer_type TEXT,
            reviewer_id INTEGER,
            reviewee_type TEXT,
            reviewee_id INTEGER,
            rating INTEGER,
            comment TEXT,
            created_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            seller_id INTEGER,
            buyer_id INTEGER,
            sender_type TEXT,
            subject TEXT,
            message TEXT,
            status TEXT DEFAULT 'New',
            created_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS seller_followers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            seller_id INTEGER,
            buyer_id INTEGER,
            created_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS seller_badges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            seller_id INTEGER,
            badge_name TEXT,
            badge_type TEXT,
            active TEXT DEFAULT 'Yes',
            created_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS store_announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            seller_id INTEGER,
            title TEXT,
            body TEXT,
            status TEXT DEFAULT 'Active',
            created_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS seller_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            seller_id INTEGER,
            event_title TEXT,
            event_type TEXT,
            event_date TEXT,
            description TEXT,
            status TEXT DEFAULT 'Active',
            created_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS listing_flags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            seller_id INTEGER,
            buyer_id INTEGER,
            reason TEXT,
            details TEXT,
            status TEXT DEFAULT 'Open',
            admin_notes TEXT,
            created_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS seller_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            seller_id INTEGER,
            buyer_id INTEGER,
            reason TEXT,
            details TEXT,
            status TEXT DEFAULT 'Open',
            admin_notes TEXT,
            created_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            buyer_id INTEGER,
            item_type TEXT,
            item_id INTEGER,
            created_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS auctions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            seller_id INTEGER,
            auction_title TEXT,
            starting_bid REAL DEFAULT 0,
            reserve_price REAL DEFAULT 0,
            buy_now_price REAL DEFAULT 0,
            bid_increment REAL DEFAULT 1,
            start_time TEXT,
            end_time TEXT,
            status TEXT DEFAULT 'Draft',
            notes TEXT,
            created_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS bids (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            auction_id INTEGER,
            buyer_id INTEGER,
            bid_amount REAL,
            bid_time TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS culture_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            category TEXT,
            author TEXT,
            body TEXT,
            image_url TEXT,
            status TEXT DEFAULT 'Published',
            created_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS disputes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            product_id INTEGER,
            seller_id INTEGER,
            buyer_id INTEGER,
            opened_by TEXT,
            reason TEXT,
            details TEXT,
            status TEXT DEFAULT 'Open',
            resolution TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS platform_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            category TEXT,
            rule_text TEXT,
            active TEXT DEFAULT 'Yes',
            created_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS seller_notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            seller_id INTEGER,
            subject TEXT,
            message TEXT,
            status TEXT DEFAULT 'Unread',
            created_at TEXT
        )
    """)

    conn.commit()
    conn.close()

    # Migration safety for older DBs missing columns.
    seller_columns = {
        "state": "TEXT",
        "website": "TEXT",
        "instagram": "TEXT",
        "seller_story": "TEXT",
        "specialties": "TEXT",
        "logo_url": "TEXT",
        "banner_url": "TEXT",
    }
    for col, typ in seller_columns.items():
        add_column_if_missing("sellers", col, typ)

    defaults = {
        "logo_url": "",
        "site_tagline": "A seller-powered marketplace for records, music culture, clothing, and collectors.",
        "announcement": "TEST MODE: all major features are unlocked so we can test fast.",
        "platform_commission_percent": "9",
        "auction_commission_percent": "10",
        "auction_min_completed_sales": "0",
        "auction_min_rating": "0",
        "default_processing_time": "3 business days",
        "buyer_payment_window_hours": "48",
        "storefront_url": "https://record-store-manager-nsgwoj39v4rgxphhxcrgqn.streamlit.app/",
    }

    for key, value in defaults.items():
        if get_df("SELECT key FROM settings WHERE key = ?", (key,)).empty:
            run_sql("INSERT INTO settings (key, value) VALUES (?, ?)", (key, value))


setup_database()


# -----------------------------
# Data logic
# -----------------------------
def get_seller(seller_id):
    if not seller_id:
        return None
    df = get_df("SELECT * FROM sellers WHERE id = ?", (int(seller_id),))
    return None if df.empty else df.iloc[0]


def get_buyer(buyer_id):
    if not buyer_id:
        return None
    df = get_df("SELECT * FROM buyers WHERE id = ?", (int(buyer_id),))
    return None if df.empty else df.iloc[0]


def follower_count(seller_id):
    df = get_df("SELECT COUNT(*) AS count FROM seller_followers WHERE seller_id=?", (int(seller_id),))
    return 0 if df.empty else int(df.iloc[0]["count"] or 0)


def seller_badges_text(seller_id):
    df = get_df("SELECT badge_name FROM seller_badges WHERE seller_id=? AND active='Yes' ORDER BY created_at DESC", (int(seller_id),))
    if df.empty:
        return ""
    return " • ".join([safe(x) for x in df["badge_name"].tolist()])


def recalculate_rating(reviewee_type, reviewee_id):
    df = get_df("SELECT AVG(rating) AS avg_rating FROM feedback WHERE reviewee_type=? AND reviewee_id=?", (reviewee_type, int(reviewee_id)))
    avg = df.iloc[0]["avg_rating"]
    if pd.isna(avg):
        return
    score = round(float(avg) * 20, 1)
    if reviewee_type == "Seller":
        run_sql("UPDATE sellers SET rating=? WHERE id=?", (score, int(reviewee_id)))
    elif reviewee_type == "Buyer":
        run_sql("UPDATE buyers SET rating=? WHERE id=?", (score, int(reviewee_id)))


def buyer_allowed(buyer):
    if TEST_MODE:
        return True, "Testing mode active."
    if buyer is None:
        return False, "A registered buyer account is required."
    if buyer["status"] in ["Restricted Buyer", "Suspended Buyer"]:
        return False, "This buyer account is restricted."
    return True, "Buyer allowed."


def auction_eligible(seller):
    if TEST_MODE:
        return True, "Testing mode active. Auction access unlocked."
    if seller is None:
        return False, "Seller not found."
    if seller["status"] != "Approved":
        return False, "Seller must be approved first."
    return True, "Eligible."


def generate_description(data):
    artist = safe(data.get("artist"), "This listing")
    title = safe(data.get("title"))
    fmt = safe(data.get("format"), "music/culture item")
    genre = safe(data.get("genre"))
    label = safe(data.get("label"))
    year = safe(data.get("release_year"))
    media_grade = safe(data.get("media_grade"), "not specified")
    sleeve_grade = safe(data.get("sleeve_grade"), "N/A")
    notes = safe(data.get("condition_notes"))
    text = f"{artist} — {title} is listed on House Of Wax as a curated {fmt} marketplace item."
    if genre:
        text += f" It fits buyers interested in {genre}, collecting, and music culture."
    if label or year:
        text += f" Release details include {label or 'the listed label'}"
        if year:
            text += f" from {year}"
        text += "."
    text += f" Condition is listed as media/product grade {media_grade}, with sleeve or packaging grade {sleeve_grade}."
    if notes:
        text += f" Seller notes: {notes}"
    return text


def listing_score(product):
    checks = [
        float(product.get("price") or 0) > 0,
        bool(safe(product.get("image_url"))),
        bool(safe(product.get("media_grade")) or safe(product.get("condition_notes"))),
        len(safe(product.get("description"))) > 50,
        bool(safe(product.get("category"))),
    ]
    return int(sum(checks) / len(checks) * 100)


def approval_message(seller):
    return f"""Your House Of Wax seller store, {safe(seller.get('store_name'))}, has been approved for testing.

Log into the Seller Dashboard with your seller email and access code.

In testing mode, you can build your profile, upload logo/banner, add products, create announcements, use auctions, and test the full store flow.
"""


def create_seller_spotlight_post(seller_id):
    seller = get_seller(seller_id)
    if seller is None:
        return False
    title = f"Seller Spotlight: {safe(seller.get('store_name'))}"
    body = f"""Meet {safe(seller.get('store_name'))}, part of the House Of Wax community.

{safe(seller.get('seller_story'), safe(seller.get('store_bio'), 'This seller is building their presence on House Of Wax.'))}

Specialties: {safe(seller.get('specialties'), 'Music, culture, and collector goods.')}
"""
    image = safe(seller.get("banner_url")) or safe(seller.get("logo_url"))
    run_sql("INSERT INTO culture_posts (title, category, author, body, image_url, status, created_at) VALUES (?, 'Seller Spotlight', 'House Of Wax', ?, ?, 'Published', ?)", (title, body, image, now()))
    return True


def seed_demo_data():
    if get_table("buyers").empty:
        run_sql("INSERT INTO buyers (name,email,phone,city,status,rating,created_at) VALUES ('Demo Buyer','buyer@test.com','1234567890','Charlotte','Trusted Buyer',100,?)", (now(),))
    if get_table("sellers").empty:
        run_sql("""
            INSERT INTO sellers
            (store_name,owner_name,email,phone,city,state,instagram,website,store_bio,seller_story,specialties,status,seller_level,rating,completed_sales,auction_override,access_code,created_at)
            VALUES ('Demo Wax Seller','Demo Owner','seller@test.com','1234567890','Charlotte','NC','@demowax','https://example.com','A demo seller for testing House Of Wax.','We collect and sell records, culture goods, and vintage music pieces.','Soul, Jazz, Hip-Hop, Carolina music, vintage tees','Approved','Verified Seller',100,12,'Yes','test123',?)
        """, (now(),))
    sellers = get_table("sellers")
    products = get_table("products")
    if products.empty and not sellers.empty:
        sid = int(sellers.iloc[0]["id"])
        run_sql("""
            INSERT INTO products
            (seller_id,sku,barcode,catalog_number,matrix_runout,category,artist,title,format,label,release_year,genre,media_grade,sleeve_grade,condition_notes,description,price,quantity,shipping_price,image_url,listing_status,listing_type,created_at,updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (sid, "DEMO-001", "123456789", "CAT-001", "A1/B1", "Vinyl Records", "Demo Artist", "Demo Album", "Vinyl", "Demo Label", "1978", "Soul", "VG+", "VG", "Light sleeve wear. Plays strong.", "Demo product for testing House Of Wax.", 24.99, 1, 5.00, "", "Active", "Fixed Price", now(), now()))


# -----------------------------
# UI helpers
# -----------------------------
def render_header():
    logo_url = get_setting("logo_url", "").strip()
    tagline = get_setting("site_tagline", "")
    announcement = get_setting("announcement", "")

    col_logo, col_text = st.columns([1, 5])
    with col_logo:
        if logo_url:
            st.image(logo_url, use_container_width=True)
        else:
            st.markdown("## 🎧")
    with col_text:
        st.title(APP_NAME)
        st.caption(tagline)
        st.caption(f"Running {APP_VERSION}")
    if TEST_MODE:
        st.warning("TEST MODE ACTIVE: seller approval, product upload, auctions, messaging, feedback, and store tools are unlocked for testing.")
    if announcement:
        st.info(announcement)


def choose_buyer(key_prefix):
    buyers = get_table("buyers")
    if buyers.empty:
        st.warning("No buyers yet. Use Test Setup or Register / Sell.")
        return None
    options = [f"{int(r['id'])} | {safe(r['name'])} | {safe(r['email'])} | {safe(r['status'])}" for _, r in buyers.iterrows()]
    selected = st.selectbox("Buyer account", options, key=f"{key_prefix}_buyer")
    return int(selected.split("|")[0].strip())


def choose_seller(key_prefix):
    sellers = get_table("sellers")
    if sellers.empty:
        st.warning("No sellers yet. Use Test Setup or Register / Sell.")
        return None
    options = [f"{int(r['id'])} | {safe(r['store_name'])} | {safe(r['email'])} | {safe(r['status'])}" for _, r in sellers.iterrows()]
    selected = st.selectbox("Seller account", options, key=f"{key_prefix}_seller")
    return int(selected.split("|")[0].strip())


def product_card(product):
    seller = get_seller(product["seller_id"])
    seller_name = safe(seller["store_name"], "Seller") if seller is not None else "Unknown Seller"
    with st.container(border=True):
        image = safe(product.get("image_url"))
        if image:
            st.image(image, use_container_width=True)
        else:
            st.markdown("### 🎵")
        st.markdown(f"### {safe(product.get('artist'))} — {safe(product.get('title'))}")
        st.caption(f"{safe(product.get('format'))} • {safe(product.get('genre'))} • Seller: {seller_name}")
        st.write(f"**Price:** {money(product.get('price'))}")
        st.progress(listing_score(product) / 100, text=f"Listing quality: {listing_score(product)}/100")
        if st.button("View Item", key=f"view_product_{int(product['id'])}"):
            st.session_state["selected_product_id"] = int(product["id"])
            st.rerun()


def seller_card(seller):
    with st.container(border=True):
        banner = safe(seller.get("banner_url"))
        if banner:
            st.image(banner, use_container_width=True)
        c1, c2 = st.columns([1, 4])
        with c1:
            logo = safe(seller.get("logo_url"))
            if logo:
                st.image(logo, use_container_width=True)
            else:
                st.markdown("### 🏪")
        with c2:
            st.subheader(safe(seller.get("store_name")))
            st.caption(f"{safe(seller.get('seller_level'))} • Rating {seller['rating']}% • Sales {seller['completed_sales']} • Followers {follower_count(int(seller['id']))}")
            badges = seller_badges_text(int(seller["id"]))
            if badges:
                st.caption(f"Badges: {badges}")
            st.write(safe(seller.get("store_bio"), "Independent seller on House Of Wax."))
            if st.button("View Seller Profile", key=f"seller_profile_{int(seller['id'])}"):
                st.session_state["selected_seller_id"] = int(seller["id"])
                st.rerun()


def seller_profile_page(seller_id):
    seller = get_seller(seller_id)
    if seller is None:
        st.error("Seller not found.")
        return
    if st.button("← Back"):
        st.session_state.pop("selected_seller_id", None)
        st.rerun()

    banner = safe(seller.get("banner_url"))
    if banner:
        st.image(banner, use_container_width=True)

    c1, c2 = st.columns([1, 4])
    with c1:
        logo = safe(seller.get("logo_url"))
        if logo:
            st.image(logo, use_container_width=True)
        else:
            st.markdown("## 🏪")
    with c2:
        st.title(safe(seller.get("store_name")))
        st.caption(f"{safe(seller.get('seller_level'))} • Rating {seller['rating']}% • Followers {follower_count(int(seller['id']))}")
        badges = seller_badges_text(int(seller["id"]))
        if badges:
            st.info(f"Badges: {badges}")
        if safe(seller.get("instagram")):
            st.write(f"Instagram: {safe(seller.get('instagram'))}")
        if safe(seller.get("website")):
            st.link_button("Seller Website", safe(seller.get("website")))

    with st.expander("Follow this seller"):
        buyer_id = choose_buyer(f"follow_{seller_id}")
        if st.button("Follow Seller", key=f"follow_btn_{seller_id}") and buyer_id:
            exists = get_df("SELECT id FROM seller_followers WHERE seller_id=? AND buyer_id=?", (seller_id, buyer_id))
            if exists.empty:
                run_sql("INSERT INTO seller_followers (seller_id,buyer_id,created_at) VALUES (?,?,?)", (seller_id, buyer_id, now()))
                st.success("Seller followed.")
            else:
                st.info("Already following.")

    announcements = get_df("SELECT * FROM store_announcements WHERE seller_id=? AND status='Active' ORDER BY created_at DESC", (seller_id,))
    if not announcements.empty:
        st.subheader("Store Announcements")
        for _, a in announcements.iterrows():
            with st.container(border=True):
                st.write(f"**{safe(a.get('title'))}**")
                st.write(safe(a.get("body")))

    events = get_df("SELECT * FROM seller_events WHERE seller_id=? AND status='Active' ORDER BY event_date", (seller_id,))
    if not events.empty:
        st.subheader("Drops / Events")
        for _, e in events.iterrows():
            with st.container(border=True):
                st.write(f"**{safe(e.get('event_title'))}** — {safe(e.get('event_type'))}")
                st.caption(safe(e.get("event_date")))
                st.write(safe(e.get("description")))

    st.subheader("About This Seller")
    st.write(safe(seller.get("seller_story"), safe(seller.get("store_bio"), "This seller has not added a story yet.")))
    if safe(seller.get("specialties")):
        st.subheader("Specialties")
        st.write(safe(seller.get("specialties")))

    st.subheader("Seller Listings")
    products = get_df("SELECT * FROM products WHERE seller_id=? AND listing_status IN ('Active','Draft') ORDER BY created_at DESC", (seller_id,))
    if products.empty:
        st.info("No listings yet.")
    else:
        cols = st.columns(3)
        for i, (_, product) in enumerate(products.iterrows()):
            with cols[i % 3]:
                product_card(product)


def product_detail(product):
    if st.button("← Back to Marketplace"):
        st.session_state.pop("selected_product_id", None)
        st.rerun()

    seller = get_seller(product["seller_id"])
    left, right = st.columns([1.2, 1])
    with left:
        image = safe(product.get("image_url"))
        if image:
            st.image(image, use_container_width=True)
        else:
            st.markdown("## 🎵")
        gallery = get_df("SELECT * FROM product_gallery WHERE product_id=? ORDER BY created_at DESC", (int(product["id"]),))
        if not gallery.empty:
            st.subheader("Gallery")
            for _, g in gallery.iterrows():
                if safe(g.get("image_url")):
                    st.image(safe(g.get("image_url")), caption=safe(g.get("caption")), use_container_width=True)

    with right:
        st.header(f"{safe(product.get('artist'))} — {safe(product.get('title'))}")
        st.write(f"**Price:** {money(product.get('price'))}")
        st.write(f"**Shipping:** {money(product.get('shipping_price'))}")
        if seller is not None:
            st.write(f"**Seller:** {safe(seller['store_name'])}")
            if st.button("View Seller Profile", key=f"seller_from_product_{int(product['id'])}"):
                st.session_state["selected_seller_id"] = int(seller["id"])
                st.session_state.pop("selected_product_id", None)
                st.rerun()
        st.write(f"**Category:** {safe(product.get('category'))}")
        st.write(f"**Condition:** {safe(product.get('media_grade'))} / {safe(product.get('sleeve_grade'))}")

    st.subheader("Description")
    st.write(safe(product.get("description"), generate_description(product)))

    st.divider()
    st.subheader("Testing Actions")
    buyer_id = choose_buyer(f"buy_{int(product['id'])}")

    with st.expander("Request to Buy / Contact Seller", expanded=True):
        action = st.selectbox("Action", ["Request to Buy", "Ask a Question", "Make Offer"], key=f"action_{int(product['id'])}")
        message = st.text_area("Message", key=f"message_{int(product['id'])}")
        if st.button("Submit to Seller", key=f"submit_{int(product['id'])}") and buyer_id:
            item = float(product.get("price") or 0)
            ship = float(product.get("shipping_price") or 0)
            fee = calculate_fee(item + ship)
            run_sql("""
                INSERT INTO orders (product_id,seller_id,buyer_id,order_type,status,item_price,shipping_price,platform_fee,seller_payout,buyer_message,created_at,updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """, (int(product["id"]), int(product["seller_id"]), int(buyer_id), action, "New", item, ship, fee, item + ship - fee, message, now(), now()))
            run_sql("""
                INSERT INTO messages (product_id,seller_id,buyer_id,sender_type,subject,message,status,created_at)
                VALUES (?,?,?,?,?,?,?,?)
            """, (int(product["id"]), int(product["seller_id"]), int(buyer_id), "Buyer", action, message, "New", now()))
            st.success("Sent to seller.")

    with st.expander("Save / Favorite"):
        if st.button("Save Item", key=f"save_{int(product['id'])}") and buyer_id:
            run_sql("INSERT INTO favorites (buyer_id,item_type,item_id,created_at) VALUES (?,'Product',?,?)", (int(buyer_id), int(product["id"]), now()))
            st.success("Item saved.")

    with st.expander("Report Listing"):
        reason = st.selectbox("Reason", ["Counterfeit / Bootleg", "Misgraded", "Wrong Info", "Spam", "Other"], key=f"flag_reason_{int(product['id'])}")
        details = st.text_area("Details", key=f"flag_details_{int(product['id'])}")
        if st.button("Submit Report", key=f"report_{int(product['id'])}") and buyer_id:
            run_sql("INSERT INTO listing_flags (product_id,seller_id,buyer_id,reason,details,status,created_at) VALUES (?,?,?,?,?,'Open',?)", (int(product["id"]), int(product["seller_id"]), int(buyer_id), reason, details, now()))
            st.success("Report submitted.")


# -----------------------------
# Pages
# -----------------------------
def home_page():
    render_header()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Listings", len(get_table("products")))
    c2.metric("Sellers", len(get_table("sellers")))
    c3.metric("Buyers", len(get_table("buyers")))
    c4.metric("Orders", len(get_table("orders")))
    st.markdown("## Community marketplace testing build")
    st.write("Use Test Setup to create demo accounts, then test buyer, seller, product, messaging, favorites, feedback, announcements, badges, and admin tools.")


def test_setup_page():
    render_header()
    st.header("Test Setup")
    st.write("This page keeps testing moving. Use it to seed accounts and quickly access credentials.")
    if st.button("Create Demo Buyer, Seller, and Product"):
        seed_demo_data()
        st.success("Demo data ready.")
    st.code("Buyer: buyer@test.com\nSeller: seller@test.com\nSeller access code: test123")
    st.subheader("Current Data")
    st.write("Buyers")
    st.dataframe(get_table("buyers"), use_container_width=True)
    st.write("Sellers")
    st.dataframe(get_table("sellers"), use_container_width=True)
    st.write("Products")
    st.dataframe(get_table("products"), use_container_width=True)


def marketplace_page():
    render_header()
    st.header("Marketplace")
    if "selected_seller_id" in st.session_state:
        seller_profile_page(int(st.session_state["selected_seller_id"]))
        return
    products = get_df("SELECT * FROM products WHERE listing_status IN ('Active','Draft') ORDER BY created_at DESC")
    if products.empty:
        st.info("No products yet. Use Test Setup or Seller Dashboard.")
        return
    if "selected_product_id" in st.session_state:
        selected = products[products["id"] == int(st.session_state["selected_product_id"])]
        if not selected.empty:
            product_detail(selected.iloc[0])
            return
        st.session_state.pop("selected_product_id", None)
    search = st.text_input("Search")
    filtered = products.copy()
    if search:
        term = search.lower()
        filtered = filtered[
            filtered["artist"].fillna("").str.lower().str.contains(term) |
            filtered["title"].fillna("").str.lower().str.contains(term) |
            filtered["category"].fillna("").str.lower().str.contains(term)
        ]
    cols = st.columns(3)
    for i, (_, product) in enumerate(filtered.iterrows()):
        with cols[i % 3]:
            product_card(product)


def seller_stores_page():
    render_header()
    st.header("Seller Stores")
    if "selected_seller_id" in st.session_state:
        seller_profile_page(int(st.session_state["selected_seller_id"]))
        return
    sellers = get_table("sellers")
    if sellers.empty:
        st.info("No sellers yet. Use Test Setup or Register / Sell.")
        return
    for _, seller in sellers.iterrows():
        seller_card(seller)



def seller_stores_page():
    render_header()
    st.header("Seller Stores")
    if "selected_seller_id" in st.session_state:
        seller_profile_page(int(st.session_state["selected_seller_id"]))
        return
    sellers = get_table("sellers")
    if sellers.empty:
        st.info("No sellers yet. Use Test Setup or Register / Sell.")
        return
    for _, seller in sellers.iterrows():
        seller_card(seller)


def register_page():
    render_header()
    st.header("Register / Sell")
    btab, stab = st.tabs(["Buyer Registration", "Create Seller Store"])
    with btab:
        with st.form("buyer_reg"):
            name = st.text_input("Name")
            email = st.text_input("Email")
            phone = st.text_input("Phone")
            city = st.text_input("City")
            submitted = st.form_submit_button("Create Buyer")
        if submitted:
            if email_exists("buyers", email):
                st.warning("Buyer email already exists.")
            else:
                run_sql("INSERT INTO buyers (name,email,phone,city,status,rating,created_at) VALUES (?,?,?,?,?,?,?)", (name, email, phone, city, "New Buyer", 100, now()))
                st.success("Buyer created.")
    with stab:
        with st.form("seller_reg"):
            store_name = st.text_input("Store Name")
            owner = st.text_input("Owner")
            email = st.text_input("Seller Email")
            code = st.text_input("Access Code", type="password")
            bio = st.text_area("Short Bio")
            story = st.text_area("Seller Story")
            specialties = st.text_area("Specialties")
            logo_file = st.file_uploader("Logo", type=["png","jpg","jpeg","webp"])
            banner_file = st.file_uploader("Banner", type=["png","jpg","jpeg","webp"])
            submitted = st.form_submit_button("Create Seller Store")
        if submitted:
            if email_exists("sellers", email):
                st.warning("Seller email already exists.")
            else:
                logo = save_uploaded_file(logo_file, "seller_logos")
                banner = save_uploaded_file(banner_file, "seller_banners")
                status = "Approved" if TEST_MODE else "Pending"
                level = "Verified Seller" if TEST_MODE else "Starter Seller"
                run_sql("""
                    INSERT INTO sellers (store_name,owner_name,email,store_bio,seller_story,specialties,logo_url,banner_url,status,seller_level,rating,auction_override,access_code,created_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (store_name, owner, email, bio, story, specialties, logo, banner, status, level, 100, "Yes", code, now()))
                st.success("Seller store created. In test mode, it is active immediately.")


def buyer_dashboard_page():
    render_header()
    st.header("Buyer Dashboard")
    email = st.text_input("Buyer email", value="buyer@test.com")
    if not st.button("Open Buyer Dashboard"):
        return
    buyer_df = get_df("SELECT * FROM buyers WHERE lower(email)=lower(?)", (email.strip(),))
    if buyer_df.empty:
        st.error("Buyer not found. Use Test Setup.")
        return
    buyer = buyer_df.iloc[0]
    buyer_id = int(buyer["id"])
    st.success(f"Buyer: {safe(buyer['name'])}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Status", safe(buyer["status"]))
    c2.metric("Rating", f"{buyer['rating']}%")
    c3.metric("Purchases", buyer["completed_purchases"])
    tabs = st.tabs(["Profile", "Orders", "Messages", "Favorites", "Following", "Leave Seller Feedback", "Feedback Received"])
    with tabs[0]:
        with st.form("buyer_profile"):
            name = st.text_input("Name", value=safe(buyer["name"]))
            phone = st.text_input("Phone", value=safe(buyer["phone"]))
            city = st.text_input("City", value=safe(buyer["city"]))
            submitted = st.form_submit_button("Save")
        if submitted:
            run_sql("UPDATE buyers SET name=?, phone=?, city=? WHERE id=?", (name, phone, city, buyer_id))
            st.success("Saved.")
    with tabs[1]:
        orders = get_df("SELECT * FROM orders WHERE buyer_id=? ORDER BY created_at DESC", (buyer_id,))
        st.dataframe(orders, use_container_width=True)
    with tabs[2]:
        messages = get_df("SELECT * FROM messages WHERE buyer_id=? ORDER BY created_at DESC", (buyer_id,))
        st.dataframe(messages, use_container_width=True)
    with tabs[3]:
        favs = get_df("SELECT * FROM favorites WHERE buyer_id=? ORDER BY created_at DESC", (buyer_id,))
        st.dataframe(favs, use_container_width=True)
    with tabs[4]:
        following = get_df("SELECT f.*, s.store_name FROM seller_followers f LEFT JOIN sellers s ON f.seller_id=s.id WHERE f.buyer_id=?", (buyer_id,))
        st.dataframe(following, use_container_width=True)
    with tabs[5]:
        completed = get_df("SELECT * FROM orders WHERE buyer_id=? AND status='Completed'", (buyer_id,))
        st.dataframe(completed, use_container_width=True)
        if not completed.empty:
            order_id = st.selectbox("Order", completed["id"].tolist())
            order = completed[completed["id"] == order_id].iloc[0]
            rating = st.slider("Seller rating", 1, 5, 5)
            comment = st.text_area("Comment")
            if st.button("Submit Seller Feedback"):
                run_sql("INSERT INTO feedback (order_id,reviewer_type,reviewer_id,reviewee_type,reviewee_id,rating,comment,created_at) VALUES (?,'Buyer',?,'Seller',?,?,?,?)", (int(order_id), buyer_id, int(order["seller_id"]), int(rating), comment, now()))
                recalculate_rating("Seller", int(order["seller_id"]))
                st.success("Feedback submitted.")
    with tabs[6]:
        st.dataframe(get_df("SELECT * FROM feedback WHERE reviewee_type='Buyer' AND reviewee_id=?", (buyer_id,)), use_container_width=True)


def seller_dashboard_page():
    render_header()
    st.header("Seller Dashboard")
    email = st.text_input("Seller email", value="seller@test.com")
    code = st.text_input("Access code", value="test123", type="password")
    if not st.button("Enter Seller Dashboard"):
        return
    seller_df = get_df("SELECT * FROM sellers WHERE lower(email)=lower(?) AND access_code=?", (email.strip(), code))
    if seller_df.empty:
        st.error("Seller not found. Use Test Setup.")
        return
    seller = seller_df.iloc[0]
    seller_id = int(seller["id"])
    st.success(f"Seller: {safe(seller['store_name'])} | Status: {safe(seller['status'])}")
    tabs = st.tabs(["Store Profile", "Upload Product", "Bulk Import", "Gallery", "Listings", "Orders", "Messages", "Announcements", "Events/Drops", "Badges", "Feedback"])
    with tabs[0]:
        with st.form("seller_profile"):
            store_name = st.text_input("Store name", value=safe(seller["store_name"]))
            bio = st.text_area("Bio", value=safe(seller.get("store_bio")))
            story = st.text_area("Story", value=safe(seller.get("seller_story")))
            specialties = st.text_area("Specialties", value=safe(seller.get("specialties")))
            logo_file = st.file_uploader("Upload logo", type=["png","jpg","jpeg","webp"])
            banner_file = st.file_uploader("Upload banner", type=["png","jpg","jpeg","webp"])
            logo_url = st.text_input("Logo URL or saved path", value=safe(seller.get("logo_url")))
            banner_url = st.text_input("Banner URL or saved path", value=safe(seller.get("banner_url")))
            submitted = st.form_submit_button("Save Profile")
        if submitted:
            logo = save_uploaded_file(logo_file, "seller_logos") or logo_url
            banner = save_uploaded_file(banner_file, "seller_banners") or banner_url
            run_sql("UPDATE sellers SET store_name=?, store_bio=?, seller_story=?, specialties=?, logo_url=?, banner_url=? WHERE id=?", (store_name, bio, story, specialties, logo, banner, seller_id))
            st.success("Profile saved.")
    with tabs[1]:
        with st.form("product_upload"):
            artist = st.text_input("Artist / Brand")
            title = st.text_input("Title / Product")
            category = st.selectbox("Category", ["Vinyl Records","CDs","Cassettes","Clothing","Music Memorabilia","Culture Goods"])
            fmt = st.text_input("Format", value="Vinyl")
            genre = st.text_input("Genre")
            media_grade = st.selectbox("Grade", ["Mint","Near Mint","VG+","VG","Good","Used","New","N/A"])
            sleeve_grade = st.selectbox("Sleeve/Packaging", ["Mint","Near Mint","VG+","VG","Good","Used","New","N/A"])
            notes = st.text_area("Condition notes")
            price = st.number_input("Price", min_value=0.0, step=0.01)
            quantity = st.number_input("Quantity", min_value=1, value=1)
            shipping = st.number_input("Shipping", min_value=0.0, step=0.01)
            image_file = st.file_uploader("Product image", type=["png","jpg","jpeg","webp"])
            image_url = st.text_input("Or image URL")
            description = st.text_area("Description")
            submitted = st.form_submit_button("Upload Product")
        if submitted:
            image = save_uploaded_file(image_file, "product_images") or image_url
            desc = description or generate_description({"artist":artist,"title":title,"format":fmt,"genre":genre,"media_grade":media_grade,"sleeve_grade":sleeve_grade,"condition_notes":notes})
            run_sql("""
                INSERT INTO products (seller_id,category,artist,title,format,genre,media_grade,sleeve_grade,condition_notes,description,price,quantity,shipping_price,image_url,listing_status,listing_type,created_at,updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?, 'Active','Fixed Price',?,?)
            """, (seller_id, category, artist, title, fmt, genre, media_grade, sleeve_grade, notes, desc, float(price), int(quantity), float(shipping), image, now(), now()))
            st.success("Product uploaded and active.")
    with tabs[2]:
        csv = st.file_uploader("CSV product import", type=["csv"])
        if csv is not None:
            df = pd.read_csv(csv)
            st.dataframe(df, use_container_width=True)
            if st.button("Import CSV"):
                count = 0
                for _, r in df.iterrows():
                    run_sql("""
                        INSERT INTO products (seller_id,category,artist,title,format,genre,description,price,quantity,shipping_price,image_url,listing_status,listing_type,created_at,updated_at)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,'Active','Fixed Price',?,?)
                    """, (seller_id, safe(r.get("category"),"Vinyl Records"), safe(r.get("artist")), safe(r.get("title")), safe(r.get("format"),"Vinyl"), safe(r.get("genre")), safe(r.get("description")), float(r.get("price",0) or 0), int(r.get("quantity",1) or 1), float(r.get("shipping_price",0) or 0), safe(r.get("image_url")), now(), now()))
                    count += 1
                st.success(f"Imported {count} products.")
    with tabs[3]:
        products = get_df("SELECT * FROM products WHERE seller_id=?", (seller_id,))
        st.dataframe(products, use_container_width=True)
        if not products.empty:
            product_id = st.selectbox("Product", products["id"].tolist())
            gallery_file = st.file_uploader("Gallery image", type=["png","jpg","jpeg","webp"])
            gallery_url = st.text_input("Or gallery image URL")
            caption = st.text_input("Caption")
            if st.button("Add Gallery Image"):
                img = save_uploaded_file(gallery_file, "product_gallery") or gallery_url
                if img:
                    run_sql("INSERT INTO product_gallery (product_id,image_url,caption,created_at) VALUES (?,?,?,?)", (int(product_id), img, caption, now()))
                    st.success("Gallery image added.")
    with tabs[4]:
        products = get_df("SELECT * FROM products WHERE seller_id=? ORDER BY created_at DESC", (seller_id,))
        st.dataframe(products, use_container_width=True)
        if not products.empty:
            product_id = st.selectbox("Product ID", products["id"].tolist(), key="listing_id")
            status = st.selectbox("Status", ["Active","Draft","Sold","Removed"])
            if st.button("Update Listing"):
                run_sql("UPDATE products SET listing_status=?, updated_at=? WHERE id=? AND seller_id=?", (status, now(), int(product_id), seller_id))
                st.success("Updated.")
    with tabs[5]:
        orders = get_df("SELECT * FROM orders WHERE seller_id=? ORDER BY created_at DESC", (seller_id,))
        st.dataframe(orders, use_container_width=True)
        if not orders.empty:
            order_id = st.selectbox("Order", orders["id"].tolist())
            status = st.selectbox("Order status", ["New","Contacted","Invoice Sent","Paid","Shipped","Completed","Cancelled","Disputed"])
            if st.button("Update Order"):
                run_sql("UPDATE orders SET status=?, updated_at=? WHERE id=? AND seller_id=?", (status, now(), int(order_id), seller_id))
                if status == "Completed":
                    order = orders[orders["id"] == order_id].iloc[0]
                    run_sql("UPDATE sellers SET completed_sales=completed_sales+1 WHERE id=?", (seller_id,))
                    run_sql("UPDATE buyers SET completed_purchases=completed_purchases+1 WHERE id=?", (int(order["buyer_id"]),))
                st.success("Order updated.")
    with tabs[6]:
        messages = get_df("SELECT * FROM messages WHERE seller_id=? ORDER BY created_at DESC", (seller_id,))
        st.dataframe(messages, use_container_width=True)
        if not messages.empty:
            msg_id = st.selectbox("Message ID", messages["id"].tolist())
            if st.button("Mark Responded"):
                run_sql("UPDATE messages SET status='Responded' WHERE id=?", (int(msg_id),))
                st.success("Marked responded.")
    with tabs[7]:
        with st.form("announcement"):
            title = st.text_input("Announcement title")
            body = st.text_area("Announcement body")
            submitted = st.form_submit_button("Post Announcement")
        if submitted:
            run_sql("INSERT INTO store_announcements (seller_id,title,body,status,created_at) VALUES (?,?,?,'Active',?)", (seller_id, title, body, now()))
            st.success("Announcement posted.")
        st.dataframe(get_df("SELECT * FROM store_announcements WHERE seller_id=?", (seller_id,)), use_container_width=True)
    with tabs[8]:
        with st.form("event"):
            title = st.text_input("Drop/Event title")
            event_type = st.selectbox("Type", ["Record Drop","Auction Drop","Sale","Live Event","Other"])
            date = st.text_input("Date")
            description = st.text_area("Description")
            submitted = st.form_submit_button("Save Event")
        if submitted:
            run_sql("INSERT INTO seller_events (seller_id,event_title,event_type,event_date,description,status,created_at) VALUES (?,?,?,?,?,'Active',?)", (seller_id, title, event_type, date, description, now()))
            st.success("Event saved.")
        st.dataframe(get_df("SELECT * FROM seller_events WHERE seller_id=?", (seller_id,)), use_container_width=True)
    with tabs[9]:
        st.write(seller_badges_text(seller_id) or "No badges yet.")
    with tabs[10]:
        st.dataframe(get_df("SELECT * FROM feedback WHERE reviewee_type='Seller' AND reviewee_id=?", (seller_id,)), use_container_width=True)


def auctions_page():
    render_header()
    st.header("Auctions")
    st.info("Testing mode: auction access is unlocked.")
    seller_id = choose_seller("auction_create")
    products = get_df("SELECT * FROM products WHERE seller_id=? AND listing_status IN ('Active','Draft')", (seller_id,)) if seller_id else pd.DataFrame()
    if seller_id and not products.empty:
        with st.form("auction_create_form"):
            product_id = st.selectbox("Product", products["id"].tolist())
            title = st.text_input("Auction title")
            start = st.number_input("Starting bid", min_value=0.0, step=1.0)
            end = st.text_input("End time")
            submitted = st.form_submit_button("Create Live Auction")
        if submitted:
            run_sql("INSERT INTO auctions (product_id,seller_id,auction_title,starting_bid,bid_increment,end_time,status,created_at) VALUES (?,?,?,?,1,?,'Live',?)", (int(product_id), int(seller_id), title, float(start), end, now()))
            st.success("Auction created.")
    st.dataframe(get_table("auctions"), use_container_width=True)


def culture_page():
    render_header()
    st.header("Music + Culture")
    posts = get_df("SELECT * FROM culture_posts WHERE status='Published' ORDER BY created_at DESC")
    if posts.empty:
        st.info("No posts yet.")
    for _, p in posts.iterrows():
        with st.container(border=True):
            if safe(p.get("image_url")):
                st.image(safe(p.get("image_url")), use_container_width=True)
            st.subheader(safe(p.get("title")))
            st.caption(f"{safe(p.get('category'))} • {safe(p.get('author'))}")
            st.write(safe(p.get("body")))


def admin_page():
    render_header()
    st.header("Admin")
    password = st.text_input("Admin password", type="password")
    if not st.button("Login Admin"):
        return
    if ADMIN_PASSWORD and password != ADMIN_PASSWORD:
        st.error("Wrong password.")
        return
    if not ADMIN_PASSWORD:
        st.warning("No admin password set. Test mode allows admin entry.")
    admin_workspace()


def admin_workspace():
    tabs = st.tabs(["Overview","Approve Sellers","Community Tools","Reports","Testing Cleanup"])
    with tabs[0]:
        st.metric("Buyers", len(get_table("buyers")))
        st.metric("Sellers", len(get_table("sellers")))
        st.metric("Products", len(get_table("products")))
        st.metric("Orders", len(get_table("orders")))
    with tabs[1]:
        sellers = get_table("sellers")
        st.dataframe(sellers, use_container_width=True)
        if not sellers.empty:
            seller_id = st.selectbox("Seller ID", sellers["id"].tolist())
            status = st.selectbox("Status", ["Approved","Pending","Verified","Suspended","Rejected"])
            if st.button("Update Seller Status"):
                level = "Verified Seller" if status in ["Approved","Verified"] else "Starter Seller"
                run_sql("UPDATE sellers SET status=?, seller_level=?, auction_override='Yes' WHERE id=?", (status, level, int(seller_id)))
                seller = get_seller(seller_id)
                run_sql("INSERT INTO seller_notifications (seller_id,subject,message,status,created_at) VALUES (?,?,?,'Unread',?)", (int(seller_id), "Seller store approved", approval_message(seller), now()))
                st.success("Seller status updated.")
    with tabs[2]:
        sellers = get_table("sellers")
        if sellers.empty:
            st.info("No sellers yet.")
        else:
            seller_id = st.selectbox("Seller", sellers["id"].tolist(), key="community_seller")
            badge = st.text_input("Badge", placeholder="Soul Specialist, Jazz Dealer, Verified Seller")
            if st.button("Add Badge"):
                run_sql("INSERT INTO seller_badges (seller_id,badge_name,badge_type,active,created_at) VALUES (?,?,?,'Yes',?)", (int(seller_id), badge, "Community", now()))
                st.success("Badge added.")
            if st.button("Create Seller Spotlight"):
                create_seller_spotlight_post(int(seller_id))
                st.success("Seller spotlight created.")
            st.write("Messages")
            st.dataframe(get_table("messages"), use_container_width=True)
            st.write("Followers")
            st.dataframe(get_table("seller_followers"), use_container_width=True)
    with tabs[3]:
        report = st.selectbox("Report", ["buyers","sellers","products","orders","messages","seller_followers","seller_badges","store_announcements","seller_events","product_gallery","feedback","favorites","auctions","culture_posts"])
        data = get_table(report)
        st.dataframe(data, use_container_width=True)
        st.download_button("Download CSV", data.to_csv(index=False), file_name=f"{report}.csv")
    with tabs[4]:
        st.warning("Testing cleanup deletes data.")
        table_name = st.selectbox("Table", ["buyers","sellers","products","orders","messages","seller_followers","seller_badges","store_announcements","seller_events","product_gallery","feedback","favorites","auctions","culture_posts"])
        data = get_table(table_name)
        st.dataframe(data, use_container_width=True)
        if not data.empty:
            row_id = st.selectbox("Row ID", data["id"].tolist())
            confirm = st.checkbox("Confirm delete")
            if st.button("Delete Row") and confirm:
                delete_by_id(table_name, row_id)
                st.success("Deleted.")


# -----------------------------
# Navigation
# -----------------------------
menu = st.sidebar.radio("House Of Wax", [
    "Home",
    "Test Setup",
    "Marketplace",
    "Auctions",
    "Seller Stores",
    "Music + Culture",
    "Register / Sell",
    "Buyer Dashboard",
    "Seller Dashboard",
    "Admin Login",
])

if menu == "Home":
    home_page()
elif menu == "Test Setup":
    test_setup_page()
elif menu == "Marketplace":
    marketplace_page()
elif menu == "Auctions":
    auctions_page()
elif menu == "Seller Stores":
    seller_stores_page()
elif menu == "Music + Culture":
    culture_page()
elif menu == "Register / Sell":
    register_page()
elif menu == "Buyer Dashboard":
    buyer_dashboard_page()
elif menu == "Seller Dashboard":
    seller_dashboard_page()
elif menu == "Admin Login":
    admin_page()
