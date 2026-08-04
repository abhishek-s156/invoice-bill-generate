"""
views.py
--------
This file controls what happens on each page (each URL).
Every function here is called a "view". A view takes a request,
does some work, and returns a response (usually an HTML page).

We kept every view as a simple function (no classes) so it is
easy to read top-to-bottom, beginner-style.
"""

import json
import stripe

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt

from .models import UserProfile, Client, Invoice

# Tell the stripe library which secret key to use for all calls
stripe.api_key = settings.STRIPE_SECRET_KEY


# -----------------------------------------------------------------
# PUBLIC PAGES (anyone can see these, even if not logged in)
# -----------------------------------------------------------------

def home_page(request):
    """The landing page that explains what EasyBill does."""
    return render(request, 'invoices/home.html')


def signup_page(request):
    """
    Lets a new user create an account.
    We use Django's built-in UserCreationForm so we do not have
    to write password validation/hashing ourselves.
    """
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            new_user = form.save()

            # Every new user automatically gets a Free plan profile
            UserProfile.objects.create(user=new_user, plan='free')

            login(request, new_user)
            messages.success(request, "Welcome to EasyBill! You are on the Free plan.")
            return redirect('dashboard')
    else:
        form = UserCreationForm()

    return render(request, 'invoices/signup.html', {'form': form})


# -----------------------------------------------------------------
# DASHBOARD (only for logged-in users)
# -----------------------------------------------------------------

@login_required
def dashboard_page(request):
    """
    The main page a user sees after logging in.
    Shows their plan, a quick summary, and their invoice list.
    """
    profile = get_or_create_profile(request.user)
    invoice_list = Invoice.objects.filter(owner=request.user).order_by('-created_at')

    context = {
        'profile': profile,
        'invoice_list': invoice_list,
        'invoice_count': invoice_list.count(),
        'limit_reached': profile.invoice_limit_reached(),
    }
    return render(request, 'invoices/dashboard.html', context)


def get_or_create_profile(user):
    """
    Small helper used everywhere. Some users (like ones created
    via the admin panel) might not have a UserProfile yet, so we
    make one automatically instead of crashing.
    """
    profile, created = UserProfile.objects.get_or_create(user=user, defaults={'plan': 'free'})
    return profile


# -----------------------------------------------------------------
# CLIENT PAGES (the "customers" our user bills)
# -----------------------------------------------------------------

@login_required
def client_list_page(request):
    clients = Client.objects.filter(owner=request.user).order_by('name')
    return render(request, 'invoices/client_list.html', {'clients': clients})


@login_required
def add_client_page(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')

        Client.objects.create(owner=request.user, name=name, email=email)
        messages.success(request, f"Client '{name}' added.")
        return redirect('client_list')

    return render(request, 'invoices/add_client.html')


# -----------------------------------------------------------------
# INVOICE PAGES
# -----------------------------------------------------------------

@login_required
def add_invoice_page(request):
    """
    Create a new invoice. This is also where we ENFORCE the
    Free plan limit — the core "SaaS billing" logic of the project.
    """
    profile = get_or_create_profile(request.user)

    # STOP here if a free user already used all 3 free invoices
    if profile.invoice_limit_reached():
        messages.error(request, "You reached the Free plan limit (3 invoices). Please upgrade to Pro.")
        return redirect('pricing')

    clients = Client.objects.filter(owner=request.user)

    if request.method == 'POST':
        client_id = request.POST.get('client')
        title = request.POST.get('title')
        amount = request.POST.get('amount')
        due_date = request.POST.get('due_date')

        client = get_object_or_404(Client, id=client_id, owner=request.user)

        Invoice.objects.create(
            owner=request.user,
            client=client,
            title=title,
            amount=amount,
            due_date=due_date,
        )
        messages.success(request, "Invoice created.")
        return redirect('dashboard')

    return render(request, 'invoices/add_invoice.html', {'clients': clients})


@login_required
def invoice_detail_page(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id, owner=request.user)
    return render(request, 'invoices/invoice_detail.html', {'invoice': invoice})


@login_required
def mark_invoice_paid(request, invoice_id):
    """A tiny view that just flips an invoice's status to 'paid'."""
    invoice = get_object_or_404(Invoice, id=invoice_id, owner=request.user)
    invoice.status = Invoice.STATUS_PAID
    invoice.save()
    messages.success(request, "Invoice marked as paid.")
    return redirect('invoice_detail', invoice_id=invoice.id)


# -----------------------------------------------------------------
# BILLING / STRIPE PAGES  <-- this is the "SaaS plumbing" part
# -----------------------------------------------------------------

def pricing_page(request):
    """Shows the Free vs Pro plan comparison and an 'Upgrade' button."""
    return render(request, 'invoices/pricing.html')


@login_required
def create_checkout_session(request):
    """
    Called when the user clicks "Upgrade to Pro".
    We ask Stripe to create a Checkout Session (Stripe's hosted
    payment page) and then redirect the user there.
    """
    profile = get_or_create_profile(request.user)

    checkout_session = stripe.checkout.Session.create(
        customer_email=request.user.email or None,
        payment_method_types=['card'],
        mode='subscription',
        line_items=[{
            'price': settings.STRIPE_PRO_PRICE_ID,
            'quantity': 1,
        }],
        success_url=settings.DOMAIN_URL + '/billing/success/',
        cancel_url=settings.DOMAIN_URL + '/billing/cancelled/',
        # We tag the session with our own user id so the webhook
        # later knows WHICH user just paid.
        client_reference_id=str(request.user.id),
    )

    return redirect(checkout_session.url, code=303)


@login_required
def checkout_success_page(request):
    return render(request, 'invoices/checkout_success.html')


@login_required
def checkout_cancelled_page(request):
    return render(request, 'invoices/checkout_cancelled.html')


@csrf_exempt
def stripe_webhook(request):
    """
    Stripe calls THIS view automatically whenever something happens
    on their side (payment succeeded, subscription cancelled, etc).
    This is how our database stays in sync with Stripe.

    NOTE: This URL must be public (no login_required) because
    Stripe's servers — not a logged-in browser — call it.
    """
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        # The request was not really from Stripe (or was tampered with)
        return HttpResponse(status=400)

    # Event: a Checkout Session finished successfully -> upgrade the user
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        user_id = session.get('client_reference_id')

        if user_id:
            try:
                profile = UserProfile.objects.get(user_id=user_id)
                profile.plan = 'pro'
                profile.subscription_is_active = True
                profile.stripe_customer_id = session.get('customer')
                profile.stripe_subscription_id = session.get('subscription')
                profile.save()
            except UserProfile.DoesNotExist:
                pass

    # Event: a subscription was cancelled -> downgrade the user to Free
    if event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        try:
            profile = UserProfile.objects.get(stripe_subscription_id=subscription['id'])
            profile.plan = 'free'
            profile.subscription_is_active = False
            profile.save()
        except UserProfile.DoesNotExist:
            pass

    # Always tell Stripe "got it, thanks" so they stop retrying
    return JsonResponse({'status': 'received'})
