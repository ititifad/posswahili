# forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User, Group
from .models import *

class ProductForm(forms.ModelForm):
    new_category = forms.CharField(max_length=100, required=False, label="Aina Mpya ya Bidhaa")
    description = forms.CharField(widget=forms.Textarea(attrs={'rows': '3'}), required=False)

    class Meta:
        model = Product
        fields = ['name', 'quantity', 'purchase_price', 'selling_price', 'category', 'package', 'description']

    def __init__(self, *args, **kwargs):
        # Capture the store from the kwargs if passed
        store = kwargs.pop('store', None)
        super().__init__(*args, **kwargs)
        
        # Make the category field optional
        self.fields['category'].required = False

        # Filter the categories to show only those belonging to the passed store
        if store:
            self.fields['category'].queryset = Category.objects.filter(store=store)

class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['name', 'phone_number']

class SaleForm(forms.ModelForm):
    class Meta:
        model = Sale
        fields = ['date', 'customer', 'payment_type', 'discount']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        store = kwargs.pop('store', None)  # Extract store from kwargs
        super().__init__(*args, **kwargs)

        if store:
            # Filter customers based on the store
            self.fields['customer'].queryset = Customer.objects.filter(store=store)


class SaleItemForm(forms.Form):
    product = forms.ModelChoiceField(queryset=Product.objects.none())  # Initialize with an empty queryset
    quantity = forms.DecimalField(max_digits=10, decimal_places=2, min_value=1)

    def __init__(self, *args, **kwargs):
        store = kwargs.pop('store', None)  # Extract store from kwargs
        super().__init__(*args, **kwargs)

        if store:
            # Filter products based on the store
            self.fields['product'].queryset = Product.objects.filter(store=store)


# Formset for SaleItemForm
SaleItemFormSet = forms.formset_factory(SaleItemForm, extra=1)


class DebtPaymentForm(forms.ModelForm):
    class Meta:
        model = DebtPayment
        fields = ['amount']



class CreditorForm(forms.ModelForm):
    class Meta:
        model = Creditor
        fields = ['name', 'phone_number']

# class CreditForm(forms.ModelForm):
#     class Meta:
#         model = Credit
#         fields = ['creditor', 'amount', 'description']

class CreditForm(forms.ModelForm):
    # Field to create a new creditor
    create_new_creditor = forms.BooleanField(required=False, label='Ongeza Mkopeshaji Mpya')
    creditor_name = forms.CharField(required=False, max_length=200, label='Jina la Mkopeshaji')
    creditor_phone_number = forms.CharField(required=False, max_length=50, label='Namba ya Simu ya Mkopeshaji')
    description = forms.CharField(widget=forms.Textarea(attrs={'rows': '3'}))

    class Meta:
        model = Credit
        fields = ['creditor', 'create_new_creditor', 'creditor_name', 'creditor_phone_number', 'amount', 'description']
        labels = {
            'creditor': 'Chagua Mkopeshaji',
            'amount': 'Kiasi',
            'description': 'Maelezo',
        }

    def __init__(self, *args, **kwargs):
        # Capture the store passed from the view
        store = kwargs.pop('store', None)
        super().__init__(*args, **kwargs)

        if store:
            # Filter creditors based on the store
            self.fields['creditor'].queryset = Creditor.objects.filter(store=store)

    def clean(self):
        cleaned_data = super().clean()
        create_new_creditor = cleaned_data.get('create_new_creditor')
        creditor_name = cleaned_data.get('creditor_name')
        creditor_phone_number = cleaned_data.get('creditor_phone_number')

        if create_new_creditor:
            if not creditor_name:
                self.add_error('creditor_name', 'Tafadhali ingiza jina la mkopeshaji.')
            if not creditor_phone_number:
                self.add_error('creditor_phone_number', 'Tafadhali ingiza namba ya simu ya mkopeshaji.')

        return cleaned_data

class CreditPaymentForm(forms.ModelForm):
    class Meta:
        model = CreditPayment
        fields = ['amount']


class RefundForm(forms.Form):
    refund_quantity = forms.IntegerField(min_value=1, label='Refund Quantity')
    refund_reason = forms.CharField(max_length=255, required=False, label='Refund Reason')


class ExpenseForm(forms.ModelForm):
    new_category = forms.CharField(max_length=100, required=False, label="Aina Mpya ya Matumizi")

    class Meta:
        model = Expense
        fields = ['category', 'description', 'amount']

    def __init__(self, *args, **kwargs):
        self.store = kwargs.pop('store', None)
        super().__init__(*args, **kwargs)
        # Filter categories based on the store
        self.fields['category'].queryset = ExpenseCategory.objects.filter(store=self.store)
        self.fields['category'].required = False  # Category can be blank if adding a new one


class StoreForm(forms.ModelForm):
    name = forms.CharField(max_length=200, label='Jina la Biashara')
    address = forms.CharField(widget=forms.Textarea(attrs={'rows': '2'}), label='Mahali')
    phone_number = forms.CharField(max_length=50, label='Nambari ya Simu')
    class Meta:
        model = Store
        fields = ['name', 'address', 'phone_number']


class CreateSellerForm(forms.ModelForm):
    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = Seller
        fields = ['username', 'password']

    def save(self, commit=True, store=None):
        # Create the User first
        user = User.objects.create_user(
            username=self.cleaned_data['username'],
            password=self.cleaned_data['password']
        )

        # Create the Seller profile
        seller = super().save(commit=False)
        seller.user = user
        if store:
            seller.store = store
        if commit:
            seller.save()
        return seller