from django.contrib import admin
from .models import Ebook, Order, Note, SurvivalPack

@admin.register(Ebook)
class EbookAdmin(admin.ModelAdmin):
    list_display = ('title', 'price', 'is_published', 'created_at')
    list_filter = ('is_published',)
    prepopulated_fields = {'slug': ('title',)}

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'ebook', 'amount', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    readonly_fields = ('razorpay_order_id', 'razorpay_payment_id', 'razorpay_signature', 'download_token', 'paid_at')

@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'branch', 'semester', 'created_at')
    list_filter = ('branch', 'semester')

@admin.register(SurvivalPack)
class SurvivalPackAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'price', 'is_published')
    