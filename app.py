
import sqlite3
from pathlib import Path
from datetime import datetime
import pandas as pd
import streamlit as st

st.set_page_config(page_title="House Of Wax Marketplace", page_icon="🎧", layout="wide")

APP_VERSION = "V15.6 COMMUNITY MOMENTUM PATCH"
APP_NAME = "House Of Wax"
DB = Path("house_of_wax_v15_5.db")
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
        CREATE TABLE IF NOT EXISTS product_gallery (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            image_url TEXT,
            caption TEXT,
            created_at TEXT
        )
    """)

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


def get_setting(key, default=""):
    df = get_df("SELECT value FROM settings WHERE key = ?", (key,))
    if df.empty:
        return default
    return safe(df.iloc[0]["value"], default)


def save_setting(key, value):
    run_sql("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))


def email_exists(table_name, email):
    if not email:
        return False
    df = get_df(f"SELECT id FROM {table_name} WHERE lower(email)=lower(?)", (email.strip(),))
    return not df.empty


def delete_by_id(table_name, row_id):
    run_sql(f"DELETE FROM {table_name} WHERE id = ?", (int(row_id),))


def save_uploaded_file(uploaded_file, folder_name):
    if uploaded_file is None:
        return ""
    folder = MEDIA_DIR / folder_name
    folder.mkdir(parents=True, exist_ok=True)
    safe_name = uploaded_file.name.replace(" ", "_").replace("/", "_")
    path = folder / f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{safe_name}"
    path.write_bytes(uploaded_file.getbuffer())
    return str(path)


def calculate_fee(total, auction=False):
    key = "auction_commission_percent" if auction else "platform_commission_percent"
    pct = float(get_setting(key, "9"))
    return round(float(total) * pct / 100, 2)


# -----------------------------
# Database
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
        CREATE TABLE IF NOT EXISTS social_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            seller_id INTEGER,
            platform TEXT,
            caption TEXT,
            hashtags TEXT,
            status TEXT DEFAULT 'Draft',
            created_at TEXT,
            posted_at TEXT
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

    defaults = {
        "logo_url": "",
        "site_tagline": "A seller-powered marketplace for records, music culture, clothing, and collectors.",
        "announcement": "Sellers run their own stores. Buyers are accountable. House Of Wax protects the platform.",
        "platform_commission_percent": "9",
        "auction_commission_percent": "10",
        "auction_min_completed_sales": "10",
        "auction_min_rating": "90",
        "default_processing_time": "3 business days",
        "buyer_payment_window_hours": "48",
        "storefront_url": "https://record-store-manager-nsgwoj39v4rgxphhxcrgqn.streamlit.app/",
    }

    for key, value in defaults.items():
        if get_df("SELECT key FROM settings WHERE key = ?", (key,)).empty:
            run_sql("INSERT INTO settings (key, value) VALUES (?, ?)", (key, value))

    if get_table("platform_rules").empty:
        starter_rules = [
            ("Seller policies cannot weaken platform rules", "Seller Rules", "Sellers may create their own policies, but they cannot reduce required marketplace protections."),
            ("Buyers must be accountable", "Buyer Rules", "Buyers must pay for commitments, communicate respectfully, and not abuse disputes or returns."),
            ("No prohibited or counterfeit items", "Listings", "Counterfeit, stolen, illegal, hateful, or misleading items may be removed."),
            ("Auctions are earned", "Auctions", "Sellers must meet performance requirements or receive admin override to use auctions."),
            ("Community standard", "Community", "House Of Wax is a music and culture community. Buyers and sellers are expected to respect each other.")
        ]
        for title, category, rule_text in starter_rules:
            run_sql(
                "INSERT INTO platform_rules (title, category, rule_text, active, created_at) VALUES (?, ?, ?, 'Yes', ?)",
                (title, category, rule_text, now())
            )


setup_database()


# -----------------------------
# Data helpers
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


def recalculate_rating(reviewee_type, reviewee_id):
    df = get_df("SELECT AVG(rating) AS avg_rating FROM feedback WHERE reviewee_type = ? AND reviewee_id = ?", (reviewee_type, int(reviewee_id)))
    avg = df.iloc[0]["avg_rating"]
    if pd.isna(avg):
        return
    score = round(float(avg) * 20, 1)
    if reviewee_type == "Seller":
        run_sql("UPDATE sellers SET rating = ? WHERE id = ?", (score, int(reviewee_id)))
    elif reviewee_type == "Buyer":
        run_sql("UPDATE buyers SET rating = ? WHERE id = ?", (score, int(reviewee_id)))


def buyer_allowed(buyer):
    if buyer is None:
        return False, "A registered buyer account is required."
    if buyer["status"] in ["Restricted Buyer", "Suspended Buyer"]:
        return False, "This buyer account is restricted."
    if int(buyer["unpaid_orders"] or 0) >= 3:
        return False, "This buyer has too many unpaid orders."
    return True, "Buyer allowed."


def auction_eligible(seller):
    if seller is None:
        return False, "Seller not found."
    if seller["status"] != "Approved":
        return False, "Seller must be approved first."
    if seller["auction_override"] == "Yes":
        return True, "Auction access approved by House Of Wax Admin."
    min_sales = int(float(get_setting("auction_min_completed_sales", "10")))
    min_rating = float(get_setting("auction_min_rating", "90"))
    if int(seller["completed_sales"] or 0) < min_sales:
        return False, f"Needs at least {min_sales} completed sales."
    if float(seller["rating"] or 0) < min_rating:
        return False, f"Needs at least {min_rating}% seller rating."
    if int(seller["strikes"] or 0) > 0:
        return False, "Seller must have no strikes or receive admin override."
    if int(seller["disputes"] or 0) > 0:
        return False, "Seller must have no disputes or receive admin override."
    return True, "Seller meets auction requirements."


def auction_progress(seller):
    min_sales = int(float(get_setting("auction_min_completed_sales", "10")))
    min_rating = float(get_setting("auction_min_rating", "90"))
    return {
        "Completed sales": (int(seller["completed_sales"] or 0), min_sales, int(seller["completed_sales"] or 0) >= min_sales),
        "Seller rating": (float(seller["rating"] or 0), min_rating, float(seller["rating"] or 0) >= min_rating),
        "Strikes": (int(seller["strikes"] or 0), 0, int(seller["strikes"] or 0) == 0),
        "Disputes": (int(seller["disputes"] or 0), 0, int(seller["disputes"] or 0) == 0),
    }


def generate_description(data):
    artist = safe(data.get("artist"), "This listing")
    title = safe(data.get("title"))
    fmt = safe(data.get("format"), "music/culture item")
    genre = safe(data.get("genre"))
    label = safe(data.get("label"))
    year = safe(data.get("release_year"))
    media_grade = safe(data.get("media_grade"), "not specified")
    sleeve_grade = safe(data.get("sleeve_grade"), "N/A")
    barcode = safe(data.get("barcode"))
    catalog = safe(data.get("catalog_number"))
    matrix = safe(data.get("matrix_runout"))
    notes = safe(data.get("condition_notes"))

    text = f"{artist} — {title} is listed on House Of Wax as a curated {fmt} marketplace item."
    if genre:
        text += f" It is a strong fit for buyers interested in {genre}, collecting, and music culture."
    if label or year:
        text += f" Release details include {label or 'the listed label'}"
        if year:
            text += f" from {year}"
        text += "."
    text += f" Condition is listed as media/product grade {media_grade}, with sleeve or packaging grade {sleeve_grade}."
    ids = []
    if barcode:
        ids.append(f"barcode {barcode}")
    if catalog:
        ids.append(f"catalog number {catalog}")
    if matrix:
        ids.append(f"matrix/runout {matrix}")
    if ids:
        text += " Key identifiers include " + ", ".join(ids) + "."
    if notes:
        text += f" Seller notes: {notes}"
    text += " Buyers should review photos, grading notes, seller policies, shipping terms, and House Of Wax marketplace rules before buying or bidding."
    return text


def listing_score(product):
    checks = {
        "price": float(product.get("price") or 0) > 0,
        "image or media": bool(safe(product.get("image_url")) or safe(product.get("video_url")) or safe(product.get("audio_url"))),
        "condition": bool(safe(product.get("media_grade")) or safe(product.get("condition_notes"))),
        "description": len(safe(product.get("description"))) > 100,
        "identifier": bool(safe(product.get("barcode")) or safe(product.get("catalog_number")) or safe(product.get("matrix_runout"))),
        "category": bool(safe(product.get("category"))),
        "active": safe(product.get("listing_status")) == "Active",
    }
    return int(sum(checks.values()) / len(checks) * 100)


def approval_email_template(seller):
    url = get_setting("storefront_url", "")
    return f"""Subject: Your House Of Wax seller store has been approved

Hi {safe(seller.get('owner_name'), 'there')},

Good news — your House Of Wax seller store, {safe(seller.get('store_name'))}, has been approved.

You can now log in to your Seller Dashboard using your seller email and access code. From there, you can build your store profile, upload your logo and banner, write your seller policies, and start adding products.

Seller Dashboard:
{url}

Next steps:
1. Log in to the Seller Dashboard.
2. Upload your store logo and banner.
3. Complete your seller profile and story.
4. Add your shipping, return, grading, and buyer requirement policies.
5. Upload your first products.

Remember: your seller rules can be stronger than House Of Wax rules, but never weaker.

Welcome to the House Of Wax community.

House Of Wax Team
"""




def get_seller_badges(seller_id):
    badges = get_df("SELECT * FROM seller_badges WHERE seller_id=? AND active='Yes' ORDER BY created_at DESC", (int(seller_id),))
    if badges.empty:
        return ""
    return " • ".join([safe(x) for x in badges["badge_name"].tolist()])


def follower_count(seller_id):
    df = get_df("SELECT COUNT(*) AS count FROM seller_followers WHERE seller_id=?", (int(seller_id),))
    if df.empty:
        return 0
    return int(df.iloc[0]["count"] or 0)


def send_message(product_id, seller_id, buyer_id, sender_type, subject, message):
    run_sql("""
        INSERT INTO messages (product_id, seller_id, buyer_id, sender_type, subject, message, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, 'New', ?)
    """, (product_id, seller_id, buyer_id, sender_type, subject, message, now()))


def create_seller_spotlight(seller_id):
    seller = get_seller(seller_id)
    if seller is None:
        return False
    title = f"Seller Spotlight: {safe(seller.get('store_name'))}"
    body = f"""Meet {safe(seller.get('store_name'))}, part of the House Of Wax seller community.

{safe(seller.get('seller_story'), safe(seller.get('store_bio'), 'This seller is building their presence on House Of Wax.'))}

Specialties: {safe(seller.get('specialties'), 'Music, culture, and collector goods.')}

House Of Wax is built to help buyers connect with the people behind the products, not just the listings."""
    image = safe(seller.get("banner_url")) or safe(seller.get("logo_url"))
    run_sql("""
        INSERT INTO culture_posts (title, category, author, body, image_url, status, created_at)
        VALUES (?, 'Seller Spotlight', 'House Of Wax', ?, ?, 'Published', ?)
    """, (title, body, image, now()))
    return True

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

    if announcement:
        st.info(announcement)


def choose_buyer(key_prefix):
    buyers = get_table("buyers")
    if buyers.empty:
        st.warning("No buyers registered yet. Register as a buyer first.")
        return None
    options = []
    for _, row in buyers.iterrows():
        label = f"{int(row['id'])} | {safe(row['name'])} | {safe(row['email'])} | {safe(row['status'])} | Rating {row['rating']}%"
        options.append(label)
    selected = st.selectbox("Buyer account", options, key=f"{key_prefix}_buyer")
    return int(selected.split("|")[0].strip())


def seller_card(seller):
    with st.container(border=True):
        banner = safe(seller.get("banner_url"))
        if banner:
            st.image(banner, use_container_width=True)
        col1, col2 = st.columns([1, 4])
        with col1:
            logo = safe(seller.get("logo_url"))
            if logo:
                st.image(logo, use_container_width=True)
            else:
                st.markdown("### 🏪")
        with col2:
            st.subheader(safe(seller.get("store_name")))
            st.caption(f"{safe(seller.get('seller_level'))} • Rating {seller['rating']}% • Sales {seller['completed_sales']} • Followers {follower_count(int(seller['id']))}")
            badges = get_seller_badges(int(seller["id"]))
            if badges:
                st.caption(f"Badges: {badges}")
            st.write(safe(seller.get("store_bio"), "Independent seller on House Of Wax."))
            if st.button("View Seller Profile", key=f"view_seller_{int(seller['id'])}"):
                st.session_state["selected_seller_id"] = int(seller["id"])
                st.rerun()


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
        st.write(f"**Condition:** {safe(product.get('media_grade'), 'Not graded')}")
        st.progress(listing_score(product) / 100, text=f"Listing quality: {listing_score(product)}/100")

        if st.button("View Item", key=f"view_product_{int(product['id'])}"):
            st.session_state["selected_product_id"] = int(product["id"])
            st.rerun()


def seller_profile_page(seller_id):
    seller = get_seller(seller_id)
    if seller is None:
        st.error("Seller not found.")
        return

    if st.button("← Back to Seller Stores"):
        if "selected_seller_id" in st.session_state:
            del st.session_state["selected_seller_id"]
        st.rerun()

    banner = safe(seller.get("banner_url"))
    if banner:
        st.image(banner, use_container_width=True)

    col1, col2 = st.columns([1, 4])
    with col1:
        logo = safe(seller.get("logo_url"))
        if logo:
            st.image(logo, use_container_width=True)
        else:
            st.markdown("## 🏪")
    with col2:
        st.title(safe(seller.get("store_name")))
        verified = "✅ Verified Seller" if safe(seller.get("status")) in ["Verified", "Approved"] and float(seller["rating"] or 0) >= 95 else safe(seller.get("seller_level"))
        st.caption(f"{verified} • Rating {seller['rating']}% • Sales {seller['completed_sales']} • Followers {follower_count(int(seller['id']))}")
        badges = get_seller_badges(int(seller["id"]))
        if badges:
            st.caption(f"Community badges: {badges}")
        location = " ".join([safe(seller.get("city")), safe(seller.get("state"))]).strip()
        if location:
            st.caption(location)
        if safe(seller.get("instagram")):
            st.write(f"Instagram: {safe(seller.get('instagram'))}")
        if safe(seller.get("website")):
            st.link_button("Seller Website", safe(seller.get("website")))

    with st.expander("Follow this seller"):
        buyer_id = choose_buyer(f"follow_seller_{int(seller['id'])}")
        if st.button("Follow Seller", key=f"follow_btn_{int(seller['id'])}"):
            if buyer_id:
                existing = get_df("SELECT id FROM seller_followers WHERE seller_id=? AND buyer_id=?", (int(seller["id"]), int(buyer_id)))
                if existing.empty:
                    run_sql("INSERT INTO seller_followers (seller_id, buyer_id, created_at) VALUES (?, ?, ?)", (int(seller["id"]), int(buyer_id), now()))
                    st.success("Seller followed.")
                else:
                    st.info("This buyer already follows this seller.")

    announcements = get_df("SELECT * FROM store_announcements WHERE seller_id=? AND status='Active' ORDER BY created_at DESC", (int(seller["id"]),))
    if not announcements.empty:
        st.subheader("Store Announcements")
        for _, ann in announcements.iterrows():
            with st.container(border=True):
                st.write(f"**{safe(ann.get('title'))}**")
                st.write(safe(ann.get("body")))

    events = get_df("SELECT * FROM seller_events WHERE seller_id=? AND status='Active' ORDER BY event_date", (int(seller["id"]),))
    if not events.empty:
        st.subheader("Upcoming Drops / Events")
        for _, ev in events.iterrows():
            with st.container(border=True):
                st.write(f"**{safe(ev.get('event_title'))}** — {safe(ev.get('event_type'))}")
                st.caption(safe(ev.get("event_date")))
                st.write(safe(ev.get("description")))

    st.subheader("About This Seller")
    st.write(safe(seller.get("seller_story"), safe(seller.get("store_bio"), "This seller has not added a full story yet.")))

    if safe(seller.get("specialties")):
        st.subheader("Specialties")
        st.write(safe(seller.get("specialties")))

    with st.expander("Seller Policies"):
        policies = get_df("SELECT * FROM seller_policies WHERE seller_id = ?", (seller_id,))
        if policies.empty:
            st.info("This seller has not completed detailed policies yet. House Of Wax platform rules still apply.")
        else:
            p = policies.iloc[0]
            st.write("**Shipping:**", safe(p.get("shipping_policy"), "Not provided"))
            st.write("**Returns:**", safe(p.get("return_policy"), "Not provided"))
            st.write("**Grading:**", safe(p.get("grading_policy"), "Not provided"))
            st.write("**Buyer Requirements:**", safe(p.get("buyer_requirements"), "Not provided"))

    st.subheader("Seller Feedback")
    feedback = get_df("""
        SELECT f.*, b.name AS buyer_name
        FROM feedback f
        LEFT JOIN buyers b ON f.reviewer_id = b.id
        WHERE f.reviewee_type = 'Seller' AND f.reviewee_id = ?
        ORDER BY f.created_at DESC
    """, (seller_id,))
    if feedback.empty:
        st.info("No seller feedback yet.")
    else:
        for _, row in feedback.iterrows():
            with st.container(border=True):
                st.write(f"⭐ {row['rating']} / 5 from {safe(row.get('buyer_name'), 'Buyer')}")
                st.write(safe(row.get("comment")))

    st.subheader("Listings from this Seller")
    products = get_df("SELECT * FROM products WHERE seller_id = ? AND listing_status = 'Active' ORDER BY created_at DESC", (seller_id,))
    if products.empty:
        st.info("This seller has no active listings yet.")
    else:
        cols = st.columns(3)
        for idx, (_, product) in enumerate(products.iterrows()):
            with cols[idx % 3]:
                product_card(product)


def product_detail(product):
    if st.button("← Back to Marketplace"):
        if "selected_product_id" in st.session_state:
            del st.session_state["selected_product_id"]
        st.rerun()

    seller = get_seller(product["seller_id"])

    left, right = st.columns([1.2, 1])
    with left:
        image = safe(product.get("image_url"))
        video = safe(product.get("video_url"))
        audio = safe(product.get("audio_url"))
        if image:
            st.image(image, use_container_width=True)
        elif video:
            st.video(video)
        else:
            st.markdown("## 🎵")
        if audio:
            st.audio(audio)
        gallery = get_df("SELECT * FROM product_gallery WHERE product_id=? ORDER BY created_at DESC", (int(product["id"]),))
        if not gallery.empty:
            st.subheader("Product Gallery")
            for _, img in gallery.iterrows():
                if safe(img.get("image_url")):
                    st.image(safe(img.get("image_url")), caption=safe(img.get("caption")), use_container_width=True)

    with right:
        st.header(f"{safe(product.get('artist'))} — {safe(product.get('title'))}")
        st.write(f"**Price:** {money(product.get('price'))}")
        st.write(f"**Shipping:** {money(product.get('shipping_price'))}")
        if seller is not None:
            st.write(f"**Seller:** {safe(seller['store_name'])}")
            st.caption(f"Seller rating: {seller['rating']}% • Sales: {seller['completed_sales']} • Level: {seller['seller_level']}")
            if st.button("View Seller Profile", key=f"profile_from_product_{int(product['id'])}"):
                st.session_state["selected_seller_id"] = int(seller["id"])
                st.session_state.pop("selected_product_id", None)
                st.rerun()
        st.write(f"**Category:** {safe(product.get('category'))}")
        st.write(f"**Format:** {safe(product.get('format'))}")
        st.write(f"**Condition:** {safe(product.get('media_grade'), 'N/A')} / Sleeve-Packaging: {safe(product.get('sleeve_grade'), 'N/A')}")

    st.subheader("Description")
    desc = safe(product.get("description"))
    st.write(desc if desc else generate_description(product))

    if seller is not None:
        with st.expander("Seller Store Policies"):
            policies = get_df("SELECT * FROM seller_policies WHERE seller_id = ?", (int(seller["id"]),))
            if policies.empty:
                st.info("This seller has not added detailed policies yet. House Of Wax minimum platform rules still apply.")
            else:
                p = policies.iloc[0]
                st.write("**Shipping:**", safe(p.get("shipping_policy"), "Not provided"))
                st.write("**Returns:**", safe(p.get("return_policy"), "Not provided"))
                st.write("**Grading:**", safe(p.get("grading_policy"), "Not provided"))
                st.write("**Buyer Requirements:**", safe(p.get("buyer_requirements"), "Not provided"))

    st.divider()
    st.subheader("Buy / Contact Seller")
    buyer_id = choose_buyer(f"buy_{int(product['id'])}")
    action = st.selectbox("Action", ["Request to Buy", "Ask a Question", "Make Offer"], key=f"action_{int(product['id'])}")
    message = st.text_area("Message to seller", key=f"message_{int(product['id'])}")
    agree = st.checkbox("I reviewed the listing, condition notes, shipping terms, and seller store policies.", key=f"agree_{int(product['id'])}")
    st.caption("This is not payment yet. The seller will contact the buyer to complete payment and shipping.")

    if st.button("Submit to Seller", key=f"submit_{int(product['id'])}"):
        if buyer_id is None:
            st.error("Register as a buyer first.")
        elif not agree:
            st.error("Please confirm that you reviewed the listing and seller policies.")
        else:
            buyer = get_buyer(buyer_id)
            allowed, reason = buyer_allowed(buyer)
            if action == "Request to Buy" and not allowed:
                st.error(reason)
            else:
                item = float(product.get("price") or 0)
                ship = float(product.get("shipping_price") or 0)
                fee = calculate_fee(item + ship)
                run_sql("""
                    INSERT INTO orders
                    (product_id, seller_id, buyer_id, order_type, status, item_price, shipping_price, platform_fee, seller_payout, buyer_message, created_at, updated_at)
                    VALUES (?, ?, ?, ?, 'New', ?, ?, ?, ?, ?, ?, ?)
                """, (int(product["id"]), int(product["seller_id"]), int(buyer_id), action, item, ship, fee, item + ship - fee, message, now(), now()))
                st.success("Sent to seller.")

    with st.expander("Message seller about this item"):
        msg_buyer_id = choose_buyer(f"message_seller_{int(product['id'])}")
        subject = st.text_input("Subject", value=f"Question about {safe(product.get('artist'))} - {safe(product.get('title'))}", key=f"msg_subject_{int(product['id'])}")
        direct_msg = st.text_area("Message", key=f"direct_msg_{int(product['id'])}")
        if st.button("Send Message", key=f"send_msg_{int(product['id'])}"):
            if msg_buyer_id:
                send_message(int(product["id"]), int(product["seller_id"]), int(msg_buyer_id), "Buyer", subject, direct_msg)
                st.success("Message sent to seller.")

    with st.expander("Save / Favorite this item"):
        fav_buyer_id = choose_buyer(f"favorite_{int(product['id'])}")
        if st.button("Save Item", key=f"save_item_{int(product['id'])}"):
            if fav_buyer_id:
                run_sql("INSERT INTO favorites (buyer_id, item_type, item_id, created_at) VALUES (?, 'Product', ?, ?)", (int(fav_buyer_id), int(product["id"]), now()))
                st.success("Item saved.")

    with st.expander("Report this listing"):
        reason = st.selectbox("Report reason", ["Counterfeit / Bootleg", "Misgraded Condition", "Wrong Information", "Offensive Content", "Spam / Scam", "Prohibited Item", "Other"], key=f"flag_reason_{int(product['id'])}")
        details = st.text_area("Details", key=f"flag_details_{int(product['id'])}")
        flag_buyer_id = choose_buyer(f"flag_{int(product['id'])}")
        if st.button("Submit Listing Report", key=f"flag_button_{int(product['id'])}"):
            if flag_buyer_id:
                run_sql("""
                    INSERT INTO listing_flags (product_id, seller_id, buyer_id, reason, details, status, created_at)
                    VALUES (?, ?, ?, ?, ?, 'Open', ?)
                """, (int(product["id"]), int(product["seller_id"]), int(flag_buyer_id), reason, details, now()))
                run_sql("UPDATE products SET listing_status = 'Flagged' WHERE id = ?", (int(product["id"]),))
                st.success("Listing reported.")


# -----------------------------
# Public pages
# -----------------------------
def home_page():
    render_header()
    products = get_table("products")
    sellers = get_table("sellers")
    buyers = get_table("buyers")
    auctions = get_table("auctions")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Listings", len(products))
    c2.metric("Sellers", len(sellers))
    c3.metric("Buyers", len(buyers))
    c4.metric("Auctions", len(auctions))
    st.markdown("""
    ## A seller-powered music and culture marketplace.

    House Of Wax is built around community. Sellers get profile pages, storefront identity, policies, feedback, and tools to tell their story. Buyers register, save items, purchase, bid, and leave feedback.
    """)


def marketplace_page():
    render_header()
    st.header("Marketplace")

    if "selected_seller_id" in st.session_state:
        seller_profile_page(int(st.session_state["selected_seller_id"]))
        return

    products = get_df("SELECT * FROM products WHERE listing_status = 'Active' AND quantity > 0 ORDER BY created_at DESC")
    if products.empty:
        st.info("No active marketplace listings yet.")
        return

    if "selected_product_id" in st.session_state:
        selected = products[products["id"] == int(st.session_state["selected_product_id"])]
        if not selected.empty:
            product_detail(selected.iloc[0])
            return
        st.session_state.pop("selected_product_id", None)

    col1, col2, col3 = st.columns(3)
    search = col1.text_input("Search")
    categories = ["All"] + sorted([str(x) for x in products["category"].dropna().unique().tolist() if str(x).strip()])
    category = col2.selectbox("Category", categories)
    sort = col3.selectbox("Sort", ["Newest", "Price Low", "Price High", "Artist A-Z"])

    filtered = products.copy()
    if search:
        term = search.lower()
        mask = (
            filtered["artist"].fillna("").str.lower().str.contains(term) |
            filtered["title"].fillna("").str.lower().str.contains(term) |
            filtered["barcode"].fillna("").str.lower().str.contains(term) |
            filtered["catalog_number"].fillna("").str.lower().str.contains(term)
        )
        filtered = filtered[mask]
    if category != "All":
        filtered = filtered[filtered["category"] == category]
    if sort == "Price Low":
        filtered = filtered.sort_values("price")
    elif sort == "Price High":
        filtered = filtered.sort_values("price", ascending=False)
    elif sort == "Artist A-Z":
        filtered = filtered.sort_values("artist")

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

    sellers = get_df("SELECT * FROM sellers WHERE status = 'Approved' ORDER BY store_name")
    if sellers.empty:
        st.info("No approved seller stores yet.")
        return

    for _, seller in sellers.iterrows():
        seller_card(seller)


def auctions_page():
    render_header()
    st.header("Auctions")
    st.caption("Auctions are earned by seller performance.")

    auctions = get_df("""
        SELECT a.*, p.artist, p.title, p.image_url, s.store_name
        FROM auctions a
        LEFT JOIN products p ON a.product_id = p.id
        LEFT JOIN sellers s ON a.seller_id = s.id
        WHERE a.status = 'Live'
        ORDER BY a.end_time
    """)
    if auctions.empty:
        st.info("No live auctions yet.")
        return

    for _, auction in auctions.iterrows():
        with st.container(border=True):
            if safe(auction.get("image_url")):
                st.image(safe(auction.get("image_url")), width=250)
            st.subheader(safe(auction.get("auction_title")))
            st.caption(f"{safe(auction.get('artist'))} — {safe(auction.get('title'))} • Seller: {safe(auction.get('store_name'))}")
            high = get_df("SELECT MAX(bid_amount) AS high_bid FROM bids WHERE auction_id = ?", (int(auction["id"]),))
            current = float(high.iloc[0]["high_bid"]) if pd.notna(high.iloc[0]["high_bid"]) else float(auction["starting_bid"] or 0)
            st.write(f"**Current bid:** {money(current)}")
            buyer_id = choose_buyer(f"auction_{int(auction['id'])}")
            next_bid = st.number_input("Bid amount", min_value=current + float(auction["bid_increment"] or 1), step=float(auction["bid_increment"] or 1), key=f"bid_{int(auction['id'])}")
            if st.button("Place Bid", key=f"place_bid_{int(auction['id'])}"):
                buyer = get_buyer(buyer_id)
                allowed, reason = buyer_allowed(buyer)
                if not allowed:
                    st.error(reason)
                else:
                    run_sql("INSERT INTO bids (auction_id, buyer_id, bid_amount, bid_time) VALUES (?, ?, ?, ?)", (int(auction["id"]), int(buyer_id), float(next_bid), now()))
                    st.success("Bid placed.")


def culture_page():
    render_header()
    st.header("Music + Culture")
    posts = get_df("SELECT * FROM culture_posts WHERE status='Published' ORDER BY created_at DESC")
    if posts.empty:
        st.info("No culture posts yet. Admin can add seller spotlights, artist stories, collecting guides, and culture posts.")
        return
    for _, post in posts.iterrows():
        with st.container(border=True):
            if safe(post.get("image_url")):
                st.image(safe(post.get("image_url")), use_container_width=True)
            st.subheader(safe(post.get("title")))
            st.caption(f"{safe(post.get('category'))} • {safe(post.get('author'))}")
            st.write(safe(post.get("body")))


def register_page():
    render_header()
    st.header("Register / Sell on House Of Wax")
    buyer_tab, seller_tab = st.tabs(["Buyer Registration", "Create Seller Store Application"])

    with buyer_tab:
        st.subheader("Create Buyer Account")
        with st.form("buyer_registration"):
            name = st.text_input("Full name")
            email = st.text_input("Email")
            phone = st.text_input("Phone")
            city = st.text_input("City")
            submitted = st.form_submit_button("Register Buyer")
        if submitted:
            if not name or not email:
                st.error("Name and email are required.")
            elif email_exists("buyers", email):
                st.warning("This buyer email is already registered. Use the Buyer Dashboard or use a different email.")
            else:
                run_sql("INSERT INTO buyers (name, email, phone, city, created_at) VALUES (?, ?, ?, ?, ?)", (name, email, phone, city, now()))
                st.success("Buyer account created.")

    with seller_tab:
        st.subheader("Create Seller Store Application")
        st.info("This is how sellers create their store. House Of Wax must approve the store before products can be uploaded.")

        with st.form("seller_application"):
            store_name = st.text_input("Store name")
            owner = st.text_input("Owner name")
            email = st.text_input("Seller email")
            phone = st.text_input("Phone")
            city = st.text_input("City")
            state = st.text_input("State")
            instagram = st.text_input("Instagram")
            website = st.text_input("Website")
            bio = st.text_area("Short store bio")
            story = st.text_area("Seller story / why people should know you")
            specialties = st.text_area("Specialties", placeholder="Example: rare soul 45s, jazz LPs, vintage band tees, local Carolina music")
            logo_file = st.file_uploader("Upload store logo", type=["png", "jpg", "jpeg", "webp"], key="apply_logo")
            banner_file = st.file_uploader("Upload store banner", type=["png", "jpg", "jpeg", "webp"], key="apply_banner")
            access_code = st.text_input("Choose private seller access code", type="password")
            agree = st.checkbox("I agree to House Of Wax platform rules. My store policies can be stronger than platform rules, but never weaker.")
            submitted = st.form_submit_button("Submit Seller Store Application")

        if submitted:
            if not store_name or not email or not access_code:
                st.error("Store name, seller email, and access code are required.")
            elif email_exists("sellers", email):
                st.warning("This seller email is already registered or already applied.")
            elif not agree:
                st.error("You must agree to platform rules.")
            else:
                logo_path = save_uploaded_file(logo_file, "seller_logos")
                banner_path = save_uploaded_file(banner_file, "seller_banners")
                run_sql("""
                    INSERT INTO sellers
                    (store_name, owner_name, email, phone, city, state, instagram, website, store_bio, seller_story, specialties, logo_url, banner_url, access_code, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (store_name, owner, email, phone, city, state, instagram, website, bio, story, specialties, logo_path, banner_path, access_code, now()))
                st.success("Seller store application submitted. House Of Wax must approve the store before products can be uploaded. Save your seller email and access code.")


def buyer_dashboard_page():
    render_header()
    st.header("Buyer Dashboard")
    email = st.text_input("Buyer email")
    if not st.button("Open Buyer Dashboard"):
        return

    buyer_df = get_df("SELECT * FROM buyers WHERE lower(email)=lower(?)", (email.strip(),))
    if buyer_df.empty:
        st.error("No buyer found with this email.")
        return
    buyer = buyer_df.iloc[0]
    buyer_id = int(buyer["id"])

    st.success(f"Buyer account: {safe(buyer['name'])}")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Status", safe(buyer["status"]))
    c2.metric("Rating", f"{buyer['rating']}%")
    c3.metric("Completed Purchases", buyer["completed_purchases"])
    c4.metric("Unpaid Orders", buyer["unpaid_orders"])
    c5.metric("Strikes", buyer["strikes"])

    tabs = st.tabs(["Profile", "Purchase Requests", "Bids", "Favorites", "Messages", "Following", "Leave Seller Feedback", "Feedback Received", "Rules"])

    with tabs[0]:
        with st.form("buyer_profile"):
            name = st.text_input("Name", value=safe(buyer["name"]))
            phone = st.text_input("Phone", value=safe(buyer["phone"]))
            city = st.text_input("City", value=safe(buyer["city"]))
            submitted = st.form_submit_button("Update Profile")
        if submitted:
            run_sql("UPDATE buyers SET name=?, phone=?, city=? WHERE id=?", (name, phone, city, buyer_id))
            st.success("Buyer profile updated.")

    with tabs[1]:
        orders = get_df("""
            SELECT o.*, p.artist, p.title, s.store_name
            FROM orders o
            LEFT JOIN products p ON o.product_id = p.id
            LEFT JOIN sellers s ON o.seller_id = s.id
            WHERE o.buyer_id = ?
            ORDER BY o.created_at DESC
        """, (buyer_id,))
        st.dataframe(orders, use_container_width=True)

    with tabs[2]:
        bids = get_df("""
            SELECT b.*, a.auction_title
            FROM bids b
            LEFT JOIN auctions a ON b.auction_id = a.id
            WHERE b.buyer_id = ?
            ORDER BY b.bid_time DESC
        """, (buyer_id,))
        st.dataframe(bids, use_container_width=True)

    with tabs[3]:
        favs = get_df("""
            SELECT f.*, p.artist, p.title, p.price
            FROM favorites f
            LEFT JOIN products p ON f.item_id = p.id
            WHERE f.buyer_id = ? AND f.item_type='Product'
            ORDER BY f.created_at DESC
        """, (buyer_id,))
        st.dataframe(favs, use_container_width=True)

    with tabs[4]:
        completed = get_df("""
            SELECT o.*, p.artist, p.title, s.store_name
            FROM orders o
            LEFT JOIN products p ON o.product_id = p.id
            LEFT JOIN sellers s ON o.seller_id = s.id
            WHERE o.buyer_id = ? AND o.status = 'Completed'
            ORDER BY o.created_at DESC
        """, (buyer_id,))
        if completed.empty:
            st.info("No completed orders available for feedback yet.")
        else:
            order_id = st.selectbox("Completed order", completed["id"].tolist(), key="buyer_feedback_order")
            row = completed[completed["id"] == order_id].iloc[0]
            st.write(f"Reviewing seller: **{safe(row['store_name'])}** for {safe(row['artist'])} — {safe(row['title'])}")
            rating = st.slider("Seller rating", 1, 5, 5, key="seller_rating_slider")
            comment = st.text_area("Feedback comment", key="seller_feedback_comment")
            if st.button("Submit Seller Feedback"):
                existing = get_df("SELECT id FROM feedback WHERE order_id=? AND reviewer_type='Buyer' AND reviewer_id=?", (int(order_id), buyer_id))
                if not existing.empty:
                    st.warning("You already left feedback for this order.")
                else:
                    run_sql("""
                        INSERT INTO feedback (order_id, reviewer_type, reviewer_id, reviewee_type, reviewee_id, rating, comment, created_at)
                        VALUES (?, 'Buyer', ?, 'Seller', ?, ?, ?, ?)
                    """, (int(order_id), buyer_id, int(row["seller_id"]), int(rating), comment, now()))
                    recalculate_rating("Seller", int(row["seller_id"]))
                    st.success("Seller feedback submitted.")

    with tabs[5]:
        received = get_df("""
            SELECT f.*, s.store_name
            FROM feedback f
            LEFT JOIN sellers s ON f.reviewer_id = s.id
            WHERE f.reviewee_type='Buyer' AND f.reviewee_id=?
            ORDER BY f.created_at DESC
        """, (buyer_id,))
        st.dataframe(received, use_container_width=True)

    with tabs[8]:
        st.markdown("Buyers must pay for purchase commitments, communicate respectfully, and avoid false claims or return/dispute abuse.")


# -----------------------------
# Seller dashboard
# -----------------------------
def seller_dashboard_page():
    render_header()
    st.header("Seller Dashboard")
    email = st.text_input("Seller email")
    code = st.text_input("Seller access code", type="password")
    if not st.button("Enter Seller Dashboard"):
        return

    seller_df = get_df("SELECT * FROM sellers WHERE lower(email)=lower(?) AND access_code=?", (email.strip(), code))
    if seller_df.empty:
        st.error("Seller not found or access code is wrong.")
        return

    seller = seller_df.iloc[0]
    seller_id = int(seller["id"])

    st.subheader("Seller Store Status")
    st.write(f"**Store:** {safe(seller['store_name'])}")
    st.write(f"**Status:** {safe(seller['status'])}")

    notes = get_df("SELECT * FROM seller_notifications WHERE seller_id=? ORDER BY created_at DESC", (seller_id,))
    if not notes.empty:
        with st.expander("House Of Wax Messages"):
            st.dataframe(notes, use_container_width=True)

    if seller["status"] != "Approved":
        st.warning("Your store is not approved yet. House Of Wax Admin must approve your store before you can upload products.")
        return

    seller_workspace(seller)


def seller_workspace(seller):
    seller_id = int(seller["id"])
    st.success(f"Logged in as {seller['store_name']}")
    tabs = st.tabs(["My Store Profile", "Store Policies", "Upload Products", "Product Gallery", "Bulk Product Import", "My Listings", "My Auctions", "Orders", "Messages", "Announcements", "Events/Drops", "Leave Buyer Feedback", "Feedback Received", "Social Posts", "Rules"])

    with tabs[0]:
        st.subheader("My Store Profile")
        with st.form("store_profile"):
            store_name = st.text_input("Store name", value=safe(seller.get("store_name")))
            owner = st.text_input("Owner name", value=safe(seller.get("owner_name")))
            city = st.text_input("City", value=safe(seller.get("city")))
            state = st.text_input("State", value=safe(seller.get("state")))
            instagram = st.text_input("Instagram", value=safe(seller.get("instagram")))
            website = st.text_input("Website", value=safe(seller.get("website")))
            bio = st.text_area("Short store bio", value=safe(seller.get("store_bio")))
            story = st.text_area("Seller story / profile page bio", value=safe(seller.get("seller_story")))
            specialties = st.text_area("Specialties", value=safe(seller.get("specialties")))
            logo_upload = st.file_uploader("Upload new logo", type=["png", "jpg", "jpeg", "webp"], key="seller_logo_upload")
            banner_upload = st.file_uploader("Upload new banner", type=["png", "jpg", "jpeg", "webp"], key="seller_banner_upload")
            logo_url = st.text_input("Or paste logo URL", value=safe(seller.get("logo_url")))
            banner_url = st.text_input("Or paste banner URL", value=safe(seller.get("banner_url")))
            submitted = st.form_submit_button("Save Store Profile")

        if submitted:
            logo_path = save_uploaded_file(logo_upload, "seller_logos") or logo_url
            banner_path = save_uploaded_file(banner_upload, "seller_banners") or banner_url
            run_sql("""
                UPDATE sellers
                SET store_name=?, owner_name=?, city=?, state=?, instagram=?, website=?, store_bio=?, seller_story=?, specialties=?, logo_url=?, banner_url=?
                WHERE id=?
            """, (store_name, owner, city, state, instagram, website, bio, story, specialties, logo_path, banner_path, seller_id))
            st.success("Store profile saved.")

    with tabs[1]:
        st.subheader("Store Policies")
        st.caption("Seller rules can be stronger than House Of Wax rules, but never weaker.")
        with st.expander("Policy Templates"):
            st.code("Shipping: Orders are usually processed within 3 business days. Tracking is provided when available.")
            st.code("Returns: Buyer remorse returns are not accepted unless stated. Not-as-described issues will be reviewed.")
            st.code("Grading: Records are graded using common collector standards. Buyers should review photos and notes.")
            st.code("Buyer Requirements: Buyer must be registered, in good standing, and pay within the listed payment window.")

        policy_df = get_df("SELECT * FROM seller_policies WHERE seller_id=?", (seller_id,))
        policy = policy_df.iloc[0] if not policy_df.empty else {}
        with st.form("policies_form"):
            shipping = st.text_area("Shipping policy", value=safe(policy.get("shipping_policy") if len(policy) else ""))
            returns = st.text_area("Return policy", value=safe(policy.get("return_policy") if len(policy) else ""))
            grading = st.text_area("Condition/grading policy", value=safe(policy.get("grading_policy") if len(policy) else ""))
            service = st.text_area("Customer service policy", value=safe(policy.get("customer_service_policy") if len(policy) else ""))
            bundle = st.text_area("Bundle/discount policy", value=safe(policy.get("bundle_policy") if len(policy) else ""))
            auction_policy = st.text_area("Auction policy", value=safe(policy.get("auction_policy") if len(policy) else ""))
            buyer_requirements = st.text_area("Buyer requirements", value=safe(policy.get("buyer_requirements") if len(policy) else "Buyer must be registered and in good standing."))
            pickup = st.text_area("Local pickup policy", value=safe(policy.get("local_pickup_policy") if len(policy) else ""))
            international = st.text_area("International shipping policy", value=safe(policy.get("international_shipping_policy") if len(policy) else ""))
            processing = st.text_input("Processing time", value=safe(policy.get("processing_time") if len(policy) else get_setting("default_processing_time", "3 business days")))
            submitted = st.form_submit_button("Save Policies")
        if submitted:
            run_sql("""
                INSERT OR REPLACE INTO seller_policies
                (seller_id, shipping_policy, return_policy, grading_policy, customer_service_policy, bundle_policy, auction_policy, buyer_requirements, local_pickup_policy, international_shipping_policy, processing_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (seller_id, shipping, returns, grading, service, bundle, auction_policy, buyer_requirements, pickup, international, processing))
            st.success("Policies saved.")

    with tabs[2]:
        st.subheader("Upload Products")
        with st.form("add_product_form"):
            c1, c2, c3 = st.columns(3)
            sku = c1.text_input("SKU")
            barcode = c2.text_input("Barcode / UPC / EAN")
            catalog = c3.text_input("Catalog number")
            matrix = st.text_input("Matrix / runout")
            c4, c5, c6 = st.columns(3)
            category = c4.selectbox("Category", ["Vinyl Records", "CDs", "Cassettes", "Music DVDs/VHS", "Music Books/Magazines", "Posters", "Music Memorabilia", "Vintage Clothing", "Streetwear", "Band Tees", "DJ Gear/Accessories", "Culture Goods"])
            artist = c5.text_input("Artist / Brand")
            title = c6.text_input("Title / Product Name")
            c7, c8, c9 = st.columns(3)
            fmt = c7.text_input("Format", value="Vinyl")
            label = c8.text_input("Label / Brand")
            year = c9.text_input("Year")
            genre = st.text_input("Genre / Style")
            c10, c11 = st.columns(2)
            media_grade = c10.selectbox("Media/Product grade", ["Mint", "Near Mint", "VG+", "VG", "Good", "Fair", "Poor", "New", "Used", "N/A"])
            sleeve_grade = c11.selectbox("Sleeve/Packaging grade", ["Mint", "Near Mint", "VG+", "VG", "Good", "Fair", "Poor", "New", "Used", "N/A"])
            notes = st.text_area("Condition notes")
            generated = generate_description({"artist":artist,"title":title,"format":fmt,"genre":genre,"label":label,"release_year":year,"media_grade":media_grade,"sleeve_grade":sleeve_grade,"barcode":barcode,"catalog_number":catalog,"matrix_runout":matrix,"condition_notes":notes})
            description = st.text_area("Description", value=generated, height=160)
            c12, c13, c14 = st.columns(3)
            price = c12.number_input("Price", min_value=0.0, step=0.01)
            qty = c13.number_input("Quantity", min_value=1, value=1)
            shipping = c14.number_input("Shipping price", min_value=0.0, step=0.01)
            image_file = st.file_uploader("Upload product image", type=["png","jpg","jpeg","webp"])
            image_url = st.text_input("Or paste image URL")
            video_url = st.text_input("Video URL")
            audio_url = st.text_input("Audio URL")
            external_url = st.text_input("Discogs / MusicBrainz / research URL")
            status = st.selectbox("Listing status", ["Active", "Draft"])
            submitted = st.form_submit_button("Upload Product")

        if submitted:
            saved_image = save_uploaded_file(image_file, "product_images") or image_url
            run_sql("""
                INSERT INTO products
                (seller_id, sku, barcode, catalog_number, matrix_runout, category, artist, title, format, label, release_year, genre, media_grade, sleeve_grade, condition_notes, description, price, quantity, shipping_price, image_url, video_url, audio_url, external_release_url, listing_status, listing_type, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Fixed Price', ?, ?)
            """, (seller_id, sku, barcode, catalog, matrix, category, artist, title, fmt, label, year, genre, media_grade, sleeve_grade, notes, description, float(price), int(qty), float(shipping), saved_image, video_url, audio_url, external_url, status, now(), now()))
            st.success("Product uploaded. Approved sellers can publish fixed-price products without manual product approval.")

    with tabs[3]:
        st.subheader("Product Gallery")
        products = get_df("SELECT * FROM products WHERE seller_id=? ORDER BY created_at DESC", (seller_id,))
        if products.empty:
            st.info("Upload a product first.")
        else:
            product_id = st.selectbox("Choose product", products["id"].tolist(), key="gallery_product")
            image_file = st.file_uploader("Upload gallery image", type=["png", "jpg", "jpeg", "webp"], key="gallery_image")
            image_url = st.text_input("Or paste image URL", key="gallery_image_url")
            caption = st.text_input("Caption", key="gallery_caption")
            if st.button("Add Gallery Image"):
                saved = save_uploaded_file(image_file, "product_gallery") or image_url
                if saved:
                    run_sql("INSERT INTO product_gallery (product_id, image_url, caption, created_at) VALUES (?, ?, ?, ?)", (int(product_id), saved, caption, now()))
                    st.success("Gallery image added.")
                else:
                    st.error("Upload an image or paste an image URL.")
            existing = get_df("SELECT * FROM product_gallery WHERE product_id=? ORDER BY created_at DESC", (int(product_id),))
            st.dataframe(existing, use_container_width=True)

    with tabs[4]:
        st.subheader("Bulk Product Import")
        st.write("Upload a CSV with columns like artist, title, category, format, price, quantity, image_url, and condition fields.")
        csv_file = st.file_uploader("Upload product CSV", type=["csv"], key="bulk_csv")
        if csv_file is not None:
            try:
                df = pd.read_csv(csv_file)
                st.dataframe(df, use_container_width=True)
                if st.button("Import CSV Products"):
                    imported = 0
                    for _, row in df.iterrows():
                        run_sql("""
                            INSERT INTO products
                            (seller_id, sku, barcode, catalog_number, matrix_runout, category, artist, title, format, label, release_year, genre, media_grade, sleeve_grade, condition_notes, description, price, quantity, shipping_price, image_url, video_url, audio_url, external_release_url, listing_status, listing_type, created_at, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Fixed Price', ?, ?)
                        """, (
                            seller_id,
                            safe(row.get("sku")),
                            safe(row.get("barcode")),
                            safe(row.get("catalog_number")),
                            safe(row.get("matrix_runout")),
                            safe(row.get("category"), "Vinyl Records"),
                            safe(row.get("artist")),
                            safe(row.get("title")),
                            safe(row.get("format"), "Vinyl"),
                            safe(row.get("label")),
                            safe(row.get("release_year")),
                            safe(row.get("genre")),
                            safe(row.get("media_grade")),
                            safe(row.get("sleeve_grade")),
                            safe(row.get("condition_notes")),
                            safe(row.get("description")),
                            float(row.get("price", 0) or 0),
                            int(row.get("quantity", 1) or 1),
                            float(row.get("shipping_price", 0) or 0),
                            safe(row.get("image_url")),
                            safe(row.get("video_url")),
                            safe(row.get("audio_url")),
                            safe(row.get("external_release_url")),
                            safe(row.get("listing_status"), "Active"),
                            now(),
                            now(),
                        ))
                        imported += 1
                    st.success(f"Imported {imported} products.")
            except Exception as error:
                st.error(f"Could not read/import CSV: {error}")

    with tabs[5]:
        st.subheader("My Listings")
        products = get_df("SELECT * FROM products WHERE seller_id=? ORDER BY created_at DESC", (seller_id,))
        st.dataframe(products, use_container_width=True)
        if not products.empty:
            product_id = st.selectbox("Product ID", products["id"].tolist(), key="listing_update")
            new_status = st.selectbox("New status", ["Active", "Draft", "Sold", "Removed"], key="listing_status")
            if st.button("Update Listing Status"):
                run_sql("UPDATE products SET listing_status=?, updated_at=? WHERE id=? AND seller_id=?", (new_status, now(), int(product_id), seller_id))
                st.success("Listing status updated.")

    with tabs[6]:
        st.subheader("My Auctions")
        eligible, reason = auction_eligible(seller)
        st.info(f"Auction eligibility: {'Yes' if eligible else 'No'} — {reason}")
        for label, (current, required, passed) in auction_progress(seller).items():
            st.write(f"{'✅' if passed else '❌'} {label}: {current} / {required}")

        products = get_df("SELECT * FROM products WHERE seller_id=? AND listing_status='Active'", (seller_id,))
        if eligible and not products.empty:
            with st.form("auction_form"):
                product_id = st.selectbox("Product", products["id"].tolist())
                title = st.text_input("Auction title")
                c1, c2, c3, c4 = st.columns(4)
                start = c1.number_input("Starting bid", min_value=0.0, step=1.0)
                reserve = c2.number_input("Reserve price", min_value=0.0, step=1.0)
                buy_now = c3.number_input("Buy-now price", min_value=0.0, step=1.0)
                inc = c4.number_input("Bid increment", min_value=1.0, step=1.0)
                start_time = st.text_input("Start time", value=now())
                end_time = st.text_input("End time")
                status = st.selectbox("Auction status", ["Draft", "Live"])
                notes = st.text_area("Auction notes")
                submitted = st.form_submit_button("Create Auction")
            if submitted:
                run_sql("""
                    INSERT INTO auctions (product_id, seller_id, auction_title, starting_bid, reserve_price, buy_now_price, bid_increment, start_time, end_time, status, notes, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (int(product_id), seller_id, title, start, reserve, buy_now, inc, start_time, end_time, status, notes, now()))
                st.success("Auction saved.")
        st.dataframe(get_df("SELECT * FROM auctions WHERE seller_id=?", (seller_id,)), use_container_width=True)

    with tabs[7]:
        st.subheader("Orders")
        orders = get_df("""
            SELECT o.*, b.name AS buyer_name, b.email AS buyer_email, b.status AS buyer_status, b.rating AS buyer_rating,
                   b.unpaid_orders AS buyer_unpaid_orders, b.strikes AS buyer_strikes, p.artist, p.title
            FROM orders o
            LEFT JOIN buyers b ON o.buyer_id=b.id
            LEFT JOIN products p ON o.product_id=p.id
            WHERE o.seller_id=?
            ORDER BY o.created_at DESC
        """, (seller_id,))
        st.dataframe(orders, use_container_width=True)
        if not orders.empty:
            order_id = st.selectbox("Order ID", orders["id"].tolist(), key="seller_order")
            status = st.selectbox("Update order status", ["New","Contacted","Invoice Sent","Paid","Shipped","Completed","Cancelled","Disputed"])
            if st.button("Update Order Status"):
                run_sql("UPDATE orders SET status=?, updated_at=? WHERE id=? AND seller_id=?", (status, now(), int(order_id), seller_id))
                if status == "Completed":
                    row = orders[orders["id"] == order_id].iloc[0]
                    run_sql("UPDATE sellers SET completed_sales=completed_sales+1 WHERE id=?", (seller_id,))
                    run_sql("UPDATE buyers SET completed_purchases=completed_purchases+1 WHERE id=?", (int(row["buyer_id"]),))
                st.success("Order updated.")
            if st.button("Mark Buyer as Non-Paying"):
                row = orders[orders["id"] == order_id].iloc[0]
                run_sql("UPDATE buyers SET unpaid_orders=unpaid_orders+1, strikes=strikes+1 WHERE id=?", (int(row["buyer_id"]),))
                run_sql("UPDATE orders SET status='Cancelled', updated_at=? WHERE id=? AND seller_id=?", (now(), int(order_id), seller_id))
                st.warning("Buyer marked as non-paying.")

    with tabs[8]:
        st.subheader("Messages")
        messages = get_df("""
            SELECT m.*, b.name AS buyer_name, b.email AS buyer_email, p.artist, p.title
            FROM messages m
            LEFT JOIN buyers b ON m.buyer_id=b.id
            LEFT JOIN products p ON m.product_id=p.id
            WHERE m.seller_id=?
            ORDER BY m.created_at DESC
        """, (seller_id,))
        st.dataframe(messages, use_container_width=True)
        if not messages.empty:
            message_id = st.selectbox("Message ID", messages["id"].tolist(), key="seller_message_id")
            selected = messages[messages["id"] == message_id].iloc[0]
            st.write(f"**From:** {safe(selected.get('buyer_name'))} | {safe(selected.get('buyer_email'))}")
            st.write(f"**Subject:** {safe(selected.get('subject'))}")
            st.write(safe(selected.get("message")))
            reply = st.text_area("Reply / internal response note", key="seller_reply_text")
            if st.button("Mark Message Responded"):
                run_sql("UPDATE messages SET status='Responded' WHERE id=?", (int(message_id),))
                st.success("Message marked responded.")

    with tabs[9]:
        st.subheader("Store Announcements")
        with st.form("announcement_form"):
            title = st.text_input("Announcement title")
            body = st.text_area("Announcement body")
            status = st.selectbox("Status", ["Active", "Inactive"])
            submitted = st.form_submit_button("Save Announcement")
        if submitted:
            run_sql("INSERT INTO store_announcements (seller_id, title, body, status, created_at) VALUES (?, ?, ?, ?, ?)", (seller_id, title, body, status, now()))
            st.success("Announcement saved.")
        st.dataframe(get_df("SELECT * FROM store_announcements WHERE seller_id=? ORDER BY created_at DESC", (seller_id,)), use_container_width=True)

    with tabs[10]:
        st.subheader("Events / Drops Calendar")
        with st.form("event_form"):
            event_title = st.text_input("Event/drop title")
            event_type = st.selectbox("Type", ["Record Drop", "Auction Drop", "Store Sale", "Live Event", "New Arrival Batch", "Other"])
            event_date = st.text_input("Date", placeholder="Example: 2026-07-01 7:00 PM")
            description = st.text_area("Description")
            status = st.selectbox("Status", ["Active", "Inactive"])
            submitted = st.form_submit_button("Save Event/Drop")
        if submitted:
            run_sql("INSERT INTO seller_events (seller_id, event_title, event_type, event_date, description, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)", (seller_id, event_title, event_type, event_date, description, status, now()))
            st.success("Event/drop saved.")
        st.dataframe(get_df("SELECT * FROM seller_events WHERE seller_id=? ORDER BY event_date", (seller_id,)), use_container_width=True)

    with tabs[11]:
        st.subheader("Leave Buyer Feedback")
        completed = get_df("""
            SELECT o.*, b.name AS buyer_name, b.email AS buyer_email, p.artist, p.title
            FROM orders o
            LEFT JOIN buyers b ON o.buyer_id=b.id
            LEFT JOIN products p ON o.product_id=p.id
            WHERE o.seller_id=? AND o.status='Completed'
            ORDER BY o.created_at DESC
        """, (seller_id,))
        if completed.empty:
            st.info("No completed orders available for buyer feedback yet.")
        else:
            order_id = st.selectbox("Completed order", completed["id"].tolist(), key="seller_feedback_order")
            row = completed[completed["id"] == order_id].iloc[0]
            st.write(f"Reviewing buyer: **{safe(row['buyer_name'])}** for {safe(row['artist'])} — {safe(row['title'])}")
            rating = st.slider("Buyer rating", 1, 5, 5, key="buyer_feedback_rating")
            comment = st.text_area("Feedback comment", key="buyer_feedback_comment")
            if st.button("Submit Buyer Feedback"):
                existing = get_df("SELECT id FROM feedback WHERE order_id=? AND reviewer_type='Seller' AND reviewer_id=?", (int(order_id), seller_id))
                if not existing.empty:
                    st.warning("You already left feedback for this order.")
                else:
                    run_sql("""
                        INSERT INTO feedback (order_id, reviewer_type, reviewer_id, reviewee_type, reviewee_id, rating, comment, created_at)
                        VALUES (?, 'Seller', ?, 'Buyer', ?, ?, ?, ?)
                    """, (int(order_id), seller_id, int(row["buyer_id"]), int(rating), comment, now()))
                    recalculate_rating("Buyer", int(row["buyer_id"]))
                    st.success("Buyer feedback submitted.")

    with tabs[12]:
        st.subheader("Feedback Received")
        received = get_df("""
            SELECT f.*, b.name AS buyer_name
            FROM feedback f
            LEFT JOIN buyers b ON f.reviewer_id=b.id
            WHERE f.reviewee_type='Seller' AND f.reviewee_id=?
            ORDER BY f.created_at DESC
        """, (seller_id,))
        st.dataframe(received, use_container_width=True)

    with tabs[13]:
        st.subheader("Social Posts")
        products = get_df("SELECT * FROM products WHERE seller_id=?", (seller_id,))
        if products.empty:
            st.info("Add a product first.")
        else:
            product_id = st.selectbox("Product to promote", products["id"].tolist())
            product = products[products["id"] == product_id].iloc[0]
            caption = f"Now on House Of Wax: {safe(product.get('artist'))} — {safe(product.get('title'))}. Condition: {safe(product.get('media_grade'))}. Price: {money(product.get('price'))}."
            hashtags = "#HouseOfWax #MusicMarketplace #VinylMarketplace #MusicCulture"
            st.text_area("Caption", value=caption, height=120)
            st.text_input("Hashtags", value=hashtags)
            platform = st.selectbox("Platform", ["Instagram","TikTok","Facebook","X","Email","Buffer Queue"])
            if st.button("Save Social Draft"):
                run_sql("INSERT INTO social_posts (product_id, seller_id, platform, caption, hashtags, status, created_at) VALUES (?, ?, ?, ?, ?, 'Draft', ?)", (int(product_id), seller_id, platform, caption, hashtags, now()))
                st.success("Social draft saved.")

    with tabs[14]:
        st.markdown("Sellers can create their own store policies and identity, but House Of Wax platform rules are the minimum standard.")


# -----------------------------
# Admin
# -----------------------------
def admin_page():
    render_header()
    st.header("Admin Login")
    password = st.text_input("Admin password", type="password")
    if not st.button("Login Admin"):
        return
    if not ADMIN_PASSWORD:
        st.error("Admin password is not set in Streamlit Secrets.")
        return
    if password != ADMIN_PASSWORD:
        st.error("Wrong password.")
        return
    admin_workspace()


def admin_workspace():
    tabs = st.tabs(["Overview","Seller Applications","Seller Management","Buyer Management","Flagged Listings","Seller Reports","Orders","Feedback","Messages","Community Tools","Auctions","Culture Content","Platform Rules","Fees & Settings","Reports","Testing Cleanup","Business Planning"])

    with tabs[0]:
        sellers, buyers, products, orders = get_table("sellers"), get_table("buyers"), get_table("products"), get_table("orders")
        flags, reports = get_table("listing_flags"), get_table("seller_reports")
        c1,c2,c3,c4,c5 = st.columns(5)
        c1.metric("Sellers", len(sellers))
        c2.metric("Buyers", len(buyers))
        c3.metric("Products", len(products))
        c4.metric("Orders", len(orders))
        open_items = (len(flags[flags["status"]=="Open"]) if not flags.empty else 0) + (len(reports[reports["status"]=="Open"]) if not reports.empty else 0)
        c5.metric("Open Reports", open_items)
        st.success(f"Admin loaded. Running {APP_VERSION}.")

    with tabs[1]:
        st.subheader("Seller Applications")
        pending = get_df("SELECT * FROM sellers WHERE status='Pending'")
        st.dataframe(pending, use_container_width=True)
        if not pending.empty:
            seller_id = st.selectbox("Seller ID to review", pending["id"].tolist())
            seller = pending[pending["id"] == seller_id].iloc[0]
            decision = st.selectbox("Decision", ["Approved", "Rejected"])
            if st.button("Save Seller Decision"):
                level = "Approved Seller" if decision=="Approved" else "Rejected"
                run_sql("UPDATE sellers SET status=?, seller_level=? WHERE id=?", (decision, level, int(seller_id)))
                if decision == "Approved":
                    msg = approval_email_template(seller)
                    run_sql("INSERT INTO seller_notifications (seller_id, subject, message, status, created_at) VALUES (?, ?, ?, 'Unread', ?)", (int(seller_id), "Your House Of Wax seller store has been approved", msg, now()))
                st.success("Seller updated. If approved, an in-app approval message was created.")
            st.subheader("Approval Email Template")
            st.caption("This prototype creates an in-app seller message. Real outgoing email needs an email service later.")
            st.text_area("Copy/paste this email to seller", value=approval_email_template(seller), height=260)

    with tabs[2]:
        st.subheader("Seller Management")
        sellers = get_table("sellers")
        st.dataframe(sellers, use_container_width=True)
        if not sellers.empty:
            seller_id = st.selectbox("Manage seller ID", sellers["id"].tolist(), key="manage_seller")
            seller = sellers[sellers["id"] == seller_id].iloc[0]
            status = st.selectbox("Seller status", ["Pending","Approved","Suspended","Rejected","Verified"], index=["Pending","Approved","Suspended","Rejected","Verified"].index(safe(seller["status"],"Pending")) if safe(seller["status"]) in ["Pending","Approved","Suspended","Rejected","Verified"] else 0)
            auction_override = st.selectbox("Auction override", ["No","Yes"], index=1 if safe(seller["auction_override"])=="Yes" else 0)
            completed_sales = st.number_input("Completed sales", min_value=0, step=1, value=int(seller["completed_sales"] or 0))
            rating = st.number_input("Seller rating", min_value=0.0, max_value=100.0, value=float(seller["rating"] or 100))
            strikes = st.number_input("Seller strikes", min_value=0, step=1, value=int(seller["strikes"] or 0))
            disputes = st.number_input("Seller disputes", min_value=0, step=1, value=int(seller["disputes"] or 0))
            if st.button("Update Seller"):
                run_sql("UPDATE sellers SET status=?, auction_override=?, completed_sales=?, rating=?, strikes=?, disputes=? WHERE id=?", (status, auction_override, int(completed_sales), float(rating), int(strikes), int(disputes), int(seller_id)))
                st.success("Seller updated.")

    with tabs[3]:
        st.subheader("Buyer Management")
        buyers = get_table("buyers")
        st.dataframe(buyers, use_container_width=True)
        if not buyers.empty:
            buyer_id = st.selectbox("Manage buyer ID", buyers["id"].tolist(), key="manage_buyer")
            buyer = buyers[buyers["id"] == buyer_id].iloc[0]
            status = st.selectbox("Buyer status", ["New Buyer","Verified Buyer","Trusted Buyer","Restricted Buyer","Suspended Buyer"])
            rating = st.number_input("Buyer rating", min_value=0.0, max_value=100.0, value=float(buyer["rating"] or 100), key="admin_buyer_rating")
            unpaid = st.number_input("Unpaid orders", min_value=0, step=1, value=int(buyer["unpaid_orders"] or 0))
            strikes = st.number_input("Buyer strikes", min_value=0, step=1, value=int(buyer["strikes"] or 0), key="admin_buyer_strikes")
            if st.button("Update Buyer"):
                run_sql("UPDATE buyers SET status=?, rating=?, unpaid_orders=?, strikes=? WHERE id=?", (status, float(rating), int(unpaid), int(strikes), int(buyer_id)))
                st.success("Buyer updated.")

    with tabs[4]:
        flags = get_df("""
            SELECT f.*, p.artist, p.title, s.store_name
            FROM listing_flags f
            LEFT JOIN products p ON f.product_id=p.id
            LEFT JOIN sellers s ON f.seller_id=s.id
            ORDER BY f.created_at DESC
        """)
        st.dataframe(flags, use_container_width=True)

    with tabs[5]:
        reports = get_df("""
            SELECT r.*, s.store_name, b.name AS buyer_name, b.email AS buyer_email
            FROM seller_reports r
            LEFT JOIN sellers s ON r.seller_id=s.id
            LEFT JOIN buyers b ON r.buyer_id=b.id
            ORDER BY r.created_at DESC
        """)
        st.dataframe(reports, use_container_width=True)

    with tabs[6]:
        orders = get_table("orders")
        st.dataframe(orders, use_container_width=True)
        if not orders.empty:
            order_id = st.selectbox("Order ID", orders["id"].tolist())
            status = st.selectbox("Order status", ["New","Contacted","Invoice Sent","Paid","Shipped","Completed","Cancelled","Disputed"])
            if st.button("Update Order"):
                run_sql("UPDATE orders SET status=?, updated_at=? WHERE id=?", (status, now(), int(order_id)))
                if status == "Completed":
                    order = orders[orders["id"] == order_id].iloc[0]
                    run_sql("UPDATE sellers SET completed_sales=completed_sales+1 WHERE id=?", (int(order["seller_id"]),))
                    run_sql("UPDATE buyers SET completed_purchases=completed_purchases+1 WHERE id=?", (int(order["buyer_id"]),))
                st.success("Order updated.")

    with tabs[7]:
        st.subheader("Feedback")
        st.dataframe(get_table("feedback"), use_container_width=True)

    with tabs[8]:
        st.subheader("Messages")
        st.dataframe(get_table("messages"), use_container_width=True)

    with tabs[9]:
        st.subheader("Community Tools")
        sellers = get_table("sellers")
        if sellers.empty:
            st.info("No sellers yet.")
        else:
            seller_id = st.selectbox("Seller", sellers["id"].tolist(), key="community_seller")
            seller = sellers[sellers["id"] == seller_id].iloc[0]

            st.markdown("### Badges")
            badge = st.text_input("Badge name", placeholder="Example: Soul Specialist, Verified Seller, Jazz Dealer")
            badge_type = st.selectbox("Badge type", ["Community", "Verified", "Specialty", "Performance", "Culture"])
            if st.button("Add Seller Badge"):
                run_sql("INSERT INTO seller_badges (seller_id, badge_name, badge_type, active, created_at) VALUES (?, ?, ?, 'Yes', ?)", (int(seller_id), badge, badge_type, now()))
                st.success("Badge added.")

            st.markdown("### Seller Spotlight")
            if st.button("Create Seller Spotlight Culture Post"):
                if create_seller_spotlight(int(seller_id)):
                    st.success("Seller spotlight post created in Music + Culture.")

            st.markdown("### Store Announcements")
            st.dataframe(get_df("SELECT * FROM store_announcements WHERE seller_id=? ORDER BY created_at DESC", (int(seller_id),)), use_container_width=True)

            st.markdown("### Events / Drops")
            st.dataframe(get_df("SELECT * FROM seller_events WHERE seller_id=? ORDER BY event_date", (int(seller_id),)), use_container_width=True)

            st.markdown("### Followers")
            followers = get_df("""
                SELECT f.*, b.name, b.email
                FROM seller_followers f
                LEFT JOIN buyers b ON f.buyer_id=b.id
                WHERE f.seller_id=?
                ORDER BY f.created_at DESC
            """, (int(seller_id),))
            st.dataframe(followers, use_container_width=True)

    with tabs[10]:
        st.dataframe(get_table("auctions"), use_container_width=True)

    with tabs[11]:
        st.subheader("Culture Content")
        with st.form("culture_form"):
            title = st.text_input("Title")
            category = st.selectbox("Category", ["Music","Clothing","Culture","Collecting Guide","Seller Spotlight","Auction Preview","Regional History"])
            author = st.text_input("Author", value="House Of Wax")
            image_file = st.file_uploader("Upload image", type=["png","jpg","jpeg","webp"])
            image_url = st.text_input("Or image URL")
            body = st.text_area("Body", height=200)
            submitted = st.form_submit_button("Publish")
        if submitted:
            img = save_uploaded_file(image_file, "culture_images") or image_url
            run_sql("INSERT INTO culture_posts (title, category, author, body, image_url, status, created_at) VALUES (?, ?, ?, ?, ?, 'Published', ?)", (title, category, author, body, img, now()))
            st.success("Culture post published.")
        st.dataframe(get_table("culture_posts"), use_container_width=True)

    with tabs[12]:
        rules = get_table("platform_rules")
        st.dataframe(rules, use_container_width=True)
        with st.form("rule_form"):
            title = st.text_input("Rule title")
            category = st.selectbox("Rule category", ["Seller Rules","Buyer Rules","Listings","Auctions","Fees","Trust & Safety","Community","Other"])
            text = st.text_area("Rule text")
            active = st.selectbox("Active", ["Yes","No"])
            submitted = st.form_submit_button("Add Rule")
        if submitted:
            run_sql("INSERT INTO platform_rules (title, category, rule_text, active, created_at) VALUES (?, ?, ?, ?, ?)", (title, category, text, active, now()))
            st.success("Rule added.")

    with tabs[13]:
        with st.form("settings_form"):
            commission = st.text_input("Platform commission %", value=get_setting("platform_commission_percent", "9"))
            auction_commission = st.text_input("Auction commission %", value=get_setting("auction_commission_percent", "10"))
            min_sales = st.text_input("Auction minimum completed sales", value=get_setting("auction_min_completed_sales", "10"))
            min_rating = st.text_input("Auction minimum seller rating", value=get_setting("auction_min_rating", "90"))
            storefront_url = st.text_input("Storefront URL", value=get_setting("storefront_url", ""))
            logo = st.text_input("Platform logo URL", value=get_setting("logo_url", ""))
            tagline = st.text_input("Site tagline", value=get_setting("site_tagline", ""))
            announcement = st.text_area("Announcement", value=get_setting("announcement", ""))
            submitted = st.form_submit_button("Save Settings")
        if submitted:
            for k,v in [("platform_commission_percent",commission),("auction_commission_percent",auction_commission),("auction_min_completed_sales",min_sales),("auction_min_rating",min_rating),("storefront_url",storefront_url),("logo_url",logo),("site_tagline",tagline),("announcement",announcement)]:
                save_setting(k,v)
            st.success("Settings saved.")

    with tabs[14]:
        report = st.selectbox("Report", ["sellers","seller_policies","buyers","products","orders","feedback","listing_flags","seller_reports","favorites","auctions","bids","culture_posts","disputes","social_posts","platform_rules","seller_notifications","messages","seller_followers","seller_badges","store_announcements","seller_events","product_gallery"])
        data = get_table(report)
        st.dataframe(data, use_container_width=True)
        st.download_button("Download CSV", data.to_csv(index=False), file_name=f"{report}.csv")
        if not get_table("orders").empty:
            orders = get_table("orders")
            st.metric("Estimated Platform Fees", money(orders["platform_fee"].sum()))

    with tabs[15]:
        st.warning("Use testing cleanup carefully. Deletes cannot be undone.")
        table_name = st.selectbox("Table to clean", ["buyers","sellers","products","orders","feedback","listing_flags","seller_reports","favorites","auctions","bids","culture_posts","disputes","social_posts","seller_notifications","messages","seller_followers","seller_badges","store_announcements","seller_events","product_gallery"])
        rows = get_table(table_name)
        st.dataframe(rows, use_container_width=True)
        if not rows.empty:
            row_id = st.selectbox("Row ID to delete", rows["id"].tolist())
            confirm = st.checkbox("I understand this deletes the selected row.")
            if st.button("Delete Selected Row"):
                if confirm:
                    delete_by_id(table_name, row_id)
                    st.success("Deleted.")
                else:
                    st.error("Check confirmation first.")

    with tabs[16]:
        st.markdown("Updated planning files are included in this ZIP.")


# -----------------------------
# Navigation
# -----------------------------
menu = st.sidebar.radio(
    "House Of Wax",
    ["Home","Marketplace","Auctions","Seller Stores","Music + Culture","Register / Sell","Buyer Dashboard","Seller Dashboard","Admin Login"]
)

if menu == "Home":
    home_page()
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
