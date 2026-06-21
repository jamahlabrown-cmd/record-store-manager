
import sqlite3
from pathlib import Path
from datetime import datetime
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="House Of Wax Marketplace",
    page_icon="🎧",
    layout="wide"
)

APP_VERSION = "V15.4 FIX + TESTING PATCH"
APP_NAME = "House Of Wax"
DB = Path("house_of_wax_v15_4.db")

try:
    ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "")
except Exception:
    ADMIN_PASSWORD = ""


# -----------------------------
# Basic helpers
# -----------------------------
def now():
    return datetime.now().isoformat(timespec="seconds")


def money(value):
    try:
        return f"${float(value):,.2f}"
    except Exception:
        return "$0.00"


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


def email_exists(table_name, email):
    if not email:
        return False
    df = get_df(f"SELECT id FROM {table_name} WHERE lower(email)=lower(?)", (email.strip(),))
    return not df.empty


def delete_by_id(table_name, row_id):
    run_sql(f"DELETE FROM {table_name} WHERE id = ?", (int(row_id),))


# -----------------------------
# Database setup
# -----------------------------
def setup_database():
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sellers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_name TEXT NOT NULL,
            owner_name TEXT,
            email TEXT UNIQUE,
            phone TEXT,
            city TEXT,
            store_bio TEXT,
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

    conn.commit()
    conn.close()

    default_settings = {
        "logo_url": "",
        "site_tagline": "A seller-powered marketplace for records, music culture, clothing, and collectors.",
        "announcement": "Sellers run their own stores. Buyers are accountable. House Of Wax protects the platform.",
        "platform_commission_percent": "9",
        "auction_commission_percent": "10",
        "auction_min_completed_sales": "10",
        "auction_min_rating": "90",
        "default_processing_time": "3 business days",
        "buyer_payment_window_hours": "48",
    }

    for key, value in default_settings.items():
        existing = get_df("SELECT value FROM settings WHERE key = ?", (key,))
        if existing.empty:
            run_sql("INSERT INTO settings (key, value) VALUES (?, ?)", (key, value))

    rules = get_table("platform_rules")
    if rules.empty:
        starter_rules = [
            ("Seller policies cannot weaken House Of Wax rules", "Seller Rules", "Sellers may create their own shipping, return, grading, and customer service policies, but those policies cannot reduce required buyer or seller protections."),
            ("No counterfeit or prohibited items", "Listings", "Counterfeit, stolen, illegal, hateful, or misleading items may be removed and may lead to seller restriction."),
            ("Buyers must pay for commitments", "Buyer Rules", "Buyers who commit to purchase or win auctions are expected to pay within the posted payment window."),
            ("Auctions are earned", "Auctions", "Sellers must meet performance requirements or receive admin override before using auctions."),
            ("Flagged content may be reviewed", "Trust & Safety", "House Of Wax may review flagged listings, seller reports, disputes, and suspicious activity.")
        ]
        for title, category, text in starter_rules:
            run_sql(
                "INSERT INTO platform_rules (title, category, rule_text, active, created_at) VALUES (?, ?, ?, 'Yes', ?)",
                (title, category, text, now())
            )


setup_database()


# -----------------------------
# Settings and business logic
# -----------------------------
def get_setting(key, default=""):
    df = get_df("SELECT value FROM settings WHERE key = ?", (key,))
    if df.empty:
        return default
    return safe(df.iloc[0]["value"], default)


def save_setting(key, value):
    run_sql("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))


def calculate_fee(total, auction=False):
    if auction:
        percent = float(get_setting("auction_commission_percent", "10"))
    else:
        percent = float(get_setting("platform_commission_percent", "9"))
    return round(float(total) * percent / 100, 2)


def get_seller(seller_id):
    if not seller_id:
        return None
    df = get_df("SELECT * FROM sellers WHERE id = ?", (int(seller_id),))
    if df.empty:
        return None
    return df.iloc[0]


def get_buyer(buyer_id):
    if not buyer_id:
        return None
    df = get_df("SELECT * FROM buyers WHERE id = ?", (int(buyer_id),))
    if df.empty:
        return None
    return df.iloc[0]


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
    sales = int(seller["completed_sales"] or 0)
    rating = float(seller["rating"] or 0)
    strikes = int(seller["strikes"] or 0)
    disputes = int(seller["disputes"] or 0)
    return {
        "Completed sales": (sales, min_sales, sales >= min_sales),
        "Seller rating": (rating, min_rating, rating >= min_rating),
        "Strikes": (strikes, 0, strikes == 0),
        "Disputes": (disputes, 0, disputes == 0),
    }


def generate_description(data):
    artist = safe(data.get("artist"), "This listing")
    title = safe(data.get("title"))
    format_name = safe(data.get("format"), "music/culture item")
    genre = safe(data.get("genre"))
    label = safe(data.get("label"))
    year = safe(data.get("release_year"))
    media_grade = safe(data.get("media_grade"), "not specified")
    sleeve_grade = safe(data.get("sleeve_grade"), "N/A")
    barcode = safe(data.get("barcode"))
    catalog = safe(data.get("catalog_number"))
    matrix = safe(data.get("matrix_runout"))
    notes = safe(data.get("condition_notes"))

    description = f"{artist} — {title} is listed on House Of Wax as a curated {format_name} marketplace item."
    if genre:
        description += f" It is a strong fit for buyers interested in {genre}, collecting, and music culture."
    if label or year:
        description += f" Release details include {label or 'the listed label'}"
        if year:
            description += f" from {year}"
        description += "."
    description += f" Condition is listed as media/product grade {media_grade}, with sleeve or packaging grade {sleeve_grade}."

    identifiers = []
    if barcode:
        identifiers.append(f"barcode {barcode}")
    if catalog:
        identifiers.append(f"catalog number {catalog}")
    if matrix:
        identifiers.append(f"matrix/runout {matrix}")
    if identifiers:
        description += " Key identifiers include " + ", ".join(identifiers) + "."
    if notes:
        description += f" Seller notes: {notes}"
    description += " Buyers should review photos, grading notes, seller policies, shipping terms, and House Of Wax marketplace rules before buying or bidding."
    return description


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
    score = int(sum(checks.values()) / len(checks) * 100)
    missing = [key for key, passed in checks.items() if not passed]
    return score, missing


# -----------------------------
# Safe UI helpers
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
    buyer_id = int(selected.split("|")[0].strip())
    return buyer_id


def product_card(product):
    seller = get_seller(product["seller_id"])
    seller_name = safe(seller["store_name"], "Seller") if seller is not None else "Unknown Seller"

    with st.container(border=True):
        image_url = safe(product.get("image_url"))
        if image_url:
            st.image(image_url, use_container_width=True)
        else:
            st.markdown("### 🎵")

        st.markdown(f"### {safe(product.get('artist'))} — {safe(product.get('title'))}")
        st.caption(f"{safe(product.get('format'))} • {safe(product.get('genre'))} • Seller: {seller_name}")
        st.write(f"**Price:** {money(product.get('price'))}")
        st.write(f"**Condition:** {safe(product.get('media_grade'), 'Not graded')}")

        score, missing = listing_score(product)
        st.progress(score / 100, text=f"Listing quality: {score}/100")

        if st.button("View Item", key=f"view_product_{int(product['id'])}"):
            st.session_state["selected_product_id"] = int(product["id"])
            st.rerun()


def product_detail(product):
    if st.button("← Back to Marketplace"):
        if "selected_product_id" in st.session_state:
            del st.session_state["selected_product_id"]
        st.rerun()

    seller = get_seller(product["seller_id"])

    left, right = st.columns([1.2, 1])
    with left:
        image_url = safe(product.get("image_url"))
        video_url = safe(product.get("video_url"))
        audio_url = safe(product.get("audio_url"))

        if image_url:
            st.image(image_url, use_container_width=True)
        elif video_url:
            st.video(video_url)
        else:
            st.markdown("## 🎵")

        if audio_url:
            st.audio(audio_url)

    with right:
        st.header(f"{safe(product.get('artist'))} — {safe(product.get('title'))}")
        st.write(f"**Price:** {money(product.get('price'))}")
        st.write(f"**Shipping:** {money(product.get('shipping_price'))}")

        if seller is not None:
            st.write(f"**Seller:** {safe(seller['store_name'])}")
            st.caption(f"Seller rating: {seller['rating']}% • Sales: {seller['completed_sales']} • Level: {seller['seller_level']}")
        else:
            st.write("**Seller:** Unknown")

        st.write(f"**Category:** {safe(product.get('category'))}")
        st.write(f"**Format:** {safe(product.get('format'))}")
        st.write(f"**Condition:** {safe(product.get('media_grade'), 'N/A')} / Sleeve-Packaging: {safe(product.get('sleeve_grade'), 'N/A')}")

        identifiers = []
        if safe(product.get("barcode")):
            identifiers.append(f"Barcode: {safe(product.get('barcode'))}")
        if safe(product.get("catalog_number")):
            identifiers.append(f"Catalog #: {safe(product.get('catalog_number'))}")
        if safe(product.get("matrix_runout")):
            identifiers.append(f"Matrix/Runout: {safe(product.get('matrix_runout'))}")
        if identifiers:
            st.caption(" • ".join(identifiers))

        external_url = safe(product.get("external_release_url"))
        if external_url:
            st.link_button("Research / Release Link", external_url)

    st.subheader("Description")
    description = safe(product.get("description"))
    if not description:
        description = generate_description(product)
    st.write(description)

    if seller is not None:
        with st.expander("Seller Store Policies"):
            policies = get_df("SELECT * FROM seller_policies WHERE seller_id = ?", (int(seller["id"]),))
            if policies.empty:
                st.info("This seller has not added detailed policies yet. House Of Wax minimum platform rules still apply.")
            else:
                policy = policies.iloc[0]
                st.write("**Shipping:**", safe(policy.get("shipping_policy"), "Not provided"))
                st.write("**Returns:**", safe(policy.get("return_policy"), "Not provided"))
                st.write("**Grading:**", safe(policy.get("grading_policy"), "Not provided"))
                st.write("**Buyer Requirements:**", safe(policy.get("buyer_requirements"), "Not provided"))

    st.divider()
    st.subheader("Buy / Contact Seller")
    buyer_id = choose_buyer(f"buy_{int(product['id'])}")
    action = st.selectbox("Action", ["Request to Buy", "Ask a Question", "Make Offer"], key=f"action_{int(product['id'])}")
    message = st.text_area("Message to seller", key=f"message_{int(product['id'])}")
    agree = st.checkbox(
        "I reviewed the listing, condition notes, shipping terms, and seller store policies.",
        key=f"agree_{int(product['id'])}"
    )

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
                item_price = float(product.get("price") or 0)
                shipping_price = float(product.get("shipping_price") or 0)
                total = item_price + shipping_price
                fee = calculate_fee(total, auction=False)
                payout = total - fee

                run_sql("""
                    INSERT INTO orders
                    (product_id, seller_id, buyer_id, order_type, status, item_price, shipping_price, platform_fee, seller_payout, buyer_message, created_at, updated_at)
                    VALUES (?, ?, ?, ?, 'New', ?, ?, ?, ?, ?, ?, ?)
                """, (
                    int(product["id"]),
                    int(product["seller_id"]),
                    int(buyer_id),
                    action,
                    item_price,
                    shipping_price,
                    fee,
                    payout,
                    message,
                    now(),
                    now(),
                ))
                st.success("Sent to seller.")

    with st.expander("Save / Favorite this item"):
        favorite_buyer_id = choose_buyer(f"favorite_{int(product['id'])}")
        if st.button("Save Item", key=f"save_item_{int(product['id'])}"):
            if favorite_buyer_id is None:
                st.error("Register as a buyer first.")
            else:
                run_sql(
                    "INSERT INTO favorites (buyer_id, item_type, item_id, created_at) VALUES (?, 'Product', ?, ?)",
                    (int(favorite_buyer_id), int(product["id"]), now())
                )
                st.success("Item saved to buyer favorites.")

    with st.expander("Report this listing"):
        reason = st.selectbox(
            "Report reason",
            ["Counterfeit / Bootleg", "Misgraded Condition", "Wrong Information", "Offensive Content", "Spam / Scam", "Prohibited Item", "Other"],
            key=f"flag_reason_{int(product['id'])}"
        )
        details = st.text_area("Details", key=f"flag_details_{int(product['id'])}")
        flag_buyer_id = choose_buyer(f"flag_{int(product['id'])}")

        if st.button("Submit Listing Report", key=f"flag_button_{int(product['id'])}"):
            if flag_buyer_id is None:
                st.error("Register as a buyer before reporting.")
            else:
                run_sql("""
                    INSERT INTO listing_flags
                    (product_id, seller_id, buyer_id, reason, details, status, created_at)
                    VALUES (?, ?, ?, ?, ?, 'Open', ?)
                """, (
                    int(product["id"]),
                    int(product["seller_id"]),
                    int(flag_buyer_id),
                    reason,
                    details,
                    now(),
                ))
                run_sql("UPDATE products SET listing_status = 'Flagged' WHERE id = ?", (int(product["id"]),))
                st.success("Listing reported to House Of Wax.")

    if seller is not None:
        with st.expander("Report this seller"):
            reason = st.selectbox(
                "Seller report reason",
                ["Scam Concern", "Abusive Communication", "Repeated Misgrading", "Not Shipping", "Prohibited Items", "Fee Avoidance", "Other"],
                key=f"seller_report_reason_{int(product['id'])}"
            )
            details = st.text_area("Report details", key=f"seller_report_details_{int(product['id'])}")
            report_buyer_id = choose_buyer(f"seller_report_{int(product['id'])}")
            if st.button("Submit Seller Report", key=f"seller_report_button_{int(product['id'])}"):
                if report_buyer_id is None:
                    st.error("Register as a buyer before reporting.")
                else:
                    run_sql("""
                        INSERT INTO seller_reports
                        (seller_id, buyer_id, reason, details, status, created_at)
                        VALUES (?, ?, ?, ?, 'Open', ?)
                    """, (int(seller["id"]), int(report_buyer_id), reason, details, now()))
                    st.success("Seller report submitted.")


# -----------------------------
# Public pages
# -----------------------------
def home_page():
    render_header()

    products = get_table("products")
    sellers = get_table("sellers")
    buyers = get_table("buyers")
    auctions = get_table("auctions")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Listings", len(products))
    col2.metric("Sellers", len(sellers))
    col3.metric("Buyers", len(buyers))
    col4.metric("Auctions", len(auctions))

    st.markdown("""
    ## A seller-powered music and culture marketplace.

    House Of Wax lets independent sellers build their own stores, upload their own products, set prices, manage shipping, and handle customer service.

    House Of Wax controls the platform rules, seller approval, buyer accountability, flagged listing review, fees, auction eligibility, and music-culture experience.
    """)


def marketplace_page():
    render_header()
    st.header("Marketplace")

    products = get_df("SELECT * FROM products WHERE listing_status = 'Active' AND quantity > 0 ORDER BY created_at DESC")
    if products.empty:
        st.info("No active marketplace listings yet.")
        return

    if "selected_product_id" in st.session_state:
        selected = products[products["id"] == int(st.session_state["selected_product_id"])]
        if not selected.empty:
            product_detail(selected.iloc[0])
            return
        del st.session_state["selected_product_id"]

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

    columns = st.columns(3)
    for index, (_, product) in enumerate(filtered.iterrows()):
        with columns[index % 3]:
            product_card(product)


def auctions_page():
    render_header()
    st.header("Auctions")
    st.caption("Auctions are earned by seller performance. Sellers do not get auction access automatically.")

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
            image_url = safe(auction.get("image_url"))
            if image_url:
                st.image(image_url, width=250)

            st.subheader(safe(auction.get("auction_title")))
            st.caption(f"{safe(auction.get('artist'))} — {safe(auction.get('title'))} • Seller: {safe(auction.get('store_name'))}")

            high = get_df("SELECT MAX(bid_amount) AS high_bid FROM bids WHERE auction_id = ?", (int(auction["id"]),))
            high_bid = high.iloc[0]["high_bid"]
            current_bid = float(high_bid) if pd.notna(high_bid) else float(auction["starting_bid"] or 0)

            st.write(f"**Current bid:** {money(current_bid)}")
            st.write(f"**Ends:** {safe(auction.get('end_time'))}")

            buyer_id = choose_buyer(f"auction_{int(auction['id'])}")
            next_bid = st.number_input(
                "Bid amount",
                min_value=current_bid + float(auction["bid_increment"] or 1),
                step=float(auction["bid_increment"] or 1),
                key=f"bid_amount_{int(auction['id'])}"
            )

            if st.button("Place Bid", key=f"place_bid_{int(auction['id'])}"):
                if buyer_id is None:
                    st.error("Register as a buyer first.")
                else:
                    buyer = get_buyer(buyer_id)
                    allowed, reason = buyer_allowed(buyer)
                    if not allowed:
                        st.error(reason)
                    else:
                        run_sql(
                            "INSERT INTO bids (auction_id, buyer_id, bid_amount, bid_time) VALUES (?, ?, ?, ?)",
                            (int(auction["id"]), int(buyer_id), float(next_bid), now())
                        )
                        st.success("Bid placed.")


def seller_stores_page():
    render_header()
    st.header("Seller Stores")

    sellers = get_df("SELECT * FROM sellers WHERE status = 'Approved' ORDER BY store_name")
    if sellers.empty:
        st.info("No approved seller stores yet.")
        return

    for _, seller in sellers.iterrows():
        with st.container(border=True):
            banner_url = safe(seller.get("banner_url"))
            if banner_url:
                st.image(banner_url, use_container_width=True)

            col1, col2 = st.columns([1, 4])
            with col1:
                logo_url = safe(seller.get("logo_url"))
                if logo_url:
                    st.image(logo_url, use_container_width=True)
                else:
                    st.markdown("### 🏪")

            with col2:
                st.subheader(safe(seller.get("store_name")))
                st.caption(f"{safe(seller.get('seller_level'))} • Rating {seller.get('rating')}% • Sales {seller.get('completed_sales')}")
                st.write(safe(seller.get("store_bio"), "Independent seller on House Of Wax."))

            report_buyer_id = choose_buyer(f"store_report_{int(seller['id'])}")
            with st.expander(f"Report {safe(seller.get('store_name'))}"):
                reason = st.selectbox(
                    "Reason",
                    ["Scam Concern", "Abusive Communication", "Repeated Misgrading", "Not Shipping", "Prohibited Items", "Fee Avoidance", "Other"],
                    key=f"store_report_reason_{int(seller['id'])}"
                )
                details = st.text_area("Details", key=f"store_report_details_{int(seller['id'])}")
                if st.button("Submit Seller Report", key=f"store_report_button_{int(seller['id'])}"):
                    if report_buyer_id is None:
                        st.error("Register as a buyer before reporting.")
                    else:
                        run_sql(
                            "INSERT INTO seller_reports (seller_id, buyer_id, reason, details, status, created_at) VALUES (?, ?, ?, ?, 'Open', ?)",
                            (int(seller["id"]), int(report_buyer_id), reason, details, now())
                        )
                        st.success("Seller report submitted.")


def culture_page():
    render_header()
    st.header("Music + Culture")

    posts = get_df("SELECT * FROM culture_posts WHERE status = 'Published' ORDER BY created_at DESC")
    if posts.empty:
        st.info("No culture posts yet. Admin can add artist stories, collecting guides, seller spotlights, clothing/culture posts, and auction previews.")
        return

    for _, post in posts.iterrows():
        with st.container(border=True):
            image_url = safe(post.get("image_url"))
            if image_url:
                st.image(image_url, use_container_width=True)
            st.subheader(safe(post.get("title")))
            st.caption(f"{safe(post.get('category'))} • {safe(post.get('author'))}")
            st.write(safe(post.get("body")))


def register_page():
    render_header()
    st.header("Register / Sell on House Of Wax")

    buyer_tab, seller_tab = st.tabs(["Buyer Registration", "Seller Application"])

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
                st.warning("This buyer email is already registered. Please use a different email or open the Buyer Dashboard with this account.")
            else:
                try:
                    run_sql(
                        "INSERT INTO buyers (name, email, phone, city, created_at) VALUES (?, ?, ?, ?, ?)",
                        (name, email, phone, city, now())
                    )
                    st.success("Buyer account created.")
                except Exception:
                    st.error("Could not create buyer account. Please check the information and try again.")

    with seller_tab:
        st.subheader("Apply to Sell")
        st.write("Sellers are approved by House Of Wax. Once approved, sellers can publish fixed-price listings without every product being manually approved.")

        with st.form("seller_application"):
            store_name = st.text_input("Store name")
            owner = st.text_input("Owner name")
            email = st.text_input("Seller email")
            phone = st.text_input("Phone")
            city = st.text_input("City")
            bio = st.text_area("Store bio / what you sell")
            access_code = st.text_input("Choose private seller access code", type="password")
            agree = st.checkbox("I agree to House Of Wax platform rules. My store policies can be stronger than platform rules, but never weaker.")
            submitted = st.form_submit_button("Submit Seller Application")

        if submitted:
            if not store_name or not email or not access_code:
                st.error("Store name, email, and access code are required.")
            elif email_exists("sellers", email):
                st.warning("This seller email is already registered or already applied. Please use the Seller Dashboard or contact House Of Wax.")
            elif not agree:
                st.error("You must agree to platform rules.")
            else:
                try:
                    run_sql("""
                        INSERT INTO sellers
                        (store_name, owner_name, email, phone, city, store_bio, access_code, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (store_name, owner, email, phone, city, bio, access_code, now()))
                    st.success("Your seller application has been submitted. House Of Wax must approve your store before you can list products. Save your seller email and access code.")
                except Exception:
                    st.error("Could not submit seller application. Please check the information and try again.")


def buyer_dashboard_page():
    render_header()
    st.header("Buyer Dashboard")

    email = st.text_input("Buyer email")
    if not st.button("Open Buyer Dashboard"):
        return

    buyer_df = get_df("SELECT * FROM buyers WHERE lower(email)=lower(?)", (email.strip(),))
    if buyer_df.empty:
        st.error("No buyer found with this email. Please register first.")
        return

    buyer = buyer_df.iloc[0]
    buyer_id = int(buyer["id"])

    st.success(f"Buyer account: {safe(buyer['name'])}")
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Status", safe(buyer["status"]))
    col2.metric("Rating", f"{buyer['rating']}%")
    col3.metric("Completed Purchases", buyer["completed_purchases"])
    col4.metric("Unpaid Orders", buyer["unpaid_orders"])
    col5.metric("Strikes", buyer["strikes"])

    tabs = st.tabs(["Profile", "Purchase Requests", "Bids", "Favorites", "Disputes", "Rules"])

    with tabs[0]:
        st.subheader("Profile")
        with st.form("buyer_profile_form"):
            name = st.text_input("Name", value=safe(buyer["name"]))
            phone = st.text_input("Phone", value=safe(buyer["phone"]))
            city = st.text_input("City", value=safe(buyer["city"]))
            submitted = st.form_submit_button("Update Profile")
        if submitted:
            run_sql("UPDATE buyers SET name=?, phone=?, city=? WHERE id=?", (name, phone, city, buyer_id))
            st.success("Buyer profile updated.")

    with tabs[1]:
        st.subheader("Purchase Requests")
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
        st.subheader("Bids")
        bids = get_df("""
            SELECT b.*, a.auction_title
            FROM bids b
            LEFT JOIN auctions a ON b.auction_id = a.id
            WHERE b.buyer_id = ?
            ORDER BY b.bid_time DESC
        """, (buyer_id,))
        st.dataframe(bids, use_container_width=True)

    with tabs[3]:
        st.subheader("Favorites")
        favs = get_df("""
            SELECT f.*, p.artist, p.title, p.price
            FROM favorites f
            LEFT JOIN products p ON f.item_id = p.id
            WHERE f.buyer_id = ? AND f.item_type = 'Product'
            ORDER BY f.created_at DESC
        """, (buyer_id,))
        st.dataframe(favs, use_container_width=True)

    with tabs[4]:
        st.subheader("Disputes")
        disputes = get_df("SELECT * FROM disputes WHERE buyer_id = ? ORDER BY created_at DESC", (buyer_id,))
        st.dataframe(disputes, use_container_width=True)

    with tabs[5]:
        st.subheader("Buyer Rules")
        st.markdown("""
        Buyers must pay for purchases and auction wins, communicate respectfully, and not abuse returns, disputes, chargebacks, or feedback.

        Buyers can be rated, restricted, or suspended for unpaid orders, false claims, harassment, or repeated marketplace abuse.
        """)


# -----------------------------
# Seller dashboard
# -----------------------------
def seller_dashboard_page():
    render_header()
    st.header("Seller Dashboard")

    email = st.text_input("Seller email")
    access_code = st.text_input("Seller access code", type="password")

    if not st.button("Enter Seller Dashboard"):
        return

    seller_df = get_df("SELECT * FROM sellers WHERE email = ? AND access_code = ?", (email, access_code))
    if seller_df.empty:
        st.error("Seller not found or access code is wrong.")
        return

    seller = seller_df.iloc[0]
    if seller["status"] != "Approved":
        st.warning(f"Seller status is {seller['status']}. House Of Wax Admin must approve your store before you can sell.")
        return

    seller_workspace(seller)


def seller_workspace(seller):
    seller_id = int(seller["id"])
    st.success(f"Logged in as {seller['store_name']}")

    tabs = st.tabs([
        "My Store",
        "Store Policies",
        "Add Product",
        "My Listings",
        "My Auctions",
        "Orders",
        "Social Posts",
        "Rules"
    ])

    with tabs[0]:
        st.subheader("My Store")
        with st.form("store_profile"):
            store_name = st.text_input("Store name", value=safe(seller.get("store_name")))
            bio = st.text_area("Store bio", value=safe(seller.get("store_bio")))
            logo = st.text_input("Logo URL", value=safe(seller.get("logo_url")))
            banner = st.text_input("Banner URL", value=safe(seller.get("banner_url")))
            submitted = st.form_submit_button("Save Store Profile")

        if submitted:
            run_sql(
                "UPDATE sellers SET store_name=?, store_bio=?, logo_url=?, banner_url=? WHERE id=?",
                (store_name, bio, logo, banner, seller_id)
            )
            st.success("Store profile saved.")

    with tabs[1]:
        st.subheader("Store Policies")
        st.caption("Seller rules can be stronger than House Of Wax rules, but never weaker.")

        templates = {
            "Standard Shipping Policy": "Orders are usually processed within 3 business days. Tracking will be provided when available. Items are packed carefully to protect records, sleeves, clothing, and collectibles.",
            "No Buyer Remorse Returns": "Returns are not accepted for buyer remorse, including changed mind, found cheaper elsewhere, or failure to read the listing. If an item is significantly not as described, contact the seller promptly.",
            "Buyer Pays Return Shipping": "If a return is approved, the buyer is responsible for return shipping unless the item was significantly not as described or damaged due to seller packaging.",
            "Local Pickup Available": "Local pickup may be available by appointment. Buyer and seller must agree on time, location, and pickup expectations before completing the transaction.",
            "Vinyl Grading Policy": "Records are graded using common collector standards. Buyers should review media grade, sleeve grade, photos, and condition notes before purchase.",
            "Clothing Condition Policy": "Clothing is described by size, condition, visible wear, and flaws when known. Buyers should review photos and measurements before purchase."
        }
        with st.expander("Policy Templates"):
            for name, text in templates.items():
                st.write(f"**{name}**")
                st.code(text)

        policy_df = get_df("SELECT * FROM seller_policies WHERE seller_id = ?", (seller_id,))
        policy = policy_df.iloc[0] if not policy_df.empty else {}

        with st.form("store_policies"):
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
            """, (
                seller_id,
                shipping,
                returns,
                grading,
                service,
                bundle,
                auction_policy,
                buyer_requirements,
                pickup,
                international,
                processing,
            ))
            st.success("Store policies saved.")

    with tabs[2]:
        st.subheader("Add Product")
        with st.form("add_product"):
            col1, col2, col3 = st.columns(3)
            sku = col1.text_input("SKU")
            barcode = col2.text_input("Barcode / UPC / EAN")
            catalog = col3.text_input("Catalog number")

            matrix = st.text_input("Matrix / runout")

            col4, col5, col6 = st.columns(3)
            category = col4.selectbox("Category", [
                "Vinyl Records",
                "CDs",
                "Cassettes",
                "Music DVDs/VHS",
                "Music Books/Magazines",
                "Posters",
                "Music Memorabilia",
                "Vintage Clothing",
                "Streetwear",
                "Band Tees",
                "DJ Gear/Accessories",
                "Culture Goods"
            ])
            artist = col5.text_input("Artist / Brand")
            title = col6.text_input("Title / Product Name")

            col7, col8, col9 = st.columns(3)
            format_name = col7.text_input("Format", value="Vinyl")
            label = col8.text_input("Label / Brand")
            year = col9.text_input("Year")

            genre = st.text_input("Genre / Style")

            col10, col11 = st.columns(2)
            media_grade = col10.selectbox("Media/Product grade", ["Mint", "Near Mint", "VG+", "VG", "Good", "Fair", "Poor", "New", "Used", "N/A"])
            sleeve_grade = col11.selectbox("Sleeve/Packaging grade", ["Mint", "Near Mint", "VG+", "VG", "Good", "Fair", "Poor", "New", "Used", "N/A"])

            notes = st.text_area("Condition notes")

            generated = generate_description({
                "artist": artist,
                "title": title,
                "format": format_name,
                "genre": genre,
                "label": label,
                "release_year": year,
                "media_grade": media_grade,
                "sleeve_grade": sleeve_grade,
                "barcode": barcode,
                "catalog_number": catalog,
                "matrix_runout": matrix,
                "condition_notes": notes,
            })
            description = st.text_area("Description", value=generated, height=180)

            col12, col13, col14 = st.columns(3)
            price = col12.number_input("Price", min_value=0.0, step=0.01)
            quantity = col13.number_input("Quantity", min_value=1, value=1)
            shipping_price = col14.number_input("Shipping price", min_value=0.0, step=0.01)

            image_url = st.text_input("Main image URL")
            video_url = st.text_input("Video URL")
            audio_url = st.text_input("Audio URL")
            external_url = st.text_input("Discogs / MusicBrainz / research URL")
            status = st.selectbox("Listing status", ["Active", "Draft"])

            submitted = st.form_submit_button("Save Product")

        if submitted:
            run_sql("""
                INSERT INTO products
                (seller_id, sku, barcode, catalog_number, matrix_runout, category, artist, title, format, label, release_year, genre, media_grade, sleeve_grade, condition_notes, description, price, quantity, shipping_price, image_url, video_url, audio_url, external_release_url, listing_status, listing_type, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Fixed Price', ?, ?)
            """, (
                seller_id,
                sku,
                barcode,
                catalog,
                matrix,
                category,
                artist,
                title,
                format_name,
                label,
                year,
                genre,
                media_grade,
                sleeve_grade,
                notes,
                description,
                float(price),
                int(quantity),
                float(shipping_price),
                image_url,
                video_url,
                audio_url,
                external_url,
                status,
                now(),
                now(),
            ))
            st.success("Product saved. Approved sellers can publish fixed-price listings without manual approval.")

    with tabs[3]:
        st.subheader("My Listings")
        products = get_df("SELECT * FROM products WHERE seller_id = ? ORDER BY created_at DESC", (seller_id,))
        st.dataframe(products, use_container_width=True)

        if not products.empty:
            product_id = st.selectbox("Product ID", products["id"].tolist())
            new_status = st.selectbox("New status", ["Active", "Draft", "Sold", "Removed"])
            if st.button("Update Listing Status"):
                run_sql(
                    "UPDATE products SET listing_status=?, updated_at=? WHERE id=? AND seller_id=?",
                    (new_status, now(), int(product_id), seller_id)
                )
                st.success("Listing updated.")

    with tabs[4]:
        st.subheader("My Auctions")
        eligible, reason = auction_eligible(seller)
        if eligible:
            st.success(f"Auction eligible: {reason}")
        else:
            st.warning(f"Not auction eligible yet: {reason}")

        progress = auction_progress(seller)
        for label, (current, required, passed) in progress.items():
            if label in ["Strikes", "Disputes"]:
                st.write(f"{'✅' if passed else '❌'} {label}: {current} / required {required}")
            else:
                st.write(f"{'✅' if passed else '❌'} {label}: {current} / {required}")

        products = get_df("SELECT * FROM products WHERE seller_id = ? AND listing_status = 'Active'", (seller_id,))
        if eligible and not products.empty:
            with st.form("create_auction"):
                product_id = st.selectbox("Product", products["id"].tolist())
                auction_title = st.text_input("Auction title")
                col1, col2, col3, col4 = st.columns(4)
                starting_bid = col1.number_input("Starting bid", min_value=0.0, step=1.0)
                reserve_price = col2.number_input("Reserve price", min_value=0.0, step=1.0)
                buy_now_price = col3.number_input("Buy-now price", min_value=0.0, step=1.0)
                bid_increment = col4.number_input("Bid increment", min_value=1.0, step=1.0)
                start_time = st.text_input("Start time", value=now())
                end_time = st.text_input("End time")
                status = st.selectbox("Auction status", ["Draft", "Live"])
                notes = st.text_area("Auction notes")
                submitted = st.form_submit_button("Create Auction")

            if submitted:
                run_sql("""
                    INSERT INTO auctions
                    (product_id, seller_id, auction_title, starting_bid, reserve_price, buy_now_price, bid_increment, start_time, end_time, status, notes, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    int(product_id),
                    seller_id,
                    auction_title,
                    starting_bid,
                    reserve_price,
                    buy_now_price,
                    bid_increment,
                    start_time,
                    end_time,
                    status,
                    notes,
                    now(),
                ))
                st.success("Auction saved.")

        st.dataframe(get_df("SELECT * FROM auctions WHERE seller_id = ?", (seller_id,)), use_container_width=True)

    with tabs[5]:
        st.subheader("Orders")
        orders = get_df("""
            SELECT o.*, b.name AS buyer_name, b.email AS buyer_email, b.status AS buyer_status, b.rating AS buyer_rating,
                   b.unpaid_orders AS buyer_unpaid_orders, b.strikes AS buyer_strikes,
                   p.artist, p.title
            FROM orders o
            LEFT JOIN buyers b ON o.buyer_id = b.id
            LEFT JOIN products p ON o.product_id = p.id
            WHERE o.seller_id = ?
            ORDER BY o.created_at DESC
        """, (seller_id,))
        st.dataframe(orders, use_container_width=True)

        if not orders.empty:
            order_id = st.selectbox("Order ID to manage", orders["id"].tolist(), key="seller_order_manage")
            new_status = st.selectbox("Update order status", ["New", "Contacted", "Invoice Sent", "Paid", "Shipped", "Completed", "Cancelled", "Disputed"], key="seller_order_status")
            if st.button("Update Order Status"):
                run_sql("UPDATE orders SET status=?, updated_at=? WHERE id=? AND seller_id=?", (new_status, now(), int(order_id), seller_id))
                if new_status == "Completed":
                    order = orders[orders["id"] == order_id].iloc[0]
                    run_sql("UPDATE sellers SET completed_sales = completed_sales + 1 WHERE id = ?", (seller_id,))
                    run_sql("UPDATE buyers SET completed_purchases = completed_purchases + 1 WHERE id = ?", (int(order["buyer_id"]),))
                st.success("Order status updated.")

            if st.button("Mark Buyer as Non-Paying"):
                order = orders[orders["id"] == order_id].iloc[0]
                run_sql("UPDATE buyers SET unpaid_orders = unpaid_orders + 1, strikes = strikes + 1 WHERE id = ?", (int(order["buyer_id"]),))
                run_sql("UPDATE orders SET status='Cancelled', updated_at=? WHERE id=? AND seller_id=?", (now(), int(order_id), seller_id))
                st.warning("Buyer marked as non-paying. Buyer unpaid order count and strikes were increased.")

    with tabs[6]:
        st.subheader("Social Posts")
        products = get_df("SELECT * FROM products WHERE seller_id = ?", (seller_id,))
        if products.empty:
            st.info("Add a product first.")
        else:
            product_id = st.selectbox("Product to promote", products["id"].tolist())
            product = products[products["id"] == product_id].iloc[0]
            caption = f"Now on House Of Wax: {safe(product.get('artist'))} — {safe(product.get('title'))}. Condition: {safe(product.get('media_grade'))}. Price: {money(product.get('price'))}."
            hashtags = "#HouseOfWax #MusicMarketplace #VinylMarketplace #MusicCulture"

            st.text_area("Caption", value=caption, height=120)
            st.text_input("Hashtags", value=hashtags)
            platform = st.selectbox("Platform", ["Instagram", "TikTok", "Facebook", "X", "Email", "Buffer Queue"])

            if st.button("Save Social Draft"):
                run_sql(
                    "INSERT INTO social_posts (product_id, seller_id, platform, caption, hashtags, status, created_at) VALUES (?, ?, ?, ?, ?, 'Draft', ?)",
                    (int(product_id), seller_id, platform, caption, hashtags, now())
                )
                st.success("Social draft saved.")

    with tabs[7]:
        st.subheader("Rules")
        st.markdown("""
        **Seller freedom:** Sellers can create shipping, returns, grading, customer service, bundle, auction, local pickup, international shipping, and buyer requirement policies.

        **House Of Wax minimum:** Seller rules can be stronger or more generous than platform rules, but never weaker.
        """)


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
    tabs = st.tabs([
        "Overview",
        "Seller Applications",
        "Seller Management",
        "Buyer Management",
        "Flagged Listings",
        "Seller Reports",
        "Orders",
        "Auctions",
        "Culture Content",
        "Platform Rules",
        "Fees & Settings",
        "Reports",
        "Testing Cleanup",
        "Business Planning"
    ])

    with tabs[0]:
        st.subheader("Platform Overview")
        sellers = get_table("sellers")
        buyers = get_table("buyers")
        products = get_table("products")
        orders = get_table("orders")
        flags = get_table("listing_flags")
        seller_reports = get_table("seller_reports")

        pending_sellers = len(sellers[sellers["status"] == "Pending"]) if not sellers.empty else 0
        open_flags = len(flags[flags["status"] == "Open"]) if not flags.empty else 0
        open_seller_reports = len(seller_reports[seller_reports["status"] == "Open"]) if not seller_reports.empty else 0
        restricted_buyers = len(buyers[buyers["status"].isin(["Restricted Buyer", "Suspended Buyer"])]) if not buyers.empty else 0

        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Sellers", len(sellers))
        col2.metric("Buyers", len(buyers))
        col3.metric("Products", len(products))
        col4.metric("Orders", len(orders))
        col5.metric("Open Flags", open_flags + open_seller_reports)

        st.success(f"Admin loaded successfully. Running {APP_VERSION}.")
        if pending_sellers:
            st.warning(f"{pending_sellers} seller application(s) need review.")
        if open_flags:
            st.warning(f"{open_flags} flagged listing(s) need review.")
        if open_seller_reports:
            st.warning(f"{open_seller_reports} seller report(s) need review.")
        if restricted_buyers:
            st.warning(f"{restricted_buyers} buyer account(s) are restricted or suspended.")

    with tabs[1]:
        st.subheader("Seller Applications")
        pending = get_df("SELECT * FROM sellers WHERE status = 'Pending'")
        st.dataframe(pending, use_container_width=True)

        if not pending.empty:
            seller_id = st.selectbox("Seller ID to review", pending["id"].tolist())
            decision = st.selectbox("Decision", ["Approved", "Rejected"])
            if st.button("Save Seller Decision"):
                level = "Approved Seller" if decision == "Approved" else "Rejected"
                run_sql(
                    "UPDATE sellers SET status=?, seller_level=? WHERE id=?",
                    (decision, level, int(seller_id))
                )
                st.success("Seller updated.")

    with tabs[2]:
        st.subheader("Seller Management")
        sellers = get_table("sellers")
        st.dataframe(sellers, use_container_width=True)

        if not sellers.empty:
            seller_id = st.selectbox("Manage seller ID", sellers["id"].tolist(), key="admin_seller")
            status = st.selectbox("Seller status", ["Pending", "Approved", "Suspended", "Rejected", "Verified"])
            auction_override = st.selectbox("Auction override", ["No", "Yes"])
            completed_sales = st.number_input("Completed sales", min_value=0, step=1)
            rating = st.number_input("Seller rating", min_value=0.0, max_value=100.0, value=100.0)
            strikes = st.number_input("Seller strikes", min_value=0, step=1)
            disputes = st.number_input("Seller disputes", min_value=0, step=1)

            if st.button("Update Seller"):
                run_sql(
                    "UPDATE sellers SET status=?, auction_override=?, completed_sales=?, rating=?, strikes=?, disputes=? WHERE id=?",
                    (status, auction_override, int(completed_sales), float(rating), int(strikes), int(disputes), int(seller_id))
                )
                st.success("Seller updated.")

    with tabs[3]:
        st.subheader("Buyer Management")
        buyers = get_table("buyers")
        st.dataframe(buyers, use_container_width=True)

        if not buyers.empty:
            buyer_id = st.selectbox("Manage buyer ID", buyers["id"].tolist(), key="admin_buyer")
            status = st.selectbox("Buyer status", ["New Buyer", "Verified Buyer", "Trusted Buyer", "Restricted Buyer", "Suspended Buyer"])
            rating = st.number_input("Buyer rating", min_value=0.0, max_value=100.0, value=100.0, key="buyer_rating_admin")
            unpaid = st.number_input("Unpaid orders", min_value=0, step=1)
            strikes = st.number_input("Buyer strikes", min_value=0, step=1, key="buyer_strikes_admin")

            if st.button("Update Buyer"):
                run_sql(
                    "UPDATE buyers SET status=?, rating=?, unpaid_orders=?, strikes=? WHERE id=?",
                    (status, float(rating), int(unpaid), int(strikes), int(buyer_id))
                )
                st.success("Buyer updated.")

    with tabs[4]:
        st.subheader("Flagged Listings")
        flags = get_df("""
            SELECT f.*, p.artist, p.title, s.store_name
            FROM listing_flags f
            LEFT JOIN products p ON f.product_id = p.id
            LEFT JOIN sellers s ON f.seller_id = s.id
            ORDER BY f.created_at DESC
        """)
        st.dataframe(flags, use_container_width=True)

        if not flags.empty:
            flag_id = st.selectbox("Flag ID", flags["id"].tolist())
            decision = st.selectbox("Decision", ["Dismiss", "Keep Under Review", "Remove Listing", "Suspend Seller", "Issue Seller Strike"])
            notes = st.text_area("Admin notes")

            if st.button("Resolve Flag"):
                flag = flags[flags["id"] == flag_id].iloc[0]

                if decision == "Remove Listing":
                    run_sql("UPDATE products SET listing_status = 'Removed' WHERE id = ?", (int(flag["product_id"]),))
                if decision == "Suspend Seller":
                    run_sql("UPDATE sellers SET status = 'Suspended' WHERE id = ?", (int(flag["seller_id"]),))
                if decision == "Issue Seller Strike":
                    run_sql("UPDATE sellers SET strikes = strikes + 1 WHERE id = ?", (int(flag["seller_id"]),))

                run_sql(
                    "UPDATE listing_flags SET status=?, admin_notes=? WHERE id=?",
                    (decision, notes, int(flag_id))
                )
                st.success("Flag resolved.")

    with tabs[5]:
        st.subheader("Seller Reports")
        reports = get_df("""
            SELECT r.*, s.store_name, b.name AS buyer_name, b.email AS buyer_email
            FROM seller_reports r
            LEFT JOIN sellers s ON r.seller_id = s.id
            LEFT JOIN buyers b ON r.buyer_id = b.id
            ORDER BY r.created_at DESC
        """)
        st.dataframe(reports, use_container_width=True)
        if not reports.empty:
            report_id = st.selectbox("Report ID", reports["id"].tolist())
            decision = st.selectbox("Report Decision", ["Dismiss", "Keep Under Review", "Suspend Seller", "Issue Seller Strike"])
            notes = st.text_area("Report admin notes")
            if st.button("Resolve Seller Report"):
                report = reports[reports["id"] == report_id].iloc[0]
                if decision == "Suspend Seller":
                    run_sql("UPDATE sellers SET status='Suspended' WHERE id=?", (int(report["seller_id"]),))
                if decision == "Issue Seller Strike":
                    run_sql("UPDATE sellers SET strikes = strikes + 1 WHERE id=?", (int(report["seller_id"]),))
                run_sql("UPDATE seller_reports SET status=?, admin_notes=? WHERE id=?", (decision, notes, int(report_id)))
                st.success("Seller report resolved.")

    with tabs[6]:
        st.subheader("Orders")
        orders = get_table("orders")
        st.dataframe(orders, use_container_width=True)

        if not orders.empty:
            order_id = st.selectbox("Order ID", orders["id"].tolist())
            status = st.selectbox("Order status", ["New", "Contacted", "Invoice Sent", "Paid", "Shipped", "Completed", "Cancelled", "Disputed"])

            if st.button("Update Order"):
                run_sql(
                    "UPDATE orders SET status=?, updated_at=? WHERE id=?",
                    (status, now(), int(order_id))
                )

                if status == "Completed":
                    order = orders[orders["id"] == order_id].iloc[0]
                    run_sql("UPDATE sellers SET completed_sales = completed_sales + 1 WHERE id = ?", (int(order["seller_id"]),))
                    run_sql("UPDATE buyers SET completed_purchases = completed_purchases + 1 WHERE id = ?", (int(order["buyer_id"]),))

                st.success("Order updated.")

    with tabs[7]:
        st.subheader("Auctions")
        auctions = get_table("auctions")
        st.dataframe(auctions, use_container_width=True)

    with tabs[8]:
        st.subheader("Culture Content")
        with st.form("culture_form"):
            title = st.text_input("Title")
            category = st.selectbox("Category", ["Music", "Clothing", "Culture", "Collecting Guide", "Seller Spotlight", "Auction Preview", "Regional History"])
            author = st.text_input("Author", value="House Of Wax")
            image_url = st.text_input("Image URL")
            body = st.text_area("Body", height=200)
            submitted = st.form_submit_button("Publish Culture Post")

        if submitted:
            run_sql(
                "INSERT INTO culture_posts (title, category, author, body, image_url, status, created_at) VALUES (?, ?, ?, ?, ?, 'Published', ?)",
                (title, category, author, body, image_url, now())
            )
            st.success("Culture post published.")

        st.dataframe(get_table("culture_posts"), use_container_width=True)

    with tabs[9]:
        st.subheader("Platform Rules")
        rules = get_table("platform_rules")
        st.dataframe(rules, use_container_width=True)

        with st.form("new_rule_form"):
            title = st.text_input("Rule title")
            category = st.selectbox("Rule category", ["Seller Rules", "Buyer Rules", "Listings", "Auctions", "Fees", "Trust & Safety", "Other"])
            rule_text = st.text_area("Rule text")
            active = st.selectbox("Active", ["Yes", "No"])
            submitted = st.form_submit_button("Add / Save Rule")
        if submitted:
            run_sql(
                "INSERT INTO platform_rules (title, category, rule_text, active, created_at) VALUES (?, ?, ?, ?, ?)",
                (title, category, rule_text, active, now())
            )
            st.success("Rule added.")

    with tabs[10]:
        st.subheader("Fees & Settings")
        with st.form("settings_form"):
            commission = st.text_input("Platform commission %", value=get_setting("platform_commission_percent", "9"))
            auction_commission = st.text_input("Auction commission %", value=get_setting("auction_commission_percent", "10"))
            min_sales = st.text_input("Auction minimum completed sales", value=get_setting("auction_min_completed_sales", "10"))
            min_rating = st.text_input("Auction minimum seller rating", value=get_setting("auction_min_rating", "90"))
            logo_url = st.text_input("Logo URL", value=get_setting("logo_url", ""))
            tagline = st.text_input("Site tagline", value=get_setting("site_tagline", ""))
            announcement = st.text_area("Announcement", value=get_setting("announcement", ""))
            submitted = st.form_submit_button("Save Settings")

        if submitted:
            save_setting("platform_commission_percent", commission)
            save_setting("auction_commission_percent", auction_commission)
            save_setting("auction_min_completed_sales", min_sales)
            save_setting("auction_min_rating", min_rating)
            save_setting("logo_url", logo_url)
            save_setting("site_tagline", tagline)
            save_setting("announcement", announcement)
            st.success("Settings saved.")

    with tabs[11]:
        st.subheader("Reports")
        report = st.selectbox("Report", [
            "sellers",
            "seller_policies",
            "buyers",
            "products",
            "orders",
            "listing_flags",
            "seller_reports",
            "favorites",
            "auctions",
            "bids",
            "culture_posts",
            "disputes",
            "social_posts",
            "platform_rules",
        ])
        data = get_table(report)
        st.dataframe(data, use_container_width=True)
        csv = data.to_csv(index=False)
        st.download_button("Download CSV", csv, file_name=f"{report}.csv")

        st.subheader("Business Summary Reports")
        if not get_table("orders").empty:
            orders = get_table("orders")
            st.metric("Estimated Platform Fees", money(orders["platform_fee"].sum()))
            st.metric("Estimated Seller Payouts", money(orders["seller_payout"].sum()))
            st.download_button("Download Orders Business Summary", orders.to_csv(index=False), file_name="house_of_wax_orders_business_summary.csv")

    with tabs[12]:
        st.subheader("Testing Cleanup Tools")
        st.warning("Use these tools only for testing. Deletes cannot be undone.")

        col1, col2 = st.columns(2)
        with col1:
            table_to_clean = st.selectbox("Table", ["buyers", "sellers", "products", "orders", "listing_flags", "seller_reports", "favorites", "auctions", "bids", "culture_posts", "disputes", "social_posts"])
            rows = get_table(table_to_clean)
            st.dataframe(rows, use_container_width=True)
        with col2:
            if not rows.empty:
                row_id = st.selectbox("Row ID to delete", rows["id"].tolist())
                confirm = st.checkbox("I understand this will delete the selected row.")
                if st.button("Delete Selected Row"):
                    if confirm:
                        delete_by_id(table_to_clean, row_id)
                        st.success(f"Deleted row {row_id} from {table_to_clean}.")
                    else:
                        st.error("Check the confirmation box first.")

        st.divider()
        confirm_all = st.checkbox("I understand this will clear most test data.")
        if st.button("Clear Test Data"):
            if confirm_all:
                for table_name in ["orders", "listing_flags", "seller_reports", "favorites", "auctions", "bids", "culture_posts", "disputes", "social_posts", "products", "seller_policies", "buyers", "sellers"]:
                    run_sql(f"DELETE FROM {table_name}")
                st.success("Most test data cleared.")
            else:
                st.error("Check the confirmation box first.")

    with tabs[13]:
        st.subheader("Business Planning")
        st.markdown("""
        This package includes updated planning documents:

        - HOUSE_OF_WAX_BUSINESS_PLAN_DRAFT.md
        - STARTUP_BUDGET_DRAFT.md
        - REVENUE_MODEL_DRAFT.md
        - MARKETPLACE_POLICY_SUMMARY.md
        - BUYER_POLICY_DRAFT.md
        - SELLER_POLICY_DRAFT.md
        - V15_PRODUCT_ROADMAP.md
        """)


# -----------------------------
# Navigation
# -----------------------------
menu = st.sidebar.radio(
    "House Of Wax",
    [
        "Home",
        "Marketplace",
        "Auctions",
        "Seller Stores",
        "Music + Culture",
        "Register / Sell",
        "Buyer Dashboard",
        "Seller Dashboard",
        "Admin Login",
    ]
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
