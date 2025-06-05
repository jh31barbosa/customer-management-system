from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, HTML
from crispy_forms.bootstrap import FormActions

from .models import Appointment, AppointmentType, AppointmentNote, AvailabilitySlot
from apps.customers.models import Customer

class AppointmentForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = [
            'customer', 'appointment_type', 'title', 'description',
            'start_datetime', 'end_datetime', 'assigned_to',
            'location', 'meeting_url', 'status'
        ]
        widgets = {
            'start_datetime': forms.DateTimeInput(
                attrs={'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M'
            ),
            'end_datetime': forms.DateTimeInput(
                attrs={'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M'
            ),
            'description': forms.Textarea(attrs={'rows': 4}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filter active customers
        self.fields['customer'].queryset = Customer.objects.filter(
            status__in=['active', 'prospect']
        ).order_by('first_name', 'last_name')
        
        # Filter active users
        self.fields['assigned_to'].queryset = User.objects.filter(
            is_active=True
        ).order_by('first_name', 'last_name')
        
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('customer', css_class='col-md-6'),
                Column('appointment_type', css_class='col-md-6'),
            ),
            'title',
            'description',
            Row(
                Column('start_datetime', css_class='col-md-6'),
                Column('end_datetime', css_class='col-md-6'),
            ),
            Row(
                Column('assigned_to', css_class='col-md-6'),
                Column('status', css_class='col-md-6'),
            ),
            'location',
            'meeting_url',
            FormActions(
                Submit('submit', 'Salvar Agendamento', css_class='btn btn-primary'),
                HTML('<a href="{% url "appointments:list" %}" class="btn btn-secondary">Cancelar</a>')
            )
        )
    
    def clean(self):
        cleaned_data = super().clean()
        start_datetime = cleaned_data.get('start_datetime')
        end_datetime = cleaned_data.get('end_datetime')
        
        if start_datetime and end_datetime:
            # Check if end time is after start time
            if end_datetime <= start_datetime:
                raise ValidationError('A data/hora de fim deve ser posterior à de início.')
            
            # Check if appointment is in the past
            if start_datetime < timezone.now():
                raise ValidationError('Não é possível agendar no passado.')
            
            # Check for conflicts with existing appointments
            assigned_to = cleaned_data.get('assigned_to')
            if assigned_to:
                existing_appointments = Appointment.objects.filter(
                    assigned_to=assigned_to,
                    start_datetime__lt=end_datetime,
                    end_datetime__gt=start_datetime,
                    status__in=['scheduled', 'confirmed']
                )
                
                # Exclude current instance if editing
                if self.instance and self.instance.pk:
                    existing_appointments = existing_appointments.exclude(pk=self.instance.pk)
                
                if existing_appointments.exists():
                    raise ValidationError(
                        'Já existe um agendamento neste horário para o profissional selecionado.'
                    )
        
        return cleaned_data

class AppointmentNoteForm(forms.ModelForm):
    class Meta:
        model = AppointmentNote
        fields = ['note']
        widgets = {
            'note': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Adicione uma nota...'})
        }

class AvailabilitySlotForm(forms.ModelForm):
    class Meta:
        model = AvailabilitySlot
        fields = ['weekday', 'start_time', 'end_time', 'is_active']
        widgets = {
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'weekday',
            Row(
                Column('start_time', css_class='col-md-6'),
                Column('end_time', css_class='col-md-6'),
            ),
            'is_active',
            FormActions(
                Submit('submit', 'Salvar Horário', css_class='btn btn-primary')
            )
        )
    
    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        
        if start_time and end_time:
            if end_time <= start_time:
                raise ValidationError('O horário de fim deve ser posterior ao de início.')
        
        return cleaned_data

class QuickAppointmentForm(forms.Form):
    """Simplified form for quick appointment creation"""
    customer = forms.ModelChoiceField(
        queryset=Customer.objects.filter(status__in=['active', 'prospect']),
        empty_label="Selecione um cliente"
    )
    appointment_type = forms.ModelChoiceField(
        queryset=AppointmentType.objects.all(),
        empty_label="Tipo de agendamento"
    )
    date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    time = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time'}))
    assigned_to = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True),
        empty_label="Responsável"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = 'form-inline'
        self.helper.layout = Layout(
            Row(
                Column('customer', css_class='col-md-3'),
                Column('appointment_type', css_class='col-md-2'),
                Column('date', css_class='col-md-2'),
                Column('time', css_class='col-md-2'),
                Column('assigned_to', css_class='col-md-2'),
                Column(
                    Submit('submit', 'Agendar', css_class='btn btn-primary'),
                    css_class='col-md-1'
                ),
            )
        )
