
import sqlite3
from pathlib import Path
from datetime import datetime
import pandas as pd
import streamlit as st

DB=Path('house_of_wax_v15.db')
ADMIN_PASSWORD=st.secrets.get('ADMIN_PASSWORD','')
APP='House Of Wax'

def conn(): return sqlite3.connect(DB)
def q(sql, params=()):
    c=conn(); c.execute(sql, params); c.commit(); c.close()
def df(sql, params=()):
    c=conn(); d=pd.read_sql_query(sql,c,params=params); c.close(); return d
def table(t): return df(f'SELECT * FROM {t}')
def now(): return datetime.now().isoformat(timespec='seconds')
def money(x):
    try: return f'${float(x):,.2f}'
    except: return '$0.00'

def setup():
    c=conn(); cur=c.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')
    cur.execute('''CREATE TABLE IF NOT EXISTS buyers (id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT,email TEXT UNIQUE,phone TEXT,city TEXT,status TEXT DEFAULT 'New Buyer',rating REAL DEFAULT 100,completed_purchases INTEGER DEFAULT 0,unpaid_orders INTEGER DEFAULT 0,disputes INTEGER DEFAULT 0,strikes INTEGER DEFAULT 0,created_at TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS sellers (id INTEGER PRIMARY KEY AUTOINCREMENT,store_name TEXT NOT NULL,owner_name TEXT,email TEXT UNIQUE,phone TEXT,city TEXT,store_bio TEXT,logo_url TEXT,banner_url TEXT,status TEXT DEFAULT 'Pending',seller_level TEXT DEFAULT 'Starter Seller',rating REAL DEFAULT 100,completed_sales INTEGER DEFAULT 0,disputes INTEGER DEFAULT 0,strikes INTEGER DEFAULT 0,auction_override TEXT DEFAULT 'No',access_code TEXT,created_at TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS seller_policies (seller_id INTEGER PRIMARY KEY,shipping_policy TEXT,return_policy TEXT,grading_policy TEXT,customer_service_policy TEXT,bundle_policy TEXT,auction_policy TEXT,buyer_requirements TEXT,local_pickup_policy TEXT,international_shipping_policy TEXT,processing_time TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY AUTOINCREMENT,seller_id INTEGER,sku TEXT,barcode TEXT,catalog_number TEXT,matrix_runout TEXT,category TEXT,artist TEXT,title TEXT,format TEXT,label TEXT,release_year TEXT,genre TEXT,media_grade TEXT,sleeve_grade TEXT,condition_notes TEXT,description TEXT,price REAL DEFAULT 0,quantity INTEGER DEFAULT 1,shipping_price REAL DEFAULT 0,image_url TEXT,video_url TEXT,audio_url TEXT,external_release_url TEXT,listing_status TEXT DEFAULT 'Active',listing_type TEXT DEFAULT 'Fixed Price',created_at TEXT,updated_at TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT,product_id INTEGER,seller_id INTEGER,buyer_id INTEGER,order_type TEXT,status TEXT DEFAULT 'New',item_price REAL DEFAULT 0,shipping_price REAL DEFAULT 0,platform_fee REAL DEFAULT 0,seller_payout REAL DEFAULT 0,buyer_message TEXT,created_at TEXT,updated_at TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS listing_flags (id INTEGER PRIMARY KEY AUTOINCREMENT,product_id INTEGER,seller_id INTEGER,buyer_id INTEGER,reason TEXT,details TEXT,status TEXT DEFAULT 'Open',admin_notes TEXT,created_at TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS auctions (id INTEGER PRIMARY KEY AUTOINCREMENT,product_id INTEGER,seller_id INTEGER,auction_title TEXT,starting_bid REAL DEFAULT 0,reserve_price REAL DEFAULT 0,buy_now_price REAL DEFAULT 0,bid_increment REAL DEFAULT 1,start_time TEXT,end_time TEXT,status TEXT DEFAULT 'Draft',notes TEXT,created_at TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS bids (id INTEGER PRIMARY KEY AUTOINCREMENT,auction_id INTEGER,buyer_id INTEGER,bid_amount REAL,bid_time TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS disputes (id INTEGER PRIMARY KEY AUTOINCREMENT,order_id INTEGER,product_id INTEGER,seller_id INTEGER,buyer_id INTEGER,opened_by TEXT,reason TEXT,details TEXT,status TEXT DEFAULT 'Open',resolution TEXT,created_at TEXT,updated_at TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS feedback (id INTEGER PRIMARY KEY AUTOINCREMENT,order_id INTEGER,reviewer_type TEXT,reviewer_id INTEGER,reviewee_type TEXT,reviewee_id INTEGER,rating INTEGER,comment TEXT,created_at TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS culture_posts (id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT,category TEXT,author TEXT,body TEXT,image_url TEXT,status TEXT DEFAULT 'Published',created_at TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS social_posts (id INTEGER PRIMARY KEY AUTOINCREMENT,product_id INTEGER,seller_id INTEGER,platform TEXT,caption TEXT,hashtags TEXT,status TEXT DEFAULT 'Draft',created_at TEXT,posted_at TEXT)''')
    c.commit(); c.close()
    defaults={'platform_commission_percent':'9','auction_commission_percent':'10','auction_min_completed_sales':'10','auction_min_rating':'90','site_tagline':'A seller-powered marketplace for records, clothing, music culture, and collectors.','announcement':'Sellers run their own stores. Buyers and sellers are both accountable. Auctions are earned.','logo_url':'','buyer_payment_window_hours':'48','default_processing_time':'3 business days'}
    for k,v in defaults.items():
        if df('SELECT * FROM settings WHERE key=?',(k,)).empty: q('INSERT INTO settings VALUES (?,?)',(k,v))
setup()

def setting(k,d=''):
    r=df('SELECT value FROM settings WHERE key=?',(k,)); return d if r.empty else str(r.iloc[0].value)
def set_setting(k,v): q('INSERT OR REPLACE INTO settings VALUES (?,?)',(k,str(v)))
def fee(total,auction=False): return round(float(total)*float(setting('auction_commission_percent' if auction else 'platform_commission_percent','9'))/100,2)
def desc(p):
    ids=[]
    for k,n in [('barcode','barcode'),('catalog_number','catalog #'),('matrix_runout','matrix/runout')]:
        if p.get(k): ids.append(f"{n} {p.get(k)}")
    return f"{p.get('artist','')} — {p.get('title','')} is a curated {p.get('format','item')} listing from an independent House Of Wax seller. Genre/style: {p.get('genre','not specified')}. Condition: media/product {p.get('media_grade','N/A')} and sleeve/packaging {p.get('sleeve_grade','N/A')}. {'Identifiers: '+', '.join(ids)+'.' if ids else ''} Seller notes: {p.get('condition_notes','')}. Buyers should review all photos, descriptions, seller policies, and shipping terms before purchasing or bidding."
def quality(p):
    checks=[float(p.get('price') or 0)>0,bool(p.get('image_url') or p.get('video_url') or p.get('audio_url')),bool(p.get('media_grade') or p.get('condition_notes')),bool(p.get('description') and len(str(p.get('description'))>120)),bool(p.get('barcode') or p.get('catalog_number') or p.get('matrix_runout')),bool(p.get('category')),p.get('listing_status')=='Active']
    return int(sum(checks)/len(checks)*100)
def seller_row(sid):
    r=df('SELECT * FROM sellers WHERE id=?',(sid,)); return None if r.empty else r.iloc[0]
def auction_ok(s):
    if s is None: return False,'Seller not found.'
    if s.status!='Approved': return False,'Seller must be approved first.'
    if s.auction_override=='Yes': return True,'Auction access manually approved by House Of Wax.'
    if int(s.completed_sales or 0)<int(float(setting('auction_min_completed_sales','10'))): return False,'Seller needs more completed sales.'
    if float(s.rating or 0)<float(setting('auction_min_rating','90')): return False,'Seller rating is too low.'
    if int(s.disputes or 0)>0 or int(s.strikes or 0)>0: return False,'Seller needs a clean dispute/strike record or admin override.'
    return True,'Seller qualifies for auctions.'
def buyer_ok(b):
    if b is None: return False,'Buyer must register first.'
    if b.status in ['Restricted Buyer','Suspended Buyer']: return False,'Buyer account is restricted.'
    if int(b.unpaid_orders or 0)>=3: return False,'Buyer has too many unpaid orders.'
    return True,'Buyer may purchase/bid.'

def header():
    c1,c2=st.columns([1,5])
    logo=setting('logo_url')
    with c1: st.image(logo,use_container_width=True) if logo else st.markdown('## 🎧')
    with c2: st.title(APP); st.caption(setting('site_tagline'))
    if setting('announcement'): st.info(setting('announcement'))

def product_card(p):
    with st.container(border=True):
        if p.get('image_url'): st.image(p.image_url,use_container_width=True)
        elif p.get('video_url'): st.video(p.video_url)
        else: st.markdown('### 🎵')
        st.subheader(f"{p.get('artist','')} — {p.get('title','')}")
        st.caption(f"{p.get('format','')} • {p.get('category','')} • {p.get('media_grade','')}")
        st.write(f"**{money(p.get('price'))}** + shipping {money(p.get('shipping_price'))}")
        st.progress(quality(p)/100,text=f"Listing quality {quality(p)}/100")
        if st.button('View Item',key=f'view{p.id}'):
            st.session_state.product=int(p.id); st.rerun()

def product_detail(p):
    if st.button('← Back'): st.session_state.pop('product',None); st.rerun()
    s=seller_row(int(p.seller_id))
    c1,c2=st.columns([1.2,1])
    with c1:
        if p.get('image_url'): st.image(p.image_url,use_container_width=True)
        if p.get('video_url'): st.video(p.video_url)
        if p.get('audio_url'): st.audio(p.audio_url)
    with c2:
        st.header(f"{p.artist} — {p.title}"); st.write(f"**Price:** {money(p.price)}"); st.write(f"**Seller:** {s.store_name if s is not None else 'Unknown'}"); st.write(f"**Condition:** {p.media_grade} / {p.sleeve_grade}"); st.caption(f"Barcode: {p.barcode or 'N/A'} • Catalog: {p.catalog_number or 'N/A'}")
        if p.external_release_url: st.link_button('Release/research link',p.external_release_url)
    st.subheader('Description'); st.write(p.description or desc(p))
    if s is not None:
        pol=df('SELECT * FROM seller_policies WHERE seller_id=?',(int(s.id),))
        with st.expander('Seller store policies'):
            if pol.empty: st.info('Seller has not added detailed policies yet; House Of Wax minimum rules still apply.')
            else:
                r=pol.iloc[0]
                st.write('**Shipping:**',r.shipping_policy or 'Not provided'); st.write('**Returns:**',r.return_policy or 'Not provided'); st.write('**Grading:**',r.grading_policy or 'Not provided'); st.write('**Buyer requirements:**',r.buyer_requirements or 'Not provided')
    st.divider(); st.subheader('Buy / Contact Seller')
    buyers=table('buyers')
    if buyers.empty: st.warning('Register as a buyer first.')
    else:
        choice=st.selectbox('Buyer account',[f"{r.id} | {r.name} | {r.email} | {r.status}" for _,r in buyers.iterrows()])
        bid=int(choice.split('|')[0]); b=buyers[buyers.id==bid].iloc[0]
        action=st.selectbox('Action',['Buy Now Request','Ask Seller a Question','Make Offer'])
        msg=st.text_area('Message')
        if st.button('Submit'):
            ok,reason=buyer_ok(b)
            if action=='Buy Now Request' and not ok: st.error(reason)
            else:
                total=float(p.price or 0)+float(p.shipping_price or 0); f=fee(total); payout=round(total-f,2)
                q('INSERT INTO orders (product_id,seller_id,buyer_id,order_type,status,item_price,shipping_price,platform_fee,seller_payout,buyer_message,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',(int(p.id),int(p.seller_id),bid,action,'New',float(p.price or 0),float(p.shipping_price or 0),f,payout,msg,now(),now()))
                st.success('Sent to seller.')
    with st.expander('Report this listing'):
        reason=st.selectbox('Reason',['Counterfeit / Bootleg','Misgraded Condition','Wrong Information','Offensive Content','Spam / Scam','Prohibited Item','Other'])
        details=st.text_area('Details')
        if st.button('Submit report'):
            q('INSERT INTO listing_flags (product_id,seller_id,buyer_id,reason,details,created_at) VALUES (?,?,?,?,?,?)',(int(p.id),int(p.seller_id),None,reason,details,now()))
            q("UPDATE products SET listing_status='Flagged' WHERE id=?",(int(p.id),)); st.success('Flagged for review.')

def marketplace():
    header(); st.header('Marketplace')
    products=df("SELECT * FROM products WHERE listing_status='Active' AND quantity>0 ORDER BY created_at DESC")
    if 'product' in st.session_state:
        r=products[products.id==st.session_state.product]
        if not r.empty: product_detail(r.iloc[0]); return
    if products.empty: st.info('No active listings yet.'); return
    c1,c2,c3=st.columns(3); search=c1.text_input('Search'); cat=c2.selectbox('Category',['All']+sorted(products.category.dropna().unique().tolist())); sort=c3.selectbox('Sort',['Newest','Price Low','Price High','Artist A-Z'])
    x=products.copy()
    if search:
        ss=search.lower(); x=x[x.artist.fillna('').str.lower().str.contains(ss)|x.title.fillna('').str.lower().str.contains(ss)|x.barcode.fillna('').str.lower().str.contains(ss)|x.catalog_number.fillna('').str.lower().str.contains(ss)]
    if cat!='All': x=x[x.category==cat]
    if sort=='Price Low': x=x.sort_values('price')
    elif sort=='Price High': x=x.sort_values('price',ascending=False)
    elif sort=='Artist A-Z': x=x.sort_values('artist')
    cols=st.columns(3)
    for i,(_,p) in enumerate(x.iterrows()):
        with cols[i%3]: product_card(p)

def register():
    header(); st.header('Register / Sell')
    t1,t2=st.tabs(['Buyer Registration','Seller Application'])
    with t1:
        with st.form('buyer'):
            name=st.text_input('Name'); email=st.text_input('Email'); phone=st.text_input('Phone'); city=st.text_input('City')
            if st.form_submit_button('Register Buyer'):
                try: q('INSERT INTO buyers (name,email,phone,city,created_at) VALUES (?,?,?,?,?)',(name,email,phone,city,now())); st.success('Buyer registered.')
                except Exception as e: st.error(e)
    with t2:
        st.write('Sellers must be approved. Once approved, fixed-price listings go live without product-by-product approval. Bad listings can be flagged.')
        with st.form('seller'):
            store=st.text_input('Store name'); owner=st.text_input('Owner'); email=st.text_input('Email'); phone=st.text_input('Phone'); city=st.text_input('City'); bio=st.text_area('Store bio'); code=st.text_input('Private seller access code'); agree=st.checkbox('I agree to House Of Wax platform rules.')
            if st.form_submit_button('Apply'):
                if not agree: st.error('Must agree.')
                else:
                    try: q('INSERT INTO sellers (store_name,owner_name,email,phone,city,store_bio,access_code,created_at) VALUES (?,?,?,?,?,?,?,?)',(store,owner,email,phone,city,bio,code,now())); st.success('Seller application submitted.')
                    except Exception as e: st.error(e)

def seller_dash():
    header(); st.header('Seller Dashboard')
    email=st.text_input('Seller email'); code=st.text_input('Access code',type='password')
    if not st.button('Enter'): return
    s=df('SELECT * FROM sellers WHERE email=? AND access_code=?',(email,code))
    if s.empty: st.error('Seller not found.'); return
    s=s.iloc[0]
    if s.status!='Approved': st.warning(f'Seller status: {s.status}. Admin must approve before selling.'); return
    st.success(f'Logged in as {s.store_name}')
    tabs=st.tabs(['My Store','Store Policies','Add Product','My Listings','Auctions','Orders','Social Posts','Rules'])
    sid=int(s.id)
    with tabs[0]:
        with st.form('profile'):
            store=st.text_input('Store name',value=s.store_name); bio=st.text_area('Bio',value=s.store_bio or ''); logo=st.text_input('Logo URL',value=s.logo_url or ''); banner=st.text_input('Banner URL',value=s.banner_url or '')
            if st.form_submit_button('Save'): q('UPDATE sellers SET store_name=?,store_bio=?,logo_url=?,banner_url=? WHERE id=?',(store,bio,logo,banner,sid)); st.success('Saved.')
    with tabs[1]:
        pol=df('SELECT * FROM seller_policies WHERE seller_id=?',(sid,)); r=pol.iloc[0] if not pol.empty else {}
        with st.form('pol'):
            shipping=st.text_area('Shipping policy',value=r.get('shipping_policy','') if len(r) else ''); returns=st.text_area('Return policy',value=r.get('return_policy','') if len(r) else ''); grading=st.text_area('Grading policy',value=r.get('grading_policy','') if len(r) else ''); service=st.text_area('Customer service policy',value=r.get('customer_service_policy','') if len(r) else ''); bundle=st.text_area('Bundle policy',value=r.get('bundle_policy','') if len(r) else ''); auction_policy=st.text_area('Auction policy',value=r.get('auction_policy','') if len(r) else ''); buyer_req=st.text_area('Buyer requirements',value=r.get('buyer_requirements','Buyer must be registered, in good standing, and pay within payment window.') if len(r) else 'Buyer must be registered, in good standing, and pay within payment window.'); pickup=st.text_area('Local pickup policy',value=r.get('local_pickup_policy','') if len(r) else ''); intl=st.text_area('International shipping policy',value=r.get('international_shipping_policy','') if len(r) else ''); processing=st.text_input('Processing time',value=r.get('processing_time',setting('default_processing_time')) if len(r) else setting('default_processing_time'))
            if st.form_submit_button('Save Policies'): q('INSERT OR REPLACE INTO seller_policies VALUES (?,?,?,?,?,?,?,?,?,?,?)',(sid,shipping,returns,grading,service,bundle,auction_policy,buyer_req,pickup,intl,processing)); st.success('Policies saved.')
    with tabs[2]:
        with st.form('prod'):
            c1,c2,c3=st.columns(3); sku=c1.text_input('SKU'); barcode=c2.text_input('Barcode/UPC/EAN'); catalog=c3.text_input('Catalog number')
            matrix=st.text_input('Matrix/runout'); category=st.selectbox('Category',['Vinyl Records','CDs','Cassettes','Music DVDs/VHS','Music Books/Magazines','Posters','Music Memorabilia','Vintage Clothing','Streetwear','Band Tees','DJ Gear/Accessories','Culture Goods']); artist=st.text_input('Artist/Brand'); title=st.text_input('Title/Product'); fmt=st.text_input('Format',value='Vinyl'); label=st.text_input('Label/Brand'); year=st.text_input('Year'); genre=st.text_input('Genre/Style'); media=st.selectbox('Media/Product grade',['Mint','Near Mint','VG+','VG','Good','Fair','Poor','New','Used','N/A']); sleeve=st.selectbox('Sleeve/Packaging grade',['Mint','Near Mint','VG+','VG','Good','Fair','Poor','New','Used','N/A']); notes=st.text_area('Condition notes')
            generated=desc({'artist':artist,'title':title,'format':fmt,'genre':genre,'label':label,'release_year':year,'media_grade':media,'sleeve_grade':sleeve,'catalog_number':catalog,'barcode':barcode,'matrix_runout':matrix,'condition_notes':notes})
            description=st.text_area('Description',value=generated,height=170); price=st.number_input('Price',min_value=0.0,step=0.01); qty=st.number_input('Quantity',min_value=1,value=1); ship=st.number_input('Shipping price',min_value=0.0,step=0.01); image=st.text_input('Image URL'); video=st.text_input('Video URL'); audio=st.text_input('Audio URL'); ext=st.text_input('Discogs/MusicBrainz/Popsike URL'); status=st.selectbox('Status',['Active','Draft'])
            if st.form_submit_button('Publish Product'):
                q('INSERT INTO products (seller_id,sku,barcode,catalog_number,matrix_runout,category,artist,title,format,label,release_year,genre,media_grade,sleeve_grade,condition_notes,description,price,quantity,shipping_price,image_url,video_url,audio_url,external_release_url,listing_status,listing_type,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(sid,sku,barcode,catalog,matrix,category,artist,title,fmt,label,year,genre,media,sleeve,notes,description,price,qty,ship,image,video,audio,ext,status,'Fixed Price',now(),now())); st.success('Product saved.')
    with tabs[3]:
        prods=df('SELECT * FROM products WHERE seller_id=? ORDER BY created_at DESC',(sid,)); st.dataframe(prods,use_container_width=True)
        if not prods.empty:
            pid=st.selectbox('Product ID',prods.id.tolist()); status=st.selectbox('New status',['Active','Draft','Sold','Removed'])
            if st.button('Update status'): q('UPDATE products SET listing_status=?,updated_at=? WHERE id=? AND seller_id=?',(status,now(),int(pid),sid)); st.success('Updated.')
    with tabs[4]:
        ok,reason=auction_ok(s); st.info(f'Auction eligible: {ok}. {reason}')
        prods=df("SELECT * FROM products WHERE seller_id=? AND listing_status='Active'",(sid,))
        if ok and not prods.empty:
            with st.form('auc'):
                pid=st.selectbox('Product',prods.id.tolist()); title=st.text_input('Auction title'); start=st.number_input('Starting bid',min_value=0.0,step=1.0); reserve=st.number_input('Reserve',min_value=0.0,step=1.0); buy=st.number_input('Buy now',min_value=0.0,step=1.0); inc=st.number_input('Bid increment',min_value=1.0,step=1.0); end=st.text_input('End time'); status=st.selectbox('Status',['Draft','Live']); notes=st.text_area('Notes')
                if st.form_submit_button('Create Auction'): q('INSERT INTO auctions (product_id,seller_id,auction_title,starting_bid,reserve_price,buy_now_price,bid_increment,start_time,end_time,status,notes,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',(int(pid),sid,title,start,reserve,buy,inc,now(),end,status,notes,now())); st.success('Auction created.')
        st.dataframe(df('SELECT * FROM auctions WHERE seller_id=?',(sid,)),use_container_width=True)
    with tabs[5]: st.dataframe(df('SELECT * FROM orders WHERE seller_id=? ORDER BY created_at DESC',(sid,)),use_container_width=True)
    with tabs[6]: st.write('Generate post copy from listings. Full social automation can be connected later.'); st.dataframe(df('SELECT * FROM social_posts WHERE seller_id=?',(sid,)),use_container_width=True)
    with tabs[7]: st.markdown('Seller rules can be stronger than House Of Wax rules, but never weaker. Sellers handle upload, pricing, shipping, customer service, and store policies.')

def auctions():
    header(); st.header('Auctions'); st.caption('Sellers earn auctions through sales, rating, and platform history.')
    a=df("SELECT a.*,p.artist,p.title,p.image_url,s.store_name FROM auctions a LEFT JOIN products p ON a.product_id=p.id LEFT JOIN sellers s ON a.seller_id=s.id WHERE a.status='Live'")
    if a.empty: st.info('No live auctions.'); return
    buyers=table('buyers')
    for _,r in a.iterrows():
        with st.container(border=True):
            if r.image_url: st.image(r.image_url,use_container_width=True)
            st.subheader(r.auction_title); st.caption(f"{r.artist} — {r.title} • Seller: {r.store_name}")
            high=df('SELECT MAX(bid_amount) h FROM bids WHERE auction_id=?',(int(r.id),)).iloc[0].h; current=high if pd.notna(high) else r.starting_bid
            st.write(f'Current bid: {money(current)}')
            if buyers.empty: st.warning('Register as buyer first.')
            else:
                choice=st.selectbox('Buyer',[f"{b.id} | {b.name} | {b.status}" for _,b in buyers.iterrows()],key=f'buyer{r.id}'); bid=int(choice.split('|')[0]); br=buyers[buyers.id==bid].iloc[0]; amount=st.number_input('Bid amount',min_value=float(current)+float(r.bid_increment),step=float(r.bid_increment),key=f'amt{r.id}')
                if st.button('Place Bid',key=f'pb{r.id}'):
                    ok,reason=buyer_ok(br)
                    if not ok: st.error(reason)
                    else: q('INSERT INTO bids VALUES (NULL,?,?,?,?)',(int(r.id),bid,amount,now())); st.success('Bid placed.')

def stores():
    header(); st.header('Seller Stores')
    sellers=df("SELECT * FROM sellers WHERE status='Approved' ORDER BY store_name")
    if sellers.empty: st.info('No approved seller stores yet.'); return
    for _,s in sellers.iterrows():
        with st.container(border=True):
            if s.banner_url: st.image(s.banner_url,use_container_width=True)
            st.subheader(s.store_name); st.caption(f"{s.seller_level} • Rating {s.rating}% • Sales {s.completed_sales}"); st.write(s.store_bio or '')

def culture():
    header(); st.header('Music + Culture')
    posts=df("SELECT * FROM culture_posts WHERE status='Published' ORDER BY created_at DESC")
    if posts.empty: st.info('No culture posts yet. Use Admin to publish seller spotlights, music guides, clothing/culture stories, auction previews, and collecting education.')
    for _,p in posts.iterrows():
        with st.container(border=True):
            if p.image_url: st.image(p.image_url,use_container_width=True)
            st.subheader(p.title); st.caption(f'{p.category} • {p.author}'); st.write(p.body)

def admin():
    header(); st.header('House Of Wax Platform Admin')
    pw=st.text_input('Admin password',type='password')
    if not st.button('Login'): return
    if not ADMIN_PASSWORD: st.error('Set ADMIN_PASSWORD in Streamlit Secrets.'); return
    if pw!=ADMIN_PASSWORD: st.error('Wrong password.'); return
    tabs=st.tabs(['Overview','Seller Applications','Sellers','Buyers','Flagged Listings','Orders','Disputes','Auctions','Culture','Settings','Reports','Business Plan'])
    with tabs[0]:
        c1,c2,c3,c4=st.columns(4); c1.metric('Sellers',len(table('sellers'))); c2.metric('Buyers',len(table('buyers'))); c3.metric('Listings',len(table('products'))); c4.metric('Flags',len(table('listing_flags')))
        st.info('V15 rule: approve sellers, not every listing. Flag problems. Auctions are earned. Buyers are accountable too.')
    with tabs[1]:
        pending=df("SELECT * FROM sellers WHERE status='Pending'"); st.dataframe(pending,use_container_width=True)
        if not pending.empty:
            sid=st.selectbox('Seller ID',pending.id.tolist()); action=st.selectbox('Decision',['Approved','Rejected'])
            if st.button('Apply decision'): q('UPDATE sellers SET status=?,seller_level=? WHERE id=?',(action,'Approved Seller' if action=='Approved' else 'Rejected',int(sid))); st.success('Updated.')
    with tabs[2]:
        sellers=table('sellers'); st.dataframe(sellers,use_container_width=True)
        if not sellers.empty:
            sid=st.selectbox('Manage seller ID',sellers.id.tolist()); status=st.selectbox('Status',['Pending','Approved','Suspended','Rejected','Verified']); override=st.selectbox('Auction override',['No','Yes']); sales=st.number_input('Completed sales',min_value=0,step=1); rating=st.number_input('Rating',0.0,100.0,100.0); strikes=st.number_input('Strikes',min_value=0,step=1); disputes=st.number_input('Disputes',min_value=0,step=1)
            if st.button('Update seller'): q('UPDATE sellers SET status=?,auction_override=?,completed_sales=?,rating=?,strikes=?,disputes=? WHERE id=?',(status,override,sales,rating,strikes,disputes,int(sid))); st.success('Seller updated.')
    with tabs[3]:
        buyers=table('buyers'); st.dataframe(buyers,use_container_width=True)
        if not buyers.empty:
            bid=st.selectbox('Buyer ID',buyers.id.tolist()); status=st.selectbox('Buyer status',['New Buyer','Verified Buyer','Trusted Buyer','Restricted Buyer','Suspended Buyer']); rating=st.number_input('Buyer rating',0.0,100.0,100.0); unpaid=st.number_input('Unpaid orders',min_value=0,step=1); strikes=st.number_input('Buyer strikes',min_value=0,step=1)
            if st.button('Update buyer'): q('UPDATE buyers SET status=?,rating=?,unpaid_orders=?,strikes=? WHERE id=?',(status,rating,unpaid,strikes,int(bid))); st.success('Buyer updated.')
    with tabs[4]:
        flags=df('SELECT f.*,p.artist,p.title,s.store_name FROM listing_flags f LEFT JOIN products p ON f.product_id=p.id LEFT JOIN sellers s ON f.seller_id=s.id ORDER BY f.created_at DESC'); st.dataframe(flags,use_container_width=True)
        if not flags.empty:
            fid=st.selectbox('Flag ID',flags.id.tolist()); decision=st.selectbox('Decision',['Dismiss','Keep Under Review','Remove Listing','Suspend Seller','Issue Strike']); notes=st.text_area('Admin notes')
            if st.button('Resolve flag'):
                row=flags[flags.id==fid].iloc[0]
                if decision=='Remove Listing': q("UPDATE products SET listing_status='Removed' WHERE id=?",(int(row.product_id),))
                if decision=='Suspend Seller': q("UPDATE sellers SET status='Suspended' WHERE id=?",(int(row.seller_id),))
                if decision=='Issue Strike': q('UPDATE sellers SET strikes=strikes+1 WHERE id=?',(int(row.seller_id),))
                q('UPDATE listing_flags SET status=?,admin_notes=? WHERE id=?',(decision,notes,int(fid))); st.success('Resolved.')
    with tabs[5]:
        orders=table('orders'); st.dataframe(orders,use_container_width=True)
        if not orders.empty:
            oid=st.selectbox('Order ID',orders.id.tolist()); status=st.selectbox('Order status',['New','Contacted','Invoice Sent','Paid','Shipped','Completed','Cancelled','Disputed'])
            if st.button('Update order'): q('UPDATE orders SET status=?,updated_at=? WHERE id=?',(status,now(),int(oid))); st.success('Order updated.')
    with tabs[6]: st.dataframe(table('disputes'),use_container_width=True)
    with tabs[7]: st.dataframe(table('auctions'),use_container_width=True)
    with tabs[8]:
        with st.form('culture'):
            title=st.text_input('Title'); cat=st.selectbox('Category',['Music','Clothing','Culture','Collecting Guide','Seller Spotlight','Auction Preview','Regional History']); author=st.text_input('Author',value='House Of Wax'); img=st.text_input('Image URL'); body=st.text_area('Body')
            if st.form_submit_button('Publish'): q('INSERT INTO culture_posts (title,category,author,body,image_url,created_at) VALUES (?,?,?,?,?,?)',(title,cat,author,body,img,now())); st.success('Published.')
    with tabs[9]:
        for k in ['platform_commission_percent','auction_commission_percent','auction_min_completed_sales','auction_min_rating','site_tagline','announcement','logo_url','buyer_payment_window_hours','default_processing_time']:
            val=st.text_input(k,value=setting(k),key=k)
            if st.button(f'Save {k}',key=f'save{k}'): set_setting(k,val); st.success('Saved.')
    with tabs[10]:
        choice=st.selectbox('Table',['buyers','sellers','seller_policies','products','orders','listing_flags','auctions','bids','feedback','disputes','culture_posts','social_posts','settings']); data=table(choice); st.dataframe(data,use_container_width=True); st.download_button('Download CSV',data.to_csv(index=False),f'{choice}.csv')
    with tabs[11]: st.markdown('Business plan, budget, revenue model, policy summary, buyer policy, seller policy, and roadmap are included as files in this V15 package.')

st.set_page_config(page_title='House Of Wax Marketplace',layout='wide')
menu=st.sidebar.radio('House Of Wax',['Home','Marketplace','Auctions','Seller Stores','Music + Culture','Register / Sell','Seller Dashboard','Admin Login'])
if menu=='Home':
    header(); st.markdown('## Seller-powered music and culture marketplace'); st.write('House Of Wax is a platform where approved sellers create their own stores, upload products, set prices, ship orders, and handle customer service. House Of Wax manages rules, ratings, flagged listings, buyer/seller accountability, culture content, and auction access.');
    c1,c2,c3=st.columns(3); c1.metric('Active listings',len(df("SELECT * FROM products WHERE listing_status='Active'"))); c2.metric('Approved sellers',len(df("SELECT * FROM sellers WHERE status='Approved'"))); c3.metric('Registered buyers',len(table('buyers')))
elif menu=='Marketplace': marketplace()
elif menu=='Auctions': auctions()
elif menu=='Seller Stores': stores()
elif menu=='Music + Culture': culture()
elif menu=='Register / Sell': register()
elif menu=='Seller Dashboard': seller_dash()
elif menu=='Admin Login': admin()
