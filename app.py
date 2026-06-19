
import sqlite3
from pathlib import Path
from datetime import date, datetime, time, timedelta
import pandas as pd
import streamlit as st

DB_PATH = Path("record_store_v3.db")

# -----------------------------
# Database helpers
# -----------------------------
def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sku TEXT UNIQUE,
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
        social_caption TEXT,
        hashtags TEXT,
        image_url TEXT,
        last_updated TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        expense_date TEXT NOT NULL,
        category TEXT NOT NULL,
        vendor TEXT,
        description TEXT,
        amount REAL NOT NULL,
        payment_method TEXT,
        recurring TEXT DEFAULT 'No',
        created_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS daily_operations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        op_date TEXT NOT NULL,
        sales_revenue REAL DEFAULT 0,
        records_sold INTEGER DEFAULT 0,
        foot_traffic INTEGER DEFAULT 0,
        online_orders INTEGER DEFAULT 0,
        notes TEXT,
        created_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS inventory_movements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        movement_date TEXT NOT NULL,
        sku TEXT NOT NULL,
        movement_type TEXT NOT NULL,
        quantity_change INTEGER NOT NULL,
        reason TEXT,
        created_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS scheduled_posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sku TEXT,
        platform TEXT NOT NULL,
        scheduled_date TEXT NOT NULL,
        scheduled_time TEXT NOT NULL,
        caption TEXT NOT NULL,
        hashtags TEXT,
        status TEXT DEFAULT 'Scheduled',
        image_url TEXT,
        notes TEXT,
        created_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        phone TEXT,
        favorite_genres TEXT,
        wishlist TEXT,
        notes TEXT,
        created_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS weekly_marketing_plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        week_start TEXT NOT NULL,
        plan_text TEXT NOT NULL,
        created_at TEXT
    )
    """)

    conn.commit()
    conn.close()

def read_table(table):
    conn = connect()
    df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
    conn.close()
    return df

def execute(sql, params=()):
    conn = connect()
    conn.execute(sql, params)
    conn.commit()
    conn.close()

def money(x):
    try:
        return f"${float(x):,.2f}"
    except:
        return "$0.00"

# -----------------------------
# Content generation
# -----------------------------
def auto_sku(artist, title, fmt):
    stamp = str(int(datetime.now().timestamp()))[-5:]
    return f"{fmt[:3]}-{artist[:3]}-{title[:5]}-{stamp}".upper().replace(" ", "").replace("/", "")

def generate_bio(row):
    artist = str(row.get("artist", "")).strip()
    title = str(row.get("title", "")).strip()
    genre = str(row.get("genre", "")).strip()
    fmt = str(row.get("format", "record")).strip()
    condition = str(row.get("condition", "")).strip()
    year = str(row.get("release_year", "")).strip()
    pressing = str(row.get("pressing_notes", "")).strip()

    opener = f"{artist}'s {title}" if artist and title else "This record"
    if year and year.lower() != "nan":
        opener += f" ({year})"
    opener += f" is a standout {genre.lower()} release" if genre else " is a standout release"
    opener += f" available on {fmt.lower()}."

    parts = [opener]
    if condition and condition.lower() != "nan":
        parts.append(f"This copy is listed in {condition} condition.")
    if pressing and pressing.lower() != "nan":
        parts.append(f"Pressing notes: {pressing}.")
    parts.append("A strong pickup for collectors, DJs, and anyone building a serious music library.")
    return " ".join(parts)

def generate_caption(row, style="Sales-Focused"):
    artist = str(row.get("artist", "")).strip()
    title = str(row.get("title", "")).strip()
    genre = str(row.get("genre", "")).strip()
    condition = str(row.get("condition", "")).strip()
    price = row.get("price", "")
    location = str(row.get("location", "")).strip()
    qty = int(float(row.get("quantity", 0) or 0))

    price_line = ""
    try:
        if float(price) > 0:
            price_line = f" Priced at ${float(price):.2f}."
    except:
        pass

    if style == "Collector-Focused":
        caption = f"Collector alert: {artist} — {title} just hit the bins."
        if genre:
            caption += f" This is a strong {genre} pickup"
        if condition:
            caption += f" in {condition} condition"
        caption += "."
        if qty <= 1:
            caption += " Only one copy available."
        caption += price_line
        if location:
            caption += f" Find it in-store at {location}."
        caption += " Serious crate diggers should move quick."

    elif style == "Casual":
        caption = f"Now spinning in the shop: {artist} — {title}."
        if genre:
            caption += f" Perfect if you’re in a {genre} mood."
        caption += price_line
        caption += " Stop by, flip through the bins, and check it out."

    elif style == "Storytelling":
        caption = f"There’s always something special about finding {artist} — {title} in the bins."
        if genre:
            caption += f" It brings that {genre} energy that makes record shopping feel personal."
        if condition:
            caption += f" This copy is marked {condition}."
        caption += price_line
        caption += " Come give it a look before it disappears."

    else:
        caption = f"Now in stock: {artist} — {title}."
        if genre:
            caption += f" A great {genre} pick"
        else:
            caption += " A great pickup"
        if condition:
            caption += f" in {condition} condition"
        caption += "."
        caption += price_line
        if location:
            caption += f" Find it in-store at {location}."
        caption += " Message us or stop by before it’s gone."

    return caption

def generate_hashtags(row):
    genre = str(row.get("genre", "")).strip().replace(" ", "")
    fmt = str(row.get("format", "Vinyl")).strip().replace(" ", "")
    artist = str(row.get("artist", "")).strip().replace(" ", "")
    tags = ["#RecordStore", "#VinylCommunity", "#NowSpinning", "#CrateDigging", "#MusicLovers"]
    if fmt:
        tags.append(f"#{fmt}")
    if genre:
        tags.append(f"#{genre}")
    if artist and len(artist) <= 25:
        tags.append(f"#{artist}")
    return " ".join(tags)

def best_time_to_post(platform, genre="", post_type="New Arrival"):
    platform = platform.lower()
    post_type = post_type.lower()
    genre = genre.lower()

    if "tiktok" in platform:
        return "Evening, 7:00 PM–9:00 PM", "TikTok posts often work best when people are relaxing and scrolling after school or work."
    if "instagram" in platform:
        if "new" in post_type:
            return "Lunch or evening, 12:00 PM–1:00 PM or 6:00 PM–8:00 PM", "Good for new arrivals because people can save the post and stop by later."
        return "Evening, 6:00 PM–8:00 PM", "Good general window for visual posts and music discovery."
    if "facebook" in platform:
        return "Late morning or early afternoon, 10:00 AM–2:00 PM", "Good for local community shoppers and event-style posts."
    if "email" in platform:
        return "Morning, 8:00 AM–10:00 AM", "Good for newsletters, weekend drops, and sale announcements."
    return "Evening, 6:00 PM–8:00 PM", "Safe default posting window for music retail content."

def upsert_inventory_row(row):
    row = {str(k).lower().strip(): v for k, v in row.items()}
    artist = str(row.get("artist", "")).strip()
    title = str(row.get("title", "")).strip()
    fmt = str(row.get("format", "Vinyl")).strip()
    sku = str(row.get("sku", "")).strip()
    if not sku or sku.lower() == "nan":
        sku = auto_sku(artist, title, fmt)

    prepared = {
        "sku": sku,
        "artist": artist,
        "title": title,
        "format": fmt,
        "genre": str(row.get("genre", "")).strip(),
        "condition": str(row.get("condition", "")).strip(),
        "label": str(row.get("label", "")).strip(),
        "release_year": str(row.get("release_year", "")).strip(),
        "pressing_notes": str(row.get("pressing_notes", "")).strip(),
        "cost": float(row.get("cost", 0) or 0),
        "price": float(row.get("price", 0) or 0),
        "quantity": int(float(row.get("quantity", 0) or 0)),
        "reorder_level": int(float(row.get("reorder_level", 2) or 2)),
        "location": str(row.get("location", "")).strip(),
        "bio": str(row.get("bio", "")).strip(),
        "social_caption": str(row.get("social_caption", "")).strip(),
        "hashtags": str(row.get("hashtags", "")).strip(),
        "image_url": str(row.get("image_url", "")).strip(),
        "last_updated": datetime.now().isoformat(timespec="seconds")
    }

    if not prepared["bio"] or prepared["bio"].lower() == "nan":
        prepared["bio"] = generate_bio(prepared)
    if not prepared["social_caption"] or prepared["social_caption"].lower() == "nan":
        prepared["social_caption"] = generate_caption(prepared, "Sales-Focused")
    if not prepared["hashtags"] or prepared["hashtags"].lower() == "nan":
        prepared["hashtags"] = generate_hashtags(prepared)

    conn = connect()
    conn.execute("""
    INSERT INTO inventory
    (sku, artist, title, format, genre, condition, label, release_year, pressing_notes,
     cost, price, quantity, reorder_level, location, bio, social_caption, hashtags, image_url, last_updated)
    VALUES
    (:sku, :artist, :title, :format, :genre, :condition, :label, :release_year, :pressing_notes,
     :cost, :price, :quantity, :reorder_level, :location, :bio, :social_caption, :hashtags, :image_url, :last_updated)
    ON CONFLICT(sku) DO UPDATE SET
        artist=excluded.artist,
        title=excluded.title,
        format=excluded.format,
        genre=excluded.genre,
        condition=excluded.condition,
        label=excluded.label,
        release_year=excluded.release_year,
        pressing_notes=excluded.pressing_notes,
        cost=excluded.cost,
        price=excluded.price,
        quantity=excluded.quantity,
        reorder_level=excluded.reorder_level,
        location=excluded.location,
        bio=excluded.bio,
        social_caption=excluded.social_caption,
        hashtags=excluded.hashtags,
        image_url=excluded.image_url,
        last_updated=excluded.last_updated
    """, prepared)
    conn.commit()
    conn.close()

def add_expense(expense_date, category, vendor, description, amount, payment_method, recurring):
    execute("""
    INSERT INTO expenses
    (expense_date, category, vendor, description, amount, payment_method, recurring, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (expense_date, category, vendor, description, amount, payment_method, recurring, datetime.now().isoformat(timespec="seconds")))

def add_operation(op_date, sales_revenue, records_sold, foot_traffic, online_orders, notes):
    execute("""
    INSERT INTO daily_operations
    (op_date, sales_revenue, records_sold, foot_traffic, online_orders, notes, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (op_date, sales_revenue, records_sold, foot_traffic, online_orders, notes, datetime.now().isoformat(timespec="seconds")))

def adjust_stock(sku, movement_type, quantity_change, reason):
    conn = connect()
    cur = conn.cursor()
    sku = sku.strip()
    qty = int(quantity_change)
    cur.execute("SELECT quantity FROM inventory WHERE sku = ?", (sku,))
    result = cur.fetchone()
    if result is None:
        conn.close()
        raise ValueError("SKU not found.")
    current_qty = int(result[0])

    if movement_type in ["Sale", "Damage/Loss"]:
        new_qty = current_qty - qty
        movement_qty = -qty
    else:
        new_qty = current_qty + qty
        movement_qty = qty

    if new_qty < 0:
        conn.close()
        raise ValueError("Stock cannot go below zero.")

    now = datetime.now().isoformat(timespec="seconds")
    cur.execute("UPDATE inventory SET quantity = ?, last_updated = ? WHERE sku = ?", (new_qty, now, sku))
    cur.execute("""
    INSERT INTO inventory_movements
    (movement_date, sku, movement_type, quantity_change, reason, created_at)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (date.today().isoformat(), sku, movement_type, movement_qty, reason, now))
    conn.commit()
    conn.close()

def schedule_post(sku, platform, scheduled_date, scheduled_time, caption, hashtags, status, image_url, notes):
    execute("""
    INSERT INTO scheduled_posts
    (sku, platform, scheduled_date, scheduled_time, caption, hashtags, status, image_url, notes, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (sku, platform, scheduled_date, scheduled_time, caption, hashtags, status, image_url, notes, datetime.now().isoformat(timespec="seconds")))

def update_post_status(post_id, status):
    execute("UPDATE scheduled_posts SET status = ? WHERE id = ?", (status, int(post_id)))

def add_customer(name, email, phone, favorite_genres, wishlist, notes):
    execute("""
    INSERT OR REPLACE INTO customers
    (name, email, phone, favorite_genres, wishlist, notes, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (name, email, phone, favorite_genres, wishlist, notes, datetime.now().isoformat(timespec="seconds")))

def match_wishlists(inv, customers):
    matches = []
    if inv.empty or customers.empty:
        return pd.DataFrame(matches)
    for _, item in inv.iterrows():
        item_text = " ".join([
            str(item.get("artist","")),
            str(item.get("title","")),
            str(item.get("genre","")),
            str(item.get("label","")),
            str(item.get("pressing_notes",""))
        ]).lower()
        for _, cust in customers.iterrows():
            wish_text = " ".join([
                str(cust.get("favorite_genres","")),
                str(cust.get("wishlist",""))
            ]).lower()
            if not wish_text.strip():
                continue
            keywords = [k.strip().lower() for k in wish_text.replace(",", " ").split() if len(k.strip()) >= 4]
            hit_words = sorted(set([k for k in keywords if k in item_text]))
            if hit_words:
                matches.append({
                    "customer_name": cust.get("name",""),
                    "email": cust.get("email",""),
                    "phone": cust.get("phone",""),
                    "matched_words": ", ".join(hit_words[:8]),
                    "sku": item.get("sku",""),
                    "artist": item.get("artist",""),
                    "title": item.get("title",""),
                    "genre": item.get("genre",""),
                    "quantity": item.get("quantity",0),
                    "price": item.get("price",0)
                })
    return pd.DataFrame(matches)

def generate_weekly_plan(inv, week_start):
    days = []
    week_start = pd.to_datetime(week_start).date()
    stocked = inv[inv["quantity"] > 0].copy() if not inv.empty else inv

    def pick_item(filter_text=None, idx=0):
        if stocked.empty:
            return None
        data = stocked
        if filter_text:
            filt = stocked.astype(str).apply(lambda col: col.str.contains(filter_text, case=False, na=False)).any(axis=1)
            if filt.any():
                data = stocked[filt]
        return data.iloc[idx % len(data)].to_dict()

    themes = [
        ("Monday", "New Arrival Monday", "Post a fresh arrival with a clean product photo and sales-focused caption.", pick_item(idx=0)),
        ("Tuesday", "Collector Pick", "Highlight pressing notes, condition, label, or release year.", pick_item(idx=1)),
        ("Wednesday", "Genre Spotlight", "Feature one genre and ask followers what they are currently listening to.", pick_item(idx=2)),
        ("Thursday", "Customer Wishlist Match", "Post a record that could match a customer request or popular genre.", pick_item(idx=3)),
        ("Friday", "Staff Pick Friday", "Use a more personal caption and explain why the album matters.", pick_item(idx=4)),
        ("Saturday", "Weekend Bin Pull", "Post 3–5 records as a carousel idea and drive weekend foot traffic.", pick_item(idx=5)),
        ("Sunday", "Repost / Sold / Coming Soon", "Recap what sold, tease next week, or remind people about low-stock records.", pick_item(idx=6)),
    ]

    for i, (day_name, theme, action, item) in enumerate(themes):
        post_date = week_start + timedelta(days=i)
        if item:
            record_line = f"{item.get('artist','')} — {item.get('title','')} ({item.get('genre','')})"
            caption = generate_caption(item, "Casual" if day_name in ["Wednesday", "Friday"] else "Sales-Focused")
            hashtags = generate_hashtags(item)
        else:
            record_line = "Add inventory to generate a specific record recommendation."
            caption = "Plan a store update, behind-the-scenes post, or new arrival teaser."
            hashtags = "#RecordStore #VinylCommunity #NowSpinning"
        days.append({
            "date": str(post_date),
            "day": day_name,
            "theme": theme,
            "recommended_record": record_line,
            "action": action,
            "draft_caption": caption,
            "hashtags": hashtags
        })
    return pd.DataFrame(days)

# -----------------------------
# App setup
# -----------------------------
st.set_page_config(page_title="Record Store Manager V3", layout="wide")
init_db()

st.title("Record Store Manager V3")
st.caption("Inventory, spending, operations, bios, social scheduling, post generator, sold-item warnings, wishlist matching, and weekly marketing plans.")

tabs = st.tabs([
    "Dashboard",
    "Inventory",
    "Upload Inventory",
    "Post This Item",
    "Social Scheduler",
    "Weekly Marketing Plan",
    "Wishlist Matching",
    "Stock Updates",
    "Expenses",
    "Daily Operations",
    "Customers",
    "Reports"
])

# -----------------------------
# Dashboard
# -----------------------------
with tabs[0]:
    inv = read_table("inventory")
    exp = read_table("expenses")
    ops = read_table("daily_operations")
    posts = read_table("scheduled_posts")
    customers = read_table("customers")

    total_units = int(inv["quantity"].sum()) if not inv.empty else 0
    inventory_cost = float((inv["cost"] * inv["quantity"]).sum()) if not inv.empty else 0
    inventory_retail = float((inv["price"] * inv["quantity"]).sum()) if not inv.empty else 0
    total_expenses = float(exp["amount"].sum()) if not exp.empty else 0
    total_sales = float(ops["sales_revenue"].sum()) if not ops.empty else 0
    scheduled_count = len(posts[posts["status"] == "Scheduled"]) if not posts.empty else 0
    customer_count = len(customers)

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Units in Stock", total_units)
    c2.metric("Inventory Cost", money(inventory_cost))
    c3.metric("Retail Value", money(inventory_retail))
    c4.metric("Expenses", money(total_expenses))
    c5.metric("Scheduled Posts", scheduled_count)
    c6.metric("Customers", customer_count)

    st.subheader("Low Stock Alerts")
    if inv.empty:
        st.info("Upload inventory to start tracking low-stock items.")
    else:
        low = inv[inv["quantity"] <= inv["reorder_level"]].sort_values(["quantity", "artist"])
        if low.empty:
            st.success("No low-stock items right now.")
        else:
            st.warning(f"{len(low)} item(s) are at or below reorder level.")
            st.dataframe(low[["sku", "artist", "title", "format", "quantity", "reorder_level", "location"]], use_container_width=True)

    st.subheader("Scheduled Post Warnings")
    if posts.empty or inv.empty:
        st.info("No scheduled posts to check yet.")
    else:
        merged = posts.merge(inv[["sku", "artist", "title", "quantity"]], on="sku", how="left")
        warnings = merged[(merged["status"] == "Scheduled") & (merged["sku"].notna()) & (merged["quantity"].fillna(0) <= 0)]
        if warnings.empty:
            st.success("No scheduled posts are attached to sold-out records.")
        else:
            st.error("Some scheduled posts are attached to sold-out records. Review before posting.")
            st.dataframe(warnings[["id", "platform", "scheduled_date", "scheduled_time", "sku", "artist", "title", "quantity", "status"]], use_container_width=True)

# -----------------------------
# Inventory
# -----------------------------
with tabs[1]:
    st.subheader("Inventory")
    inv = read_table("inventory")
    search = st.text_input("Search by artist, title, SKU, genre, label, format, or condition")
    display = inv.copy()
    if not display.empty and search:
        mask = display.astype(str).apply(lambda col: col.str.contains(search, case=False, na=False)).any(axis=1)
        display = display[mask]
    st.dataframe(display, use_container_width=True)

    st.subheader("Add or Edit One Record")
    with st.form("manual_inventory"):
        c1, c2, c3 = st.columns(3)
        sku = c1.text_input("SKU")
        artist = c2.text_input("Artist")
        title = c3.text_input("Title")
        c4, c5, c6, c7 = st.columns(4)
        fmt = c4.selectbox("Format", ["Vinyl", "CD", "Cassette", "DVD", "Merch", "Other"])
        genre = c5.text_input("Genre")
        condition = c6.text_input("Condition")
        label = c7.text_input("Label")
        c8, c9, c10 = st.columns(3)
        release_year = c8.text_input("Release Year")
        pressing_notes = c9.text_input("Pressing Notes")
        location = c10.text_input("Location / Bin / Shelf")
        c11, c12, c13, c14 = st.columns(4)
        cost = c11.number_input("Cost", min_value=0.0, step=0.01)
        price = c12.number_input("Price", min_value=0.0, step=0.01)
        quantity = c13.number_input("Quantity", min_value=0, step=1)
        reorder_level = c14.number_input("Reorder Level", min_value=0, value=2, step=1)
        image_url = st.text_input("Image URL / Product Photo Link")
        submitted = st.form_submit_button("Save Record")
        if submitted:
            if not artist or not title:
                st.error("Artist and title are required.")
            else:
                upsert_inventory_row({
                    "sku": sku, "artist": artist, "title": title, "format": fmt, "genre": genre,
                    "condition": condition, "label": label, "release_year": release_year,
                    "pressing_notes": pressing_notes, "cost": cost, "price": price, "quantity": quantity,
                    "reorder_level": reorder_level, "location": location, "image_url": image_url
                })
                st.success("Record saved. Bio, captions, hashtags, dashboard, and reports updated.")

# -----------------------------
# Upload Inventory
# -----------------------------
with tabs[2]:
    st.subheader("Upload Inventory CSV")
    st.write("CSV columns supported:")
    st.code("sku,artist,title,format,genre,condition,label,release_year,pressing_notes,cost,price,quantity,reorder_level,location,bio,social_caption,hashtags,image_url", language="text")
    uploaded = st.file_uploader("Choose CSV file", type=["csv"])
    if uploaded is not None:
        try:
            df = pd.read_csv(uploaded)
            df.columns = [c.lower().strip() for c in df.columns]
            st.write("Preview:")
            st.dataframe(df.head(20), use_container_width=True)
            if st.button("Import / Update Inventory"):
                missing = {"artist", "title"} - set(df.columns)
                if missing:
                    st.error(f"Missing required columns: {missing}")
                else:
                    for _, row in df.iterrows():
                        upsert_inventory_row(row.to_dict())
                    st.success(f"Imported/updated {len(df)} rows. Bios, captions, hashtags, totals, and alerts updated.")
        except Exception as e:
            st.error(f"Could not read CSV: {e}")

# -----------------------------
# Feature 1: Post This Item Button
# -----------------------------
with tabs[3]:
    st.subheader("Post This Item")
    st.write("Select a record and instantly generate multiple post styles.")

    inv = read_table("inventory")
    if inv.empty:
        st.info("Add or upload inventory first.")
    else:
        sku_options = [f"{r['sku']} | {r['artist']} - {r['title']} | Qty: {r['quantity']}" for _, r in inv.iterrows()]
        selected = st.selectbox("Record", sku_options)
        sku = selected.split("|")[0].strip()
        record = inv[inv["sku"] == sku].iloc[0].to_dict()

        if int(record.get("quantity", 0) or 0) <= 0:
            st.error("Sold-item protection: this item is sold out. Do not post it as available unless you restock it.")

        st.write("### Brief Bio")
        st.write(record.get("bio", "") or generate_bio(record))

        c1, c2, c3 = st.columns(3)
        with c1:
            st.write("### Collector-Focused")
            st.code(generate_caption(record, "Collector-Focused") + "\n\n" + generate_hashtags(record), language="text")
        with c2:
            st.write("### Casual")
            st.code(generate_caption(record, "Casual") + "\n\n" + generate_hashtags(record), language="text")
        with c3:
            st.write("### Sales-Focused")
            st.code(generate_caption(record, "Sales-Focused") + "\n\n" + generate_hashtags(record), language="text")

        st.write("### Storytelling Option")
        st.code(generate_caption(record, "Storytelling") + "\n\n" + generate_hashtags(record), language="text")

        st.write("### Schedule This Item")
        with st.form("quick_schedule_from_post_item"):
            platform = st.selectbox("Platform", ["Instagram", "Facebook", "TikTok", "X/Twitter", "Threads", "Email Newsletter", "Other"])
            post_type = st.selectbox("Post Type", ["New Arrival", "Collector Pick", "Staff Pick", "Weekend Sale", "Genre Spotlight"])
            suggested, reason = best_time_to_post(platform, record.get("genre",""), post_type)
            st.info(f"Best time suggestion: {suggested}. {reason}")
            scheduled_date = st.date_input("Post Date", value=date.today())
            scheduled_time = st.time_input("Post Time", value=time(18, 0))
            style = st.selectbox("Caption Style", ["Sales-Focused", "Collector-Focused", "Casual", "Storytelling"])
            caption = st.text_area("Caption", value=generate_caption(record, style), height=120)
            hashtags = st.text_area("Hashtags", value=generate_hashtags(record), height=80)
            submitted = st.form_submit_button("Schedule Post")
            if submitted:
                if int(record.get("quantity", 0) or 0) <= 0:
                    st.error("This record is sold out. Restock it before scheduling as available.")
                else:
                    schedule_post(sku, platform, scheduled_date.isoformat(), scheduled_time.strftime("%H:%M"), caption, hashtags, "Scheduled", record.get("image_url",""), post_type)
                    st.success("Post scheduled.")

# -----------------------------
# Social Scheduler + sold protection
# -----------------------------
with tabs[4]:
    st.subheader("Social Media Scheduler")
    inv = read_table("inventory")
    posts = read_table("scheduled_posts")

    if inv.empty:
        st.info("Add inventory first.")
    else:
        sku_options = ["No specific record"] + [f"{r['sku']} | {r['artist']} - {r['title']} | Qty: {r['quantity']}" for _, r in inv.iterrows()]
        with st.form("schedule_post_form"):
            selected = st.selectbox("Record", sku_options)
            if selected == "No specific record":
                sku = ""
                record = {}
                default_caption = ""
                default_hashtags = "#RecordStore #VinylCommunity #NowSpinning"
                default_image = ""
                qty_ok = True
            else:
                sku = selected.split("|")[0].strip()
                record = inv[inv["sku"] == sku].iloc[0].to_dict()
                default_caption = record.get("social_caption", "") or generate_caption(record)
                default_hashtags = record.get("hashtags", "") or generate_hashtags(record)
                default_image = record.get("image_url", "") or ""
                qty_ok = int(record.get("quantity", 0) or 0) > 0

            c1, c2, c3 = st.columns(3)
            platform = c1.selectbox("Platform", ["Instagram", "Facebook", "TikTok", "X/Twitter", "Threads", "Email Newsletter", "Other"])
            scheduled_date = c2.date_input("Post Date", value=date.today())
            scheduled_time = c3.time_input("Post Time", value=time(12, 0))
            post_type = st.selectbox("Post Type", ["New Arrival", "Collector Pick", "Staff Pick", "Weekend Sale", "Genre Spotlight", "Store Update"])

            if selected != "No specific record":
                suggested, reason = best_time_to_post(platform, record.get("genre",""), post_type)
                st.info(f"Best time suggestion: {suggested}. {reason}")
                if not qty_ok:
                    st.error("Sold-item protection: this item is sold out. Do not schedule it as available.")

            caption = st.text_area("Caption", value=default_caption, height=140)
            hashtags = st.text_area("Hashtags", value=default_hashtags, height=80)
            image_url = st.text_input("Image URL", value=default_image)
            notes = st.text_area("Internal Notes")
            submitted = st.form_submit_button("Schedule Post")
            if submitted:
                if selected != "No specific record" and not qty_ok:
                    st.error("This record is sold out. Restock it before scheduling as available.")
                else:
                    schedule_post(sku, platform, scheduled_date.isoformat(), scheduled_time.strftime("%H:%M"), caption, hashtags, "Scheduled", image_url, notes)
                    st.success("Post scheduled in your content calendar.")

    st.subheader("Content Calendar")
    posts = read_table("scheduled_posts")
    if posts.empty:
        st.info("No scheduled posts yet.")
    else:
        st.dataframe(posts.sort_values(["scheduled_date", "scheduled_time"]), use_container_width=True)
        c1, c2 = st.columns(2)
        selected_id = c1.selectbox("Post ID to update", [str(x) for x in posts["id"].tolist()])
        new_status = c2.selectbox("New Status", ["Scheduled", "Posted", "Skipped", "Needs Edit", "Sold Out - Do Not Post"])
        if st.button("Update Post Status"):
            update_post_status(selected_id, new_status)
            st.success("Post status updated.")
        st.download_button("Download Social Calendar CSV", posts.to_csv(index=False), "social_media_calendar.csv", "text/csv")

# -----------------------------
# Weekly marketing plan
# -----------------------------
with tabs[5]:
    st.subheader("Weekly Marketing Plan")
    inv = read_table("inventory")
    week_start = st.date_input("Week Start Date", value=date.today())
    if st.button("Generate Weekly Plan"):
        plan = generate_weekly_plan(inv, week_start)
        st.session_state["weekly_plan"] = plan

    if "weekly_plan" in st.session_state:
        plan = st.session_state["weekly_plan"]
        st.dataframe(plan, use_container_width=True)
        st.download_button("Download Weekly Marketing Plan CSV", plan.to_csv(index=False), "weekly_marketing_plan.csv", "text/csv")
        plan_text = "\n\n".join([
            f"{row['day']} ({row['date']}) — {row['theme']}\nRecord: {row['recommended_record']}\nAction: {row['action']}\nCaption: {row['draft_caption']}\nHashtags: {row['hashtags']}"
            for _, row in plan.iterrows()
        ])
        st.text_area("Copyable Weekly Plan", value=plan_text, height=350)

# -----------------------------
# Wishlist matching
# -----------------------------
with tabs[6]:
    st.subheader("Wishlist Matching")
    st.write("This checks your current inventory against customer favorite genres and wishlists.")
    inv = read_table("inventory")
    customers = read_table("customers")
    matches = match_wishlists(inv, customers)
    if matches.empty:
        st.info("No matches found yet. Add customers with favorite genres or wishlists, then upload matching inventory.")
    else:
        st.success(f"Found {len(matches)} possible customer match(es).")
        st.dataframe(matches, use_container_width=True)
        st.download_button("Download Wishlist Matches CSV", matches.to_csv(index=False), "wishlist_matches.csv", "text/csv")

        st.subheader("Copyable Customer Message")
        selected = st.selectbox("Choose match", [f"{i} | {r['customer_name']} | {r['artist']} - {r['title']}" for i, r in matches.iterrows()])
        idx = int(selected.split("|")[0].strip())
        r = matches.loc[idx]
        msg = f"Hey {r['customer_name']}, we just got something in that may fit what you were looking for: {r['artist']} — {r['title']} ({r['genre']}). It is currently priced at ${float(r['price']):.2f}. Let us know if you want us to hold it for you."
        st.code(msg, language="text")

# -----------------------------
# Stock updates
# -----------------------------
with tabs[7]:
    st.subheader("Record a Sale, Restock, Damage, or Adjustment")
    inv = read_table("inventory")
    if inv.empty:
        st.info("Add inventory first.")
    else:
        sku_options = [f"{r['sku']} | {r['artist']} - {r['title']} | Qty: {r['quantity']}" for _, r in inv.iterrows()]
        with st.form("stock_update"):
            selected = st.selectbox("Item", sku_options)
            sku = selected.split("|")[0].strip()
            movement_type = st.selectbox("Update Type", ["Sale", "Restock", "Damage/Loss", "Manual Adjustment"])
            quantity_change = st.number_input("Quantity", min_value=1, step=1)
            reason = st.text_input("Reason / Note")
            submitted = st.form_submit_button("Update Stock")
            if submitted:
                try:
                    adjust_stock(sku, movement_type, quantity_change, reason)
                    st.success("Stock updated automatically.")
                except Exception as e:
                    st.error(str(e))

# -----------------------------
# Expenses
# -----------------------------
with tabs[8]:
    st.subheader("Spending on Supplies and Daily Operations")
    with st.form("expense_form"):
        c1, c2, c3 = st.columns(3)
        expense_date = c1.date_input("Date", value=date.today())
        category = c2.selectbox("Category", ["Supplies", "Rent", "Utilities", "Payroll", "Marketing", "Shipping", "Repairs", "Software", "Inventory Purchase", "Other"])
        amount = c3.number_input("Amount", min_value=0.0, step=0.01)
        vendor = st.text_input("Vendor")
        description = st.text_area("Description")
        c4, c5 = st.columns(2)
        payment_method = c4.text_input("Payment Method")
        recurring = c5.selectbox("Recurring?", ["No", "Weekly", "Monthly", "Quarterly", "Yearly"])
        submitted = st.form_submit_button("Add Expense")
        if submitted:
            add_expense(expense_date.isoformat(), category, vendor, description, amount, payment_method, recurring)
            st.success("Expense added.")
    exp = read_table("expenses")
    st.dataframe(exp.sort_values("expense_date", ascending=False) if not exp.empty else exp, use_container_width=True)

# -----------------------------
# Daily ops
# -----------------------------
with tabs[9]:
    st.subheader("Daily Operations")
    with st.form("daily_ops_form"):
        op_date = st.date_input("Operation Date", value=date.today())
        c1, c2, c3, c4 = st.columns(4)
        sales_revenue = c1.number_input("Sales Revenue", min_value=0.0, step=0.01)
        records_sold = c2.number_input("Records Sold", min_value=0, step=1)
        foot_traffic = c3.number_input("Foot Traffic", min_value=0, step=1)
        online_orders = c4.number_input("Online Orders", min_value=0, step=1)
        notes = st.text_area("Notes")
        submitted = st.form_submit_button("Save Daily Operations")
        if submitted:
            add_operation(op_date.isoformat(), sales_revenue, records_sold, foot_traffic, online_orders, notes)
            st.success("Daily operations saved.")
    ops = read_table("daily_operations")
    st.dataframe(ops.sort_values("op_date", ascending=False) if not ops.empty else ops, use_container_width=True)

# -----------------------------
# Customers
# -----------------------------
with tabs[10]:
    st.subheader("Customers & Wishlists")
    with st.form("customer_form"):
        c1, c2, c3 = st.columns(3)
        name = c1.text_input("Customer Name")
        email = c2.text_input("Email")
        phone = c3.text_input("Phone")
        favorite_genres = st.text_input("Favorite Genres")
        wishlist = st.text_area("Wishlist")
        notes = st.text_area("Notes")
        submitted = st.form_submit_button("Save Customer")
        if submitted:
            if not email:
                st.error("Email is required so the customer record can be updated later.")
            else:
                add_customer(name, email, phone, favorite_genres, wishlist, notes)
                st.success("Customer saved.")
    customers = read_table("customers")
    st.dataframe(customers, use_container_width=True)

# -----------------------------
# Reports
# -----------------------------
with tabs[11]:
    st.subheader("Reports")
    inv = read_table("inventory")
    exp = read_table("expenses")
    ops = read_table("daily_operations")
    posts = read_table("scheduled_posts")
    customers = read_table("customers")
    matches = match_wishlists(inv, customers)

    report_type = st.selectbox("Report", [
        "Inventory Value",
        "Expenses by Category",
        "Daily Sales",
        "Low Stock",
        "Social Media Calendar",
        "Customer Wishlists",
        "Wishlist Matches",
        "Marketing-Ready Inventory"
    ])

    if report_type == "Inventory Value":
        if inv.empty:
            st.info("No inventory yet.")
        else:
            inv["cost_value"] = inv["cost"] * inv["quantity"]
            inv["retail_value"] = inv["price"] * inv["quantity"]
            st.dataframe(inv[["sku", "artist", "title", "quantity", "cost_value", "retail_value"]], use_container_width=True)
            st.download_button("Download Inventory Report CSV", inv.to_csv(index=False), "inventory_report.csv", "text/csv")

    elif report_type == "Expenses by Category":
        if exp.empty:
            st.info("No expenses yet.")
        else:
            summary = exp.groupby("category", as_index=False)["amount"].sum().sort_values("amount", ascending=False)
            st.bar_chart(summary.set_index("category"))
            st.dataframe(summary, use_container_width=True)
            st.download_button("Download Expense Report CSV", summary.to_csv(index=False), "expense_report.csv", "text/csv")

    elif report_type == "Daily Sales":
        if ops.empty:
            st.info("No daily operations yet.")
        else:
            ops["op_date"] = pd.to_datetime(ops["op_date"])
            daily = ops.groupby("op_date", as_index=False)[["sales_revenue", "records_sold", "foot_traffic", "online_orders"]].sum()
            st.line_chart(daily.set_index("op_date")["sales_revenue"])
            st.dataframe(daily, use_container_width=True)
            st.download_button("Download Daily Sales Report CSV", daily.to_csv(index=False), "daily_sales_report.csv", "text/csv")

    elif report_type == "Low Stock":
        low = inv[inv["quantity"] <= inv["reorder_level"]] if not inv.empty else inv
        st.dataframe(low, use_container_width=True)
        if not low.empty:
            st.download_button("Download Low Stock Report CSV", low.to_csv(index=False), "low_stock_report.csv", "text/csv")

    elif report_type == "Social Media Calendar":
        st.dataframe(posts, use_container_width=True)
        if not posts.empty:
            st.download_button("Download Social Calendar CSV", posts.to_csv(index=False), "social_media_calendar.csv", "text/csv")

    elif report_type == "Customer Wishlists":
        st.dataframe(customers, use_container_width=True)
        if not customers.empty:
            st.download_button("Download Customer Wishlist CSV", customers.to_csv(index=False), "customer_wishlists.csv", "text/csv")

    elif report_type == "Wishlist Matches":
        st.dataframe(matches, use_container_width=True)
        if not matches.empty:
            st.download_button("Download Wishlist Matches CSV", matches.to_csv(index=False), "wishlist_matches.csv", "text/csv")

    elif report_type == "Marketing-Ready Inventory":
        if inv.empty:
            st.info("No inventory yet.")
        else:
            marketing = inv[["sku", "artist", "title", "format", "genre", "price", "quantity", "bio", "social_caption", "hashtags", "image_url"]]
            st.dataframe(marketing, use_container_width=True)
            st.download_button("Download Marketing Inventory CSV", marketing.to_csv(index=False), "marketing_ready_inventory.csv", "text/csv")
