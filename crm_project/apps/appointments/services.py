import os
import json
from datetime import datetime, timedelta
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import requests

class CalendarService:
    """Service for calendar integrations"""
    
    def __init__(self):
        self.google_credentials = None
        self.outlook_credentials = None
    
    def get_google_calendar_service(self):
        """Get Google Calendar service"""
        if not settings.GOOGLE_CALENDAR_CLIENT_ID:
            return None
        
        # Load credentials from user settings or database
        # This is a simplified version - in production, store user credentials securely
        creds = None
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json')
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                # Need to implement OAuth flow for first-time setup
                return None
        
        return build('calendar', 'v3', credentials=creds)
    
    def create_appointment_event(self, appointment):
        """Create calendar event for appointment"""
        service = self.get_google_calendar_service()
        if not service:
            return
        
        event = {
            'summary': appointment.title,
            'description': f"Cliente: {appointment.customer.full_name}\n{appointment.description}",
            'start': {
                'dateTime': appointment.start_datetime.isoformat(),
                'timeZone': settings.TIME_ZONE,
            },
            'end': {
                'dateTime': appointment.end_datetime.isoformat(),
                'timeZone': settings.TIME_ZONE,
            },
            'attendees': [
                {'email': appointment.customer.email},
            ],
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60},  # 24 hours before
                    {'method': 'popup', 'minutes': 60},       # 1 hour before
                ],
            },
        }
        
        if appointment.location:
            event['location'] = appointment.location
        
        try:
            created_event = service.events().insert(calendarId='primary', body=event).execute()
            appointment.google_calendar_event_id = created_event['id']
            appointment.save(update_fields=['google_calendar_event_id'])
        except Exception as e:
            print(f"Error creating Google Calendar event: {e}")
    
    def update_appointment_event(self, appointment):
        """Update existing calendar event"""
        if not appointment.google_calendar_event_id:
            return self.create_appointment_event(appointment)
        
        service = self.get_google_calendar_service()
        if not service:
            return
        
        event = {
            'summary': appointment.title,
            'description': f"Cliente: {appointment.customer.full_name}\n{appointment.description}",
            'start': {
                'dateTime': appointment.start_datetime.isoformat(),
                'timeZone': settings.TIME_ZONE,
            },
            'end': {
                'dateTime': appointment.end_datetime.isoformat(),
                'timeZone': settings.TIME_ZONE,
            },
        }
        
        try:
            service.events().update(
                calendarId='primary',
                eventId=appointment.google_calendar_event_id,
                body=event
            ).execute()
        except Exception as e:
            print(f"Error updating Google Calendar event: {e}")
    
    def cancel_appointment_event(self, appointment):
        """Cancel/delete calendar event"""
        if not appointment.google_calendar_event_id:
            return
        
        service = self.get_google_calendar_service()
        if not service:
            return
        
        try:
            service.events().delete(
                calendarId='primary',
                eventId=appointment.google_calendar_event_id
            ).execute()
        except Exception as e:
            print(f"Error cancelling Google Calendar event: {e}")

class NotificationService:
    """Service for sending notifications"""
    
    def send_appointment_confirmation(self, appointment):
        """Send appointment confirmation email"""
        subject = f"Confirmação de Agendamento - {appointment.title}"
        
        context = {
            'appointment': appointment,
            'customer': appointment.customer,
        }
        
        html_message = render_to_string('emails/appointment_confirmation.html', context)
        plain_message = render_to_string('emails/appointment_confirmation.txt', context)
        
        try:
            send_mail(
                subject=subject,
                message=plain_message,
                html_message=html_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[appointment.customer.email],
                fail_silently=False,
            )
            appointment.confirmation_sent = True
            appointment.save(update_fields=['confirmation_sent'])
        except Exception as e:
            print(f"Error sending confirmation email: {e}")
    
    def send_appointment_reminder(self, appointment):
        """Send appointment reminder"""
        subject = f"Lembrete de Agendamento - {appointment.title}"
        
        context = {
            'appointment': appointment,
            'customer': appointment.customer,
        }
        
        html_message = render_to_string('emails/appointment_reminder.html', context)
        plain_message = render_to_string('emails/appointment_reminder.txt', context)
        
        try:
            send_mail(
                subject=subject,
                message=plain_message,
                html_message=html_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[appointment.customer.email],
                fail_silently=False,
            )
            appointment.reminder_sent = True
            appointment.save(update_fields=['reminder_sent'])
        except Exception as e:
            print(f"Error sending reminder email: {e}")
    
    def send_appointment_cancellation(self, appointment):
        """Send appointment cancellation notification"""
        subject = f"Agendamento Cancelado - {appointment.title}"
        
        context = {
            'appointment': appointment,
            'customer': appointment.customer,
        }
        
        html_message = render_to_string('emails/appointment_cancellation.html', context)
        plain_message = render_to_string('emails/appointment_cancellation.txt', context)
        
        try:
            send_mail(
                subject=subject,
                message=plain_message,
                html_message=html_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[appointment.customer.email],
                fail_silently=False,
            )
        except Exception as e:
            print(f"Error sending cancellation email: {e}")
    
    def send_sms_reminder(self, appointment):
        """Send SMS reminder using Twilio"""
        if not settings.TWILIO_ACCOUNT_SID or not appointment.customer.phone:
            return
        
        from twilio.rest import Client
        
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        
        message_body = f"""
        Lembrete: Você tem um agendamento marcado para {appointment.start_datetime.strftime('%d/%m/%Y às %H:%M')}.
        
        {appointment.title}
        Local: {appointment.location or 'A definir'}
        
        Para reagendar ou cancelar, entre em contato conosco.
        """
        
        try:
            client.messages.create(
                body=message_body.strip(),
                from_=settings.TWILIO_PHONE_NUMBER,
                to=appointment.customer.phone
            )
        except Exception as e:
            print(f"Error sending SMS: {e}")

            at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Additional Information
    notes = models.TextField(blank=True, verbose_name='Observações')
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def get_absolute_url(self):
        return reverse('customers:detail', kwargs={'pk': self.pk})
    
    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering = ['-created_at']

class CustomerInteraction(models.Model):
    """Track all customer interactions"""
    INTERACTION_TYPES = [
        ('email', 'Email'),
        ('phone', 'Telefone'),
        ('meeting', 'Reunião'),
        ('note', 'Nota'),
        ('purchase', 'Compra'),
        ('support', 'Suporte'),
    ]
    
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='interactions')
    interaction_type = models.CharField(max_length=20, choices=INTERACTION_TYPES)
    subject = models.CharField(max_length=200)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    
    def __str__(self):
        return f"{self.customer.full_name} - {self.subject}"
    
    class Meta:
        verbose_name = 'Interação com Cliente'
        verbose_name_plural = 'Interações com Clientes'
        ordering = ['-created_at']

class Purchase(models.Model):
    """Customer purchase history"""
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='purchases')
    product_service = models.CharField(max_length=200, verbose_name='Produto/Serviço')
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Valor')
    purchase_date = models.DateTimeField(default=timezone.now, verbose_name='Data da Compra')
    description = models.TextField(blank=True, verbose_name='Descrição')
    
    def __str__(self):
        return f"{self.customer.full_name} - {self.product_service}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update customer total revenue
        self.customer.total_revenue = self.customer.purchases.aggregate(
            total=models.Sum('amount')
        )['total'] or 0
        self.customer.save()
    
    class Meta:
        verbose_name = 'Compra'
        verbose_name_plural = 'Compras'
        ordering = ['-purchase_date']
