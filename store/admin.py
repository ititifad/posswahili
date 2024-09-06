from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
# Register your models here.
from .models import *

class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 1


@admin.register(Sale)
class PaymentAdmin(ImportExportModelAdmin, admin.ModelAdmin):
    list_display = ['customer','payment_type','total_amount','discount','final_amount', 'created_at']
    inlines = (SaleItemInline,)
    list_filter = ['payment_type','created_at']

admin.site.register(Customer)
admin.site.register(Product, ImportExportModelAdmin)
admin.site.register(Store)
admin.site.register(Debt)
admin.site.register(Creditor)
admin.site.register(Expense)
admin.site.register(ExpenseCategory)
