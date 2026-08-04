"""
urls.py (for the invoices app)
-------------------------------
This file maps a URL path (like "/dashboard/") to a view function
(like dashboard_page) that handles it.

Each url() line has a "name" so our templates can use
{% url 'name' %} instead of hardcoding paths everywhere.
"""

from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Public pages
    path('', views.home_page, name='home'),
    path('signup/', views.signup_page, name='signup'),
    path('pricing/', views.pricing_page, name='pricing'),

    # Login / logout (Django already provides the logic, we just
    # tell it which HTML template to use)
    path('login/', auth_views.LoginView.as_view(template_name='invoices/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # Dashboard
    path('dashboard/', views.dashboard_page, name='dashboard'),

    # Clients
    path('clients/', views.client_list_page, name='client_list'),
    path('clients/add/', views.add_client_page, name='add_client'),

    # Invoices
    path('invoices/add/', views.add_invoice_page, name='add_invoice'),
    path('invoices/<int:invoice_id>/', views.invoice_detail_page, name='invoice_detail'),
    path('invoices/<int:invoice_id>/mark-paid/', views.mark_invoice_paid, name='mark_invoice_paid'),

    # Billing / Stripe
    path('billing/upgrade/', views.create_checkout_session, name='create_checkout_session'),
    path('billing/success/', views.checkout_success_page, name='checkout_success'),
    path('billing/cancelled/', views.checkout_cancelled_page, name='checkout_cancelled'),
    path('billing/webhook/', views.stripe_webhook, name='stripe_webhook'),
]
