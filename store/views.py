# views.py
import os
from django.conf import settings

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.http import HttpResponse,JsonResponse
from django.template.loader import get_template
from .decorators import allowed_users, admin_only
from xhtml2pdf import pisa
from django.db.models import Sum, F, Q
from django.utils.timezone import now, timedelta
from .models import *
from .forms import *
from django.utils import timezone
from datetime import date, timedelta, datetime
import calendar


@login_required
def dashboard(request):
    # Get the logged-in user's store
    user_store = Store.objects.filter(owner=request.user).first()

    # If the user doesn't own a store, redirect or return a message
    if not user_store:
        return render(request, 'dashboard.html', {'error': 'Haumiliki duka kwa sasa'})

    # Today's date
    today = date.today()

    # Filter sales by the user's store, excluding fully refunded items
    today_sales_total = Sale.objects.filter(
        store=user_store, date=today
    ).aggregate(total_sales=Sum('final_amount'))['total_sales'] or Decimal('0')

    all_time_sales_total = Sale.objects.filter(
        store=user_store
    ).aggregate(total_sales=Sum('final_amount'))['total_sales'] or Decimal('0')

    # Calculate total purchase cost for today using purchase_price_at_sale
    today_purchase_total = SaleItem.objects.filter(
        sale__store=user_store, sale__date=today, is_fully_refunded=False
    ).aggregate(
        total_purchase=Sum(F('purchase_price_at_sale') * F('quantity'))
    )['total_purchase'] or Decimal('0')

    # Calculate total purchase cost for all time
    all_time_purchase_total = SaleItem.objects.filter(
        sale__store=user_store, is_fully_refunded=False
    ).aggregate(
        total_purchase=Sum(F('purchase_price_at_sale') * F('quantity'))
    )['total_purchase'] or Decimal('0')

    # Calculate today's profit
    today_profit = today_sales_total - today_purchase_total

    # Calculate all-time profit
    all_time_profit = all_time_sales_total - all_time_purchase_total

    # Today's expenses
    today_expenses_total = Expense.objects.filter(
        store=user_store, date__date=today
    ).aggregate(
        total_expenses=Sum('amount')
    )['total_expenses'] or Decimal('0')

    # All-time expenses
    all_time_expenses_total = Expense.objects.filter(
        store=user_store
    ).aggregate(
        total_expenses=Sum('amount')
    )['total_expenses'] or Decimal('0')

    context = {
        'user_store': user_store,
        'today_sales_total': today_sales_total,
        'all_time_sales_total': all_time_sales_total,
        'today_purchase_total': today_purchase_total,
        'all_time_purchase_total': all_time_purchase_total,
        'today_profit': today_profit,
        'all_time_profit': all_time_profit,
        'today_expenses_total': today_expenses_total,
        'all_time_expenses_total': all_time_expenses_total,
        'today': today
    }

    return render(request, 'dashboard.html', context)



@login_required
def store_list(request):
    user_store = Store.objects.filter(owner=request.user).first()


    # If the user doesn't own a store, redirect or return a message
    if not user_store:
        messages.error(request, 'Haumiliki duka kwa sasa.')
        return redirect('dashboard')
    stores = Store.objects.filter(owner=request.user)
    
    return render(request, 'store_list.html', {'stores': stores})

@login_required
def edit_store(request, store_id):
    store = get_object_or_404(Store, id=store_id, owner=request.user)
    
    if request.method == 'POST':
        form = StoreForm(request.POST, instance=store)
        if form.is_valid():
            form.save()
            messages.success(request, 'Taarifa za duka zimehaririwa kikamilifu!')
            return redirect('store_list')
    else:
        form = StoreForm(instance=store)
    
    return render(request, 'edit_store.html', {'form': form})

@login_required
def delete_store(request, store_id):
    store = get_object_or_404(Store, id=store_id, owner=request.user)
    
    if request.method == 'POST':
        store.delete()
        messages.success(request, 'Duka Limefutwa kikamilifu!')
        return redirect('store_list')
    
    return render(request, 'delete_store.html', {'store': store})


# @login_required
# def assign_seller(request, store_id):
#     store = Store.objects.get(id=store_id, owner=request.user)
    
#     if request.method == 'POST':
#         username = request.POST.get('username')
#         password = request.POST.get('password')
        
#         # Create user for seller
#         user = User.objects.create_user(username=username, password=password)
        
#         # Assign seller to store
#         Seller.objects.create(user=user, store=store)
        
#         return redirect('store_list')  # Redirect to store dashboard after assigning seller
    
#     return render(request, 'assign_seller.html', {'store': store})



@login_required
def assign_seller(request, store_id):
    store = get_object_or_404(Store, id=store_id, owner=request.user)
    
    if request.method == 'POST':
        form = CreateSellerForm(request.POST)
        if form.is_valid():
            form.save(store=store)
            messages.success(request, 'Muuzaji amesajiliwa kikamilifu!')
            return redirect('store_list')
    else:
        form = CreateSellerForm()

    return render(request, 'assign_seller.html', {'form': form, 'store': store})

@login_required
def user_redirect(request):
    if request.user.is_seller:
        return redirect('add_sale')
    else:
        return redirect('store_list')  # Assuming you have a view to list stores owned by the user

@login_required
def store_details(request, store_id):
    store = get_object_or_404(Store, id=store_id, owner=request.user)
    sellers = store.sellers.all()
    # Sales data
    total_sales = float(Sale.objects.filter(store=store).aggregate(total_sales=Sum('final_amount'))['total_sales'] or 0)
    today_sales = float(Sale.objects.filter(store=store, date=datetime.today().date()).aggregate(today_sales=Sum('final_amount'))['today_sales'] or 0)
    
    # Expenses data
    total_expenses = float(Expense.objects.filter(store=store).aggregate(total_expenses=Sum('amount'))['total_expenses'] or 0)
    today_expenses = float(Expense.objects.filter(store=store, date__date=datetime.today().date()).aggregate(today_expenses=Sum('amount'))['today_expenses'] or 0)

    # Debt data
    total_debts = float(Debt.objects.filter(store=store).aggregate(total_debts=Sum('remaining_amount'))['total_debts'] or 0)

    # Weekly sales chart data (last 7 days)
    last_week = datetime.today() - timedelta(days=7)
    weekly_sales = Sale.objects.filter(store=store, date__gte=last_week).values('date').annotate(total_sales=Sum('final_amount'))

    # Convert Decimal values to float for compatibility with JS
    weekly_sales_labels = [sale['date'].strftime('%Y-%m-%d') for sale in weekly_sales]
    weekly_sales_data = [float(sale['total_sales']) for sale in weekly_sales]

    # Days with the most sales (top 7 days by sales amount)
    top_sales_days = Sale.objects.filter(store=store).values('date').annotate(total_sales=Sum('final_amount')).order_by('-total_sales')[:7]

    # Convert dates to day names
    top_sales_days_labels = [calendar.day_name[day['date'].weekday()] for day in top_sales_days]
    top_sales_days_data = [float(day['total_sales']) for day in top_sales_days]
    # Sales grouped by products (for product-based sales analysis)
    product_sales = SaleItem.objects.filter(sale__store=store).values('product__name').annotate(total_sold=Sum('quantity')).order_by('-total_sold')[:10]

    top_products = SaleItem.objects.filter(sale__store=store).values('product__name').annotate(
        total_quantity=Sum('quantity'),
        total_revenue=Sum('total_price')
    ).order_by('-total_quantity')[:10]  # Top 10 products

    refunds = SaleItem.objects.filter(sale__store=store, refunded_quantity__gt=0).values(
        'product__name', 'refund_reason'
    ).annotate(
        total_refunded=Sum(F('unit_price') * F('refunded_quantity')),
        total_quantity_refunded=Sum('refunded_quantity')
    )

    # Get debts with the sale date and remaining amount
    debts = Debt.objects.filter(store=store, remaining_amount__gt=0).values(
        'customer__name', 'remaining_amount', 'sale__date'
    )
    
    # Calculate the debt age manually in Python
    for debt in debts:
        debt_date = debt['sale__date']
        debt['debt_age'] = (datetime.now().date() - debt_date).days  # Calculate days since the sale


    today = date.today()

    # Total revenue (sales)
    total_revenue = Sale.objects.filter(store=store).aggregate(total=Sum('final_amount'))['total'] or 0

    # COGS
    cogs = SaleItem.objects.filter(sale__store=store, is_fully_refunded=False).aggregate(
        total_cogs=Sum(F('purchase_price_at_sale') * F('quantity'))
    )['total_cogs'] or 0

    # Total expenses
    total_expenses = Expense.objects.filter(store=store).aggregate(total=Sum('amount'))['total'] or 0

    net_profit = total_revenue - cogs - total_expenses


    context = {
        'store': store,
        'total_sales': total_sales,
        'today_sales': today_sales,
        'total_expenses': total_expenses,
        'today_expenses': today_expenses,
        'total_debts': total_debts,
        'weekly_sales': weekly_sales,
        'weekly_sales_labels': weekly_sales_labels,
        'weekly_sales_data': weekly_sales_data,
        'top_sales_days':top_sales_days,
        'product_sales': product_sales,
        'sellers': sellers,
        'top_products': top_products,
        'refunds': refunds,
        'debts':debts,
        'total_revenue': total_revenue,
        'cogs': cogs,
        'top_sales_days_labels': top_sales_days_labels,
        'top_sales_days_data': top_sales_days_data,
        'net_profit': net_profit,
    }
    return render(request, 'store_details.html', context)

@login_required
def product_list(request):
    user_store = Store.objects.filter(owner=request.user).first()


    # If the user doesn't own a store, redirect or return a message
    if not user_store:
        messages.error(request, 'Haumiliki duka kwa sasa.')
        return redirect('dashboard')
    # Initial query
    products = Product.objects.filter(store=user_store).order_by('-id')
    

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
    total_quantity = products.aggregate(total_quantity=Sum('quantity'))['total_quantity'] or 0
    total_purchase_price = products.aggregate(total_purchase_price=Sum(F('purchase_price') * F('quantity')))['total_purchase_price'] or 0
    total_selling_price = products.aggregate(total_selling_price=Sum(F('selling_price') * F('quantity')))['total_selling_price'] or 0
    
    # All-time total profit
    profit = total_selling_price - total_purchase_price

    # Get distinct categories for filtering
    categories = Category.objects.filter(store=user_store)

    context = {
        'products': products,
        'total_products': total_products,
        'total_purchase_price': total_purchase_price,
        'total_selling_price': total_selling_price,
        'profit': profit,
        'total_quantity':total_quantity,
        'categories': categories,
        'selected_category': category_filter,
        'zero_inventory_filter': zero_inventory_filter,
        'low_stock_filter': low_stock_filter,
    }
    
    return render(request, 'product_list.html', context)
@login_required

def add_product(request):
    user_store = Store.objects.filter(owner=request.user).first()

    # If the user doesn't own a store, redirect or return a message
    if not user_store:
        messages.error(request, 'Haumiliki duka kwa sasa.')
        return redirect('dashboard')

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, store=user_store)
        if form.is_valid():
            product = form.save(commit=False)
            
            # Check if a new category was provided
            new_category = form.cleaned_data.get('new_category')
            if new_category:
                # Create or get the category for the user's store
                category, created = Category.objects.get_or_create(name=new_category, store=user_store)
                product.category = category
            elif not form.cleaned_data.get('category'):
                # If no category was selected and no new category was provided, return an error
                form.add_error('category', "Tafadhali chagua aina ya bidhaa au ongeza aina mpya.")
                return render(request, 'add_product.html', {'form': form})

            # Associate the product with the user's store
            product.store = user_store
            product.save()

            messages.success(request, 'Bidhaa imeongezwa kikamilifu!')
            return redirect('product_list')
    else:
        form = ProductForm(store=user_store)

    return render(request, 'add_product.html', {'form': form})

@login_required
def sale_list(request):
    user_store = Store.objects.filter(owner=request.user).first()

    # If the user doesn't own a store, redirect or return a message
    if not user_store:
        messages.error(request, 'Haumiliki duka kwa sasa.')
        return redirect('dashboard')
    
    # Get query parameters for filters
    product_category = request.GET.get('category')
    payment_type = request.GET.get('payment_type')
    time_filter = request.GET.get('time_filter')
    start_date = request.GET.get('start_date')  # Get the start date from query params
    end_date = request.GET.get('end_date')      # Get the end date from query params

    # Initialize sales queryset, filter where total_amount and final_amount are greater than 0
    sales = Sale.objects.filter(
        Q(total_amount__gt=0) & Q(final_amount__gt=0) & Q(store=user_store)
    ).order_by('-id')

    # Filter by product category
    if product_category:
        sales = sales.filter(items__product__category_id=product_category).distinct()

    # Filter by payment type
    if payment_type:
        sales = sales.filter(payment_type=payment_type)

    # Filter by time (daily, weekly, monthly, yearly)
    if time_filter:
        today = date.today()
        if time_filter == 'daily':
            sales = sales.filter(date=today)
        elif time_filter == 'weekly':
            start_of_week = today - timedelta(days=today.weekday())
            sales = sales.filter(date__gte=start_of_week.today())
        elif time_filter == 'monthly':
            sales = sales.filter(date__year=today.year, date__month=today.month)
        elif time_filter == 'yearly':
            sales = sales.filter(date__year=today.year)

    # Filter by date range (start_date and end_date)
    if start_date and end_date:
        sales = sales.filter(date__range=[start_date, end_date])
    elif start_date:
        sales = sales.filter(date__gte=start_date)
    elif end_date:
        sales = sales.filter(date__lte=end_date)

    # Calculate totals for filtered sales
    total_amount = sales.aggregate(total=Sum('final_amount'))['total'] or 0
    total_sales_count = sales.count()
    total_products_sold = SaleItem.objects.filter(sale__in=sales).aggregate(total=Sum('quantity'))['total'] or 0

    # Get all categories for the filter dropdown
    categories = Category.objects.filter(store=user_store)

    context = {
        'sales': sales,
        'total_amount': total_amount,
        'total_sales_count': total_sales_count,
        'total_products_sold': total_products_sold,
        'categories': categories,
        'selected_category': product_category,
        'selected_payment_type': payment_type,
        'selected_time_filter': time_filter,
        'start_date': start_date,  # Pass start_date to the context
        'end_date': end_date,      # Pass end_date to the context
    }

    return render(request, 'sale_list.html', context)


@login_required
# @store_owner_or_seller_required
@transaction.atomic

# def add_sale(request):
#     # Fetch the store of the logged-in user
#     user_store = Store.objects.filter(owner=request.user).first()

#     if not user_store:
#         messages.error(request, 'You do not own a store.')
#         return redirect('dashboard')

#     if request.method == 'POST':
#         sale_form = SaleForm(request.POST, store=user_store)
#         item_formset = SaleItemFormSet(request.POST, form_kwargs={'store': user_store})

#         if sale_form.is_valid() and item_formset.is_valid():
#             sale = sale_form.save(commit=False)
#             sale.created_by = request.user
#             sale.store = user_store  # Associate sale with the user's store

#             total_amount = Decimal('0')
#             sufficient_stock = True

#             with transaction.atomic():
#                 for item_form in item_formset:
#                     if item_form.cleaned_data:
#                         product = item_form.cleaned_data.get('product')
#                         quantity = item_form.cleaned_data.get('quantity')

#                         if product and quantity:
#                             if product.quantity < quantity:
#                                 sufficient_stock = False
#                                 messages.error(request, f'Insufficient quantity for {product.name}. Only {product.quantity} available.')
#                                 break
#                             price = product.selling_price
#                             total_amount += quantity * price

#                 if sufficient_stock:
#                     sale.total_amount = total_amount
#                     sale.final_amount = total_amount - (sale.discount or Decimal('0'))
#                     sale.save()

#                     for item_form in item_formset:
#                         if item_form.cleaned_data:
#                             product = item_form.cleaned_data.get('product')
#                             quantity = item_form.cleaned_data.get('quantity')
#                             price = product.selling_price
#                             SaleItem.objects.create(
#                                 sale=sale,
#                                 product=product,
#                                 quantity=quantity,
#                                 unit_price=price,
#                                 total_price=quantity * price
#                             )
#                             product.quantity -= quantity
#                             product.save()

#                     if sale.payment_type == 'credit':
#                         Debt.objects.create(
#                             customer=sale.customer,
#                             sale=sale,
#                             amount=sale.total_amount,
#                             remaining_amount=sale.total_amount - sale.discount
#                         )

#                     messages.success(request, 'Sale recorded successfully!')
#                     return redirect('view_sale', sale_id=sale.id)
#         else:
#             messages.error(request, 'Please correct the errors below.')
#     else:
#         sale_form = SaleForm(store=user_store)
#         item_formset = SaleItemFormSet(form_kwargs={'store': user_store})

#     return render(request, 'add_sale.html', {
#         'sale_form': sale_form,
#         'item_formset': item_formset,
#     })
# @login_required
# def add_sale(request):
#     user_store = Store.objects.filter(owner=request.user).first() or Seller.objects.filter(user=request.user).first().store

#     if request.method == 'POST':
#         sale_form = SaleForm(request.POST, store=user_store)
#         item_formset = SaleItemFormSet(request.POST, form_kwargs={'store': user_store})

#         if sale_form.is_valid() and item_formset.is_valid():
#             sale = sale_form.save(commit=False)
#             sale.created_by = request.user
#             sale.store = user_store  # Associate sale with the user's store

#             total_amount = Decimal('0')
#             sufficient_stock = True

#             with transaction.atomic():
#                 for item_form in item_formset:
#                     if item_form.cleaned_data:
#                         product = item_form.cleaned_data.get('product')
#                         quantity = item_form.cleaned_data.get('quantity')

#                         if product and quantity:
#                             if product.quantity < quantity:
#                                 sufficient_stock = False
#                                 messages.error(request, f'Insufficient quantity for {product.name}. Only {product.quantity} available.')
#                                 break
#                             price = product.selling_price
#                             total_amount += quantity * price

#                 if sufficient_stock:
#                     sale.total_amount = total_amount
#                     sale.final_amount = total_amount - (sale.discount or Decimal('0'))
#                     sale.save()

#                     for item_form in item_formset:
#                         if item_form.cleaned_data:
#                             product = item_form.cleaned_data.get('product')
#                             quantity = item_form.cleaned_data.get('quantity')
#                             price = product.selling_price
#                             SaleItem.objects.create(
#                                 sale=sale,
#                                 product=product,
#                                 quantity=quantity,
#                                 unit_price=price,
#                                 total_price=quantity * price
#                             )
#                             product.quantity -= quantity
#                             product.save()

#                     if sale.payment_type == 'credit':
#                         Debt.objects.create(
#                             customer=sale.customer,
#                             sale=sale,
#                             store=sale.store,
#                             amount=sale.total_amount,
#                             remaining_amount=sale.total_amount - sale.discount
#                         )

#                     messages.success(request, 'Sale recorded successfully!')
#                     return redirect('view_sale', sale_id=sale.id)
#         else:
#             messages.error(request, 'Please correct the errors below.')
#     else:
#         sale_form = SaleForm(store=user_store)
#         item_formset = SaleItemFormSet(form_kwargs={'store': user_store})

#     return render(request, 'add_sale.html', {
#         'sale_form': sale_form,
#         'item_formset': item_formset,
#     })

def add_sale(request):
    user_store = Store.objects.filter(owner=request.user).first() or Seller.objects.filter(user=request.user).first().store

    if request.method == 'POST':
        sale_form = SaleForm(request.POST, store=user_store)
        item_formset = SaleItemFormSet(request.POST, form_kwargs={'store': user_store})

        if sale_form.is_valid() and item_formset.is_valid():
            sale = sale_form.save(commit=False)
            sale.created_by = request.user
            sale.store = user_store

            total_amount = Decimal('0')
            sufficient_stock = True

            with transaction.atomic():
                for item_form in item_formset:
                    if item_form.cleaned_data:
                        product = item_form.cleaned_data.get('product')
                        quantity = item_form.cleaned_data.get('quantity')

                        if product and quantity:
                            if product.quantity < quantity:
                                sufficient_stock = False
                                messages.error(request, f'Insufficient quantity for {product.name}. Only {product.quantity} available.')
                                break
                            price = product.selling_price
                            total_amount += quantity * price

                if sufficient_stock:
                    sale.total_amount = total_amount
                    sale.final_amount = total_amount - (sale.discount or Decimal('0'))
                    sale.save()

                    for item_form in item_formset:
                        if item_form.cleaned_data:
                            product = item_form.cleaned_data.get('product')
                            quantity = item_form.cleaned_data.get('quantity')
                            price = product.selling_price

                            # Create sale item and lock prices at the time of sale
                            SaleItem.objects.create(
                                sale=sale,
                                product=product,
                                quantity=quantity,
                                unit_price=price,
                                total_price=quantity * price,
                                purchase_price_at_sale=product.purchase_price,
                                selling_price_at_sale=price
                            )
                            product.quantity -= quantity
                            product.save()

                    if sale.payment_type == 'credit':
                        Debt.objects.create(
                            customer=sale.customer,
                            sale=sale,
                            store=sale.store,
                            amount=sale.total_amount,
                            remaining_amount=sale.total_amount - sale.discount
                        )

                    messages.success(request, 'Mauzo yamerekodiwa kikamilifu!')
                    return redirect('view_sale', sale_id=sale.id)
        else:
            messages.error(request, 'Tafadhali sahihisha makosa yaliyojitokeza.')
    else:
        sale_form = SaleForm(store=user_store)
        item_formset = SaleItemFormSet(form_kwargs={'store': user_store})

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
                    store=sale.store,
                    amount=sale_item.price * sale_item.quantity,
                    remaining_amount=sale_item.price * sale_item.quantity
                )

            return redirect('add_sale_items', sale_id=sale.id)
    else:
        form = SaleItemForm()
    
    sale_items = SaleItem.objects.filter(sale=sale)
    return render(request, 'add_sale_items.html', {'form': form, 'sale': sale, 'sale_items': sale_items})



@login_required
def debt_list(request):
    user_store = Store.objects.filter(owner=request.user).first()

    # If the user doesn't own a store, redirect or return a message
    if not user_store:
        messages.error(request, 'Haumiliki duka kwa sasa.')
        return redirect('dashboard')
    # Get query parameters for filters
    customer_id = request.GET.get('customer')
    time_filter = request.GET.get('time_filter')

    # Initialize debt queryset
    debts = Debt.objects.filter(remaining_amount__gt=0, store=user_store).order_by('-sale__date')

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
    customers = Customer.objects.filter(store=user_store)

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
            payment.store = debt.store  # Associate the payment with the store
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
    user_store = Store.objects.filter(owner=request.user).first() or Seller.objects.filter(user=request.user).first().store

    # If the user doesn't own a store, redirect or return a message
    if not user_store:
        messages.error(request, 'Haumiliki duka kwa sasa.')
        return redirect('dashboard')
    # Get query parameters for filters
    category_id = request.GET.get('category')
    time_filter = request.GET.get('time_filter')

    # Initialize expense queryset
    expenses = Expense.objects.filter(store=user_store).order_by('-date')

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
    daily_expenses = expenses.filter(date__date=today)
    weekly_expenses = expenses.filter(date__date__gte=today - timedelta(days=7))
    monthly_expenses = expenses.filter(date__year=today.year, date__month=today.month)
    yearly_expenses = expenses.filter(date__year=today.year)

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
    categories = ExpenseCategory.objects.filter(store=user_store)

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
    user_store = Store.objects.filter(owner=request.user).first() or Seller.objects.filter(user=request.user).first().store

    # If the user doesn't own a store, redirect or return a message
    if not user_store:
        messages.error(request, 'Haumiliki duka kwa sasa.')
        return redirect('dashboard')

    if request.method == 'POST':
        form = ExpenseForm(request.POST, store=user_store)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.store = user_store  # Associate the expense with the store

            # Handle new category creation
            new_category = form.cleaned_data.get('new_category')
            if new_category:
                category, created = ExpenseCategory.objects.get_or_create(store=user_store, name=new_category)
                expense.category = category
            elif not form.cleaned_data.get('category'):
                # If no category is selected and no new category is provided, return an error
                form.add_error('category', "Tafadhali chagua aina ya matumizi au ongeza aina mpya.")
                return render(request, 'add_expense.html', {'form': form})

            expense.save()
            messages.success(request, 'Matumizi yamerekodiwa kikamilifu!')
            return redirect('expense_list')
    else:
        form = ExpenseForm(store=user_store)

    return render(request, 'add_expense.html', {'form': form})


@login_required
def customer_list(request):
    user_store = Store.objects.filter(owner=request.user).first()

    # If the user doesn't own a store, redirect or return a message
    if not user_store:
        messages.error(request, 'Haumiliki duka kwa sasa.')
        return redirect('dashboard')
    # Fetch query parameters from the request
    customer_name = request.GET.get('customer_name', '')
    debt_status = request.GET.get('debt_status', 'all')  # 'all', 'active', or 'paid'

    # Fetch all customers for the dropdown
    all_customers = Customer.objects.filter(store=user_store)

    # Filter customers by selected name if provided
    customers = all_customers
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
    user_store = Store.objects.filter(owner=request.user).first()

    # If the user doesn't own a store, redirect or return a message
    if not user_store:
        messages.error(request, 'Haumiliki duka kwa sasa.')
        return redirect('dashboard')

    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            customer = form.save(commit=False)
            customer.store = user_store  # Associate the customer with the store
            customer.save()
            messages.success(request, 'Mteja mpya amerekodiwa kikamilifu!')
            return redirect('customer_list')
    else:
        form = CustomerForm()

    return render(request, 'add_customer.html', {'form': form})


@login_required
def creditor_list(request):
    user_store = Store.objects.filter(owner=request.user).first()

    # If the user doesn't own a store, redirect or return a message
    if not user_store:
        messages.error(request, 'Haumiliki duka kwa sasa.')
        return redirect('dashboard')
    creditors = Creditor.objects.filter(store=user_store)
    return render(request, 'creditor_list.html', {'creditors': creditors})

@login_required
def add_creditor(request):
    user_store = Store.objects.filter(owner=request.user).first()

    # If the user doesn't own a store, redirect or return a message
    if not user_store:
        messages.error(request, 'Haumiliki duka kwa sasa.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = CreditorForm(request.POST)
        if form.is_valid():
            creditor = form.save(commit=False)
            creditor.store = user_store  # Associate the creditor with the store
            creditor.save()
            messages.success(request, 'Mdai amerekodiwa kikamilifu!')
            return redirect('creditor_list')
    else:
        form = CreditorForm()
    return render(request, 'add_creditor.html', {'form': form})



@login_required
def credit_list(request):
    user_store = Store.objects.filter(owner=request.user).first()

    # If the user doesn't own a store, redirect or return a message
    if not user_store:
        messages.error(request, 'Haumiliki duka kwa sasa.')
        return redirect('dashboard')
    
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
    credits = Credit.objects.filter(store=user_store)

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
    creditors = Creditor.objects.filter(store=user_store)

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
    user_store = Store.objects.filter(owner=request.user).first()

    if not user_store:
        messages.error(request, 'Haumiliki duka kwa sasa.')
        return redirect('dashboard')

    if request.method == 'POST':
        form = CreditForm(request.POST, store=user_store)
        if form.is_valid():
            create_new_creditor = form.cleaned_data.get('create_new_creditor')
            if create_new_creditor:
                creditor_name = form.cleaned_data.get('creditor_name')
                creditor_phone_number = form.cleaned_data.get('creditor_phone_number')
                creditor, created = Creditor.objects.get_or_create(
                    name=creditor_name,
                    phone_number=creditor_phone_number,
                    store=user_store  # Associate the creditor with the store
                )
            else:
                creditor = form.cleaned_data.get('creditor')

            credit = form.save(commit=False)
            credit.creditor = creditor
            credit.store = user_store
            credit.remaining_amount = credit.amount
            credit.save()

            messages.success(request, 'Mkopo umerekodiwa kikamilifu!')
            return redirect('credit_list')
    else:
        form = CreditForm(store=user_store)

    return render(request, 'add_credit.html', {'form': form})


@login_required
def add_credit_payment(request, credit_id):
    credit = get_object_or_404(Credit, id=credit_id)
    user_store = Store.objects.filter(owner=request.user).first()

    # If the store associated with the credit doesn't match the user's store, restrict access
    if credit.store != user_store:
        messages.error(request, 'Huna ruhusa ya kufanya malipo kwa mkopo huu.')
        return redirect('credit_list')

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

    # Check if the logged-in user is the owner of the store associated with the product
    if product.store.owner != request.user:
        messages.error(request, 'Huna ruhusa ya kuhariri bidhaa hii.')
        return redirect('product_list')

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product, store=product.store)
        if form.is_valid():
            form.save()
            messages.success(request, 'Bidhaa imehaririwa kikamilifu!')
            return redirect('product_list')
    else:
        form = ProductForm(instance=product, store=product.store)
    
    return render(request, 'edit_product.html', {'form': form, 'product': product})




@login_required
def delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    # Check if the logged-in user is the owner of the store associated with the product
    if product.store.owner != request.user:
        messages.error(request, 'Huna ruhusa ya kufuta bidhaa hii.')
        return redirect('product_list')

    if request.method == 'POST':
        product.delete()
        messages.success(request, 'Bidhaa imefutwa kikamilifu!')
        return redirect('product_list')
    
    return render(request, 'delete_product.html', {'product': product})


@login_required
def edit_customer(request, customer_id):
    customer = get_object_or_404(Customer, id=customer_id)

    # Check if the logged-in user is the owner of the store associated with the customer
    if customer.store.owner != request.user:
        messages.error(request, 'Huna ruhusa ya kuhariri mteja huyu.')
        return redirect('customer_list')

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

    # Check if the logged-in user is the owner of the store associated with the customer
    if customer.store.owner != request.user:
        messages.error(request, 'Huna ruhusa ya kufuta mteja huyu.')
        return redirect('customer_list')

    if request.method == 'POST':
        customer.delete()
        messages.success(request, 'Mteja amefutwa kikamilifu!')
        return redirect('customer_list')
    
    return render(request, 'delete_customer.html', {'customer': customer})



# Creditor views
@login_required
def edit_creditor(request, creditor_id):
    creditor = get_object_or_404(Creditor, id=creditor_id)

       # Check if the logged-in user is the owner of the store associated with the customer
    if creditor.store.owner != request.user:
        messages.error(request, 'Huna ruhusa ya kuhariri mdai huyu.')
        return redirect('creditor_list')
    
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

       # Check if the logged-in user is the owner of the store associated with the customer
    if creditor.store.owner != request.user:
        messages.error(request, 'Huna ruhusa ya kumfuta mdai huyu.')
        return redirect('creditor_list')
    
    if request.method == 'POST':
        creditor.delete()
        return redirect('creditor_list')
    return render(request, 'delete_creditor.html', {'creditor': creditor})


@login_required
def view_sale(request, sale_id):
    sale = get_object_or_404(Sale, id=sale_id)

    # Check if the logged-in user is the owner of the store associated with the sale
    if sale.store.owner != request.user:
        messages.error(request, 'Huna ruhusa ya kuona mauzo haya.')
        return redirect('dashboard')

    sale_items = sale.items.filter(is_fully_refunded=False)
    return render(request, 'view_sale.html', {'sale': sale, 'sale_items': sale_items})


@login_required
def view_debt(request, debt_id):
    debt = get_object_or_404(Debt, id=debt_id)

    # Check if the logged-in user is the owner of the store associated with the debt
    if debt.store.owner != request.user:
        messages.error(request, 'Huna ruhusa ya kuona deni hili.')
        return redirect('dashboard')

    sale_items = debt.sale.items.all()
    payments = debt.debtpayment_set.all()
    return render(request, 'view_debt.html', {'debt': debt, 'payments': payments, 'sale_items': sale_items})


@login_required
def view_credit(request, credit_id):
    credit = get_object_or_404(Credit, id=credit_id)

    # Check if the logged-in user is the owner of the store associated with the credit
    if credit.store.owner != request.user:
        messages.error(request, 'Huna ruhusa ya kuona mkopo huu.')
        return redirect('dashboard')

    payments = credit.creditpayment_set.all()
    return render(request, 'view_credit.html', {'credit': credit, 'payments': payments})



@login_required
def edit_expense(request, expense_id):
    expense = get_object_or_404(Expense, id=expense_id)

      # Check if the logged-in user is the owner of the store associated with the customer
    if expense.store.owner != request.user:
        messages.error(request, 'Huna ruhusa ya kuhariri matumizi haya.')
        return redirect('expense_list')
    
    if request.method == 'POST':
        form = ExpenseForm(request.POST, instance=expense, store=expense.store)
        if form.is_valid():
            form.save()
            messages.success(request, 'Matumizi yamebadilishwa kikamilifu.')
            return redirect('expense_list')
    else:
        form = ExpenseForm(instance=expense, store=expense.store)
    return render(request, 'edit_expense.html', {'form': form, 'expense': expense})

@login_required
def delete_expense(request, expense_id):
    expense = get_object_or_404(Expense, id=expense_id)

      # Check if the logged-in user is the owner of the store associated with the customer
    if expense.store.owner != request.user:
        messages.error(request, 'Huna ruhusa ya kufuta matumizi haya.')
        return redirect('expense_list')
    
    if request.method == 'POST':
        expense.delete()
        messages.success(request, 'Matumizi yamefutwa kikamilifu.')
        return redirect('expense_list')
    return render(request, 'delete_expense.html', {'expense': expense})


@login_required
def generate_pdf_invoice(request, sale_id):
    sale = get_object_or_404(Sale, id=sale_id)

    # Check if the logged-in user is the owner of the store associated with the sale
    if sale.store.owner != request.user:
        messages.error(request, 'Huna ruhusa ya kutengeneza ankara kwa mauzo haya.')
        return redirect('dashboard')

    sale_items = sale.items.filter(is_fully_refunded=False)
    
    template_path = 'invoice_pdf.html'  # Separate template for generating PDF
    context = {
        'sale': sale,
        'sale_items': sale_items,
    }
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Invoice_{sale.id}.pdf"'

    template = get_template(template_path)
    html = template.render(context)

    # Generate PDF
    pisa_status = pisa.CreatePDF(html, dest=response)

    if pisa_status.err:
        return HttpResponse('PDF generation failed', status=400)

    return response


# @login_required
# def refund_product(request, sale_item_id):
#     sale_item = get_object_or_404(SaleItem, id=sale_item_id)
    
#     if request.method == 'POST':
#         form = RefundForm(request.POST)
#         if form.is_valid():
#             refund_quantity = form.cleaned_data['refund_quantity']
#             refund_reason = form.cleaned_data['refund_reason']
            
#             # Check if the refund quantity exceeds available quantity
#             available_quantity = sale_item.quantity - sale_item.refunded_quantity
#             if refund_quantity > available_quantity:
#                 form.add_error('refund_quantity', 'Refund quantity exceeds available quantity.')
#             else:
#                 with transaction.atomic():
#                     # Update SaleItem refund information
#                     sale_item.refunded_quantity += refund_quantity
#                     sale_item.refund_reason = refund_reason

#                     # Mark as fully refunded if all quantity is refunded
#                     if sale_item.refunded_quantity == sale_item.quantity:
#                         sale_item.is_fully_refunded = True
#                     sale_item.save()

#                     # Return the refunded product to the inventory
#                     product = sale_item.product
#                     product.quantity += refund_quantity
#                     product.save()

#                     # Update the Sale's total_amount and final_amount
#                     refund_value = refund_quantity * sale_item.unit_price
#                     sale = sale_item.sale
#                     sale.total_amount -= refund_value
#                     sale.final_amount = sale.total_amount - (sale.discount or Decimal('0'))
#                     sale.save()

#                     messages.success(request, f'{refund_quantity} of {product.name} has been refunded and returned to inventory.')
#                     return redirect('view_sale', sale_id=sale_item.sale.id)
#     else:
#         form = RefundForm()

#     return render(request, 'refund_product.html', {
#         'form': form,
#         'sale_item': sale_item
#     })

@login_required
def refund_product(request, sale_item_id):
    sale_item = get_object_or_404(SaleItem, id=sale_item_id)
    sale = sale_item.sale

    # Check if the logged-in user is the owner of the store associated with the sale
    if sale.store.owner != request.user:
        messages.error(request, 'Huna ruhusa ya kurudisha bidhaa hii.')
        return redirect('view_sale', sale_id=sale.id)

    if request.method == 'POST':
        form = RefundForm(request.POST)
        if form.is_valid():
            refund_quantity = form.cleaned_data['refund_quantity']
            refund_reason = form.cleaned_data['refund_reason']
            
            # Check if the refund quantity exceeds available quantity
            available_quantity = sale_item.quantity - sale_item.refunded_quantity
            if refund_quantity > available_quantity:
                form.add_error('refund_quantity', 'Kiasi cha kurudisha kinazidi kiasi kilichobaki.')
            else:
                with transaction.atomic():
                    # Update SaleItem refund information
                    sale_item.refunded_quantity += refund_quantity
                    sale_item.refund_reason = refund_reason

                    # Mark as fully refunded if all quantity is refunded
                    if sale_item.refunded_quantity == sale_item.quantity:
                        sale_item.is_fully_refunded = True
                    sale_item.save()

                    # Return the refunded product to the inventory
                    product = sale_item.product
                    product.quantity += refund_quantity
                    product.save()

                    # Update the Sale's total_amount and final_amount
                    refund_value = refund_quantity * sale_item.unit_price
                    sale.total_amount -= refund_value
                    sale.final_amount = sale.total_amount - (sale.discount or Decimal('0'))
                    sale.save()

                    messages.success(request, f'{refund_quantity} ya {product.name} imerudishwa kwenye hesabu.')
                    return redirect('view_sale', sale_id=sale_item.sale.id)
    else:
        form = RefundForm()

    return render(request, 'refund_product.html', {
        'form': form,
        'sale_item': sale_item
    })
