from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Q, Sum, Count
from django.http import JsonResponse, HttpResponse
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.core.paginator import Paginator
import csv
from datetime import datetime, timedelta

from .models import Customer, CustomerSegment, CustomerInteraction, Purchase
from .forms import CustomerForm, CustomerInteractionForm, PurchaseForm

class CustomerListView(LoginRequiredMixin, ListView):
    model = Customer
    template_name = 'customers/customer_list.html'
    context_object_name = 'customers'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Customer.objects.select_related('segment', 'created_by')
        
        # Search functionality
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search) |
                Q(company__icontains=search)
            )
        
        # Filter by segment
        segment = self.request.GET.get('segment')
        if segment:
            queryset = queryset.filter(segment_id=segment)
        
        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['segments'] = CustomerSegment.objects.all()
        context['status_choices'] = Customer.STATUS_CHOICES
        context['search'] = self.request.GET.get('search', '')
        context['selected_segment'] = self.request.GET.get('segment', '')
        context['selected_status'] = self.request.GET.get('status', '')
        return context

class CustomerDetailView(LoginRequiredMixin, DetailView):
    model = Customer
    template_name = 'customers/customer_detail.html'
    context_object_name = 'customer'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        customer = self.get_object()
        
        # Get recent interactions
        context['recent_interactions'] = customer.interactions.all()[:10]
        
        # Get purchase history
        context['purchases'] = customer.purchases.all()[:10]
        
        # Calculate statistics
        context['total_purchases'] = customer.purchases.count()
        context['total_revenue'] = customer.total_revenue
        context['last_interaction'] = customer.interactions.first()
        
        return context

class CustomerCreateView(LoginRequiredMixin, CreateView):
    model = Customer
    form_class = CustomerForm
    template_name = 'customers/customer_form.html'
    success_url = reverse_lazy('customers:list')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Cliente criado com sucesso!')
        return super().form_valid(form)

class CustomerUpdateView(LoginRequiredMixin, UpdateView):
    model = Customer
    form_class = CustomerForm
    template_name = 'customers/customer_form.html'
    
    def form_valid(self, form):
        messages.success(self.request, 'Cliente atualizado com sucesso!')
        return super().form_valid(form)

class CustomerDeleteView(LoginRequiredMixin, DeleteView):
    model = Customer
    template_name = 'customers/customer_confirm_delete.html'
    success_url = reverse_lazy('customers:list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Cliente excluído com sucesso!')
        return super().delete(request, *args, **kwargs)

@login_required
def add_interaction(request, customer_id):
    customer = get_object_or_404(Customer, id=customer_id)
    
    if request.method == 'POST':
        form = CustomerInteractionForm(request.POST)
        if form.is_valid():
            interaction = form.save(commit=False)
            interaction.customer = customer
            interaction.created_by = request.user
            interaction.save()
            messages.success(request, 'Interação adicionada com sucesso!')
            return redirect('customers:detail', pk=customer_id)
    else:
        form = CustomerInteractionForm()
    
    return render(request, 'customers/add_interaction.html', {
        'form': form,
        'customer': customer
    })

@login_required
def add_purchase(request, customer_id):
    customer = get_object_or_404(Customer, id=customer_id)
    
    if request.method == 'POST':
        form = PurchaseForm(request.POST)
        if form.is_valid():
            purchase = form.save(commit=False)
            purchase.customer = customer
            purchase.save()
            messages.success(request, 'Compra adicionada com sucesso!')
            return redirect('customers:detail', pk=customer_id)
    else:
        form = PurchaseForm()
    
    return render(request, 'customers/add_purchase.html', {
        'form': form,
        'customer': customer
    })

@login_required
def export_customers(request):
    """Export customers to CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="customers.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Nome', 'Email', 'Telefone', 'Empresa', 'Segmento', 
        'Status', 'Receita Total', 'Data de Criação'
    ])
    
    customers = Customer.objects.select_related('segment').all()
    for customer in customers:
        writer.writerow([
            customer.full_name,
            customer.email,
            customer.phone,
            customer.company,
            customer.segment.name if customer.segment else '',
            customer.get_status_display(),
            customer.total_revenue,
            customer.created_at.strftime('%d/%m/%Y')
        ])
    
    return response

@login_required
def customer_stats_api(request):
    """API endpoint for customer statistics"""
    stats = {
        'total_customers': Customer.objects.count(),
        'active_customers': Customer.objects.filter(status='active').count(),
        'prospects': Customer.objects.filter(status='prospect').count(),
        'total_revenue': Customer.objects.aggregate(
            total=Sum('total_revenue')
        )['total'] or 0,
        'customers_by_segment': list(
            CustomerSegment.objects.annotate(
                count=Count('customer')
            ).values('name', 'count', 'color')
        ),
        'recent_customers': Customer.objects.filter(
            created_at__gte=timezone.now() - timedelta(days=30)
        ).count(),
    }
    
    return JsonResponse(stats)
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Q, Sum, Count
from django.http import JsonResponse, HttpResponse
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.core.paginator import Paginator
import csv
from datetime import datetime, timedelta

from .models import Customer, CustomerSegment, CustomerInteraction, Purchase
from .forms import CustomerForm, CustomerInteractionForm, PurchaseForm

class CustomerListView(LoginRequiredMixin, ListView):
    model = Customer
    template_name = 'customers/customer_list.html'
    context_object_name = 'customers'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Customer.objects.select_related('segment', 'created_by')
        
        # Search functionality
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search) |
                Q(company__icontains=search)
            )
        
        # Filter by segment
        segment = self.request.GET.get('segment')
        if segment:
            queryset = queryset.filter(segment_id=segment)
        
        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['segments'] = CustomerSegment.objects.all()
        context['status_choices'] = Customer.STATUS_CHOICES
        context['search'] = self.request.GET.get('search', '')
        context['selected_segment'] = self.request.GET.get('segment', '')
        context['selected_status'] = self.request.GET.get('status', '')
        return context

class CustomerDetailView(LoginRequiredMixin, DetailView):
    model = Customer
    template_name = 'customers/customer_detail.html'
    context_object_name = 'customer'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        customer = self.get_object()
        
        # Get recent interactions
        context['recent_interactions'] = customer.interactions.all()[:10]
        
        # Get purchase history
        context['purchases'] = customer.purchases.all()[:10]
        
        # Calculate statistics
        context['total_purchases'] = customer.purchases.count()
        context['total_revenue'] = customer.total_revenue
        context['last_interaction'] = customer.interactions.first()
        
        return context

class CustomerCreateView(LoginRequiredMixin, CreateView):
    model = Customer
    form_class = CustomerForm
    template_name = 'customers/customer_form.html'
    success_url = reverse_lazy('customers:list')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Cliente criado com sucesso!')
        return super().form_valid(form)

class CustomerUpdateView(LoginRequiredMixin, UpdateView):
    model = Customer
    form_class = CustomerForm
    template_name = 'customers/customer_form.html'
    
    def form_valid(self, form):
        messages.success(self.request, 'Cliente atualizado com sucesso!')
        return super().form_valid(form)

class CustomerDeleteView(LoginRequiredMixin, DeleteView):
    model = Customer
    template_name = 'customers/customer_confirm_delete.html'
    success_url = reverse_lazy('customers:list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Cliente excluído com sucesso!')
        return super().delete(request, *args, **kwargs)

@login_required
def add_interaction(request, customer_id):
    customer = get_object_or_404(Customer, id=customer_id)
    
    if request.method == 'POST':
        form = CustomerInteractionForm(request.POST)
        if form.is_valid():
            interaction = form.save(commit=False)
            interaction.customer = customer
            interaction.created_by = request.user
            interaction.save()
            messages.success(request, 'Interação adicionada com sucesso!')
            return redirect('customers:detail', pk=customer_id)
    else:
        form = CustomerInteractionForm()
    
    return render(request, 'customers/add_interaction.html', {
        'form': form,
        'customer': customer
    })

@login_required
def add_purchase(request, customer_id):
    customer = get_object_or_404(Customer, id=customer_id)
    
    if request.method == 'POST':
        form = PurchaseForm(request.POST)
        if form.is_valid():
            purchase = form.save(commit=False)
            purchase.customer = customer
            purchase.save()
            messages.success(request, 'Compra adicionada com sucesso!')
            return redirect('customers:detail', pk=customer_id)
    else:
        form = PurchaseForm()
    
    return render(request, 'customers/add_purchase.html', {
        'form': form,
        'customer': customer
    })

@login_required
def export_customers(request):
    """Export customers to CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="customers.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Nome', 'Email', 'Telefone', 'Empresa', 'Segmento', 
        'Status', 'Receita Total', 'Data de Criação'
    ])
    
    customers = Customer.objects.select_related('segment').all()
    for customer in customers:
        writer.writerow([
            customer.full_name,
            customer.email,
            customer.phone,
            customer.company,
            customer.segment.name if customer.segment else '',
            customer.get_status_display(),
            customer.total_revenue,
            customer.created_at.strftime('%d/%m/%Y')
        ])
    
    return response

@login_required
def customer_stats_api(request):
    """API endpoint for customer statistics"""
    stats = {
        'total_customers': Customer.objects.count(),
        'active_customers': Customer.objects.filter(status='active').count(),
        'prospects': Customer.objects.filter(status='prospect').count(),
        'total_revenue': Customer.objects.aggregate(
            total=Sum('total_revenue')
        )['total'] or 0,
        'customers_by_segment': list(
            CustomerSegment.objects.annotate(
                count=Count('customer')
            ).values('name', 'count', 'color')
        ),
        'recent_customers': Customer.objects.filter(
            created_at__gte=timezone.now() - timedelta(days=30)
        ).count(),
    }
    
    return JsonResponse(stats)
