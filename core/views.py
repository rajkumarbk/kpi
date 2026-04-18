from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .forms import TransactionForm
from .models import Transaction, VehicleModel, Branch, CustomerTypeMaster
from django.http import JsonResponse
from django.db.models import Count, Q, Sum, Avg
from django.utils import timezone
import json
from django.core.paginator import Paginator
from datetime import timedelta, datetime

def create_transaction(request):
    if request.method == 'POST':
        form = TransactionForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Transaction recorded successfully!')
            return redirect('core:dashboard')
    else:
        form = TransactionForm()
    return render(request, 'core/transaction_form.html', {'form': form})

def load_models(request):
    """AJAX endpoint to get models for selected brand"""
    brand_id = request.GET.get('brand')
    models = VehicleModel.objects.filter(brand_id=brand_id).order_by('name')
    return JsonResponse(list(models.values('id', 'name')), safe=False)

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

def transaction_list(request):
    transactions = Transaction.objects.all().order_by('-created_at')
    
    # Apply filters
    branch = request.GET.get('branch')
    customer_type = request.GET.get('customer_type')
    outcome = request.GET.get('outcome')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if branch:
        transactions = transactions.filter(branch_id=branch)
    if customer_type:
        transactions = transactions.filter(customer_type_id=customer_type)
    if outcome:
        transactions = transactions.filter(outcome=outcome)
    if date_from:
        transactions = transactions.filter(created_at__date__gte=date_from)
    if date_to:
        transactions = transactions.filter(created_at__date__lte=date_to)
    
    # Calculate stats
    total_count = transactions.count()
    total_revenue = transactions.filter(outcome='success').aggregate(total=Sum('price'))['total'] or 0
    success_count = transactions.filter(outcome='success').count()
    success_rate = round((success_count / total_count * 100) if total_count > 0 else 0, 1)
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
        'avg_transaction': avg_transaction,
        'branches': Branch.objects.all(),
        'customer_types': CustomerTypeMaster.objects.all(),
    }
    return render(request, 'core/transaction_list.html', context)

def transaction_detail(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk)
    return render(request, 'core/transaction_detail.html', {'transaction': transaction})

def dashboard(request):
    # Date range logic
    date_range = request.GET.get('date_range', 'this_month')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
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
    
    # Previous period for trend
    period_days = (date_to - date_from).days
    prev_date_from = date_from - timedelta(days=period_days)
    prev_date_to = date_from - timedelta(days=1)
    prev_transactions = Transaction.objects.filter(created_at__date__gte=prev_date_from, created_at__date__lte=prev_date_to)
    
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
    }
    return render(request, 'core/dashboard.html', context)