# EasyBill — Simple Invoicing SaaS (Django + Stripe)

EasyBill is a small invoicing tool for freelancers. It is a real
**SaaS billing app**: users sign up on a Free plan (limited to 3
invoices), and can upgrade to a Pro plan (unlimited invoices) by
paying through **Stripe**. This is the exact pattern used by almost
every real SaaS product.

## What this project demonstrates (for your resume / interview)

- User signup/login (Django's built-in auth system)
- A "Free vs Pro" plan model, with a real limit enforced in code
- Stripe Checkout integration (redirecting users to Stripe's hosted
  payment page — the safe, recommended way to take payments)
- Stripe **webhooks** — the server-to-server events that keep our
  database in sync with what actually happened on Stripe's side
  (this is the part most beginner tutorials skip, and the part
  real companies care about most)
- Normal CRUD: creating clients and invoices, marking invoices paid

## Folder structure (plain English)

```
easybill_project/
│
├── manage.py              <- the command you run to start/manage the project
├── requirements.txt       <- list of Python packages this project needs
│
├── easybill/               <- PROJECT settings (the "control room")
│   ├── settings.py         <- all configuration (database, Stripe keys, etc.)
│   ├── urls.py              <- top-level URL routing
│   └── wsgi.py / asgi.py    <- files used when deploying (ignore for now)
│
└── invoices/                <- our APP (all the actual feature code)
    ├── models.py             <- database tables: UserProfile, Client, Invoice
    ├── views.py               <- the logic behind every page
    ├── urls.py                <- maps URLs to views, for this app
    ├── admin.py                <- lets you view/edit data at /admin/
    └── templates/invoices/      <- all the HTML pages
        ├── base.html              <- shared layout (navbar, styling)
        ├── home.html               <- landing page
        ├── signup.html / login.html
        ├── dashboard.html           <- main page after login
        ├── client_list.html / add_client.html
        ├── add_invoice.html / invoice_detail.html
        ├── pricing.html              <- Free vs Pro comparison + Upgrade button
        └── checkout_success.html / checkout_cancelled.html
```

## How to run it locally

1. Create a virtual environment and install packages:
   ```
   python3 -m venv venv
   source venv/bin/activate        (on Windows: venv\Scripts\activate)
   pip install -r requirements.txt
   ```

2. Run database migrations (this creates the SQLite database file):
   ```
   python manage.py migrate
   ```

3. (Optional but recommended) Create an admin account so you can
   view data at /admin/:
   ```
   python manage.py createsuperuser
   ```

4. Start the server:
   ```
   python manage.py runserver
   ```

5. Open http://127.0.0.1:8000/ in your browser.

At this point everything works EXCEPT the actual payment — because
you have not connected your own Stripe account yet (see below).

## How to connect real Stripe test payments

1. Create a free account at https://dashboard.stripe.com and switch
   to **Test mode** (toggle in the top right).

2. Go to **Developers → API keys** and copy your "Publishable key"
   and "Secret key".

3. Go to **Product catalog → Add product**, name it "Pro Plan",
   set a recurring price (e.g. $9/month), save it, and copy the
   **Price ID** (looks like `price_1AbCdEfGh...`).

4. Set these as environment variables before running the server
   (or put them in a `.env` file and load it — many tutorials show
   how to do this with `python-decouple` or `django-environ`):
   ```
   export STRIPE_PUBLIC_KEY=pk_test_xxxxx
   export STRIPE_SECRET_KEY=sk_test_xxxxx
   export STRIPE_PRO_PRICE_ID=price_xxxxx
   ```

5. For webhooks to work locally, install the Stripe CLI and run:
   ```
   stripe listen --forward-to localhost:8000/billing/webhook/
   ```
   This command will print a `whsec_...` value — set that as:
   ```
   export STRIPE_WEBHOOK_SECRET=whsec_xxxxx
   ```

6. Now when you click "Upgrade to Pro" on the Pricing page, you'll
   be sent to a real (test-mode) Stripe Checkout page. Use Stripe's
   test card number `4242 4242 4242 4242`, any future expiry date,
   and any CVC to "pay". Your account will be upgraded to Pro
   automatically once the webhook is received.

## Things you could add next (good talking points in an interview)

- Email notifications when an invoice is created or marked paid
  (using Celery so emails are sent in the background, not blocking
  the request)
- A "Cancel Subscription" button that calls `stripe.Subscription.delete()`
- PDF generation for invoices (so clients can download a real PDF)
- A proper `.env` file + `django-environ` instead of raw env vars
- Deploying it for real (Render, Railway, or Fly.io are all free-tier
  friendly and Django-friendly)
- Writing tests for the invoice limit logic and the webhook handler
