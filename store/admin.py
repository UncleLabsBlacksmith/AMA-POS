from django.contrib import admin

from .models import Category, CreditPayment, Customer, Product, Sale, SaleItem

admin.site.site_header = 'ระบบหลังร้าน'
admin.site.site_title = 'ระบบหลังร้าน'
admin.site.index_title = 'จัดการข้อมูลร้าน'


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['emoji', 'name', 'sort_order']
    list_editable = ['sort_order']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['emoji', 'name', 'price', 'stock', 'category', 'is_favorite', 'is_active']
    list_editable = ['price', 'stock', 'is_favorite', 'is_active']
    list_filter = ['category', 'is_favorite', 'is_active']
    search_fields = ['name', 'barcode']


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ['id', 'created_at', 'total', 'payment_method', 'customer', 'is_void']
    list_filter = ['payment_method', 'is_void', 'created_at']
    inlines = [SaleItemInline]


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone', 'balance', 'is_active']
    search_fields = ['name', 'phone']


@admin.register(CreditPayment)
class CreditPaymentAdmin(admin.ModelAdmin):
    list_display = ['customer', 'amount', 'created_at']
    list_filter = ['created_at']
