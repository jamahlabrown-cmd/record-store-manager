# House Of Wax V15.3 Clean Reset

This is a clean reset package built to replace the old broken `app.py`.

The app should display:

`Running V15.3 CLEAN RESET`

near the top of every page. If you do not see that, Streamlit is still running an older file.

## Model

- House Of Wax is the platform.
- Sellers apply and are approved.
- Approved sellers run their own stores.
- Sellers create their own policies.
- Buyers register and are accountable.
- Fixed-price listings do not require manual approval.
- Listings can be flagged for admin review.
- Auctions are earned by seller performance or admin override.

## Admin Password

Set Streamlit Secrets:

```toml
ADMIN_PASSWORD = "your-private-password"
```
