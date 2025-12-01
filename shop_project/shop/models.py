from django.db import models
from django.utils import timezone

class Product(models.Model):
    """Fixed catalog products (we'll seed 3 products)."""
    name = models.CharField(max_length=200)
    price_cents = models.PositiveIntegerField() 
    description = models.TextField(blank=True)
    stripe_price_id = models.CharField(max_length=200, blank=True)  

    def price_display(self):
        return f"{self.price_cents/100:.2f}"

    def __str__(self):
        return f"{self.name} ({self.price_display()})"

class Order(models.Model):
    created_at = models.DateTimeField(default=timezone.now)
    paid = models.BooleanField(default=False)
    stripe_session_id = models.CharField(max_length=255, blank=True, null=True, unique=True)
    total_cents = models.PositiveIntegerField(default=0)

    def total_display(self):
        return f"{self.total_cents/100:.2f}"

    def __str__(self):
        return f"Order #{self.id} paid={self.paid} total={self.total_display()}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    line_total_cents = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.product.name} x{self.quantity}"
