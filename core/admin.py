from django.contrib import admin
from .models import CustomUser, Category, Job, PromotedWorker, Transaction, Review, Product, OfflineService, OfflineBooking, Cart, CartItem, BranchAdminInvite

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'user_type', 'wallet_balance', 'is_verified', 'is_staff')
    list_filter = ('user_type', 'is_verified', 'is_staff', 'is_superuser')
    search_fields = ('username', 'email')

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('title', 'provider', 'worker', 'budget', 'status', 'created_at')
    list_filter = ('status', 'created_at', 'category')
    search_fields = ('title', 'description', 'provider__username', 'worker__username')

@admin.register(PromotedWorker)
class PromotedWorkerAdmin(admin.ModelAdmin):
    list_display = ('worker', 'promotion_bid', 'clicks', 'promoted_at')
    search_fields = ('worker__username',)

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction_type', 'user', 'amount', 'timestamp')
    list_filter = ('transaction_type', 'timestamp')
    search_fields = ('user__username', 'job__title')

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('reviewer', 'reviewee', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'seller', 'price', 'stock', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'seller__username')

@admin.register(OfflineService)
class OfflineServiceAdmin(admin.ModelAdmin):
    list_display = ('title', 'provider', 'base_price', 'location', 'created_at')
    list_filter = ('location', 'created_at')
    search_fields = ('title', 'provider__username')

@admin.register(OfflineBooking)
class OfflineBookingAdmin(admin.ModelAdmin):
    list_display = ('customer', 'service', 'booking_date', 'status', 'created_at')
    list_filter = ('status', 'booking_date', 'created_at')
    search_fields = ('customer__username', 'service__title')

@admin.register(BranchAdminInvite)
class BranchAdminInviteAdmin(admin.ModelAdmin):
    list_display = ('token', 'created_by', 'used_by', 'is_used', 'expires_at')
    list_filter = ('is_used', 'expires_at')
    search_fields = ('token',)

admin.site.register(Cart)
admin.site.register(CartItem)
