from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("create-checkout-session/", views.create_checkout_session, name="create-checkout-session"),
    path("stripe/webhook/", views.stripe_webhook, name="stripe_webhook"),
]
