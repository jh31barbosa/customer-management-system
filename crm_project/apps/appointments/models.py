from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse
from apps.customers.models import Customer
import uuid

class AppointmentType(models.Model):
    """Different types of appointments"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    duration = models.DurationField(help_text='Duração padrão do agendamento')
    color = models.CharField(max_length=7, default='#007bff')
    price = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = 'Tipo de Agendamento'
        verbose_name_plural = 'Tipos de Agendamento'

class Appointment(models.Model):
    """Main appointment model"""
    STATUS_CHOICES = [
        ('scheduled', 'Agendado'),
        ('confirmed', 'Confirmado'),
        ('completed', 'Concluído'),
        ('cancelled', 'Cancelado'),
        ('no_show', 'Não Compareceu'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='appointments')
    appointment_type = models.ForeignKey(AppointmentType, on_delete=models.CASCADE)
    
    # Date and Time
    start_datetime = models.DateTimeField(verbose_name='Data/Hora de Início')
    end_datetime = models.DateTimeField(verbose_name='Data/Hora de Fim')
    
    # Assignment
    assigned_to = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='assigned_appointments',
        verbose_name='Responsável'
    )
    
    # Status and Details
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    title = models.CharField(max_length=200, verbose_name='Título')
    description = models.TextField(blank=True, verbose_name='Descrição')
    location = models.CharField(max_length=200, blank=True, verbose_name='Local')
    
    # Online Meeting
    meeting_url = models.URLField(blank=True, verbose_name='URL da Reunião')
    meeting_id = models.CharField(max_length=100, blank=True, verbose_name='ID da Reunião')
    
    # Notifications
    reminder_sent = models.BooleanField(default=False)
    confirmation_sent = models.BooleanField(default=False)
    
    # Calendar Integration
    google_calendar_event_id = models.CharField(max_length=255, blank=True)
    outlook_calendar_event_id = models.CharField(max_length=255, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.title} - {self.customer.name} ({self.start_datetime})"
    
    def get_absolute_url(self):
        return reverse('appointments:detail', kwargs={'pk': self.pk})
    
    @property
    def duration(self):
        """Calculate appointment duration"""
        return self.end_datetime - self.start_datetime
    
    def is_past(self):
        """Check if appointment is in the past"""
        return self.end_datetime < timezone.now()
    
    def is_today(self):
        """Check if appointment is today"""
        return self.start_datetime.date() == timezone.now().date()
    
    class Meta:
        verbose_name = 'Agendamento'
        verbose_name_plural = 'Agendamentos'
        ordering = ['start_datetime']