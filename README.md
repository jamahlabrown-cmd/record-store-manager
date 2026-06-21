# House Of Wax V15 — Marketplace Platform Reset

House Of Wax V15 resets the project as a seller-powered marketplace platform. House Of Wax is not the inventory owner. Sellers create stores, upload products, set prices, ship orders, and handle customer service. House Of Wax approves sellers, manages trust, reviews flagged listings, tracks buyer/seller accountability, and controls auction eligibility.

Set Streamlit Secrets:
```toml
ADMIN_PASSWORD = "your-private-password"
```


## Fixed build note

This package patches the original V15 build by placing `st.set_page_config` at the beginning of the app and making Streamlit Secrets loading safer for local/Codespaces testing.
