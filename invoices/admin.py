"""
admin.py
--------
Register our models with Django's built-in admin panel
(visible at /admin/) so we can view/edit data without
writing any extra code.
"""

from django.contrib import admin
from .models import UserProfile, Client, Invoice

admin.site.register(UserProfile)
admin.site.register(Client)
admin.site.register(Invoice)
