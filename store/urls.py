# urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('stores/', views.store_list, name='store_list'),
    path('stores/edit/<int:store_id>/', views.edit_store, name='edit_store'),
    path('stores/delete/<int:store_id>/', views.delete_store, name='delete_store'),
    path('store/<int:store_id>/assign_seller/', views.assign_seller, name='assign_seller'),
    path('store/<int:store_id>/details/', views.store_details, name='store_details'),
    path('products/', views.product_list, name='product_list'),
    path('products/add/', views.add_product, name='add_product'),
    # New URLs for products
    path('products/<int:product_id>/edit/', views.edit_product, name='edit_product'),
    path('products/<int:product_id>/delete/', views.delete_product, name='delete_product'),
    
    path('sales/', views.sale_list, name='sale_list'),
    path('sales/add/', views.add_sale, name='add_sale'),
    path('sales/<int:sale_id>/items/', views.add_sale_items, name='add_sale_items'),
    # Detailed view URLs
    path('sales/<int:sale_id>/', views.view_sale, name='view_sale'),
    path('refund/<int:sale_item_id>/', views.refund_product, name='refund_product'),

    path('debts/', views.debt_list, name='debt_list'),
    path('debts/<int:debt_id>/pay/', views.add_debt_payment, name='add_debt_payment'),
    path('expenses/', views.expense_list, name='expense_list'),
    path('expenses/add/', views.add_expense, name='add_expense'),
    path('expenses/<int:expense_id>/edit/', views.edit_expense, name='edit_expense'),
    path('expenses/<int:expense_id>/delete/', views.delete_expense, name='delete_expense'),
    path('customers/', views.customer_list, name='customer_list'),
    path('customers/add/', views.add_customer, name='add_customer'),
    path('customers/<int:customer_id>/edit/', views.edit_customer, name='edit_customer'),
    path('customers/<int:customer_id>/delete/', views.delete_customer, name='delete_customer'),
    path('creditors/', views.creditor_list, name='creditor_list'),
    path('creditors/add/', views.add_creditor, name='add_creditor'),
    path('credits/', views.credit_list, name='credit_list'),
    path('credits/add/', views.add_credit, name='add_credit'),
    path('creditors/<int:creditor_id>/edit/', views.edit_creditor, name='edit_creditor'),
    path('creditors/<int:creditor_id>/delete/', views.delete_creditor, name='delete_creditor'),
    path('debts/<int:debt_id>/', views.view_debt, name='view_debt'),
    path('credits/<int:credit_id>/', views.view_credit, name='view_credit'),
    path('credits/<int:credit_id>/pay/', views.add_credit_payment, name='add_credit_payment'),
    path('reports/inventory/', views.inventory_report, name='inventory_report'),
    path('reports/sales/', views.sales_report, name='sales_report'),
    path('sales/<int:sale_id>/pdf/', views.generate_pdf_invoice, name='generate_pdf_invoice'),
    
]