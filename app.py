
# ROOT APP DEPLOY FIX — upload THIS app.py to the repository root, replacing the old root app.py.
import sqlite3
from pathlib import Path
from datetime import datetime
import pandas as pd
import streamlit as st

st.set_page_config(page_title='House Of Wax', page_icon='🎧', layout='wide')
APP_VERSION='V18 HOME + EDITORIAL EXPERIENCE'
DB=Path('house_of_wax.db')
UPLOAD=Path('house_of_wax_uploads'); UPLOAD.mkdir(exist_ok=True)
try:
    ADMIN_PASSWORD=st.secrets.get('ADMIN_PASSWORD','')
except Exception:
    ADMIN_PASSWORD=''

def now(): return datetime.now().isoformat(timespec='seconds')
def safe(v,d=''):
    if v is None: return d
    try:
        if pd.isna(v): return d
    except Exception: pass
    s=str(v)
    return d if s.lower() in ['nan','none'] else s
def money(v):
    try: return f'${float(v):,.2f}'
    except Exception: return '$0.00'
def conn(): return sqlite3.connect(DB)
def run(sql,p=()):
    c=conn(); c.execute(sql,p); c.commit(); c.close()
def df(sql,p=()):
    c=conn(); out=pd.read_sql_query(sql,c,params=p); c.close(); return out
def table(t):
    try: return df(f'SELECT * FROM {t}')
    except Exception: return pd.DataFrame()
def addcol(t,c,typ):
    try:
        info=df(f'PRAGMA table_info({t})')
        if c not in info['name'].tolist(): run(f'ALTER TABLE {t} ADD COLUMN {c} {typ}')
    except Exception: pass
def save_file(up,folder):
    if up is None: return ''
    f=UPLOAD/folder; f.mkdir(parents=True,exist_ok=True)
    p=f/(datetime.now().strftime('%Y%m%d%H%M%S')+'_'+up.name.replace(' ','_').replace('/','_'))
    p.write_bytes(up.getbuffer()); return str(p)
def setting(k,d=''):
    try:
        run('CREATE TABLE IF NOT EXISTS app_settings(key TEXT PRIMARY KEY,value TEXT)')
        r=df('SELECT value FROM app_settings WHERE key=?',(k,))
        return d if r.empty else safe(r.iloc[0]['value'],d)
    except Exception:
        return d
def set_setting(k,v):
    run('CREATE TABLE IF NOT EXISTS app_settings(key TEXT PRIMARY KEY,value TEXT)')
    run('INSERT OR REPLACE INTO app_settings(key,value) VALUES(?,?)',(k,str(v)))
def email_exists(t,email):
    return bool(email) and not df(f'SELECT id FROM {t} WHERE lower(email)=lower(?)',(email.strip(),)).empty

# ---------- Database ----------
def setup():
    c=conn(); cur=c.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS app_settings(key TEXT PRIMARY KEY,value TEXT)')
    cur.execute('''CREATE TABLE IF NOT EXISTS buyers(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT,email TEXT UNIQUE,phone TEXT,city TEXT,state TEXT,bio TEXT,status TEXT DEFAULT 'Trusted Buyer',rating REAL DEFAULT 100,completed_purchases INTEGER DEFAULT 0,unpaid_orders INTEGER DEFAULT 0,disputes INTEGER DEFAULT 0,strikes INTEGER DEFAULT 0,created_at TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS sellers(id INTEGER PRIMARY KEY AUTOINCREMENT,store_name TEXT,owner_name TEXT,email TEXT UNIQUE,phone TEXT,city TEXT,state TEXT,website TEXT,instagram TEXT,store_bio TEXT,seller_story TEXT,specialties TEXT,logo_url TEXT,banner_url TEXT,status TEXT DEFAULT 'Approved',seller_level TEXT DEFAULT 'Verified Seller',rating REAL DEFAULT 100,completed_sales INTEGER DEFAULT 0,disputes INTEGER DEFAULT 0,strikes INTEGER DEFAULT 0,auction_override TEXT DEFAULT 'Yes',access_code TEXT,created_at TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY AUTOINCREMENT,seller_id INTEGER,sku TEXT,barcode TEXT,catalog_number TEXT,matrix_runout TEXT,category TEXT,artist TEXT,title TEXT,format TEXT,label TEXT,release_year TEXT,genre TEXT,media_grade TEXT,sleeve_grade TEXT,condition_notes TEXT,description TEXT,price REAL DEFAULT 0,quantity INTEGER DEFAULT 1,shipping_price REAL DEFAULT 0,image_url TEXT,video_url TEXT,audio_url TEXT,external_release_url TEXT,listing_status TEXT DEFAULT 'Active',listing_type TEXT DEFAULT 'Fixed Price',created_at TEXT,updated_at TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS product_gallery(id INTEGER PRIMARY KEY AUTOINCREMENT,product_id INTEGER,image_url TEXT,caption TEXT,created_at TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY AUTOINCREMENT,product_id INTEGER,seller_id INTEGER,buyer_id INTEGER,order_type TEXT,status TEXT DEFAULT 'New',item_price REAL DEFAULT 0,shipping_price REAL DEFAULT 0,platform_fee REAL DEFAULT 0,seller_payout REAL DEFAULT 0,buyer_message TEXT,created_at TEXT,updated_at TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS feedback(id INTEGER PRIMARY KEY AUTOINCREMENT,order_id INTEGER,reviewer_type TEXT,reviewer_id INTEGER,reviewee_type TEXT,reviewee_id INTEGER,rating INTEGER,comment TEXT,public TEXT DEFAULT 'Yes',created_at TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY AUTOINCREMENT,product_id INTEGER,seller_id INTEGER,buyer_id INTEGER,sender_type TEXT,subject TEXT,message TEXT,status TEXT DEFAULT 'New',created_at TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS seller_followers(id INTEGER PRIMARY KEY AUTOINCREMENT,seller_id INTEGER,buyer_id INTEGER,created_at TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS seller_badges(id INTEGER PRIMARY KEY AUTOINCREMENT,seller_id INTEGER,badge_name TEXT,badge_type TEXT,active TEXT DEFAULT 'Yes',created_at TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS store_announcements(id INTEGER PRIMARY KEY AUTOINCREMENT,seller_id INTEGER,title TEXT,body TEXT,status TEXT DEFAULT 'Active',created_at TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS seller_events(id INTEGER PRIMARY KEY AUTOINCREMENT,seller_id INTEGER,event_title TEXT,event_type TEXT,event_date TEXT,description TEXT,status TEXT DEFAULT 'Active',created_at TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS seller_policies(seller_id INTEGER PRIMARY KEY,shipping_policy TEXT,return_policy TEXT,grading_policy TEXT,customer_service_policy TEXT,buyer_requirements TEXT,local_pickup_policy TEXT,processing_time TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS auctions(id INTEGER PRIMARY KEY AUTOINCREMENT,product_id INTEGER,seller_id INTEGER,auction_title TEXT,starting_bid REAL,reserve_price REAL,buy_now_price REAL,bid_increment REAL DEFAULT 1,start_time TEXT,end_time TEXT,status TEXT DEFAULT 'Live',notes TEXT,created_at TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS bids(id INTEGER PRIMARY KEY AUTOINCREMENT,auction_id INTEGER,buyer_id INTEGER,bid_amount REAL,bid_time TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS listing_flags(id INTEGER PRIMARY KEY AUTOINCREMENT,product_id INTEGER,seller_id INTEGER,buyer_id INTEGER,reason TEXT,details TEXT,status TEXT DEFAULT 'Open',created_at TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS culture_posts(id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT,category TEXT,author TEXT,body TEXT,image_url TEXT,status TEXT DEFAULT 'Published',created_at TEXT)''')
    cur.execute("""CREATE TABLE IF NOT EXISTS knowledge_posts(id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT,category TEXT,audience TEXT,level TEXT,summary TEXT,body TEXT,house_tip TEXT,image_url TEXT,status TEXT DEFAULT 'Draft',featured TEXT DEFAULT 'No',created_at TEXT,updated_at TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS glossary_terms(id INTEGER PRIMARY KEY AUTOINCREMENT,term TEXT UNIQUE,category TEXT,plain_definition TEXT,why_it_matters TEXT,example TEXT,status TEXT DEFAULT 'Published',created_at TEXT,updated_at TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS content_drafts(id INTEGER PRIMARY KEY AUTOINCREMENT,source_type TEXT,source_id INTEGER,title TEXT,platform TEXT,caption TEXT,script TEXT,hashtags TEXT,cta TEXT,status TEXT DEFAULT 'Draft',created_at TEXT,updated_at TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS content_calendar(id INTEGER PRIMARY KEY AUTOINCREMENT,content_type TEXT,topic TEXT,platform TEXT,planned_date TEXT,status TEXT DEFAULT 'Planned',notes TEXT,created_at TEXT,updated_at TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS homepage_blocks(id INTEGER PRIMARY KEY AUTOINCREMENT,block_name TEXT,title TEXT,subtitle TEXT,body TEXT,button_text TEXT,button_target TEXT,image_url TEXT,status TEXT DEFAULT 'Active',sort_order INTEGER DEFAULT 0,created_at TEXT,updated_at TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS quick_tips(id INTEGER PRIMARY KEY AUTOINCREMENT,tip_text TEXT,category TEXT,status TEXT DEFAULT 'Active',created_at TEXT,updated_at TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS did_you_know(id INTEGER PRIMARY KEY AUTOINCREMENT,fact_text TEXT,category TEXT,status TEXT DEFAULT 'Active',created_at TEXT,updated_at TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS newsletter_signups(id INTEGER PRIMARY KEY AUTOINCREMENT,email TEXT,name TEXT,source TEXT,created_at TEXT)""")
    c.commit(); c.close()
    mig={'buyers':{'state':'TEXT','bio':'TEXT','status':'TEXT','rating':'REAL','completed_purchases':'INTEGER','unpaid_orders':'INTEGER'},'sellers':{'state':'TEXT','website':'TEXT','instagram':'TEXT','seller_story':'TEXT','specialties':'TEXT','logo_url':'TEXT','banner_url':'TEXT','status':'TEXT','seller_level':'TEXT','rating':'REAL','completed_sales':'INTEGER','auction_override':'TEXT','access_code':'TEXT'},'products':{'sku':'TEXT','barcode':'TEXT','catalog_number':'TEXT','matrix_runout':'TEXT','label':'TEXT','release_year':'TEXT','video_url':'TEXT','audio_url':'TEXT','external_release_url':'TEXT','listing_status':'TEXT','listing_type':'TEXT'},'feedback':{'public':'TEXT'}}
    for t,cols in mig.items():
        for col,typ in cols.items(): addcol(t,col,typ)
    for k,v in {'site_tagline':'A seller-powered marketplace for records, music culture, clothing, and collectors.','announcement':'V16 testing build: all core options are active.','platform_commission_percent':'9','auction_commission_percent':'10'}.items():
        if setting(k, None) is None: set_setting(k,v)
setup()

# ---------- Data helpers ----------
def get_buyer(i):
    r=df('SELECT * FROM buyers WHERE id=?',(int(i),)); return None if r.empty else r.iloc[0]
def get_seller(i):
    r=df('SELECT * FROM sellers WHERE id=?',(int(i),)); return None if r.empty else r.iloc[0]
def ensure_buyer():
    b=table('buyers')
    if not b.empty: return int(b.iloc[0]['id'])
    run('''INSERT INTO buyers(name,email,phone,city,state,bio,status,rating,completed_purchases,unpaid_orders,disputes,strikes,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)''',('Demo Buyer','buyer@test.com','1234567890','Charlotte','NC','Demo buyer for testing.','Trusted Buyer',100,0,0,0,0,now()))
    return int(table('buyers').iloc[0]['id'])
def ensure_seller():
    s=table('sellers')
    if not s.empty: return int(s.iloc[0]['id'])
    run('''INSERT INTO sellers(store_name,owner_name,email,phone,city,state,website,instagram,store_bio,seller_story,specialties,logo_url,banner_url,status,seller_level,rating,completed_sales,disputes,strikes,auction_override,access_code,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',('Demo Wax Seller','Demo Owner','seller@test.com','1234567890','Charlotte','NC','https://example.com','@demowax','A demo seller for testing.','We collect records, culture goods, vintage music pieces, and community stories.','Soul, jazz, hip-hop, Carolina music, vintage tees','','','Approved','Verified Seller',100,12,0,0,'Yes','test123',now()))
    return int(table('sellers').iloc[0]['id'])
def ensure_product():
    p=table('products')
    if not p.empty: return int(p.iloc[0]['id'])
    sid=ensure_seller()
    run('''INSERT INTO products(seller_id,sku,barcode,catalog_number,matrix_runout,category,artist,title,format,label,release_year,genre,media_grade,sleeve_grade,condition_notes,description,price,quantity,shipping_price,image_url,video_url,audio_url,external_release_url,listing_status,listing_type,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',(sid,'DEMO-001','602547234567','CAT-001','A1/B1','Vinyl Records','Demo Artist','Demo Album','Vinyl','Demo Label','1978','Soul','VG+','VG','Light sleeve wear. Plays strong.','Demo product with barcode metadata.',24.99,1,5.00,'','','','','Active','Fixed Price',now(),now()))
    return int(table('products').iloc[0]['id'])
def seed_all(): return ensure_buyer(), ensure_seller(), ensure_product()
def create_buyer(email,name='Test Buyer'):
    email=(email or 'buyer@test.com').strip().lower()
    r=df('SELECT id FROM buyers WHERE lower(email)=lower(?)',(email,))
    if not r.empty: return int(r.iloc[0]['id'])
    run('''INSERT INTO buyers(name,email,phone,city,state,bio,status,rating,completed_purchases,unpaid_orders,disputes,strikes,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)''',(name,email,'','','','','Trusted Buyer',100,0,0,0,0,now()))
    return int(df('SELECT id FROM buyers WHERE lower(email)=lower(?)',(email,)).iloc[0]['id'])
def update_rating(kind,i):
    r=df("SELECT AVG(rating) avg FROM feedback WHERE reviewee_type=? AND reviewee_id=? AND public='Yes'",(kind,int(i)))
    if not r.empty and not pd.isna(r.iloc[0]['avg']):
        score=round(float(r.iloc[0]['avg'])*20,1)
        run(('UPDATE sellers SET rating=? WHERE id=?' if kind=='Seller' else 'UPDATE buyers SET rating=? WHERE id=?'),(score,int(i)))
def barcode_lookup(code):
    if not code: return {}
    r=df('''SELECT barcode,catalog_number,matrix_runout,category,artist,title,format,label,release_year,genre,media_grade,sleeve_grade,description,price,shipping_price,image_url FROM products WHERE barcode=? ORDER BY created_at DESC LIMIT 1''',(code.strip(),))
    return {} if r.empty else r.iloc[0].to_dict()
def badges(sid):
    r=df("SELECT badge_name FROM seller_badges WHERE seller_id=? AND active='Yes'",(int(sid),))
    return '' if r.empty else ' • '.join([safe(x) for x in r['badge_name'].tolist()])
def followers(sid):
    r=df('SELECT COUNT(*) c FROM seller_followers WHERE seller_id=?',(int(sid),)); return 0 if r.empty else int(r.iloc[0]['c'] or 0)
def fee(total,auction=False): return round(float(total)*float(setting('auction_commission_percent' if auction else 'platform_commission_percent','9'))/100,2)

# ---------- UI helpers ----------
def header():
    st.title('🎧 House Of Wax')
    st.caption(setting('site_tagline'))
    st.caption(f'Running {APP_VERSION}')
    st.warning('TESTING BUILD: seller stores, product upload, barcode inventory, buyer/seller profiles, public feedback, messaging, auctions, and admin are active.')
    st.info(setting('announcement'))
def buyer_pick(key,label='Buyer account'):
    if table('buyers').empty: ensure_buyer()
    opts=[f"{int(r['id'])} | {safe(r['name'])} | {safe(r['email'])} | {safe(r['status'])}" for _,r in table('buyers').iterrows()]
    return int(st.selectbox(label,opts,key=key).split('|')[0].strip())
def seller_pick(key,label='Seller account'):
    if table('sellers').empty: ensure_seller()
    opts=[f"{int(r['id'])} | {safe(r['store_name'])} | {safe(r['email'])} | {safe(r['status'])}" for _,r in table('sellers').iterrows()]
    return int(st.selectbox(label,opts,key=key).split('|')[0].strip())
def feedback_public(kind,i):
    r=df("SELECT * FROM feedback WHERE reviewee_type=? AND reviewee_id=? AND public='Yes' ORDER BY created_at DESC",(kind,int(i)))
    if r.empty: st.info('No public feedback yet.'); return
    st.metric('Public feedback score',f"{round(r['rating'].mean(),2)} / 5")
    for _,x in r.iterrows():
        with st.container(border=True): st.write(f"⭐ **{x['rating']} / 5**"); st.caption(f"{safe(x['reviewer_type'])} review • {safe(x['created_at'])}"); st.write(safe(x['comment'],'No comment.'))
def buyer_profile_public(bid):
    b=get_buyer(bid)
    if b is None: bid=ensure_buyer(); b=get_buyer(bid)
    st.subheader(f"Buyer trust profile: {safe(b['name'])}")
    c1,c2,c3,c4=st.columns(4); c1.metric('Status',safe(b['status'])); c2.metric('Rating',f"{b['rating']}%"); c3.metric('Purchases',int(b['completed_purchases'] or 0)); c4.metric('Unpaid orders',int(b['unpaid_orders'] or 0))
    st.write(f"**Bio:** {safe(b['bio'],'No buyer bio yet.')}"); feedback_public('Buyer',bid)
def product_card(p):
    with st.container(border=True):
        if safe(p['image_url']): st.image(safe(p['image_url']),use_container_width=True)
        else: st.markdown('### 🎵')
        st.subheader(f"{safe(p['artist'])} — {safe(p['title'])}"); st.caption(f"{safe(p['category'])} • {safe(p['format'])} • Barcode: {safe(p['barcode'],'none')}"); st.write(f"**Price:** {money(p['price'])}")
        if st.button('View item',key=f"item_{int(p['id'])}"): st.session_state['product_id']=int(p['id']); st.rerun()
def seller_profile(sid):
    s=get_seller(sid)
    if s is None: st.error('Seller not found.'); return
    if st.button('← Back'): st.session_state.pop('seller_id',None); st.rerun()
    if safe(s['banner_url']): st.image(safe(s['banner_url']),use_container_width=True)
    col1,col2=st.columns([1,4])
    with col1:
        if safe(s['logo_url']): st.image(safe(s['logo_url']),use_container_width=True)
        else: st.markdown('## 🏪')
    with col2:
        st.title(safe(s['store_name'])); st.caption(f"{safe(s['seller_level'])} • Rating {s['rating']}% • Sales {s['completed_sales']} • Followers {followers(sid)}")
        if badges(sid): st.info('Badges: '+badges(sid))
        if safe(s['instagram']): st.write('Instagram: '+safe(s['instagram']))
        if safe(s['website']): st.link_button('Seller website',safe(s['website']))
    with st.expander('Follow this seller'):
        bid=buyer_pick(f'follow{sid}')
        if st.button('Follow seller',key=f'followbtn{sid}'):
            if df('SELECT id FROM seller_followers WHERE seller_id=? AND buyer_id=?',(sid,bid)).empty: run('INSERT INTO seller_followers(seller_id,buyer_id,created_at) VALUES(?,?,?)',(sid,bid,now())); st.success('Followed.')
            else: st.info('Already following.')
    anns=df("SELECT * FROM store_announcements WHERE seller_id=? AND status='Active' ORDER BY created_at DESC",(sid,))
    if not anns.empty:
        st.subheader('Store announcements')
        for _,a in anns.iterrows():
            with st.container(border=True): st.write('**'+safe(a['title'])+'**'); st.write(safe(a['body']))
    evs=df("SELECT * FROM seller_events WHERE seller_id=? AND status='Active' ORDER BY event_date",(sid,))
    if not evs.empty:
        st.subheader('Drops / events')
        for _,e in evs.iterrows():
            with st.container(border=True): st.write(f"**{safe(e['event_title'])}** — {safe(e['event_type'])}"); st.caption(safe(e['event_date'])); st.write(safe(e['description']))
    st.subheader('About this seller'); st.write(safe(s['seller_story'],safe(s['store_bio'],'No story yet.'))); st.write('**Specialties:** '+safe(s['specialties'],'Not listed'))
    st.subheader('Public seller feedback'); feedback_public('Seller',sid)
    st.subheader('Public inventory')
    prods=df("SELECT * FROM products WHERE seller_id=? AND listing_status IN ('Active','Draft') ORDER BY created_at DESC",(sid,))
    if prods.empty: st.info('No inventory yet.')
    else:
        cols=st.columns(3)
        for i,(_,p) in enumerate(prods.iterrows()):
            with cols[i%3]: product_card(p)
def product_detail(pid):
    r=df('SELECT * FROM products WHERE id=?',(int(pid),))
    if r.empty: st.error('Product missing.'); st.session_state.pop('product_id',None); return
    p=r.iloc[0]; s=get_seller(int(p['seller_id']))
    if st.button('← Back to marketplace'): st.session_state.pop('product_id',None); st.rerun()
    l,rcol=st.columns([1.2,1])
    with l:
        if safe(p['image_url']): st.image(safe(p['image_url']),use_container_width=True)
        else: st.markdown('## 🎵')
        gal=df('SELECT * FROM product_gallery WHERE product_id=? ORDER BY created_at DESC',(pid,))
        if not gal.empty:
            st.subheader('Gallery')
            for _,g in gal.iterrows():
                if safe(g['image_url']): st.image(safe(g['image_url']),caption=safe(g['caption']),use_container_width=True)
    with rcol:
        st.title(f"{safe(p['artist'])} — {safe(p['title'])}"); st.write('**Price:** '+money(p['price'])); st.write('**Shipping:** '+money(p['shipping_price']))
        for label,col in [('Category','category'),('Format','format'),('Label','label'),('Release year','release_year'),('Barcode / UPC / EAN','barcode'),('Catalog #','catalog_number'),('Matrix / runout','matrix_runout'),('Condition','media_grade')]: st.write(f"**{label}:** {safe(p[col],'Not listed')}")
        if s is not None and st.button('View seller public profile'): st.session_state['seller_id']=int(s['id']); st.session_state.pop('product_id',None); st.rerun()
    st.subheader('Description'); st.write(safe(p['description'],'No description.'))
    st.divider(); st.subheader('Buyer actions')
    bid=buyer_pick(f'buy{pid}')
    with st.expander('Request to buy / message seller',expanded=True):
        action=st.selectbox('Action',['Request to Buy','Ask a Question','Make Offer'],key=f'act{pid}'); msg=st.text_area('Message',key=f'msg{pid}')
        if st.button('Send to seller',key=f'send{pid}'):
            total=float(p['price'] or 0)+float(p['shipping_price'] or 0); pf=fee(total)
            run('''INSERT INTO orders(product_id,seller_id,buyer_id,order_type,status,item_price,shipping_price,platform_fee,seller_payout,buyer_message,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)''',(pid,int(p['seller_id']),bid,action,'New',float(p['price'] or 0),float(p['shipping_price'] or 0),pf,total-pf,msg,now(),now()))
            run('''INSERT INTO messages(product_id,seller_id,buyer_id,sender_type,subject,message,status,created_at) VALUES(?,?,?,?,?,?,?,?)''',(pid,int(p['seller_id']),bid,'Buyer',action,msg,'New',now()))
            st.success('Sent. It appears in seller orders and messages.')
    with st.expander('Report listing'):
        reason=st.selectbox('Reason',['Counterfeit / Bootleg','Misgraded','Wrong information','Spam','Other']); details=st.text_area('Details')
        if st.button('Submit report'): run("INSERT INTO listing_flags(product_id,seller_id,buyer_id,reason,details,status,created_at) VALUES(?,?,?,?,?,'Open',?)",(pid,int(p['seller_id']),bid,reason,details,now())); st.success('Report submitted.')

# ---------- Pages ----------

# ---------- House Of Wax Knowledge Hub ----------
KNOWLEDGE_CATEGORIES=[
    'Record Collecting 101',
    'Vinyl Grading School',
    'Barcode, Catalog & Matrix Guides',
    'Spotting Bootlegs and Reissues',
    'How to Buy Safely',
    'Care, Storage & Cleaning',
    'Genre Education',
    'Music History & Culture',
    'House Of Wax Trust Standards',
    'Marketplace Education'
]

def seed_knowledge():
    posts=table('knowledge_posts')
    if posts.empty:
        starters=[
            ('What Does VG+ Mean When Buying Vinyl?','Vinyl Grading School','Beginners','Beginner','VG+ means Very Good Plus. It usually describes a record that has been played but still has strong sound quality.','VG+ does not mean perfect. It usually means the record may show light marks, minor sleeve scuffs, or small signs of handling, but it should play well without major issues like repeated skips. Buyers should read condition notes, review photos, and ask questions when a grade is not clear.','On House Of Wax, grading education helps buyers understand what they are paying for before they purchase.'),
            ('What Is a Matrix / Runout?','Barcode, Catalog & Matrix Guides','Collectors','Beginner','A matrix or runout is information etched or stamped near the center label of a record.','The matrix/runout area can help collectors identify a pressing, plant, mastering engineer, or version. It is one of the most useful clues when comparing originals, reissues, promos, and different pressings.','House Of Wax encourages sellers and buyers to record matrix/runout information whenever possible.'),
            ('How to Spot a Bootleg or Unofficial Pressing','Spotting Bootlegs and Reissues','Buyers','Intermediate','Bootlegs and unofficial pressings can look real at first glance, but details often reveal the truth.','Collectors should compare label design, barcode, catalog number, matrix/runout, print quality, release history, and seller notes. A suspiciously low price on a rare record can also be a warning sign.','House Of Wax believes transparency protects both buyers and honest sellers.'),
            ('How to Store Vinyl Records the Right Way','Care, Storage & Cleaning','Beginners','Beginner','Good storage protects sound quality, jacket condition, and long-term value.','Store records vertically, avoid heat and sunlight, use inner and outer sleeves, and keep records away from moisture. Never stack records flat for long periods because weight can cause warping or ring wear.','Better storage means better collecting and fewer condition disputes.'),
            ('Why Buyer and Seller Feedback Should Be Public','House Of Wax Trust Standards','Everyone','Beginner','Public feedback helps the community understand who they are doing business with.','Trust matters in a marketplace built around used, collectible, and condition-sensitive goods. Public feedback gives buyers and sellers more confidence before a transaction.','House Of Wax is built around education, transparency, and accountability.')
        ]
        for title,cat,aud,level,summary,body,tip in starters:
            run("""INSERT INTO knowledge_posts(title,category,audience,level,summary,body,house_tip,status,featured,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (title,cat,aud,level,summary,body,tip,'Published','Yes' if 'VG+' in title else 'No',now(),now()))
    terms=table('glossary_terms')
    if terms.empty:
        starter_terms=[
            ('VG+','Vinyl grading','Very Good Plus. A common collector grade for a used record that should still play well.','Helps buyers understand condition and price.','A VG+ record may have light sleeve scuffs but should not have deep scratches.'),
            ('Matrix / Runout','Record identification','Etched or stamped information near the center label of a vinyl record.','Can help identify the exact pressing.','A1/B1 or stamped plant codes can point to a specific version.'),
            ('Catalog Number','Record identification','The label or release number assigned to a record, CD, cassette, or music item.','Helps verify the release and compare versions.','A catalog number printed on the spine may match the label listing.'),
            ('Reissue','Pressing history','A later release of an album or single after the original issue.','Reissues can be valuable, but they are not the same as originals.','A 2020 reissue of a 1972 soul record is not the original 1972 pressing.'),
            ('Promo Copy','Record collecting','A promotional copy distributed to radio stations, DJs, reviewers, or industry contacts.','Promos can be collectible but should be clearly described.','White label promo copies often have special labels or stamps.')
        ]
        for term,cat,definition,why,example in starter_terms:
            run("""INSERT OR IGNORE INTO glossary_terms(term,category,plain_definition,why_it_matters,example,status,created_at,updated_at) VALUES(?,?,?,?,?,'Published',?,?)""",
                (term,cat,definition,why,example,now(),now()))

def make_social_pack(title,category,summary,body,tip):
    core=safe(summary) or safe(body)[:180]
    hashtag_base='#HouseOfWax #VinylCommunity #RecordCollecting #MusicCulture #CollectSmarter'
    caption=f"{title}\n\n{core}\n\nHouse Of Wax is here to help people collect smarter, buy with confidence, and understand the culture behind the music.\n\n{hashtag_base}"
    reel=f"Hook: Before you buy another record, learn this: {title}\n\nScene 1: Show the record/detail being discussed.\nScene 2: Explain the simple definition in one sentence.\nScene 3: Show why it matters for buyers and collectors.\nScene 4: End with: Collect smarter with House Of Wax."
    fb=f"House Of Wax Knowledge Hub: {title}\n\n{core}\n\nWhy it matters: {safe(tip,'Education builds trust in the marketplace.')}\n\nLearn more inside House Of Wax."
    newsletter=f"This week in the House Of Wax Knowledge Hub: {title}. {core} This is part of our mission to make record collecting, marketplace trust, and music culture easier to understand for everyone."
    return {'Instagram/Facebook caption':caption,'Short-form video script':reel,'Facebook educational post':fb,'Newsletter blurb':newsletter,'Hashtags':hashtag_base,'CTA':'Learn more in the House Of Wax Knowledge Hub.'}

def knowledge_card(row):
    with st.container(border=True):
        if safe(row.get('image_url')): st.image(safe(row.get('image_url')),use_container_width=True)
        st.subheader(safe(row.get('title')))
        st.caption(f"{safe(row.get('category'))} • {safe(row.get('level'))} • {safe(row.get('audience'))}")
        st.write(safe(row.get('summary')))
        if st.button('Read article',key=f"read_knowledge_{int(row['id'])}"):
            st.session_state['selected_knowledge_id']=int(row['id']); st.rerun()

def knowledge_hub():
    seed_knowledge()
    header()
    st.header('House Of Wax Knowledge Hub')
    st.write('Education owned by House Of Wax. This is not seller promotion. This hub teaches buyers, collectors, and visitors how to understand records, music culture, marketplace trust, grading, barcodes, catalog numbers, matrix/runouts, and safe buying.')
    if 'selected_knowledge_id' in st.session_state:
        rows=df('SELECT * FROM knowledge_posts WHERE id=?',(int(st.session_state['selected_knowledge_id']),))
        if rows.empty:
            st.session_state.pop('selected_knowledge_id',None); st.rerun()
        post=rows.iloc[0]
        if st.button('← Back to Knowledge Hub'):
            st.session_state.pop('selected_knowledge_id',None); st.rerun()
        st.title(safe(post['title']))
        st.caption(f"{safe(post['category'])} • {safe(post['level'])} • For {safe(post['audience'])}")
        if safe(post['image_url']): st.image(safe(post['image_url']),use_container_width=True)
        st.markdown('### Quick answer')
        st.write(safe(post['summary']))
        st.markdown('### Full guide')
        st.write(safe(post['body']))
        st.markdown('### House Of Wax tip')
        st.info(safe(post['house_tip'],'Collect smarter with House Of Wax.'))
        with st.expander('House Of Wax social media copy for this education post'):
            pack=make_social_pack(post['title'],post['category'],post['summary'],post['body'],post['house_tip'])
            for k,v in pack.items():
                st.markdown(f'**{k}**')
                st.text_area(k,v,height=140,key=f"social_pack_{k}_{int(post['id'])}")
        return
    featured=df("SELECT * FROM knowledge_posts WHERE status='Published' AND featured='Yes' ORDER BY updated_at DESC")
    if not featured.empty:
        st.subheader('Featured education')
        knowledge_card(featured.iloc[0])
    st.subheader('Search the education library')
    q=st.text_input('Search topics like VG+, barcode, runout, bootleg, storage, trust')
    cats=['All']+KNOWLEDGE_CATEGORIES
    cat=st.selectbox('Category',cats)
    posts=df("SELECT * FROM knowledge_posts WHERE status='Published' ORDER BY updated_at DESC")
    if q:
        term=q.lower()
        posts=posts[
            posts['title'].fillna('').str.lower().str.contains(term) |
            posts['summary'].fillna('').str.lower().str.contains(term) |
            posts['body'].fillna('').str.lower().str.contains(term) |
            posts['category'].fillna('').str.lower().str.contains(term)
        ]
    if cat!='All': posts=posts[posts['category']==cat]
    cols=st.columns(2)
    for i,(_,row) in enumerate(posts.iterrows()):
        with cols[i%2]: knowledge_card(row)
    st.divider()
    st.subheader('Collector glossary')
    terms=df("SELECT * FROM glossary_terms WHERE status='Published' ORDER BY term")
    tq=st.text_input('Search glossary')
    if tq:
        term=tq.lower()
        terms=terms[
            terms['term'].fillna('').str.lower().str.contains(term) |
            terms['plain_definition'].fillna('').str.lower().str.contains(term) |
            terms['category'].fillna('').str.lower().str.contains(term)
        ]
    for _,t in terms.iterrows():
        with st.expander(f"{safe(t['term'])} — {safe(t['category'])}"):
            st.write(safe(t['plain_definition']))
            st.caption(f"Why it matters: {safe(t['why_it_matters'])}")
            if safe(t['example']): st.write(f"Example: {safe(t['example'])}")

def content_admin():
    seed_knowledge()
    header()
    st.header('House Of Wax Content Admin')
    st.write('Create House Of Wax educational content only. This is for teaching and brand authority, not seller promotion.')
    tabs=st.tabs(['Article creator','Glossary builder','Social copy generator','Draft library','Content calendar','Reports'])
    with tabs[0]:
        with st.form('knowledge_article_form'):
            title=st.text_input('Article title')
            category=st.selectbox('Category',KNOWLEDGE_CATEGORIES)
            audience=st.selectbox('Audience',['Beginners','Collectors','Buyers','Sellers','Everyone'])
            level=st.selectbox('Level',['Beginner','Intermediate','Advanced'])
            summary=st.text_area('Short plain-English summary')
            body=st.text_area('Full educational article')
            tip=st.text_area('House Of Wax tip')
            img_file=st.file_uploader('Optional image',type=['png','jpg','jpeg','webp'])
            img_url=st.text_input('Or image URL')
            status=st.selectbox('Status',['Draft','Published'])
            featured=st.selectbox('Featured',['No','Yes'])
            submitted=st.form_submit_button('Save education article')
        if submitted:
            img=save(img_file,'knowledge_images') or img_url
            run("""INSERT INTO knowledge_posts(title,category,audience,level,summary,body,house_tip,image_url,status,featured,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                (title,category,audience,level,summary,body,tip,img,status,featured,now(),now()))
            st.success('Knowledge article saved.')
        st.dataframe(table('knowledge_posts'),use_container_width=True)
    with tabs[1]:
        with st.form('glossary_form'):
            term=st.text_input('Term')
            category=st.text_input('Category',value='Record collecting')
            definition=st.text_area('Plain-English definition')
            why=st.text_area('Why it matters')
            example=st.text_area('Example')
            status=st.selectbox('Status',['Published','Draft'])
            submitted=st.form_submit_button('Save glossary term')
        if submitted:
            run("""INSERT OR REPLACE INTO glossary_terms(term,category,plain_definition,why_it_matters,example,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)""",
                (term,category,definition,why,example,status,now(),now()))
            st.success('Glossary term saved.')
        st.dataframe(table('glossary_terms'),use_container_width=True)
    with tabs[2]:
        posts=table('knowledge_posts')
        if posts.empty: st.info('Create an article first.')
        else:
            pid=st.selectbox('Choose education article',posts['id'].tolist())
            post=posts[posts['id']==pid].iloc[0]
            pack=make_social_pack(post['title'],post['category'],post['summary'],post['body'],post['house_tip'])
            platform=st.selectbox('Save draft for platform',['Instagram','TikTok/Reels','Facebook','YouTube Shorts','Email/Newsletter','In-App'])
            for k,v in pack.items():
                st.markdown(f'**{k}**')
                st.text_area(k,v,height=140,key=f"admin_pack_{k}")
            if st.button('Save social draft for House Of Wax'):
                run("""INSERT INTO content_drafts(source_type,source_id,title,platform,caption,script,hashtags,cta,status,created_at,updated_at) VALUES('Knowledge Article',?,?,?,?,?,?,?,'Draft',?,?)""",
                    (int(pid),safe(post['title']),platform,pack['Instagram/Facebook caption'],pack['Short-form video script'],pack['Hashtags'],pack['CTA'],now(),now()))
                st.success('Draft saved.')
    with tabs[3]:
        drafts=table('content_drafts')
        st.dataframe(drafts,use_container_width=True)
        if not drafts.empty:
            did=st.selectbox('Draft ID',drafts['id'].tolist())
            status=st.selectbox('Draft status',['Draft','Ready','Posted','Archived'])
            if st.button('Update draft status'):
                run('UPDATE content_drafts SET status=?,updated_at=? WHERE id=?',(status,now(),int(did))); st.success('Draft updated.')
    with tabs[4]:
        with st.form('calendar_form'):
            ctype=st.selectbox('Content type',['Article','Short-form video','Instagram post','Facebook post','Email','In-app feature'])
            topic=st.text_input('Topic')
            platform=st.selectbox('Platform',['House Of Wax App','Instagram','TikTok','YouTube Shorts','Facebook','Email'])
            pdate=st.text_input('Planned date')
            status=st.selectbox('Status',['Planned','Drafting','Ready','Posted'])
            notes=st.text_area('Notes')
            submitted=st.form_submit_button('Add to calendar')
        if submitted:
            run("""INSERT INTO content_calendar(content_type,topic,platform,planned_date,status,notes,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)""",
                (ctype,topic,platform,pdate,status,notes,now(),now()))
            st.success('Calendar item saved.')
        st.dataframe(table('content_calendar'),use_container_width=True)
    with tabs[5]:
        rep=st.selectbox('Content report',['knowledge_posts','glossary_terms','content_drafts','content_calendar','homepage_blocks','quick_tips','did_you_know','newsletter_signups'])
        data=table(rep)
        st.dataframe(data,use_container_width=True)
        st.download_button('Download CSV',data.to_csv(index=False),file_name=f'{rep}.csv')


# ---------- V18 Home + Editorial Experience ----------
def seed_homepage_editorial():
    seed_knowledge()
    if table('homepage_blocks').empty:
        blocks=[
            ('hero','House Of Wax','Music. Culture. Collecting. Community.','Discover the stories, sounds, formats, and knowledge behind the music you collect. House Of Wax is where marketplace trust meets music culture education.','Visit Knowledge Hub','Knowledge Hub','Active',1),
            ('featured_story','What Does VG+ Really Mean?','Featured Story','VG+ does not mean perfect. It means the record has been played but should still sound strong, with only light signs of use. Before you buy used vinyl, learn what grades actually mean.','Read the Guide','Knowledge Hub','Active',2),
            ('weekly_focus','This Week at House Of Wax','Matrix / Runout','The small letters and numbers etched near the center of a record can tell a big story. Matrix and runout information can help identify pressings, mastering details, and release versions.','Learn About Runouts','Knowledge Hub','Active',3),
            ('genre_spotlight','Southern Soul Essentials','Genre / Era Spotlight','Southern soul is more than a sound. It carries church roots, regional storytelling, blues influence, deep vocals, and a sense of place.','Explore Spotlight','Knowledge Hub','Active',4),
            ('editorial_pick','Format Focus: Why Cassettes Still Matter','House Of Wax Editorial Pick','Cassettes are portable, imperfect, personal, and deeply tied to mixtape culture. Their return is not just nostalgia — it is about physical connection.','Read More','Knowledge Hub','Active',5),
            ('newsletter','Join House Of Wax','Join the Culture','Get collector tips, music culture stories, grading guides, and marketplace education from House Of Wax.','Join the List','Newsletter','Active',6)
        ]
        for b in blocks:
            run("INSERT INTO homepage_blocks(block_name,title,subtitle,body,button_text,button_target,status,sort_order,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)",(*b,now(),now()))
    if table('quick_tips').empty:
        for tip,cat in [
            ('A barcode can help identify a reissue, but it does not tell the whole story.','Barcode, Catalog & Matrix Guides'),
            ('A clean sleeve does not always mean the record is clean. Check both media and sleeve grades.','Vinyl Grading School'),
            ('Original pressings are not always the best sounding version. Research matters.','Record Collecting 101'),
            ('A promo copy can be collectible, but condition and demand still matter.','Record Collecting 101'),
            ('If a rare record is priced too low, slow down and verify the details.','How to Buy Safely')]:
            run("INSERT INTO quick_tips(tip_text,category,status,created_at,updated_at) VALUES(?,?,'Active',?,?)",(tip,cat,now(),now()))
    if table('did_you_know').empty:
        for fact,cat in [
            ('The matrix/runout area of a record can sometimes help identify the pressing plant, mastering engineer, or version.','Barcode, Catalog & Matrix Guides'),
            ('VG+ is one of the most common collector grades, but it still allows minor signs of use.','Vinyl Grading School'),
            ('Some reissues are highly respected by collectors, especially when they are well mastered and clearly documented.','Spotting Bootlegs and Reissues'),
            ('Music memorabilia can carry cultural value even when it is not rare.','Music History & Culture')]:
            run("INSERT INTO did_you_know(fact_text,category,status,created_at,updated_at) VALUES(?,?,'Active',?,?)",(fact,cat,now(),now()))

def home_block(name):
    r=df("SELECT * FROM homepage_blocks WHERE block_name=? AND status='Active' ORDER BY sort_order,id LIMIT 1",(name,))
    return {} if r.empty else r.iloc[0].to_dict()

def mini_card(title,subtitle,body):
    with st.container(border=True):
        st.caption(safe(subtitle))
        st.subheader(safe(title))
        st.write(safe(body))

def home():
    seed_homepage_editorial()
    header()
    hero=home_block('hero')
    st.markdown('---')
    left,right=st.columns([1.35,1])
    with left:
        st.caption('HOUSE OF WAX')
        st.markdown(f"# {safe(hero.get('title'),'House Of Wax')}")
        st.markdown(f"### {safe(hero.get('subtitle'),'Music. Culture. Collecting. Community.')}")
        st.write(safe(hero.get('body'),'Discover records, learn the culture, and collect smarter.'))
        a,b,c=st.columns(3)
        if a.button('Explore Marketplace'): st.info('Use the sidebar to open Marketplace.')
        if b.button('Visit Knowledge Hub'): st.info('Use the sidebar to open Knowledge Hub.')
        if c.button("Read This Week's Feature"): st.info('Use the sidebar to open Knowledge Hub.')
    with right:
        st.markdown('### 🎧 A marketplace with a built-in culture magazine')
        st.write('House Of Wax teaches people how to collect, buy, sell, and understand music culture the right way.')
    c1,c2,c3,c4=st.columns(4)
    c1.metric('Knowledge Articles',len(table('knowledge_posts')))
    c2.metric('Glossary Terms',len(table('glossary_terms')))
    c3.metric('Marketplace Items',len(table('products')))
    c4.metric('Community Posts',len(table('culture_posts')))
    st.markdown('---')
    l,r=st.columns(2)
    with l:
        x=home_block('featured_story'); mini_card(x.get('title','What Does VG+ Really Mean?'),x.get('subtitle','Featured Story'),x.get('body','Learn grading before you buy.'))
    with r:
        x=home_block('weekly_focus'); mini_card(x.get('title','This Week at House Of Wax'),x.get('subtitle','Matrix / Runout'),x.get('body','Runout markings can reveal pressing details.'))
    st.markdown('---')
    st.markdown('## Learn the Culture')
    st.caption('Start with the basics or go deeper into pressings, grading, formats, trust, and music history.')
    tiles=[
        ('Record Collecting 101','Learn the basic language of collecting.'),
        ('Vinyl Grading School','Understand Mint, Near Mint, VG+, VG, and Good.'),
        ('Barcode, Catalog & Matrix Guides','Learn how identifiers help verify releases.'),
        ('Bootlegs & Reissues','Learn originals, reissues, unofficial pressings, and bootlegs.'),
        ('Care, Storage & Cleaning','Protect records, sleeves, tapes, CDs, posters, and memorabilia.'),
        ('Music History & Culture','Explore scenes, regions, genres, and movements.'),
        ('Genre Education','Learn the roots and sounds behind different genres.'),
        ('House Of Wax Trust Standards','Understand transparency and public feedback.')
    ]
    cols=st.columns(4)
    for i,(t,bdy) in enumerate(tiles):
        with cols[i%4]: mini_card(t,'Knowledge path',bdy)
    st.markdown('---')
    q,d=st.columns(2)
    with q:
        st.markdown('## Collector Quick Tips')
        tips=df("SELECT * FROM quick_tips WHERE status='Active' ORDER BY id LIMIT 5")
        for _,tip in tips.iterrows(): st.write(f"• {safe(tip['tip_text'])}")
    with d:
        st.markdown('## Did You Know?')
        facts=df("SELECT * FROM did_you_know WHERE status='Active' ORDER BY id LIMIT 4")
        for _,fact in facts.iterrows(): mini_card('Did you know?',safe(fact['category']),safe(fact['fact_text']))
    st.markdown('---')
    s,p=st.columns(2)
    with s:
        x=home_block('genre_spotlight'); mini_card(x.get('title','Southern Soul Essentials'),x.get('subtitle','Genre / Era Spotlight'),x.get('body','Explore the sound, labels, artists, and culture.'))
    with p:
        x=home_block('editorial_pick'); mini_card(x.get('title','Format Focus: Why Cassettes Still Matter'),x.get('subtitle','House Of Wax Editorial Pick'),x.get('body','Cassettes connect music to memory and mixtape culture.'))
    st.markdown('---')
    st.markdown('## Latest From the Knowledge Hub')
    posts=df("SELECT * FROM knowledge_posts WHERE status='Published' ORDER BY updated_at DESC LIMIT 6")
    cols=st.columns(3)
    for i,(_,post) in enumerate(posts.iterrows()):
        with cols[i%3]: knowledge_card(post)
    st.markdown('---')
    news=home_block('newsletter')
    st.markdown(f"## {safe(news.get('title'),'Join House Of Wax')}")
    st.write(safe(news.get('body'),'Get collector tips, music culture stories, grading guides, and marketplace education from House Of Wax.'))
    n1,n2,n3=st.columns([1,1,1])
    name=n1.text_input('Name',key='newsletter_name')
    email=n2.text_input('Email',key='newsletter_email')
    if n3.button('Join the List'):
        if not safe(email): st.warning('Enter an email first.')
        else:
            run("INSERT INTO newsletter_signups(email,name,source,created_at) VALUES(?,?,?,?)",(email,name,'Homepage',now()))
            st.success('You are on the House Of Wax list.')

def homepage_editor():
    seed_homepage_editorial()
    st.subheader('Homepage Editor')
    tabs=st.tabs(['Homepage Blocks','Quick Tips','Did You Know','Newsletter Signups'])
    with tabs[0]:
        st.dataframe(table('homepage_blocks'),use_container_width=True)
        with st.form('home_block_form'):
            bn=st.selectbox('Block',['hero','featured_story','weekly_focus','genre_spotlight','editorial_pick','newsletter'])
            title=st.text_input('Title'); sub=st.text_input('Subtitle'); body=st.text_area('Body')
            btn=st.text_input('Button text'); target=st.text_input('Button target')
            status=st.selectbox('Status',['Active','Draft','Hidden'])
            order=st.number_input('Sort order',min_value=0,value=1)
            if st.form_submit_button('Save homepage block'):
                run("INSERT INTO homepage_blocks(block_name,title,subtitle,body,button_text,button_target,status,sort_order,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)",(bn,title,sub,body,btn,target,status,int(order),now(),now()))
                st.success('Homepage block saved.')
    with tabs[1]:
        st.dataframe(table('quick_tips'),use_container_width=True)
        with st.form('tip_form'):
            tip=st.text_area('Quick tip'); cat=st.text_input('Category')
            status=st.selectbox('Status',['Active','Draft','Hidden'],key='tip_status')
            if st.form_submit_button('Save quick tip'):
                run("INSERT INTO quick_tips(tip_text,category,status,created_at,updated_at) VALUES(?,?,?,?,?)",(tip,cat,status,now(),now()))
                st.success('Quick tip saved.')
    with tabs[2]:
        st.dataframe(table('did_you_know'),use_container_width=True)
        with st.form('fact_form'):
            fact=st.text_area('Fact'); cat=st.text_input('Category',key='fact_cat')
            status=st.selectbox('Status',['Active','Draft','Hidden'],key='fact_status')
            if st.form_submit_button('Save fact'):
                run("INSERT INTO did_you_know(fact_text,category,status,created_at,updated_at) VALUES(?,?,?,?,?)",(fact,cat,status,now(),now()))
                st.success('Fact saved.')
    with tabs[3]:
        data=table('newsletter_signups')
        st.dataframe(data,use_container_width=True)
        if not data.empty:
            st.download_button('Download newsletter signups',data.to_csv(index=False),file_name='newsletter_signups.csv')

def test_setup():
    header(); st.header('Test setup')
    if st.button('Create/repair demo buyer, seller, and product'): st.success(f'Demo ready: buyer/seller/product IDs {seed_all()}')
    st.code('Buyer: buyer@test.com\nSeller: seller@test.com\nSeller access code: test123')
    st.subheader('Buyers'); st.dataframe(table('buyers'),use_container_width=True); st.subheader('Sellers'); st.dataframe(table('sellers'),use_container_width=True); st.subheader('Products'); st.dataframe(table('products'),use_container_width=True)
def register():
    header(); st.header('Register / create accounts'); btab,stab=st.tabs(['Buyer','Seller store'])
    with btab:
        with st.form('buyerform'):
            name=st.text_input('Buyer name'); email=st.text_input('Buyer email'); phone=st.text_input('Phone'); city=st.text_input('City'); state=st.text_input('State'); bio=st.text_area('Buyer bio'); sub=st.form_submit_button('Create buyer')
        if sub:
            if email_exists('buyers',email): st.warning('Buyer already exists. Open Buyer Dashboard.')
            else: run('''INSERT INTO buyers(name,email,phone,city,state,bio,status,rating,completed_purchases,unpaid_orders,disputes,strikes,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)''',(name,email,phone,city,state,bio,'Trusted Buyer',100,0,0,0,0,now())); st.success('Buyer created.')
    with stab:
        with st.form('sellerform'):
            store=st.text_input('Store name'); owner=st.text_input('Owner'); email=st.text_input('Seller email'); code=st.text_input('Access code',type='password'); bio=st.text_area('Store bio'); story=st.text_area('Seller story'); spec=st.text_area('Specialties'); logo=st.file_uploader('Logo',type=['png','jpg','jpeg','webp']); banner=st.file_uploader('Banner',type=['png','jpg','jpeg','webp']); sub=st.form_submit_button('Create active seller store')
        if sub:
            if email_exists('sellers',email): st.warning('Seller already exists. Open Seller Dashboard.')
            else: run('''INSERT INTO sellers(store_name,owner_name,email,phone,city,state,website,instagram,store_bio,seller_story,specialties,logo_url,banner_url,status,seller_level,rating,completed_sales,disputes,strikes,auction_override,access_code,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',(store,owner,email,'','','','','',bio,story,spec,save_file(logo,'seller_logos'),save_file(banner,'seller_banners'),'Approved','Verified Seller',100,0,0,0,'Yes',code,now())); st.success('Seller store active.')
def marketplace():
    header(); st.header('Marketplace')
    if 'seller_id' in st.session_state: seller_profile(int(st.session_state['seller_id'])); return
    if 'product_id' in st.session_state: product_detail(int(st.session_state['product_id'])); return
    prods=df("SELECT * FROM products WHERE listing_status IN ('Active','Draft') ORDER BY created_at DESC")
    if prods.empty: st.info('No inventory yet. Use Test Setup or Seller Dashboard.'); return
    q=st.text_input('Search title, artist, barcode, catalog, category')
    if q:
        term=q.lower(); prods=prods[prods['artist'].fillna('').str.lower().str.contains(term)|prods['title'].fillna('').str.lower().str.contains(term)|prods['barcode'].fillna('').str.lower().str.contains(term)|prods['catalog_number'].fillna('').str.lower().str.contains(term)|prods['category'].fillna('').str.lower().str.contains(term)]
    cols=st.columns(3)
    for i,(_,p) in enumerate(prods.iterrows()):
        with cols[i%3]: product_card(p)
def seller_stores():
    header(); st.header('Seller stores')
    if 'seller_id' in st.session_state: seller_profile(int(st.session_state['seller_id'])); return
    sellers=table('sellers')
    if sellers.empty: st.info('No sellers yet.'); return
    for _,s in sellers.iterrows():
        with st.container(border=True):
            if safe(s['banner_url']): st.image(safe(s['banner_url']),use_container_width=True)
            st.subheader(safe(s['store_name'])); st.caption(f"{safe(s['seller_level'])} • Rating {s['rating']}% • Followers {followers(int(s['id']))}"); st.write(safe(s['store_bio']))
            if badges(int(s['id'])): st.info('Badges: '+badges(int(s['id'])))
            if st.button('Open public profile',key=f"openseller{int(s['id'])}"): st.session_state['seller_id']=int(s['id']); st.rerun()
def buyer_dashboard():
    header(); st.header('Buyer dashboard')
    mode=st.radio('Open buyer by',['Choose existing buyer','Create/open by email'],horizontal=True)
    if mode=='Choose existing buyer': bid=buyer_pick('buyerdb')
    else:
        email=st.text_input('Buyer email',value='buyer@test.com'); name=st.text_input('Buyer name',value='Test Buyer')
        if st.button('Create/open buyer'): st.session_state['buyer_id']=create_buyer(email,name)
        bid=st.session_state.get('buyer_id',ensure_buyer())
    b=get_buyer(bid); st.success(f"Loaded buyer: {safe(b['name'])} | {safe(b['email'])}")
    tabs=st.tabs(['Profile','Orders','Messages','Following','Leave seller feedback','Public feedback'])
    with tabs[0]:
        with st.form('bp'):
            name=st.text_input('Name',value=safe(b['name'])); email=st.text_input('Email',value=safe(b['email'])); bio=st.text_area('Bio',value=safe(b['bio'])); sub=st.form_submit_button('Save buyer profile')
        if sub: run('UPDATE buyers SET name=?,email=?,bio=? WHERE id=?',(name,email,bio,bid)); st.success('Saved.')
    with tabs[1]: st.dataframe(df('SELECT * FROM orders WHERE buyer_id=? ORDER BY created_at DESC',(bid,)),use_container_width=True)
    with tabs[2]: st.dataframe(df('SELECT * FROM messages WHERE buyer_id=? ORDER BY created_at DESC',(bid,)),use_container_width=True)
    with tabs[3]: st.dataframe(df('SELECT f.*,s.store_name,s.rating FROM seller_followers f LEFT JOIN sellers s ON f.seller_id=s.id WHERE f.buyer_id=?',(bid,)),use_container_width=True)
    with tabs[4]:
        orders=df("SELECT * FROM orders WHERE buyer_id=? AND status='Completed' ORDER BY created_at DESC",(bid,)); st.dataframe(orders,use_container_width=True)
        if not orders.empty:
            oid=st.selectbox('Completed order',orders['id'].tolist()); o=orders[orders['id']==oid].iloc[0]; rating=st.slider('Seller rating',1,5,5); comment=st.text_area('Public seller feedback')
            if st.button('Submit public seller feedback'): run("INSERT INTO feedback(order_id,reviewer_type,reviewer_id,reviewee_type,reviewee_id,rating,comment,public,created_at) VALUES(?,'Buyer',?,'Seller',?,?,?,'Yes',?)",(int(oid),bid,int(o['seller_id']),int(rating),comment,now())); update_rating('Seller',int(o['seller_id'])); st.success('Feedback posted.')
    with tabs[5]: buyer_profile_public(bid)
def upload_product(sid,key):
    with st.form(key):
        c1,c2,c3=st.columns(3); sku=c1.text_input('SKU'); barcode=c2.text_input('Barcode / UPC / EAN'); catalog=c3.text_input('Catalog number'); matrix=st.text_input('Matrix / runout')
        c4,c5,c6=st.columns(3); category=c4.selectbox('Category',['Vinyl Records','CDs','Cassettes','Clothing','Music Memorabilia','Culture Goods']); artist=c5.text_input('Artist / Brand'); title=c6.text_input('Title / Product')
        c7,c8,c9=st.columns(3); fmt=c7.text_input('Format',value='Vinyl'); label=c8.text_input('Label / Brand'); year=c9.text_input('Release year')
        genre=st.text_input('Genre / style'); mg=st.selectbox('Media/product grade',['Mint','Near Mint','VG+','VG','Good','Used','New','N/A']); sg=st.selectbox('Sleeve/packaging grade',['Mint','Near Mint','VG+','VG','Good','Used','New','N/A']); notes=st.text_area('Condition notes'); desc=st.text_area('Description')
        c10,c11,c12=st.columns(3); price=c10.number_input('Price',min_value=0.0,step=.01); qty=c11.number_input('Quantity',min_value=1,value=1); ship=c12.number_input('Shipping price',min_value=0.0,step=.01)
        img=st.file_uploader('Product image',type=['png','jpg','jpeg','webp']); imgurl=st.text_input('Or image URL'); sub=st.form_submit_button('Upload product')
    if sub:
        image=save_file(img,'product_images') or imgurl; description=desc or f'{artist} — {title}. {notes}'
        run('''INSERT INTO products(seller_id,sku,barcode,catalog_number,matrix_runout,category,artist,title,format,label,release_year,genre,media_grade,sleeve_grade,condition_notes,description,price,quantity,shipping_price,image_url,video_url,audio_url,external_release_url,listing_status,listing_type,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',(sid,sku,barcode,catalog,matrix,category,artist,title,fmt,label,year,genre,mg,sg,notes,description,float(price),int(qty),float(ship),image,'','','','Active','Fixed Price',now(),now()))
        st.success('Product uploaded and public.')
def seller_dashboard():
    header(); st.header('Seller dashboard')
    mode=st.radio('Open seller by',['Choose existing seller','Email + access code'],horizontal=True)
    if mode=='Choose existing seller': sid=seller_pick('sellerdb')
    else:
        email=st.text_input('Seller email',value='seller@test.com'); code=st.text_input('Access code',value='test123',type='password'); r=df('SELECT * FROM sellers WHERE lower(email)=lower(?) AND access_code=?',(email.strip(),code)); sid=ensure_seller() if r.empty else int(r.iloc[0]['id'])
    s=get_seller(sid); st.success(f"Loaded seller: {safe(s['store_name'])} | {safe(s['email'])}")
    tabs=st.tabs(['Store profile','Policies','Upload product','Barcode scanner','Bulk import','Gallery','Listings','Orders','Messages','Announcements','Events/drops','Badges','Leave buyer feedback','Public feedback'])
    with tabs[0]:
        with st.form('sp'):
            store=st.text_input('Store name',value=safe(s['store_name'])); bio=st.text_area('Store bio',value=safe(s['store_bio'])); story=st.text_area('Seller story',value=safe(s['seller_story'])); spec=st.text_area('Specialties',value=safe(s['specialties'])); logo=st.file_uploader('Logo',type=['png','jpg','jpeg','webp']); banner=st.file_uploader('Banner',type=['png','jpg','jpeg','webp']); logo_url=st.text_input('Logo URL/path',value=safe(s['logo_url'])); banner_url=st.text_input('Banner URL/path',value=safe(s['banner_url'])); sub=st.form_submit_button('Save profile')
        if sub: run("UPDATE sellers SET store_name=?,store_bio=?,seller_story=?,specialties=?,logo_url=?,banner_url=?,status='Approved',seller_level='Verified Seller',auction_override='Yes' WHERE id=?",(store,bio,story,spec,save_file(logo,'seller_logos') or logo_url,save_file(banner,'seller_banners') or banner_url,sid)); st.success('Saved.')
    with tabs[1]:
        p=df('SELECT * FROM seller_policies WHERE seller_id=?',(sid,)); pol=p.iloc[0] if not p.empty else {}
        with st.form('policy'):
            shipping=st.text_area('Shipping policy',value=safe(pol.get('shipping_policy') if len(pol) else 'Ships within 3 business days.')); returns=st.text_area('Return policy',value=safe(pol.get('return_policy') if len(pol) else 'No buyer remorse returns unless seller approves.')); grading=st.text_area('Grading policy',value=safe(pol.get('grading_policy') if len(pol) else 'Collector grading standards.')); sub=st.form_submit_button('Save policies')
        if sub: run('INSERT OR REPLACE INTO seller_policies(seller_id,shipping_policy,return_policy,grading_policy) VALUES(?,?,?,?)',(sid,shipping,returns,grading)); st.success('Policies saved.')
    with tabs[2]: upload_product(sid,'normal_upload')
    with tabs[3]:
        st.subheader('Barcode scanner / inventory quick add'); st.info('Click the barcode field and scan with USB/Bluetooth scanner, phone keyboard scanner, or type/paste barcode.')
        code=st.text_input('Scan or enter barcode / UPC / EAN'); known=barcode_lookup(code)
        if known: st.success('Known barcode found; details shown below.'); st.json(known)
        with st.form('barcodeadd'):
            barcode=st.text_input('Barcode',value=code); catalog=st.text_input('Catalog number',value=safe(known.get('catalog_number'))); matrix=st.text_input('Matrix / runout'); artist=st.text_input('Artist / Brand',value=safe(known.get('artist'))); title=st.text_input('Title / Product',value=safe(known.get('title'))); fmt=st.text_input('Format',value=safe(known.get('format'),'Vinyl')); label=st.text_input('Label',value=safe(known.get('label'))); year=st.text_input('Release year',value=safe(known.get('release_year'))); genre=st.text_input('Genre',value=safe(known.get('genre'))); price=st.number_input('Price',min_value=0.0,step=.01); qty=st.number_input('Quantity',min_value=1,value=1); img=st.file_uploader('Image',type=['png','jpg','jpeg','webp']); sub=st.form_submit_button('Add scanned item to inventory')
        if sub: run('''INSERT INTO products(seller_id,sku,barcode,catalog_number,matrix_runout,category,artist,title,format,label,release_year,genre,media_grade,sleeve_grade,condition_notes,description,price,quantity,shipping_price,image_url,video_url,audio_url,external_release_url,listing_status,listing_type,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',(sid,'',barcode,catalog,matrix,'Vinyl Records',artist,title,fmt,label,year,genre,'N/A','N/A','',f'{artist} — {title}. Barcode {barcode}.',float(price),int(qty),0,save_file(img,'product_images'),'','','','Active','Fixed Price',now(),now())); st.success('Scanned item added.')
    with tabs[4]:
        csv=st.file_uploader('Upload CSV',type=['csv']); st.caption('Supports barcode,catalog_number,matrix_runout,artist,title,format,label,release_year,genre,price,quantity,image_url')
        if csv is not None:
            data=pd.read_csv(csv); st.dataframe(data,use_container_width=True)
            if st.button('Import CSV products'):
                n=0
                for _,r in data.iterrows(): run('''INSERT INTO products(seller_id,sku,barcode,catalog_number,matrix_runout,category,artist,title,format,label,release_year,genre,media_grade,sleeve_grade,condition_notes,description,price,quantity,shipping_price,image_url,video_url,audio_url,external_release_url,listing_status,listing_type,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',(sid,safe(r.get('sku')),safe(r.get('barcode')),safe(r.get('catalog_number')),safe(r.get('matrix_runout')),safe(r.get('category'),'Vinyl Records'),safe(r.get('artist')),safe(r.get('title')),safe(r.get('format'),'Vinyl'),safe(r.get('label')),safe(r.get('release_year')),safe(r.get('genre')),safe(r.get('media_grade')),safe(r.get('sleeve_grade')),safe(r.get('condition_notes')),safe(r.get('description')),float(r.get('price',0) or 0),int(r.get('quantity',1) or 1),float(r.get('shipping_price',0) or 0),safe(r.get('image_url')),safe(r.get('video_url')),safe(r.get('audio_url')),safe(r.get('external_release_url')),safe(r.get('listing_status'),'Active'),'Fixed Price',now(),now())); n+=1
                st.success(f'Imported {n}.')
    with tabs[5]:
        prods=df('SELECT * FROM products WHERE seller_id=?',(sid,)); st.dataframe(prods,use_container_width=True)
        if not prods.empty:
            pid=st.selectbox('Product for gallery',prods['id'].tolist()); img=st.file_uploader('Gallery image',type=['png','jpg','jpeg','webp']); url=st.text_input('Or image URL'); cap=st.text_input('Caption')
            if st.button('Add gallery image'):
                image=save_file(img,'product_gallery') or url
                if image: run('INSERT INTO product_gallery(product_id,image_url,caption,created_at) VALUES(?,?,?,?)',(int(pid),image,cap,now())); st.success('Gallery image added.')
    with tabs[6]:
        prods=df('SELECT * FROM products WHERE seller_id=? ORDER BY created_at DESC',(sid,)); st.dataframe(prods,use_container_width=True)
        if not prods.empty:
            pid=st.selectbox('Listing ID',prods['id'].tolist()); status=st.selectbox('Status',['Active','Draft','Sold','Removed'])
            if st.button('Update listing'): run('UPDATE products SET listing_status=?,updated_at=? WHERE id=? AND seller_id=?',(status,now(),int(pid),sid)); st.success('Updated.')
    with tabs[7]:
        orders=df('SELECT o.*,b.name buyer_name,b.email buyer_email,b.rating buyer_rating FROM orders o LEFT JOIN buyers b ON o.buyer_id=b.id WHERE o.seller_id=? ORDER BY o.created_at DESC',(sid,)); st.dataframe(orders,use_container_width=True)
        if not orders.empty:
            bids=orders['buyer_id'].dropna().astype(int).unique().tolist(); bp=st.selectbox('View buyer public trust profile',bids); buyer_profile_public(int(bp)); oid=st.selectbox('Order ID',orders['id'].tolist()); status=st.selectbox('Order status',['New','Contacted','Invoice Sent','Paid','Shipped','Completed','Cancelled','Disputed'])
            if st.button('Update order'):
                run('UPDATE orders SET status=?,updated_at=? WHERE id=? AND seller_id=?',(status,now(),int(oid),sid))
                if status=='Completed': row=orders[orders['id']==oid].iloc[0]; run('UPDATE sellers SET completed_sales=completed_sales+1 WHERE id=?',(sid,)); run('UPDATE buyers SET completed_purchases=completed_purchases+1 WHERE id=?',(int(row['buyer_id']),))
                st.success('Order updated.')
    with tabs[8]: st.dataframe(df('SELECT * FROM messages WHERE seller_id=? ORDER BY created_at DESC',(sid,)),use_container_width=True)
    with tabs[9]:
        with st.form('ann'): title=st.text_input('Announcement title'); body=st.text_area('Announcement body'); sub=st.form_submit_button('Post announcement')
        if sub: run("INSERT INTO store_announcements(seller_id,title,body,status,created_at) VALUES(?,?,?,'Active',?)",(sid,title,body,now())); st.success('Posted.')
        st.dataframe(df('SELECT * FROM store_announcements WHERE seller_id=?',(sid,)),use_container_width=True)
    with tabs[10]:
        with st.form('ev'): title=st.text_input('Drop/event title'); typ=st.selectbox('Type',['Record Drop','Auction Drop','Sale','Live Event','Other']); date=st.text_input('Date/time'); desc=st.text_area('Description'); sub=st.form_submit_button('Save event')
        if sub: run("INSERT INTO seller_events(seller_id,event_title,event_type,event_date,description,status,created_at) VALUES(?,?,?,?,?,'Active',?)",(sid,title,typ,date,desc,now())); st.success('Saved.')
    with tabs[11]: st.write(badges(sid) or 'No badges yet.'); st.dataframe(df('SELECT * FROM seller_badges WHERE seller_id=?',(sid,)),use_container_width=True)
    with tabs[12]:
        orders=df("SELECT * FROM orders WHERE seller_id=? AND status='Completed'",(sid,)); st.dataframe(orders,use_container_width=True)
        if not orders.empty:
            oid=st.selectbox('Completed order',orders['id'].tolist(),key='sellerfb'); o=orders[orders['id']==oid].iloc[0]; rating=st.slider('Buyer rating',1,5,5); comment=st.text_area('Public buyer feedback')
            if st.button('Submit public buyer feedback'): run("INSERT INTO feedback(order_id,reviewer_type,reviewer_id,reviewee_type,reviewee_id,rating,comment,public,created_at) VALUES(?,'Seller',?,'Buyer',?,?,?,'Yes',?)",(int(oid),sid,int(o['buyer_id']),int(rating),comment,now())); update_rating('Buyer',int(o['buyer_id'])); st.success('Feedback posted.')
    with tabs[13]: feedback_public('Seller',sid)
def auctions():
    header(); st.header('Auctions'); sid=seller_pick('auction_seller'); prods=df("SELECT * FROM products WHERE seller_id=? AND listing_status IN ('Active','Draft')",(sid,))
    if not prods.empty:
        with st.form('auction'): pid=st.selectbox('Product',prods['id'].tolist()); title=st.text_input('Auction title'); start=st.number_input('Starting bid',min_value=0.0,step=1.0); end=st.text_input('End time'); sub=st.form_submit_button('Create live auction')
        if sub: run("INSERT INTO auctions(product_id,seller_id,auction_title,starting_bid,reserve_price,buy_now_price,bid_increment,start_time,end_time,status,notes,created_at) VALUES(?,?,?,?,?,?,1,?,?,'Live','',?)",(int(pid),sid,title,float(start),0,0,now(),end,now())); st.success('Auction created.')
    st.dataframe(table('auctions'),use_container_width=True)
def culture():
    header(); st.header('Music + Culture'); posts=df("SELECT * FROM culture_posts WHERE status='Published' ORDER BY created_at DESC")
    if posts.empty: st.info('No culture posts yet.')
    for _,p in posts.iterrows():
        with st.container(border=True):
            if safe(p['image_url']): st.image(safe(p['image_url']),use_container_width=True)
            st.subheader(safe(p['title'])); st.caption(f"{safe(p['category'])} • {safe(p['author'])}"); st.write(safe(p['body']))
def admin():
    header(); st.header('Admin')
    if ADMIN_PASSWORD:
        pwd=st.text_input('Admin password',type='password')
        if not st.button('Enter admin'): return
        if pwd!=ADMIN_PASSWORD: st.error('Wrong password.'); return
    else: st.info('No admin password set. Testing build allows admin access.')
    tabs=st.tabs(['Overview','Sellers','Buyers','Community tools','Reports','Cleanup'])
    with tabs[0]: c1,c2,c3,c4=st.columns(4); c1.metric('Buyers',len(table('buyers'))); c2.metric('Sellers',len(table('sellers'))); c3.metric('Products',len(table('products'))); c4.metric('Orders',len(table('orders')))
    with tabs[1]: st.dataframe(table('sellers'),use_container_width=True)
    with tabs[2]: st.dataframe(table('buyers'),use_container_width=True)
    with tabs[3]:
        sid=seller_pick('adminseller'); badge=st.text_input('Badge',placeholder='Soul Specialist, Jazz Dealer, Verified Seller'); typ=st.selectbox('Badge type',['Community','Specialty','Performance','Verified'])
        if st.button('Add badge'): run("INSERT INTO seller_badges(seller_id,badge_name,badge_type,active,created_at) VALUES(?,?,?,'Yes',?)",(sid,badge,typ,now())); st.success('Badge added.')
        if st.button('Create seller spotlight culture post'):
            s=get_seller(sid); run("INSERT INTO culture_posts(title,category,author,body,image_url,status,created_at) VALUES(?,'Seller Spotlight','House Of Wax',?,?,'Published',?)",(f"Seller Spotlight: {safe(s['store_name'])}",safe(s['seller_story'],safe(s['store_bio'])),safe(s['banner_url']) or safe(s['logo_url']),now())); st.success('Spotlight created.')
        st.subheader('Messages'); st.dataframe(table('messages'),use_container_width=True); st.subheader('Feedback'); st.dataframe(table('feedback'),use_container_width=True)
    with tabs[4]:
        rep=st.selectbox('Report',['buyers','sellers','products','product_gallery','orders','feedback','messages','seller_followers','seller_badges','store_announcements','seller_events','auctions','bids','listing_flags','culture_posts','knowledge_posts','glossary_terms','content_drafts','content_calendar']); data=table(rep); st.dataframe(data,use_container_width=True); st.download_button('Download CSV',data.to_csv(index=False),file_name=f'{rep}.csv')
    with tabs[5]:
        t=st.selectbox('Table',['buyers','sellers','products','product_gallery','orders','feedback','messages','seller_followers','seller_badges','store_announcements','seller_events','auctions','bids','listing_flags','culture_posts','knowledge_posts','glossary_terms','content_drafts','content_calendar']); data=table(t); st.dataframe(data,use_container_width=True)
        if not data.empty:
            rid=st.selectbox('Row ID',data['id'].tolist()); confirm=st.checkbox('Confirm delete')
            if st.button('Delete row') and confirm: run(f'DELETE FROM {t} WHERE id=?',(int(rid),)); st.success('Deleted.')

menu=st.sidebar.radio('House Of Wax',['Home','Knowledge Hub','Content Admin','Test Setup','Marketplace','Auctions','Seller Stores','Music + Culture','Register / Sell','Buyer Dashboard','Seller Dashboard','Admin'])
if menu=='Home': home()
elif menu=='Knowledge Hub': knowledge_hub()
elif menu=='Content Admin': content_admin()
elif menu=='Test Setup': test_setup()
elif menu=='Marketplace': marketplace()
elif menu=='Auctions': auctions()
elif menu=='Seller Stores': seller_stores()
elif menu=='Music + Culture': culture()
elif menu=='Register / Sell': register()
elif menu=='Buyer Dashboard': buyer_dashboard()
elif menu=='Seller Dashboard': seller_dashboard()
elif menu=='Admin': admin()
