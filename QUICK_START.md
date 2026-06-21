# Quick Start

1. Upload all files to GitHub, especially `app.py`.
2. In Streamlit, set Secrets:

```toml
ADMIN_PASSWORD = "your-private-password"
```

3. Reboot the app.
4. Confirm the app says:

`Running V15.4 FIX + TESTING PATCH`

## Test Flow

1. Register buyer.
2. Apply as seller.
3. Admin approves seller.
4. Seller logs in and creates policies.
5. Seller adds product.
6. Product appears in Marketplace.
7. Buyer saves item or sends Request to Buy.
8. Seller sees buyer rating and order.
9. Seller updates order or marks buyer non-paying.
10. Admin reviews reports, flags, sellers, buyers, and test cleanup.
