from django import forms
from django.core.exceptions import ValidationError
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, HTML
from crispy_forms.bootstrap import FormActions

from .models import Customer, CustomerSegment, CustomerInteraction, Purchase

class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = [
            'first_name', 'last_name', 'email', 'phone',
            'address', 'city', 'state', 'postal_code', 'country',
            'company', 'position', 'segment', 'status', 'notes'
        ]
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 4}),
            'address': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('first_name', css_class='col-md-6'),
                Column('last_name', css_class='col-md-6'),
            ),
            Row(
                Column('email', css_class='col-md-6'),
                Column('phone', css_class='col-md-6'),
            ),
            Row(
                Column('company', css_class='col-md-6'),
                Column('position', css_class='col-md-6'),
            ),
            Row(
                Column('segment', css_class='col-md-6'),
                Column('status', css_class='col-md-6'),
            ),
            'address',
            Row(
                Column('city', css_class='col-md-4'),
                Column('state', css_class='col-md-4'),
                Column('postal_code', css_class='col-md-4'),
            ),
            'country',
            'notes',
            FormActions(
                Submit('submit', 'Salvar Cliente', css_class='btn btn-primary'),
                HTML('<a href="{% url "customers:list" %}" class="btn btn-secondary">Cancelar</a>')
            )
        )
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            # Check if email already exists (excluding current instance)
            existing = Customer.objects.filter(email=email)
            if self.instance and self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            
            if existing.exists():
                raise ValidationError('Este email já está sendo usado por outro cliente.')
        
        return email

class CustomerInteractionForm(forms.ModelForm):
    class Meta:
        model = CustomerInteraction
        fields = ['interaction_type', 'subject', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'interaction_type',
            'subject',
            'description',
            FormActions(
                Submit('submit', 'Adicionar Interação', css_class='btn btn-primary')
            )
        )

class PurchaseForm(forms.ModelForm):
    class Meta:
        model = Purchase
        fields = ['product_service', 'amount', 'purchase_date', 'description']
        widgets = {
            'purchase_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'product_service',
            Row(
                Column('amount', css_class='col-md-6'),
                Column('purchase_date', css_class='col-md-6'),
            ),
            'description',
            FormActions(
                Submit('submit', 'Adicionar Compra', css_class='btn btn-primary')
            )
        )

class CustomerImportForm(forms.Form):
    """Form for importing customers from CSV"""
    csv_file = forms.FileField(
        label='Arquivo CSV',
        help_text='Selecione um arquivo CSV com os dados dos clientes'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'csv_file',
            FormActions(
                Submit('submit', 'Importar Clientes', css_class='btn btn-primary')
            )
        )
    
    def clean_csv_file(self):
        file = self.cleaned_data.get('csv_file')
        if file:
            if not file.name.endswith('.csv'):
                raise ValidationError('O arquivo deve ser um CSV.')
            
            # Check file size (max 5MB)
            if file.size > 5 * 1024 * 1024:
                raise ValidationError('O arquivo é muito grande. Máximo 5MB.')
        
        return file
