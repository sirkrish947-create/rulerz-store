
from django.contrib import admin
from .models import Ebook, Order, Note, SurvivalPack, Review


@admin.register(Ebook)
class EbookAdmin(admin.ModelAdmin):
    list_display = ('title', 'price', 'is_published', 'created_at')
    list_filter = ('is_published',)
    search_fields = ('title', 'author')
    prepopulated_fields = {'slug': ('title',)}


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'product_title',
        'amount',
        'status',
        'created_at',
        'paid_at',
    )

    list_filter = ('status', 'created_at')
    search_fields = (
        'user__username',
        'razorpay_order_id',
        'razorpay_payment_id',
    )

    readonly_fields = (
        'razorpay_order_id',
        'razorpay_payment_id',
        'razorpay_signature',
        'download_token',
        'paid_at',
        'created_at',
    )


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'subject',
        'branch',
        'semester',
        'created_at',
    )
    list_filter = ('branch', 'semester')
    search_fields = ('title', 'subject')


@admin.register(SurvivalPack)
class SurvivalPackAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'subject',
        'price',
        'is_published',
    )
    list_filter = ('is_published',)
    search_fields = ('title', 'subject')


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('user', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('user__username', 'feedback')
