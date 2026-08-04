"""
models.py
---------
This file describes the "things" (database tables) our app needs.

We have 3 simple things:
1. UserProfile  -> extra info about a user (their plan, stripe customer id)
2. Client       -> a customer that OUR user sends invoices to
3. Invoice      -> a bill/invoice that OUR user creates for their client
"""

from django.db import models
from django.contrib.auth.models import User


# Two simple plan choices. Keeping it as just 2 plans (Free / Pro)
# makes the whole project much easier to understand.
PLAN_FREE = 'free'
PLAN_PRO = 'pro'

PLAN_CHOICES = [
    (PLAN_FREE, 'Free Plan'),
    (PLAN_PRO, 'Pro Plan'),
]

# How many invoices a Free user is allowed to create.
# Pro users get unlimited invoices.
FREE_PLAN_INVOICE_LIMIT = 3


class UserProfile(models.Model):
    """
    Extra information about a user that Django's built-in User model
    does not have, like which plan they are on and their Stripe IDs.

    Every normal Django User will get ONE UserProfile (one-to-one).
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    plan = models.CharField(
        max_length=10,
        choices=PLAN_CHOICES,
        default=PLAN_FREE,
    )

    # Stripe gives every paying customer a unique ID, like "cus_12345".
    # We save it here so we can look them up later (e.g. in webhooks).
    stripe_customer_id = models.CharField(max_length=100, blank=True, null=True)

    # Stripe also gives every active subscription an ID, like "sub_12345".
    stripe_subscription_id = models.CharField(max_length=100, blank=True, null=True)

    # Is their subscription currently active? Stripe webhooks update this.
    subscription_is_active = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} - {self.plan}"

    def is_pro(self):
        """Small helper so templates/views can simply ask profile.is_pro()"""
        return self.plan == PLAN_PRO and self.subscription_is_active

    def invoice_limit_reached(self):
        """
        Returns True if a Free user has already used up their
        3 free invoices. Pro users never hit this limit.
        """
        if self.is_pro():
            return False
        invoice_count = self.user.invoice_set.count()
        return invoice_count >= FREE_PLAN_INVOICE_LIMIT


class Client(models.Model):
    """
    A client is someone that OUR user (the business owner using EasyBill)
    sends invoices to. For example, "Acme Corp" or "John Doe".
    """
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Invoice(models.Model):
    """
    A single invoice/bill created by our user for one of their clients.
    """
    STATUS_DRAFT = 'draft'
    STATUS_SENT = 'sent'
    STATUS_PAID = 'paid'

    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_SENT, 'Sent'),
        (STATUS_PAID, 'Paid'),
    ]

    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    client = models.ForeignKey(Client, on_delete=models.CASCADE)

    title = models.CharField(max_length=200, help_text="e.g. 'Website redesign work'")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_DRAFT)

    created_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateField()

    def __str__(self):
        return f"Invoice #{self.id} - {self.title} (${self.amount})"
