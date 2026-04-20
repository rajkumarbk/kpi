from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django import forms
from .forms import TransactionForm, LoginForm
from .models import Transaction, VehicleModel, Branch, CustomerTypeMaster
from django.http import JsonResponse
from django.db.models import Count, Q, Sum, Avg
from django.utils import timezone
import json
from django.core.paginator import Paginator
from datetime import timedelta, datetime
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import UserCreationForm

def check_admin(user):
    return user.is_authenticated and hasattr(user, 'userprofile') and user.userprofile.role == 'admin'

def admin_required(view_func):
    decorated_view = user_passes_test(check_admin, login_url='core:login')(view_func)
    return decorated_view

def login_view(request):
    if request.user.is_authenticated:
        try:
            if request.user.userprofile.role == 'admin':
                return redirect('core:dashboard')
            else:
                return redirect('core:add_transaction')
        except:
            return redirect('core:add_transaction')
    
    error = None
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            try:
                if user.userprofile.role == 'admin':
                    return redirect('core:dashboard')
                else:
                    return redirect('core:add_transaction')
            except:
                return redirect('core:add_transaction')
        else:
            error = "Invalid username or password"
    
    return render(request, 'registration/login.html', {'error': error})

def logout_view(request):
    logout(request)
    return redirect('core:login')

@login_required
def create_transaction(request):
    if request.method == 'POST':
        form = TransactionForm(request.POST, request.FILES)
        if form.is_valid():
            transaction = form.save(commit=False)
            # Auto-set branch for non-admin users
            if request.user.userprofile.role != 'admin':
                transaction.branch = request.user.userprofile.branch
            transaction.save()
            messages.success(request, 'Transaction recorded successfully!')
            return redirect('core:transaction_list')
    else:
        form = TransactionForm()
        # Hide branch field for non-admin users
        if request.user.userprofile.role != 'admin':
            form.fields['branch'].widget = forms.HiddenInput()
            form.fields['branch'].initial = request.user.userprofile.branch
    
    return render(request, 'core/transaction_form.html', {'form': form})

@admin_required
@login_required
def dashboard(request):
    # Overall stats
    total = Transaction.objects.count()
    success_count = Transaction.objects.filter(outcome='success').count()
    fail_count = Transaction.objects.filter(outcome='fail').count()

    # Success/Fail pie chart data
    pie_data = {
        'labels': ['Success', 'Fail'],
        'data': [success_count, fail_count],
    }

    # Reasons distribution (for fail cases)
    reason_counts = Transaction.objects.filter(outcome='fail').values('reason__name').annotate(count=Count('id')).order_by('-count')
    reason_labels = [item['reason__name'] or 'Unknown' for item in reason_counts]
    reason_data = [item['count'] for item in reason_counts]

    # Branch performance
    branch_stats = Transaction.objects.values('branch__code').annotate(
        total=Count('id'),
        success=Count('id', filter=Q(outcome='success')),
        fail=Count('id', filter=Q(outcome='fail')),
        revenue=Sum('price', filter=Q(outcome='success'))
    ).order_by('branch__code')

    # Customer type distribution
    customer_type_counts = Transaction.objects.values('customer_type__name').annotate(count=Count('id'))

    context = {
        'total': total,
        'success_count': success_count,
        'fail_count': fail_count,
        'pie_data': json.dumps(pie_data),
        'reason_labels': json.dumps(reason_labels),
        'reason_data': json.dumps(reason_data),
        'branch_stats': branch_stats,
        'customer_type_counts': customer_type_counts,
    }
    return render(request, 'core/dashboard.html', context)

def load_models(request):
    brand_id = request.GET.get('brand')
    models = VehicleModel.objects.filter(brand_id=brand_id).order_by('name')
    return JsonResponse(list(models.values('id', 'name')), safe=False)

@login_required
def transaction_list(request):
    if request.user.userprofile.role == 'admin':
        transactions = Transaction.objects.all()
    else:
        transactions = Transaction.objects.filter(branch=request.user.userprofile.branch)
    
    
    # Apply filters
    branch = request.GET.get('branch')
    customer_type = request.GET.get('customer_type')
    outcome = request.GET.get('outcome')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if branch and request.user.userprofile.role == 'admin':
        transactions = transactions.filter(branch_id=branch)
    if customer_type:
        transactions = transactions.filter(customer_type_id=customer_type)
    if outcome:
        transactions = transactions.filter(outcome=outcome)
    if date_from:
        transactions = transactions.filter(created_at__date__gte=date_from)
    if date_to:
        transactions = transactions.filter(created_at__date__lte=date_to)
    
    transactions = transactions.order_by('-created_at')
    
    # Calculate stats
    total_count = transactions.count()
    total_revenue = transactions.filter(outcome='success').aggregate(total=Sum('price'))['total'] or 0
    success_count = transactions.filter(outcome='success').count()
    success_rate = round((success_count / total_count * 100) if total_count > 0 else 0, 1)
    fail_count = transactions.filter(outcome='fail').count()
    fail_rate = round((fail_count / total_count * 100) if total_count > 0 else 0, 1)
    avg_transaction = total_revenue / success_count if success_count > 0 else 0
    
    # Pagination
    paginator = Paginator(transactions, 20)
    page = request.GET.get('page')
    transactions = paginator.get_page(page)
    
    context = {
        'transactions': transactions,
        'total_count': total_count,
        'total_revenue': total_revenue,
        'success_rate': success_rate,
        'fail_rate': fail_rate,
        'avg_transaction': avg_transaction,
        'branches': Branch.objects.all(),
        'customer_types': CustomerTypeMaster.objects.all(),
    }
    return render(request, 'core/transaction_list.html', context)

@login_required
def transaction_detail(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk)
    return render(request, 'core/transaction_detail.html', {'transaction': transaction})

@login_required
@admin_required
def dashboard(request):
    # Date range logic
    date_range = request.GET.get('date_range', 'this_month')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    selected_branch = request.GET.get('branch', '')
    
    today = timezone.now().date()
    
    if date_range == 'today':
        date_from = date_to = today
    elif date_range == 'yesterday':
        date_from = date_to = today - timedelta(days=1)
    elif date_range == 'this_week':
        date_from = today - timedelta(days=today.weekday())
        date_to = today
    elif date_range == 'last_week':
        date_from = today - timedelta(days=today.weekday() + 7)
        date_to = date_from + timedelta(days=6)
    elif date_range == 'this_month':
        date_from = today.replace(day=1)
        date_to = today
    elif date_range == 'last_month':
        first_of_month = today.replace(day=1)
        date_to = first_of_month - timedelta(days=1)
        date_from = date_to.replace(day=1)
    elif date_range == 'this_year':
        date_from = today.replace(month=1, day=1)
        date_to = today
    elif date_range == 'custom' and date_from and date_to:
        date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
        date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
    else:
        date_from = today - timedelta(days=30)
        date_to = today
    
    # Filter transactions by date
    transactions = Transaction.objects.filter(created_at__date__gte=date_from, created_at__date__lte=date_to)
    if selected_branch:
        transactions = transactions.filter(branch_id=selected_branch)
    
    # Previous period for trend
    period_days = (date_to - date_from).days
    prev_date_from = date_from - timedelta(days=period_days)
    prev_date_to = date_from - timedelta(days=1)
    prev_transactions = Transaction.objects.filter(created_at__date__gte=prev_date_from, created_at__date__lte=prev_date_to)
    if selected_branch:
        prev_transactions = prev_transactions.filter(branch_id=selected_branch)
    # Calculate trends
    current_total = transactions.count()
    prev_total = prev_transactions.count()
    trend_total = round(((current_total - prev_total) / prev_total * 100) if prev_total > 0 else 0, 1)
    
    # Dashboard data
    total = current_total
    success_count = transactions.filter(outcome='success').count()
    fail_count = transactions.filter(outcome='fail').count()
    success_rate = round((success_count / total * 100) if total > 0 else 0, 1)
    fail_rate = round((fail_count / total * 100) if total > 0 else 0, 1)
    total_revenue = transactions.filter(outcome='success').aggregate(total=Sum('price'))['total'] or 0
    avg_value = total_revenue / success_count if success_count > 0 else 0
    
    # Pie chart data
    pie_data = {
        'labels': ['Success', 'Fail'],
        'data': [success_count, fail_count],
    }
    
    # Daily trend data
    daily_data = []
    daily_labels = []
    current_date = date_from
    while current_date <= date_to:
        day_transactions = transactions.filter(created_at__date=current_date).count()
        daily_labels.append(current_date.strftime('%d %b'))
        daily_data.append(day_transactions)
        current_date += timedelta(days=1)
    
    # Branch performance
    branch_stats = transactions.values('branch__code').annotate(
        total=Count('id'),
        success=Count('id', filter=Q(outcome='success')),
        fail=Count('id', filter=Q(outcome='fail')),
        revenue=Sum('price', filter=Q(outcome='success'))
    ).order_by('branch__code')
    
    branch_labels = [stat['branch__code'] for stat in branch_stats]
    branch_data = [stat['total'] for stat in branch_stats]
    
    # Customer type distribution
    customer_type_stats = transactions.values('customer_type__name').annotate(count=Count('id'))
    customer_type_labels = [stat['customer_type__name'] for stat in customer_type_stats]
    customer_type_data = [stat['count'] for stat in customer_type_stats]
    
    # Failure reasons
    reason_counts = transactions.filter(outcome='fail').values('reason__name').annotate(count=Count('id')).order_by('-count')[:5]
    reason_labels = [item['reason__name'] or 'Unknown' for item in reason_counts]
    reason_data = [item['count'] for item in reason_counts]
    
    # Recent transactions
    recent_transactions = transactions.order_by('-created_at')[:5]
    
    context = {
        'date_range': date_range,
        'date_from': date_from.strftime('%Y-%m-%d') if date_from else '',
        'date_to': date_to.strftime('%Y-%m-%d') if date_to else '',
        'total': total,
        'success_count': success_count,
        'fail_count': fail_count,
        'success_rate': success_rate,
        'fail_rate': fail_rate,
        'total_revenue': total_revenue,
        'avg_value': avg_value,
        'trend': {'total': trend_total},
        'pie_data': json.dumps(pie_data),
        'trend_labels': json.dumps(daily_labels),
        'trend_data': json.dumps(daily_data),
        'branch_labels': json.dumps(branch_labels),
        'branch_data': json.dumps(branch_data),
        'customer_type_labels': json.dumps(customer_type_labels),
        'customer_type_data': json.dumps(customer_type_data),
        'reason_labels': json.dumps(reason_labels),
        'reason_data': json.dumps(reason_data),
        'branch_stats': branch_stats,
        'recent_transactions': recent_transactions,
        'selected_branch': selected_branch,
        'branches': Branch.objects.all().order_by('code'),
    }
    return render(request, 'core/dashboard.html', context)