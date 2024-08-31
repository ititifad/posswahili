# forms.py
from django import forms
from .models import *

class ProductForm(forms.ModelForm):
    new_category = forms.CharField(max_length=100, required=False, label="Aina Mpya ya Bidhaa")
    description = forms.CharField(widget=forms.Textarea(attrs={'rows': '3'}))
    class Meta:
        model = Product
        fields = ['name', 'quantity', 'purchase_price', 'selling_price', 'category', 'package', 'description']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].required = False

class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['name', 'phone_number']

class SaleForm(forms.ModelForm):
    class Meta:
        model = Sale
        fields = ['date','customer', 'payment_type', 'discount', 'notes']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }

class SaleItemForm(forms.Form):
    product = forms.ModelChoiceField(queryset=Product.objects.all())
    quantity = forms.DecimalField(max_digits=10, decimal_places=2, min_value=0.01)

SaleItemFormSet = forms.formset_factory(SaleItemForm, extra=1)

class DebtPaymentForm(forms.ModelForm):
    class Meta:
        model = DebtPayment
        fields = ['amount']

class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ['category','description', 'amount']

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