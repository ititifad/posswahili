from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
# Register your models here.
from .models import *

admin.site.register(Customer)
admin.site.register(Product, ImportExportModelAdmin)
admin.site.register(Sale)
admin.site.register(Debt)
admin.site.register(Creditor)
admin.site.register(Expense)
admin.site.register(ExpenseCategory)