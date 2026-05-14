from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid
from django.utils import timezone
from datetime import timedelta

class CustomUser(AbstractUser):
    USER_TYPE_CHOICES = (
        ('ADMIN', 'Admin'),
        ('PROVIDER', 'Job Provider'),
        ('WORKER', 'Digital Worker'),
        ('CUSTOMER', 'Customer'),
        ('SELLER', 'Product Seller'),
        ('OFFLINE_PROVIDER', 'Offline Service Provider'),
    )
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default='CUSTOMER')
    wallet_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    is_verified = models.BooleanField(default=False)
    skills = models.TextField(blank=True, help_text="Comma-separated skills")
    bio = models.TextField(blank=True, help_text="Short personal/professional bio")
    phone = models.CharField(max_length=20, blank=True)
    location = models.CharField(max_length=100, blank=True)
    profile_image = models.ImageField(upload_to='profile_images/', blank=True, null=True)
    
    @property
    def average_rating(self):
        reviews = self.reviews_received.all()
        if reviews.exists():
            return sum(r.rating for r in reviews) / float(reviews.count())
        return 0.0

    def __str__(self):
        return f"{self.username} ({self.get_user_type_display()})"


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Tailwind icon class or SVG string")
    description = models.TextField(blank=True)
    
    class Meta:
        verbose_name_plural = "Categories"
        
    def __str__(self):
        return self.name


class Job(models.Model):
    STATUS_CHOICES = (
        ('OPEN', 'Open'),
        ('IN_PROGRESS', 'In Progress'),
        ('SUBMITTED', 'Submitted'),
        ('COMPLETED', 'Completed'),
    )
    title = models.CharField(max_length=200)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='jobs')
    description = models.TextField()
    budget = models.DecimalField(max_digits=10, decimal_places=2)
    featured_image = models.ImageField(upload_to='job_images/', null=True, blank=True)
    provider = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='jobs_posted')
    worker = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='jobs_assigned')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN')
    file_submission = models.FileField(upload_to='submissions/', null=True, blank=True)
    is_deposited = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.title} - {self.get_status_display()}"


class PromotedWorker(models.Model):
    worker = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='promotion')
    promotion_bid = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    clicks = models.PositiveIntegerField(default=0)
    promoted_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Promoted: {self.worker.username} (Bid: ${self.promotion_bid})"


class Transaction(models.Model):
    TX_TYPE_CHOICES = (
        ('DEPOSIT', 'Deposit to Escrow'),
        ('RELEASE', 'Release to Worker'),
        ('REFUND', 'Refund to Provider'),
        ('WITHDRAW', 'Withdrawal'),
        ('PROMOTION', 'Self Promotion Bid'),
        ('PURCHASE', 'Product Purchase'),
    )
    job = models.ForeignKey(Job, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=20, choices=TX_TYPE_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.get_transaction_type_display()} - ${self.amount} - {self.user.username}"


class Review(models.Model):
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='reviews')
    reviewer = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='reviews_given')
    reviewee = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='reviews_received')
    rating = models.IntegerField(choices=[(i, str(i)) for i in range(1, 6)])
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.reviewer.username} -> {self.reviewee.username}: {self.rating} stars"

# --- E-Commerce & Offline Services ---

class Product(models.Model):
    seller = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='product_images/', blank=True, null=True)
    stock = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

class OfflineService(models.Model):
    provider = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='offline_services')
    title = models.CharField(max_length=200)
    description = models.TextField()
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    location = models.CharField(max_length=255, help_text="City, Region, or specific address")
    opening_time = models.TimeField(default='09:00:00', help_text="e.g. 09:00:00")
    closing_time = models.TimeField(default='17:00:00', help_text="e.g. 17:00:00")
    image = models.ImageField(upload_to='offline_service_images/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.title

class OfflineBooking(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    )
    customer = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='bookings_made')
    service = models.ForeignKey(OfflineService, on_delete=models.CASCADE, related_name='bookings')
    booking_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    customer_phone = models.CharField(max_length=20, help_text="Contact number for the provider")
    notes = models.TextField(blank=True, help_text="Special instructions from customer")
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.customer.username} - {self.service.title} on {self.booking_date.date()}"

class Cart(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def get_total_price(self):
        return sum(item.get_cost() for item in self.items.all())
        
    def __str__(self):
        return f"Cart for {self.user.username}"

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    
    def get_cost(self):
        return self.product.price * self.quantity
        
    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

class Order(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('SHIPPED', 'Shipped'),
        ('DELIVERED', 'Delivered'),
        ('CANCELLED', 'Cancelled'),
    )
    customer = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='orders')
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Order #{self.id} - {self.customer.username}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2) # Price at purchase
    
    def get_cost(self):
        return self.price * self.quantity

class BranchAdminInvite(models.Model):
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='invites_created')
    used_by = models.OneToOneField(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='invite_used')
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)

    def is_valid(self):
        return not self.is_used and self.expires_at > timezone.now()

    def __str__(self):
        return f"Passkey: {self.token} (Used: {self.is_used})"
