from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
import uuid

class CustomerSegment(models.Model):
    """Customer segmentation categories"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#007bff')  # Hex color
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = 'Segmento de Cliente'
        verbose_name_plural = 'Segmentos de Clientes'

class Customer(models.Model):
    """Main customer model"""
    STATUS_CHOICES = [
        ('active', 'Ativo'),
        ('inactive', 'Inativo'),
        ('prospect', 'Prospect'),
        ('lost', 'Perdido'),
    ]
    
    # Basic Information
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    first_name = models.CharField(max_length=100, verbose_name='Nome')
    last_name = models.CharField(max_length=100, verbose_name='Sobrenome')
    email = models.EmailField(unique=True, verbose_name='Email')
    phone = models.CharField(max_length=20, blank=True, verbose_name='Telefone')
    
    # Address Information
    address = models.TextField(blank=True, verbose_name='Endereço')
    city = models.CharField(max_length=100, blank=True, verbose_name='Cidade')
    state = models.CharField(max_length=50, blank=True, verbose_name='Estado')
    postal_code = models.CharField(max_length=20, blank=True, verbose_name='CEP')
    country = models.CharField(max_length=100, default='Brasil', verbose_name='País')
    
    # Business Information
    company = models.CharField(max_length=200, blank=True, verbose_name='Empresa')
    position = models.CharField(max_length=100, blank=True, verbose_name='Cargo')
    segment = models.ForeignKey(CustomerSegment, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='prospect')
    
    # Financial Information
    total_revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='created_appointments'
    )
    
    # Notes and Follow-up
    notes = models.TextField(blank=True, verbose_name='Observações')
    follow_up_required = models.BooleanField(default=False, verbose_name='Requer Follow-up')
    
    def __str__(self):
        return f"{self.title} - {self.customer.full_name} ({self.start_datetime.strftime('%d/%m/%Y %H:%M')})"
    
    @property
    def duration(self):
        return self.end_datetime - self.start_datetime
    
    @property
    def is_past(self):
        return self.end_datetime < timezone.now()
    
    @property
    def is_today(self):
        today = timezone.now().date()
        return self.start_datetime.date() == today
    
    def get_absolute_url(self):
        return reverse('appointments:detail', kwargs={'pk': self.pk})
    
    def can_be_cancelled(self):
        """Check if appointment can still be cancelled"""
        return self.status in ['scheduled', 'confirmed'] and not self.is_past
    
    class Meta:
        verbose_name = 'Agendamento'
        verbose_name_plural = 'Agendamentos'
        ordering = ['start_datetime']

class AppointmentNote(models.Model):
    """Notes added to appointments"""
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name='appointment_notes')
    note = models.TextField(verbose_name='Nota')
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    
    def __str__(self):
        return f"Nota para {self.appointment.title}"
    
    class Meta:
        verbose_name = 'Nota do Agendamento'
        verbose_name_plural = 'Notas dos Agendamentos'
        ordering = ['-created_at']

class AvailabilitySlot(models.Model):
    """Define available time slots for appointments"""
    WEEKDAY_CHOICES = [
        (0, 'Segunda-feira'),
        (1, 'Terça-feira'),
        (2, 'Quarta-feira'),
        (3, 'Quinta-feira'),
        (4, 'Sexta-feira'),
        (5, 'Sábado'),
        (6, 'Domingo'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='availability_slots')
    weekday = models.IntegerField(choices=WEEKDAY_CHOICES)
    start_time = models.TimeField(verbose_name='Hora de Início')
    end_time = models.TimeField(verbose_name='Hora de Fim')
    is_active = models.BooleanField(default=True, verbose_name='Ativo')
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.get_weekday_display()} ({self.start_time}-{self.end_time})"
    
    class Meta:
        verbose_name = 'Horário Disponível'
        verbose_name_plural = 'Horários Disponíveis'
        unique_together = ['user', 'weekday', 'start_time']
