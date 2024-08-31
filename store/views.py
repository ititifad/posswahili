# views.py
import os
from django.conf import settings

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.http import HttpResponse,JsonResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from django.db.models import Sum, F
from django.utils.timezone import now, timedelta
from .models import *
from .forms import *
from django.utils import timezone


@login_required
def dashboard(request):
    # Today's date
    today = timezone.now()
    
    # Today's sales
    today_sales_total = Sale.objects.filter(date=today).aggregate(total_sales=Sum('final_amount'))['total_sales'] or 0

    # All-time total sales
    all_time_sales_total = Sale.objects.aggregate(total_sales=Sum('final_amount'))['total_sales'] or 0
    
    # Total purchase price of sold items today
    today_purchase_total = (
        SaleItem.objects.filter(sale__date=today)
        .aggregate(total_purchase=Sum(F('product__purchase_price') * F('quantity')))['total_purchase'] or 0
    )

    # All-time total purchase price
    all_time_purchase_total = (
        SaleItem.objects.aggregate(total_purchase=Sum(F('product__purchase_price') * F('quantity')))['total_purchase'] or 0
    )

    # Total profit today (sales total - purchase total)
    today_profit = today_sales_total - today_purchase_total

    # All-time total profit
    all_time_profit = all_time_sales_total - all_time_purchase_total

    # Today's expenses
    today_expenses_total = Expense.objects.filter(date__date=today).aggregate(total_expenses=Sum('amount'))['total_expenses'] or 0

    # All-time total expenses
    all_time_expenses_total = Expense.objects.aggregate(total_expenses=Sum('amount'))['total_expenses'] or 0

    context = {
        'today_sales_total': today_sales_total,
        'all_time_sales_total': all_time_sales_total,
        'today_purchase_total': today_purchase_total,
        'all_time_purchase_total': all_time_purchase_total,
        'today_profit': today_profit,
        'all_time_profit': all_time_profit,
        'today_expenses_total': today_expenses_total,
        'all_time_expenses_total': all_time_expenses_total,
        'today':today
    }

    return render(request, 'dashboard.html', context)

@login_required
def product_list(request):
    # Initial query
    products = Product.objects.all().order_by('-id')

    # Filtering logic
    category_filter = request.GET.get('category')
    zero_inventory_filter = request.GET.get('zero_inventory')
    low_stock_filter = request.GET.get('low_stock')

    if category_filter:
        products = products.filter(category__id=category_filter)

    if zero_inventory_filter == 'true':
        products = products.filter(quantity=0)

    if low_stock_filter == 'true':
        low_stock_threshold = 5  # Define a threshold for low stock, e.g., less than 5
        products = products.filter(quantity__lt=low_stock_threshold)

    # Aggregating totals based on the filtered products
    total_products = products.count()
    total_purchase_price = products.aggregate(total_purchase_price=Sum(F('purchase_price') * F('quantity')))['total_purchase_price'] or 0
    total_selling_price = products.aggregate(total_selling_price=Sum(F('selling_price') * F('quantity')))['total_selling_price'] or 0
    
    # All-time total profit
    profit = total_selling_price - total_purchase_price

    # Get distinct categories for filtering
    categories = Category.objects.all()

    context = {
        'products': products,
        'total_products': total_products,
        'total_purchase_price': total_purchase_price,
        'total_selling_price': total_selling_price,
        'profit': profit,
        'categories': categories,
        'selected_category': category_filter,
        'zero_inventory_filter': zero_inventory_filter,
        'low_stock_filter': low_stock_filter,
    }
    
    return render(request, 'product_list.html', context)
@login_required

def add_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            
            # Check if a new category was provided
            new_category = form.cleaned_data.get('new_category')
            if new_category:
                category, created = Category.objects.get_or_create(name=new_category)
                product.category = category
            elif not form.cleaned_data.get('category'):
                # If no category was selected and no new category was provided, return an error
                form.add_error('category', "Tafadhali chagua aina ya bidhaa au ongeza aina mpya.")
                return render(request, 'add_product.html', {'form': form})

            product.save()
            messages.success(request, 'Bidhaa imeongezwa kikamilifu!')
            return redirect('product_list')
    else:
        form = ProductForm()
    return render(request, 'add_product.html', {'form': form})

@login_required
def sale_list(request):
    # Get query parameters for filters
    product_category = request.GET.get('category')
    payment_type = request.GET.get('payment_type')
    time_filter = request.GET.get('time_filter')

    # Initialize sales queryset
    sales = Sale.objects.all().order_by('-id')

    # Filter by product category
    if product_category:
        sales = sales.filter(items__product__category_id=product_category).distinct()

    # Filter by payment type
    if payment_type:
        sales = sales.filter(payment_type=payment_type)

    # Filter by time
    if time_filter:
        today = timezone.now()
        if time_filter == 'daily':
            sales = sales.filter(date=today)
        elif time_filter == 'weekly':
            start_of_week = today - timedelta(days=today.weekday())
            sales = sales.filter(date__gte=start_of_week)
        elif time_filter == 'monthly':
            sales = sales.filter(date__year=today.year, date__month=today.month)
        elif time_filter == 'yearly':
            sales = sales.filter(date__year=today.year)

    # Calculate totals for filtered sales
    total_amount = sales.aggregate(total=Sum('final_amount'))['total'] or 0
    total_sales_count = sales.count()
    total_products_sold = SaleItem.objects.filter(sale__in=sales).aggregate(total=Sum('quantity'))['total'] or 0

    # Get all categories for the filter dropdown
    categories = Category.objects.all()

    context = {
        'sales': sales,
        'total_amount': total_amount,
        'total_sales_count': total_sales_count,
        'total_products_sold': total_products_sold,
        'categories': categories,  # Pass categories to the context
        'selected_category': product_category,
        'selected_payment_type': payment_type,
        'selected_time_filter': time_filter,
    }

    return render(request, 'sale_list.html', context)
@login_required
@transaction.atomic
def add_sale(request):
    if request.method == 'POST':
        sale_form = SaleForm(request.POST)
        item_formset = SaleItemFormSet(request.POST)
        
        if sale_form.is_valid() and item_formset.is_valid():
            # Create sale object but don't save to DB yet
            sale = sale_form.save(commit=False)
            sale.created_by = request.user

            total_amount = Decimal('0')  # Initialize total_amount as Decimal

            for item_form in item_formset:
                # Ensure the form is not empty
                if item_form.cleaned_data:
                    product = item_form.cleaned_data.get('product')
                    quantity = item_form.cleaned_data.get('quantity')
                    if product and quantity:
                        price = product.selling_price
                        item = SaleItem(
                            sale=sale,
                            product=product,
                            quantity=quantity,
                            unit_price=price,
                            total_price=quantity * price
                        )
                        total_amount += item.total_price

                        # Update product quantity in the database
                        product.quantity -= quantity
                        product.save()
            
            # Set the total_amount and final_amount in sale object
            sale.total_amount = total_amount
            sale.final_amount = total_amount - (sale.discount or Decimal('0'))
            sale.save()  # Save sale to DB
            
            # Now save all SaleItem instances with the saved sale
            for item_form in item_formset:
                if item_form.cleaned_data:
                    product = item_form.cleaned_data.get('product')
                    quantity = item_form.cleaned_data.get('quantity')
                    if product and quantity:
                        price = product.selling_price
                        SaleItem.objects.create(
                            sale=sale,
                            product=product,
                            quantity=quantity,
                            unit_price=price,
                            total_price=quantity * price
                        )
            
            # Create debt if payment type is credit
            if sale.payment_type == 'credit':
                Debt.objects.create(
                    customer=sale.customer,
                    sale=sale,
                    amount=sale.total_amount,
                    remaining_amount=sale.total_amount - sale.discount  # or use final_amount if discounts apply
                )

            messages.success(request, 'Mauzo yamerekodiwa kikamilifu!')
            return redirect('view_sale', sale_id=sale.id)
        else:
            messages.error(request, 'Please correct the errors below.')
            print(sale_form.errors, item_formset.errors)  # Debugging output
    else:
        sale_form = SaleForm()
        item_formset = SaleItemFormSet()
    
    return render(request, 'add_sale.html', {
        'sale_form': sale_form,
        'item_formset': item_formset,
    })


    
@login_required
def add_sale_items(request, sale_id):
    sale = get_object_or_404(Sale, id=sale_id)
    if request.method == 'POST':
        form = SaleItemForm(request.POST)
        if form.is_valid():
            sale_item = form.save(commit=False)
            sale_item.sale = sale
            sale_item.save()
            
            # Update product quantity
            product = sale_item.product
            product.quantity -= sale_item.quantity
            product.save()

            # Create debt if payment type is credit
            if sale.payment_type == 'credit':
                Debt.objects.create(
                    customer=sale.customer,
                    sale=sale,
                    
                    amount=sale_item.price * sale_item.quantity,
                    remaining_amount=sale_item.price * sale_item.quantity
                )

            return redirect('add_sale_items', sale_id=sale.id)
    else:
        form = SaleItemForm()
    
    sale_items = SaleItem.objects.filter(sale=sale)
    return render(request, 'add_sale_items.html', {'form': form, 'sale': sale, 'sale_items': sale_items})

# @login_required
# def debt_list(request):
#     debts = Debt.objects.filter(remaining_amount__gt=0).order_by('-id')
#     return render(request, 'debt_list.html', {'debts': debts})


# @login_required
# def debt_list(request):
#     total_customers_owed = Debt.objects.values('customer').distinct().count()
#     total_amount_owed = Debt.objects.aggregate(total=Sum('amount'))['total'] or 0
#     total_amount_paid = Debt.objects.aggregate(total=Sum('paid_amount'))['total'] or 0
#     total_remaining_amount = Debt.objects.aggregate(total=Sum('remaining_amount'))['total'] or 0

#     debts = Debt.objects.filter(remaining_amount__gt=0).order_by('-sale__date')

#     return render(request, 'debt_list.html', {
#         'debts': debts,
#         'total_customers_owed': total_customers_owed,
#         'total_amount_owed': total_amount_owed,
#         'total_amount_paid': total_amount_paid,
#         'total_remaining_amount': total_remaining_amount,
#     })

@login_required
def debt_list(request):
    # Get query parameters for filters
    customer_id = request.GET.get('customer')
    time_filter = request.GET.get('time_filter')

    # Initialize debt queryset
    debts = Debt.objects.filter(remaining_amount__gt=0).order_by('-sale__date')

    # Filter by customer
    if customer_id:
        debts = debts.filter(customer_id=customer_id)

    # Filter by time
    if time_filter:
        today = now().date()
        if time_filter == 'daily':
            debts = debts.filter(sale__date=today)
        elif time_filter == 'weekly':
            start_of_week = today - timedelta(days=today.weekday())
            debts = debts.filter(sale__date__gte=start_of_week)
        elif time_filter == 'monthly':
            debts = debts.filter(sale__date__year=today.year, sale__date__month=today.month)
        elif time_filter == 'yearly':
            debts = debts.filter(sale__date__year=today.year)

    # Get total debt and remaining amount for the filtered results
    total_customers_owed = debts.values('customer').distinct().count()
    total_debt = debts.aggregate(total=Sum('amount'))['total'] or 0
    total_amount_paid = debts.aggregate(total=Sum('paid_amount'))['total'] or 0
    total_remaining_amount = debts.aggregate(total=Sum('remaining_amount'))['total'] or 0

    # Get all customers for the filter dropdown
    customers = Customer.objects.all()

    context = {
        'debts': debts,
        'total_customers_owed':total_customers_owed,
        'total_debt': total_debt,
        'total_amount_paid':total_amount_paid,
        'total_remaining_amount': total_remaining_amount,
        'customers': customers,
        'selected_customer': customer_id,
        'selected_time_filter': time_filter,
    }

    return render(request, 'debt_list.html', context)


@login_required
def add_debt_payment(request, debt_id):
    debt = get_object_or_404(Debt, id=debt_id)
    if request.method == 'POST':
        form = DebtPaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.debt = debt
            payment.save()

            # Update remaining amount
            debt.remaining_amount -= payment.amount
            debt.save()
            messages.success(request, 'Malipo yamerekodiwa kikamilifu!')
            return redirect('debt_list')
    else:
        form = DebtPaymentForm()
    return render(request, 'add_debt_payment.html', {'form': form, 'debt': debt})

@login_required
def expense_list(request):
    # Get query parameters for filters
    category_id = request.GET.get('category')
    time_filter = request.GET.get('time_filter')

    # Initialize expense queryset
    expenses = Expense.objects.all().order_by('-date')

    # Filter by category
    if category_id:
        expenses = expenses.filter(category_id=category_id)

    # Filter by time
    today = timezone.now()
    if time_filter == 'daily':
        expenses = expenses.filter(date__date=today)
    elif time_filter == 'weekly':
        one_week_ago = today - timedelta(days=7)
        expenses = expenses.filter(date__date__gte=one_week_ago)
    elif time_filter == 'monthly':
        expenses = expenses.filter(date__year=today.year, date__month=today.month)
    elif time_filter == 'yearly':
        expenses = expenses.filter(date__year=today.year)

    # Calculate total amounts for filtered results
    total_expenses = expenses.aggregate(total_amount=Sum('amount'))['total_amount'] or 0

    # Calculate totals for specific time periods regardless of other filters
    daily_expenses = Expense.objects.filter(date__date=today)
    weekly_expenses = Expense.objects.filter(date__date__gte=today - timedelta(days=7))
    monthly_expenses = Expense.objects.filter(date__year=today.year, date__month=today.month)
    yearly_expenses = Expense.objects.filter(date__year=today.year)

    if category_id:
        daily_expenses = daily_expenses.filter(category_id=category_id)
        weekly_expenses = weekly_expenses.filter(category_id=category_id)
        monthly_expenses = monthly_expenses.filter(category_id=category_id)
        yearly_expenses = yearly_expenses.filter(category_id=category_id)

    daily_expenses = daily_expenses.aggregate(total_amount=Sum('amount'))['total_amount'] or 0
    weekly_expenses = weekly_expenses.aggregate(total_amount=Sum('amount'))['total_amount'] or 0
    monthly_expenses = monthly_expenses.aggregate(total_amount=Sum('amount'))['total_amount'] or 0
    yearly_expenses = yearly_expenses.aggregate(total_amount=Sum('amount'))['total_amount'] or 0

    # Get all categories for the filter dropdown
    categories = ExpenseCategory.objects.all()

    context = {
        'expenses': expenses,
        'total_expenses': total_expenses,
        'daily_expenses': daily_expenses,
        'weekly_expenses': weekly_expenses,
        'monthly_expenses': monthly_expenses,
        'yearly_expenses': yearly_expenses,
        'categories': categories,
        'selected_category': category_id,
        'selected_time_filter': time_filter,
    }

    return render(request, 'expense_list.html', context)


@login_required
def add_expense(request):
    if request.method == 'POST':
        form = ExpenseForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Matumizi yamerekodiwa kikamilifu!')
            return redirect('expense_list')
    else:
        form = ExpenseForm()
    return render(request, 'add_expense.html', {'form': form})

@login_required
def customer_list(request):
    # Fetch query parameters from the request
    customer_name = request.GET.get('customer_name', '')
    debt_status = request.GET.get('debt_status', 'all')  # 'all', 'active', or 'paid'

    # Fetch all customers for the dropdown
    all_customers = Customer.objects.all()

    # Filter customers by selected name if provided
    customers = Customer.objects.all()
    if customer_name:
        customers = customers.filter(name=customer_name)

    # Filter customers based on debt status
    if debt_status == 'active':
        customers = customers.filter(debt__remaining_amount__gt=0).distinct()
    elif debt_status == 'paid':
        customers = customers.filter(debt__remaining_amount=0).distinct()

    # Annotate customers with debt information
    customers = customers.annotate(
        total_debt=Sum('debt__amount'),
        total_paid=Sum('debt__paid_amount'),
        total_remaining=Sum('debt__remaining_amount')
    )

    context = {
        'customers': customers,
        'all_customers': all_customers,
        'customer_name': customer_name,
        'debt_status': debt_status,
    }




    return render(request, 'customer_list.html', context)

@login_required
def add_customer(request):
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Mteja mpya amerekodiwa kikamilifu!')
            return redirect('customer_list')
    else:
        form = CustomerForm()
    return render(request, 'add_customer.html', {'form': form})

@login_required
def creditor_list(request):
    creditors = Creditor.objects.all()
    return render(request, 'creditor_list.html', {'creditors': creditors})

@login_required
def add_creditor(request):
    if request.method == 'POST':
        form = CreditorForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Mdai amerekodiwa kikamilifu!')
            return redirect('creditor_list')
    else:
        form = CreditorForm()
    return render(request, 'add_creditor.html', {'form': form})

# @login_required
# def credit_list(request):
#     credits = Credit.objects.filter(remaining_amount__gt=0)
#     return render(request, 'credit_list.html', {'credits': credits})


@login_required
def credit_list(request):
    # Get filter parameters from request
    period = request.GET.get('period', 'all')  # 'daily', 'weekly', 'monthly', 'yearly', or 'all'
    status = request.GET.get('status', 'active')  # 'active', 'inactive', or 'all'
    selected_creditor = request.GET.get('creditor', None)  # ID of the selected creditor or None

    # Define time filtering
    current_time = now()
    if period == 'daily':
        start_date = current_time - timedelta(days=1)
    elif period == 'weekly':
        start_date = current_time - timedelta(weeks=1)
    elif period == 'monthly':
        start_date = current_time - timedelta(days=30)
    elif period == 'yearly':
        start_date = current_time - timedelta(days=365)
    else:
        start_date = None  # No time filter

    # Base queryset
    credits = Credit.objects.all()

    # Apply time filter
    if start_date:
        credits = credits.filter(date__gte=start_date)

    # Apply active/inactive filter
    if status == 'active':
        credits = credits.filter(remaining_amount__gt=0)
    elif status == 'inactive':
        credits = credits.filter(remaining_amount__lte=0)

    # Apply creditor filter
    if selected_creditor:
        credits = credits.filter(creditor_id=selected_creditor)

    # Aggregations for cards
    total_creditors = credits.values('creditor').distinct().count()
    total_amount_borrowed = credits.aggregate(total=Sum('amount'))['total'] or 0
    total_amount_paid = credits.aggregate(total=Sum(F('amount') - F('remaining_amount')))['total'] or 0
    total_remaining_amount = credits.aggregate(total=Sum('remaining_amount'))['total'] or 0

    # Order credits by date
    credits = credits.order_by('-date')

    # Get all creditors for the filter dropdown
    creditors = Creditor.objects.all()

    return render(request, 'credit_list.html', {
        'credits': credits,
        'total_creditors': total_creditors,
        'total_amount_borrowed': total_amount_borrowed,
        'total_amount_paid': total_amount_paid,
        'total_remaining_amount': total_remaining_amount,
        'selected_period': period,
        'selected_status': status,
        'creditors': creditors,  # Pass creditors to template
        'selected_creditor': selected_creditor,
    })

@login_required
def add_credit(request):
    if request.method == 'POST':
        form = CreditForm(request.POST)
        if form.is_valid():
            create_new_creditor = form.cleaned_data.get('create_new_creditor')
            if create_new_creditor:
                # Create new creditor
                creditor_name = form.cleaned_data.get('creditor_name')
                creditor_phone_number = form.cleaned_data.get('creditor_phone_number')
                creditor, created = Creditor.objects.get_or_create(
                    name=creditor_name,
                    phone_number=creditor_phone_number
                )
            else:
                creditor = form.cleaned_data.get('creditor')

            # Create new credit entry
            credit = form.save(commit=False)
            credit.creditor = creditor
            credit.remaining_amount = credit.amount
            credit.save()
            messages.success(request, 'Mkopo umerekodiwa kikamilifu!')
            return redirect('credit_list')
    else:
        form = CreditForm()

    return render(request, 'add_credit.html', {'form': form})

@login_required
def add_credit_payment(request, credit_id):
    credit = get_object_or_404(Credit, id=credit_id)
    if request.method == 'POST':
        form = CreditPaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.credit = credit
            payment.save()

            # Update remaining amount
            credit.remaining_amount -= payment.amount
            credit.save()
            messages.success(request, 'Malipo ya mkopo yamerekodiwa kikamilifu!')
            return redirect('credit_list')
    else:
        form = CreditPaymentForm()
    return render(request, 'add_credit_payment.html', {'form': form, 'credit': credit})

@login_required
def inventory_report(request):
    products = Product.objects.all()
    return render(request, 'inventory_report.html', {'products': products})

@login_required
def sales_report(request):
    sales = Sale.objects.all()
    return render(request, 'sales_report.html', {'sales': sales})

@login_required
def expense_report(request):
    expenses = Expense.objects.all()
    return render(request, 'expense_report.html', {'expenses': expenses})


@login_required
def edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, 'Bidhaa imehaririwa kikamilifu!')
            return redirect('product_list')
    else:
        form = ProductForm(instance=product)
    return render(request, 'edit_product.html', {'form': form, 'product': product})

@login_required
def delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        product.delete()
        messages.success(request, 'Bidhaa imefutwa kikamilifu!')
        return redirect('product_list')
    return render(request, 'delete_product.html', {'product': product})

# Customer views
@login_required
def edit_customer(request, customer_id):
    customer = get_object_or_404(Customer, id=customer_id)
    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            messages.success(request, 'Taarifa za mteja zimehaririwa kikamilifu!')
            return redirect('customer_list')
    else:
        form = CustomerForm(instance=customer)
    return render(request, 'edit_customer.html', {'form': form, 'customer': customer})

@login_required
def delete_customer(request, customer_id):
    customer = get_object_or_404(Customer, id=customer_id)
    if request.method == 'POST':
        customer.delete()
        messages.success(request, 'Mteja amefutwa kikamilifu!')
        return redirect('customer_list')
    return render(request, 'delete_customer.html', {'customer': customer})

# Creditor views
@login_required
def edit_creditor(request, creditor_id):
    creditor = get_object_or_404(Creditor, id=creditor_id)
    if request.method == 'POST':
        form = CreditorForm(request.POST, instance=creditor)
        if form.is_valid():
            form.save()
            return redirect('creditor_list')
    else:
        form = CreditorForm(instance=creditor)
    return render(request, 'edit_creditor.html', {'form': form, 'creditor': creditor})

@login_required
def delete_creditor(request, creditor_id):
    creditor = get_object_or_404(Creditor, id=creditor_id)
    if request.method == 'POST':
        creditor.delete()
        return redirect('creditor_list')
    return render(request, 'delete_creditor.html', {'creditor': creditor})


@login_required
def view_sale(request, sale_id):
    sale = get_object_or_404(Sale, id=sale_id)
    sale_items = sale.items.all()
    return render(request, 'view_sale.html', {'sale': sale, 'sale_items': sale_items})

@login_required
def view_debt(request, debt_id):
    debt = get_object_or_404(Debt, id=debt_id)
    sale_items = debt.sale.items.all()
    payments = debt.debtpayment_set.all()
    return render(request, 'view_debt.html', {'debt': debt, 'payments': payments,'sale_items': sale_items,})

@login_required
def view_credit(request, credit_id):
    credit = get_object_or_404(Credit, id=credit_id)
    
    payments = credit.creditpayment_set.all()
    return render(request, 'view_credit.html', {'credit': credit, 'payments': payments})


@login_required
def edit_expense(request, expense_id):
    expense = get_object_or_404(Expense, id=expense_id)
    if request.method == 'POST':
        form = ExpenseForm(request.POST, instance=expense)
        if form.is_valid():
            form.save()
            messages.success(request, 'Matumizi yamebadilishwa kikamilifu.')
            return redirect('expense_list')
    else:
        form = ExpenseForm(instance=expense)
    return render(request, 'edit_expense.html', {'form': form, 'expense': expense})

@login_required
def delete_expense(request, expense_id):
    expense = get_object_or_404(Expense, id=expense_id)
    if request.method == 'POST':
        expense.delete()
        messages.success(request, 'Matumizi yamefutwa kikamilifu.')
        return redirect('expense_list')
    return render(request, 'delete_expense.html', {'expense': expense})


@login_required
def generate_pdf_invoice(request, sale_id):
    sale = get_object_or_404(Sale, id=sale_id)
    sale_items = sale.items.all()
    
    template_path = 'invoice_pdf.html'  # Separate template for generating PDF
    context = {
        'sale': sale,
        'sale_items': sale_items,
    }
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Invoice_{sale.id}.pdf"'

    template = get_template(template_path)
    html = template.render(context)

    pisa_status = pisa.CreatePDF(html, dest=response)

    if pisa_status.err:
        return HttpResponse('PDF generation failed', status=400)

    return response


