from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Q, Count
from django.http import JsonResponse, HttpResponse
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.utils import timezone
from datetime import datetime, timedelta, time
import json

from .models import Appointment, AppointmentType, AppointmentNote, AvailabilitySlot
from .forms import AppointmentForm, AppointmentNoteForm, AvailabilitySlotForm
from apps.customers.models import Customer
from .services import CalendarService, NotificationService

class AppointmentListView(LoginRequiredMixin, ListView):
    model = Appointment
    template_name = 'appointments/appointment_list.html'
    context_object_name = 'appointments'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Appointment.objects.select_related(
            'customer', 'appointment_type', 'assigned_to'
        )
        
        # Filter by date range
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        
        if date_from:
            queryset = queryset.filter(start_datetime__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(start_datetime__date__lte=date_to)
        
        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Filter by assigned user
        assigned_to = self.request.GET.get('assigned_to')
        if assigned_to:
            queryset = queryset.filter(assigned_to_id=assigned_to)
        
        # Search functionality
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(customer__first_name__icontains=search) |
                Q(customer__last_name__icontains=search) |
                Q(customer__email__icontains=search)
            )
        
        return queryset.order_by('start_datetime')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = Appointment.STATUS_CHOICES
        context['appointment_types'] = AppointmentType.objects.all()
        from django.contrib.auth.models import User
        context['users'] = User.objects.filter(is_active=True)
        return context

class AppointmentCalendarView(LoginRequiredMixin, ListView):
    model = Appointment
    template_name = 'appointments/calendar.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['appointment_types'] = AppointmentType.objects.all()
        return context

class AppointmentDetailView(LoginRequiredMixin, DetailView):
    model = Appointment
    template_name = 'appointments/appointment_detail.html'
    context_object_name = 'appointment'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        appointment = self.get_object()
        context['notes'] = appointment.appointment_notes.all()
        context['note_form'] = AppointmentNoteForm()
        return context

class AppointmentCreateView(LoginRequiredMixin, CreateView):
    model = Appointment
    form_class = AppointmentForm
    template_name = 'appointments/appointment_form.html'
    success_url = reverse_lazy('appointments:list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        
        # Create calendar event
        calendar_service = CalendarService()
        calendar_service.create_appointment_event(self.object)
        
        # Send confirmation
        notification_service = NotificationService()
        notification_service.send_appointment_confirmation(self.object)
        
        messages.success(self.request, 'Agendamento criado com sucesso!')
        return response

class AppointmentUpdateView(LoginRequiredMixin, UpdateView):
    model = Appointment
    form_class = AppointmentForm
    template_name = 'appointments/appointment_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Update calendar event
        calendar_service = CalendarService()
        calendar_service.update_appointment_event(self.object)
        
        messages.success(self.request, 'Agendamento atualizado com sucesso!')
        return response

@login_required
def cancel_appointment(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk)
    
    if not appointment.can_be_cancelled():
        messages.error(request, 'Este agendamento não pode ser cancelado.')
        return redirect('appointments:detail', pk=pk)
    
    if request.method == 'POST':
        appointment.status = 'cancelled'
        appointment.save()
        
        # Cancel calendar event
        calendar_service = CalendarService()
        calendar_service.cancel_appointment_event(appointment)
        
        # Send cancellation notification
        notification_service = NotificationService()
        notification_service.send_appointment_cancellation(appointment)
        
        messages.success(request, 'Agendamento cancelado com sucesso!')
        return redirect('appointments:list')
    
    return render(request, 'appointments/cancel_appointment.html', {
        'appointment': appointment
    })

@login_required
def add_appointment_note(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk)
    
    if request.method == 'POST':
        form = AppointmentNoteForm(request.POST)
        if form.is_valid():
            note = form.save(commit=False)
            note.appointment = appointment
            note.created_by = request.user
            note.save()
            messages.success(request, 'Nota adicionada com sucesso!')
            return redirect('appointments:detail', pk=pk)
    
    return redirect('appointments:detail', pk=pk)

@login_required
def appointment_calendar_data(request):
    """API endpoint for calendar data"""
    start_date = request.GET.get('start')
    end_date = request.GET.get('end')
    
    appointments = Appointment.objects.filter(
        start_datetime__date__gte=start_date,
        start_datetime__date__lte=end_date
    ).select_related('customer', 'appointment_type', 'assigned_to')
    
    events = []
    for appointment in appointments:
        color = appointment.appointment_type.color
        if appointment.status == 'cancelled':
            color = '#dc3545'  # Red for cancelled
        elif appointment.status == 'completed':
            color = '#28a745'  # Green for completed
        
        events.append({
            'id': str(appointment.id),
            'title': f"{appointment.title} - {appointment.customer.full_name}",
            'start': appointment.start_datetime.isoformat(),
            'end': appointment.end_datetime.isoformat(),
            'backgroundColor': color,
            'borderColor': color,
            'url': appointment.get_absolute_url(),
            'extendedProps': {
                'customer': appointment.customer.full_name,
                'status': appointment.get_status_display(),
                'assigned_to': appointment.assigned_to.get_full_name(),
                'description': appointment.description,
            }
        })
    
    return JsonResponse(events, safe=False)

@login_required
def available_slots(request):
    """API endpoint for available time slots"""
    date = request.GET.get('date')
    user_id = request.GET.get('user_id')
    
    if not date or not user_id:
        return JsonResponse({'error': 'Date and user_id are required'}, status=400)
    
    try:
        selected_date = datetime.strptime(date, '%Y-%m-%d').date()
        weekday = selected_date.weekday()
        
        # Get availability slots for the user and weekday
        availability_slots = AvailabilitySlot.objects.filter(
            user_id=user_id,
            weekday=weekday,
            is_active=True
        )
        
        # Get existing appointments for that date and user
        existing_appointments = Appointment.objects.filter(
            assigned_to_id=user_id,
            start_datetime__date=selected_date,
            status__in=['scheduled', 'confirmed']
        )
        
        available_slots = []
        for slot in availability_slots:
            current_time = datetime.combine(selected_date, slot.start_time)
            end_time = datetime.combine(selected_date, slot.end_time)
            
            while current_time < end_time:
                slot_end = current_time + timedelta(hours=1)  # 1-hour slots
                
                # Check if this slot conflicts with existing appointments
                conflict = existing_appointments.filter(
                    start_datetime__lt=slot_end,
                    end_datetime__gt=current_time
                ).exists()
                
                if not conflict:
                    available_slots.append({
                        'start': current_time.strftime('%H:%M'),
                        'end': slot_end.strftime('%H:%M'),
                        'datetime': current_time.isoformat()
                    })
                
                current_time = slot_end
        
        return JsonResponse({'slots': available_slots})
        
    except ValueError:
        return JsonResponse({'error': 'Invalid date format'}, status=400)

@login_required
def appointment_stats(request):
    """API endpoint for appointment statistics"""
    today = timezone.now().date()
    this_week_start = today - timedelta(days=today.weekday())
    this_month_start = today.replace(day=1)
    
    stats = {
        'today': {
            'total': Appointment.objects.filter(start_datetime__date=today).count(),
            'completed': Appointment.objects.filter(
                start_datetime__date=today, 
                status='completed'
            ).count(),
            'cancelled': Appointment.objects.filter(
                start_datetime__date=today, 
                status='cancelled'
            ).count(),
        },
        'this_week': {
            'total': Appointment.objects.filter(
                start_datetime__date__gte=this_week_start,
                start_datetime__date__lte=today
            ).count(),
        },
        'this_month': {
            'total': Appointment.objects.filter(
                start_datetime__date__gte=this_month_start
            ).count(),
        },
        'by_status': list(
            Appointment.objects.filter(
                start_datetime__date__gte=this_month_start
            ).values('status').annotate(count=Count('id'))
        ),
        'no_show_rate': 0,  # Calculate based on your business logic
    }
    
    # Calculate no-show rate
    total_past = Appointment.objects.filter(
        end_datetime__lt=timezone.now()
    ).count()
    
    no_shows = Appointment.objects.filter(
        end_datetime__lt=timezone.now(),
        status='no_show'
    ).count()
    
    if total_past > 0:
        stats['no_show_rate'] = round((no_shows / total_past) * 100, 2)
    
    return JsonResponse(stats)

