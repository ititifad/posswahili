from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal

class Category(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Product(models.Model):
    PACKAGE_TYPES = (
        ('pcs', 'Pcs'),
        ('box', 'Box'),
        ('ctn', 'Carton'),
        ('ltr', 'Ltr'),
        ('kg', 'Kg'),
        ('pair', 'Pair'),
        ('bag', 'Bag'),
        ('dozen', 'Dozen'),
        ('gram', 'Gram'),
        ('roll', 'Roll'),
    )
    name = models.CharField(max_length=200)
    # image = models.ImageField(upload_to='products/')
    quantity = models.PositiveIntegerField(default=0)
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True,blank=True)
    package = models.CharField(max_length=100, choices=PACKAGE_TYPES, null=True,blank=True)
    description = models.TextField(null=True, blank=True)
    

    def __str__(self):
        return self.name

class Customer(models.Model):
    name = models.CharField(max_length=200)
    phone_number = models.CharField(max_length=50)
    

    def __str__(self):
        return self.name

class Sale(models.Model):
    PAYMENT_TYPES = (
        ('cash', 'Cash'),
        ('credit', 'Credit'),
    )
    customer = models.ForeignKey('Customer', on_delete=models.SET_NULL, null=True, blank=True)
    date = models.DateField()
    payment_type = models.CharField(max_length=10, choices=PAYMENT_TYPES, default='cash')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    final_amount = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.TextField(blank=True, null=True)  # For "Maelezo ya ziada"
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Sale {self.id} on {self.date}"

    def save(self, *args, **kwargs):
        # Ensure total_amount and discount are not None, defaulting to 0 if they are
        total = self.total_amount or Decimal('0')
        discount = self.discount or Decimal('0')
        
        # Calculate final_amount as total_amount minus discount
        self.final_amount = total - discount
        super().save(*args, **kwargs)

class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.product.name} - {self.quantity}"

    def save(self, *args, **kwargs):
        self.total_price = self.quantity * self.unit_price
        super().save(*args, **kwargs)

class Debt(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    remaining_amount = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Debt for {self.customer.name} - {self.sale.id}"
    
    def save(self, *args, **kwargs):
        self.paid_amount = self.amount - self.remaining_amount
        super().save(*args, **kwargs)

class DebtPayment(models.Model):
    debt = models.ForeignKey(Debt, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment for Debt {self.debt.id}"
    
class ExpenseCategory(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Expense(models.Model):
    category = models.ForeignKey(ExpenseCategory, on_delete=models.SET_NULL, null=True)
    description = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.description} - {self.amount}"

class Creditor(models.Model):
    name = models.CharField(max_length=200)
    phone_number = models.CharField(max_length=50)
    # address = models.TextField()

    def __str__(self):
        return self.name

class Credit(models.Model):
    creditor = models.ForeignKey(Creditor, on_delete=models.CASCADE, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    remaining_amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)
    description = models.TextField()

    def __str__(self):
        return f"Credit from {self.creditor.name} - {self.amount}"

class CreditPayment(models.Model):
    credit = models.ForeignKey(Credit, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment for Credit {self.credit.id}"