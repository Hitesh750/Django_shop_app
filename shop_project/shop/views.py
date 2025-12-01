import os
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest
from .models import Product, Order, OrderItem
import stripe
import json

stripe.api_key = 'sk_test_51SZWjAFt9K8SHBWA2jERz9hk2Ilmz115yttJvRJyG8ejv4VW0ch49UI9KvPI7UB8s8SCVnVtM4hs0KuH60UojO5000GapFGVD3'
def index(request):
    products = Product.objects.all()
    orders = Order.objects.filter(paid=True).order_by('-created_at')
    return render(request, "index.html", {"products": products, "orders": orders, "STRIPE_PUBLISHABLE_KEY": settings.STRIPE_PUBLISHABLE_KEY})

@csrf_exempt
def create_checkout_session(request):
    """
    Create an Order (unpaid) and a Stripe Checkout Session, return URL to redirect.
    Protect from double-submits by creating a server-side Order record first and passing its id as client_reference_id.
    """
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")

    data = json.loads(request.body)
    items = data.get("items", [])  # list of {product_id, quantity}

    # Build line_items, create Order in DB (unpaid)
    line_items = []
    total_cents = 0
    order = Order.objects.create(paid=False, total_cents=0)

    for it in items:
        try:
            p = Product.objects.get(pk=it["product_id"])
        except Product.DoesNotExist:
            order.delete()
            return HttpResponseBadRequest("Invalid product")
        qty = max(0, int(it.get("quantity", 0)))
        if qty <= 0:
            continue
        line_items.append({
            "price_data": {
                "currency": "usd",
                "product_data": {"name": p.name, "description": p.description},
                "unit_amount": p.price_cents,
            },
            "quantity": qty,
        })
        line_total = p.price_cents * qty
        total_cents += line_total
        OrderItem.objects.create(order=order, product=p, quantity=qty, line_total_cents=line_total)

    if not line_items:
        order.delete()
        return HttpResponseBadRequest("No items")

    order.total_cents = total_cents
    order.save()

    domain = request.build_absolute_uri('/')[:-1]

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=line_items,
            mode="payment",
            success_url=domain + "/?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=domain + "/",
            client_reference_id=str(order.id),        # link session to order
            metadata={"order_id": str(order.id)},
        )
    except Exception as e:
        order.delete()
        return JsonResponse({"error": str(e)}, status=400)

    # Save session ID on order to make idempotent processing later
    order.stripe_session_id = session.id
    order.save()

    return JsonResponse({"checkout_url": session.url})

@csrf_exempt
def stripe_webhook(request):
    # verify signature if webhook secret present
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    webhook_secret = getattr(settings, "STRIPE_WEBHOOK_SECRET", None)
    event = None
    try:
        if webhook_secret:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        else:
            event = json.loads(payload)
    except Exception as e:
        return HttpResponse(status=400)

    # Handle the checkout.session.completed event
    if event['type'] == 'checkout.session.completed' or (isinstance(event, dict) and event.get("type") == "checkout.session.completed"):
        session = event['data']['object']
        session_id = session.get("id")
        client_ref = session.get("client_reference_id") or session.get("metadata", {}).get("order_id")
        if not client_ref:
            return HttpResponse(status=400)

        try:
            order = Order.objects.get(pk=int(client_ref))
        except Order.DoesNotExist:
            return HttpResponse(status=404)

        # idempotency: if already marked paid, do nothing
        if order.paid:
            return HttpResponse(status=200)

        # Double-check payment status with Stripe
        try:
            s = stripe.checkout.Session.retrieve(session_id, expand=["payment_intent"])
            if s.payment_status == "paid" or s.payment_intent.status == "succeeded":
                order.paid = True
                order.save()
        except Exception:
            # in case of error, keep order unpaid (manual review)
            pass

    return HttpResponse(status=200)
