from django.shortcuts import render, redirect, get_object_or_404
from .forms import TransactionForm
from .models import (
    Transaction,
    VehicleModel,
    Branch,
    BusinessModel,
    Reason,
    WholesaleCompany,
    CorporateClient,
    GovernmentOrganization,
)
from django.http import JsonResponse
from django.db.models import Count, Q, Sum, Avg
from django.db.models.functions import TruncDate
from django.utils import timezone
import json
from django.core.paginator import Paginator
from datetime import timedelta, datetime
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import UserCreationForm

from django.contrib.auth.decorators import user_passes_test


def check_admin(user):
    return (
        user.is_authenticated
        and hasattr(user, "userprofile")
        and user.userprofile.role == "admin"
    )


def admin_required(view_func):
    decorated_view = user_passes_test(check_admin, login_url="core:login")(view_func)
    return decorated_view


def login_view(request):
    if request.user.is_authenticated:
        try:
            if request.user.userprofile.role == "admin":
                return redirect("core:dashboard")
            else:
                return redirect("core:add_transaction")
        except:
            return redirect("core:add_transaction")

    error = None
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            try:
                if user.userprofile.role == "admin":
                    return redirect("core:dashboard")
                else:
                    return redirect("core:add_transaction")
            except:
                return redirect("core:add_transaction")
        else:
            error = "Invalid username or password"

    return render(request, "registration/login.html", {"error": error})


def logout_view(request):
    logout(request)
    return redirect("core:login")


@login_required
def create_transaction(request):
    if request.method == "POST":
        form = TransactionForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            transaction = form.save(commit=False)
            if request.user.userprofile.role != "admin":
                transaction.branch = request.user.userprofile.branch
            transaction.save()
            return redirect("core:transaction_list")
    else:
        form = TransactionForm(user=request.user)
        if request.user.userprofile.role != "admin":
            form.fields["branch"].initial = request.user.userprofile.branch
            form.fields["branch"].disabled = True
    return render(request, "core/form.html", {"form": form})


def load_models(request):
    brand_id = request.GET.get("brand")
    models = VehicleModel.objects.filter(brand_id=brand_id).order_by("name")
    return JsonResponse(list(models.values("id", "name")), safe=False)


@login_required
def transaction_edit(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk)
    form = TransactionForm(
        request.POST or None,
        request.FILES or None,
        instance=transaction,
        user=request.user,  # ← this was missing
    )
    if form.is_valid():
        form.save()
        return redirect("core:transaction_detail", pk=pk)
    return render(request, "core/form.html", {"form": form, "transaction": transaction})


@login_required
def transaction_delete(request, pk):
    if request.method == "POST":
        get_object_or_404(Transaction, pk=pk).delete()
        return redirect(request.META.get("HTTP_REFERER") or "core:transaction_list")
    return redirect("core:transaction_detail", pk=pk)


@login_required
def transaction_list(request):
    if request.user.userprofile.role == "admin":
        transactions = Transaction.objects.all()
    else:
        transactions = Transaction.objects.filter(
            branch=request.user.userprofile.branch
        )

    # Apply filters
    branch = request.GET.get("branch")
    business_model = request.GET.get("business_model")
    outcome = request.GET.get("outcome")
    reason = request.GET.get("reason")
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")
    day_of_week = request.GET.get("day_of_week")

    if branch and request.user.userprofile.role == "admin":
        transactions = transactions.filter(branch_id=branch)
    if business_model:
        transactions = transactions.filter(business_model_id=business_model)
    if outcome:
        transactions = transactions.filter(outcome=outcome)
    if reason:
        transactions = transactions.filter(reason_id=reason)
    if date_from:
        transactions = transactions.filter(created_at__date__gte=date_from)
    if date_to:
        transactions = transactions.filter(created_at__date__lte=date_to)
    if day_of_week:
        transactions = transactions.filter(created_at__week_day=day_of_week)

    transactions = transactions.order_by("-created_at")

    daily_summary = (
        transactions.annotate(day=TruncDate("created_at"))
        .values("day", "branch__code")
        .annotate(
            success_count=Count("id", filter=Q(outcome="success")),
            fail_count=Count("id", filter=Q(outcome="fail")),
            day_revenue=Sum("price", filter=Q(outcome="success")),
        )
        .order_by("-day")
    )

    # Calculate stats
    total_count = transactions.count()
    total_revenue = (
        transactions.filter(outcome="success").aggregate(total=Sum("price"))["total"]
        or 0
    )
    success_count = transactions.filter(outcome="success").count()
    success_rate = round(
        (success_count / total_count * 100) if total_count > 0 else 0, 1
    )
    fail_count = transactions.filter(outcome="fail").count()
    fail_rate = round((fail_count / total_count * 100) if total_count > 0 else 0, 1)
    avg_transaction = total_revenue / success_count if success_count > 0 else 0

    # Pagination
    paginator = Paginator(transactions, 50)
    page = request.GET.get("page")
    transactions = paginator.get_page(page)

    context = {
        "transactions": transactions,
        "total_count": total_count,
        "total_revenue": total_revenue,
        "success_rate": success_rate,
        "fail_rate": fail_rate,
        "avg_transaction": avg_transaction,
        "daily_summary": daily_summary,
        "branches": Branch.objects.all(),
        "business_models": BusinessModel.objects.all(),
        "reasons": Reason.objects.all(),
        "day_of_week": day_of_week,
    }
    return render(request, "core/list.html", context)


@login_required
def transaction_detail(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk)
    return render(request, "core/detail.html", {"transaction": transaction})


@login_required
@admin_required
def dashboard(request):
    # Date range logic
    date_range = request.GET.get("date_range", "this_month")
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")
    selected_branch = request.GET.get("branch", "")
    day_filter = request.GET.get("day_filter", "")

    today = timezone.now().date()

    if date_range == "today":
        date_from = date_to = today
    elif date_range == "yesterday":
        date_from = date_to = today - timedelta(days=1)
    elif date_range == "this_week":
        date_from = today - timedelta(days=today.weekday())
        date_to = today
    elif date_range == "last_week":
        date_from = today - timedelta(days=today.weekday() + 7)
        date_to = date_from + timedelta(days=6)
    elif date_range == "this_month":
        date_from = today.replace(day=1)
        date_to = today
    elif date_range == "last_month":
        first_of_month = today.replace(day=1)
        date_to = first_of_month - timedelta(days=1)
        date_from = date_to.replace(day=1)
    elif date_range == "this_year":
        date_from = today.replace(month=1, day=1)
        date_to = today
    elif date_range == "custom" and date_from and date_to:
        date_from = datetime.strptime(date_from, "%Y-%m-%d").date()
        date_to = datetime.strptime(date_to, "%Y-%m-%d").date()
    else:
        date_from = today - timedelta(days=30)
        date_to = today

    # Filter transactions by date
    transactions = Transaction.objects.filter(
        created_at__date__gte=date_from, created_at__date__lte=date_to
    )
    if selected_branch:
        transactions = transactions.filter(branch_id=selected_branch)
    if day_filter != "":
        transactions = transactions.filter(created_at__week_day=int(day_filter) + 1)

    # Previous period for trend
    period_days = (date_to - date_from).days
    prev_date_from = date_from - timedelta(days=period_days)
    prev_date_to = date_from - timedelta(days=1)
    prev_transactions = Transaction.objects.filter(
        created_at__date__gte=prev_date_from, created_at__date__lte=prev_date_to
    )
    if selected_branch:
        prev_transactions = prev_transactions.filter(branch_id=selected_branch)

    # Calculate trends
    current_total = transactions.count()
    prev_total = prev_transactions.count()
    trend_total = round(
        ((current_total - prev_total) / prev_total * 100) if prev_total > 0 else 0, 1
    )

    # Dashboard data
    total = current_total
    success_count = transactions.filter(outcome="success").count()
    fail_count = transactions.filter(outcome="fail").count()
    success_rate = round((success_count / total * 100) if total > 0 else 0, 1)
    fail_rate = round((fail_count / total * 100) if total > 0 else 0, 1)
    total_revenue = (
        transactions.filter(outcome="success").aggregate(total=Sum("price"))["total"]
        or 0
    )
    avg_value = total_revenue / success_count if success_count > 0 else 0

    # Pie chart data
    pie_data = {
        "labels": ["Success", "Fail"],
        "data": [success_count, fail_count],
    }

    # Daily trend data
    daily_data = []
    daily_labels = []
    current_date = date_from
    while current_date <= date_to:
        day_transactions = transactions.filter(created_at__date=current_date).count()
        daily_labels.append(current_date.strftime("%d %b"))
        daily_data.append(day_transactions)
        current_date += timedelta(days=1)

    # Branch performance
    branch_stats = (
        transactions.values("branch__code")
        .annotate(
            total=Count("id"),
            success=Count("id", filter=Q(outcome="success")),
            fail=Count("id", filter=Q(outcome="fail")),
            revenue=Sum("price", filter=Q(outcome="success")),
        )
        .order_by("branch__code")
    )

    branch_labels = [stat["branch__code"] for stat in branch_stats]
    branch_data = [stat["total"] for stat in branch_stats]

    # Business Model distribution
    business_model_stats = (
        transactions.values("business_model__name")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    business_model_labels = [
        stat["business_model__name"] or "Unknown" for stat in business_model_stats
    ]
    business_model_data = [stat["count"] for stat in business_model_stats]

    # Sales Type distribution
    sales_type_stats = (
        transactions.exclude(sales_type__isnull=True)
        .values("sales_type__name")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    sales_type_labels = [stat["sales_type__name"] for stat in sales_type_stats]
    sales_type_data = [stat["count"] for stat in sales_type_stats]

    # Parts & Maintenance Type distribution
    parts_stats = (
        transactions.exclude(parts_type__isnull=True)
        .values("parts_type__name")
        .annotate(count=Count("id"))
    )
    maintenance_stats = (
        transactions.exclude(maintenance_type__isnull=True)
        .values("maintenance_type__name")
        .annotate(count=Count("id"))
    )

    parts_maintenance_labels = []
    parts_maintenance_data = []
    for stat in parts_stats:
        if stat["parts_type__name"]:
            parts_maintenance_labels.append(f"Parts: {stat['parts_type__name']}")
            parts_maintenance_data.append(stat["count"])
    for stat in maintenance_stats:
        if stat["maintenance_type__name"]:
            parts_maintenance_labels.append(
                f"Maintenance: {stat['maintenance_type__name']}"
            )
            parts_maintenance_data.append(stat["count"])

    # Customer Source distribution
    customer_source_stats = (
        transactions.values("customer_source__name")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    customer_source_labels = [
        stat["customer_source__name"] or "Unknown" for stat in customer_source_stats
    ]
    customer_source_data = [stat["count"] for stat in customer_source_stats]

    # B2B Type breakdown (Corporate vs Wholesale)
    b2b_corporate_count = transactions.filter(corporate_client__isnull=False).count()
    b2b_wholesale_count = transactions.filter(wholesale_company__isnull=False).count()
    b2b_type_labels = ["Corporate Clients", "Wholesale Customers"]
    b2b_type_data = [b2b_corporate_count, b2b_wholesale_count]

    # Vehicle Brand distribution
    vehicle_brand_stats = (
        transactions.values("vehicle_brand__name")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )
    vehicle_brand_labels = [stat["vehicle_brand__name"] for stat in vehicle_brand_stats]
    vehicle_brand_data = [stat["count"] for stat in vehicle_brand_stats]

    # Failure reasons
    reason_counts = (
        transactions.filter(outcome="fail")
        .values("reason__name")
        .annotate(count=Count("id"))
        .order_by("-count")[:5]
    )
    reason_labels = [item["reason__name"] or "Unknown" for item in reason_counts]
    reason_data = [item["count"] for item in reason_counts]

    # Recent transactions
    recent_transactions = transactions.order_by("-created_at")[:5]

    context = {
        "date_range": date_range,
        "date_from": date_from.strftime("%Y-%m-%d") if date_from else "",
        "date_to": date_to.strftime("%Y-%m-%d") if date_to else "",
        "total": total,
        "success_count": success_count,
        "fail_count": fail_count,
        "success_rate": success_rate,
        "fail_rate": fail_rate,
        "total_revenue": total_revenue,
        "avg_value": avg_value,
        "trend": {"total": trend_total},
        "pie_data": json.dumps(pie_data),
        "trend_labels": json.dumps(daily_labels),
        "trend_data": json.dumps(daily_data),
        "branch_labels": json.dumps(branch_labels),
        "branch_data": json.dumps(branch_data),
        "business_model_labels": json.dumps(business_model_labels),
        "business_model_data": json.dumps(business_model_data),
        "sales_type_labels": json.dumps(sales_type_labels),
        "sales_type_data": json.dumps(sales_type_data),
        "parts_maintenance_labels": json.dumps(parts_maintenance_labels),
        "parts_maintenance_data": json.dumps(parts_maintenance_data),
        "customer_source_labels": json.dumps(customer_source_labels),
        "customer_source_data": json.dumps(customer_source_data),
        "b2b_type_labels": json.dumps(b2b_type_labels),
        "b2b_type_data": json.dumps(b2b_type_data),
        "vehicle_brand_labels": json.dumps(vehicle_brand_labels),
        "vehicle_brand_data": json.dumps(vehicle_brand_data),
        "reason_labels": json.dumps(reason_labels),
        "reason_data": json.dumps(reason_data),
        "branch_stats": branch_stats,
        "recent_transactions": recent_transactions,
        "selected_branch": selected_branch,
        "branches": Branch.objects.all().order_by("code"),
        "day_filter": day_filter,
    }
    return render(request, "core/dashboard.html", context)


from django.http import HttpResponse
from django.template.loader import render_to_string
from django.db.models import Sum


@login_required
def transaction_pdf(request):
    from weasyprint import HTML

    qs = Transaction.objects.select_related(
        "branch",
        "business_model",
        "vehicle_brand",
        "vehicle_model",
        "glass_position",
        "reason",
    ).order_by("-created_at")

    user_profile = request.user.userprofile
    if user_profile.role != "admin":
        qs = qs.filter(branch=user_profile.branch)

    branch_id = request.GET.get("branch")
    business_model = request.GET.get("business_model")
    outcome = request.GET.get("outcome")
    reason = request.GET.get("reason")
    glass_position = request.GET.get("glass_position")
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")

    if branch_id:
        qs = qs.filter(branch_id=branch_id)
    if business_model:
        qs = qs.filter(business_model_id=business_model)
    if outcome:
        qs = qs.filter(outcome=outcome)
    if reason:
        qs = qs.filter(reason_id=reason)
    if glass_position:
        qs = qs.filter(glass_position_id=glass_position)
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)

    # branch label
    if branch_id:
        try:
            branch_label = str(Branch.objects.get(pk=branch_id))
        except Branch.DoesNotExist:
            branch_label = "All Branches"
    elif user_profile.role != "admin":
        branch_label = str(user_profile.branch)
    else:
        branch_label = "All Branches"

    # reason label
    if reason:
        try:
            reason_label = str(Reason.objects.get(pk=reason))
        except Reason.DoesNotExist:
            reason_label = "All Reasons"
    else:
        reason_label = "All Reasons"

    # company detection for header logo
    company = None
    if branch_id:
        try:
            company = Branch.objects.get(pk=branch_id).company
        except Branch.DoesNotExist:
            company = None
    elif user_profile.role != "admin":
        company = user_profile.branch.company
    elif qs.exists():
        companies = qs.values_list("branch__company", flat=True).distinct()
        if companies.count() == 1:
            company = companies[0]

    total_revenue = qs.aggregate(total=Sum("price"))["total"] or 0

    context = {
        "transactions": qs,
        "branch_label": branch_label,
        "reason_label": reason_label,
        "date_from": date_from,
        "date_to": date_to,
        "total_count": qs.count(),
        "total_revenue": total_revenue,
        "company": company,
    }

    html_string = render_to_string("core/report.html", context, request=request)
    pdf = HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf()

    response = HttpResponse(pdf, content_type="application/pdf")
    filename = (
        f"Transactions_{branch_label}_{date_from or 'all'}_To_{date_to or 'all'}.pdf"
    )
    filename = filename.replace(" ", "_")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def _is_admin(user):
    return (
        user.is_authenticated
        and hasattr(user, "userprofile")
        and user.userprofile.role == "admin"
    )


def load_corporate_clients(request):
    branch_id = request.GET.get("branch_id")
    qs = CorporateClient.objects.all()
    if branch_id:
        qs = qs.filter(branch_id=branch_id)
    elif not _is_admin(request.user):
        qs = qs.none()
    return JsonResponse(list(qs.order_by("name").values("id", "name")), safe=False)


def load_wholesale_companies(request):
    branch_id = request.GET.get("branch_id")
    qs = WholesaleCompany.objects.all()
    if branch_id:
        qs = qs.filter(branch_id=branch_id)
    elif not _is_admin(request.user):
        qs = qs.none()
    return JsonResponse(list(qs.order_by("name").values("id", "name")), safe=False)
