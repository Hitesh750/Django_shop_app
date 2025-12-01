# Simple Django + Stripe Checkout Shop

A minimal, secure, production-grade e-commerce prototype using **Django + Stripe Checkout (one-time payment)**.


GitHub: https://github.com/Hitesh750/Django_shop_app.git

## Assumptions (Spec Was Intentionally Sparse)

- We sell **digital or non-inventory products** (no stock management needed).
- Only **card payments** in USD.
- No user accounts or login required (guest checkout).
- We want to display paid orders publicly on the homepage (as shown in the original template).
- The shop starts with 3 seeded products (done via migrations/fixtures in real projects — here via Django admin or manual insert).
- Security & correctness over feature richness (focus on no double-charging, no lost orders).


→ **Checkout is the official Stripe-recommended flow for simple "Buy Now" shops.**

## How We Prevent Double Charges & Inconsistent State

1. **Server-side Order is created first** (unpaid) before redirecting to Stripe.
2. `client_reference_id` + `metadata` both contain the Django `Order.id`.
3. `order.stripe_session_id` is saved → makes webhook processing **idempotent**.
4. Webhook only marks order as `paid=True` if:
   - The order exists
   - It is not already marked paid
   - Stripe reports `payment_status == "paid"`
5. Webhook signature verification is **required in production** (graceful fallback only in DEBUG).
6. Success page verifies the session belongs to a paid order before celebrating.

→ Even if the user refreshes, closes browser, or webhook fires 10 times → **exactly one successful charge and one paid order**.

## Local Setup & Run

### 1. Clone & install
```bash
git clone https://github.com/Hitesh750/Django_shop_app.git
cd shop_project
python -m venv env
source venv/scripts/activate(for window) or  source venv/bin/activate (Linux)
pip install -r requirement.txt
python manage.py makemigrations ### create model migration file
python manage.py migrate ## create database table
python manage.py runserver (run locally)