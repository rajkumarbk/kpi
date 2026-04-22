from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import User

# ---------- Master Data Models ----------
class Branch(models.Model):
    COMPANY_CHOICES = [
        ('Al Salem Auto Glass', 'Al Salem Auto Glass'),
        ('Watam Auto Glass', 'Watam Auto Glass'),
    ]
    company = models.CharField(max_length=20, choices=COMPANY_CHOICES)
    code = models.CharField(max_length=10, unique=True)  # e.g., 101, W01
    name = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"{self.company} - {self.code}"

    class Meta:
        ordering = ['company', 'code']

class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('user', 'User'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.role}"

# ---------- New Master Models for Business Hierarchy ----------
class BusinessModel(models.Model):
    """B2C, B2B, B2G"""
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['id']

class SalesType(models.Model):
    """Parts, Maintenance"""
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['id']

class PartsType(models.Model):
    """With Installation, Without Installation"""
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['id']

class CorporateClient(models.Model):
    """Master list of corporate clients (for B2B → Corporate Clients)"""
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['id']

class GovernmentOrganization(models.Model):
    """Master list of government organizations (for B2G)"""
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['id']

# Existing wholesale models (kept as is)
class WholesaleCustomerType(models.Model):
    name = models.CharField(max_length=20)  # Company, Shop

    def __str__(self):
        return self.name

class WholesaleCompany(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class WholesaleShop(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

# Existing vehicle and other masters (unchanged)
class VehicleBrand(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

class VehicleModel(models.Model):
    brand = models.ForeignKey(VehicleBrand, on_delete=models.CASCADE, related_name='models')
    name = models.CharField(max_length=50)

    class Meta:
        unique_together = ('brand', 'name')

    def __str__(self):
        return f"{self.brand.name} {self.name}"

class ManufactureYear(models.Model):
    year = models.PositiveIntegerField(unique=True, validators=[MinValueValidator(1960), MaxValueValidator(2050)])

    class Meta:
        ordering = ['year']

    def __str__(self):
        return str(self.year)

class GlassPosition(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class MaintenanceType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    maintenance_note = models.TextField(blank=True)

    def __str__(self):
        return self.name

class Reason(models.Model):
    """Reasons for failure"""
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class CustomerSource(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

# ---------- Transaction Model (Updated) ----------
class Transaction(models.Model):
    # Common fields (unchanged)
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT)
    vehicle_brand = models.ForeignKey(VehicleBrand, on_delete=models.PROTECT)
    vehicle_model = models.ForeignKey(VehicleModel, on_delete=models.PROTECT)
    manufacture_year = models.ForeignKey(ManufactureYear, on_delete=models.PROTECT)
    glass_position = models.ForeignKey(GlassPosition, on_delete=models.PROTECT)
    customer_source = models.ForeignKey(CustomerSource, on_delete=models.PROTECT)

    # New hierarchical fields
    business_model = models.ForeignKey(BusinessModel, on_delete=models.PROTECT)
    sales_type = models.ForeignKey(SalesType, on_delete=models.PROTECT, null=True, blank=True)
    parts_type = models.ForeignKey(PartsType, on_delete=models.SET_NULL, null=True, blank=True)
    maintenance_type = models.ForeignKey(MaintenanceType, on_delete=models.SET_NULL, null=True, blank=True)

    # B2B specific
    corporate_client = models.ForeignKey(CorporateClient, on_delete=models.SET_NULL, null=True, blank=True)
    # Wholesale fields (kept for B2B → Wholesale)
    # wholesale_customer_type = models.ForeignKey(WholesaleCustomerType, on_delete=models.SET_NULL, null=True, blank=True)
    wholesale_company = models.ForeignKey(WholesaleCompany, on_delete=models.SET_NULL, null=True, blank=True)
    # wholesale_shop = models.ForeignKey(WholesaleShop, on_delete=models.SET_NULL, null=True, blank=True)

    # B2G specific
    government_org = models.ForeignKey(GovernmentOrganization, on_delete=models.SET_NULL, null=True, blank=True)

    # Outcome fields (unchanged)
    OUTCOME_CHOICES = [
        ('success', 'Success'),
        ('fail', 'Fail'),
    ]
    outcome = models.CharField(max_length=10, choices=OUTCOME_CHOICES)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    document = models.FileField(upload_to='documents/', null=True, blank=True)
    note = models.TextField(blank=True)
    reason = models.ForeignKey(Reason, on_delete=models.SET_NULL, null=True, blank=True)
    expected_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    maintenance_other_note = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.business_model} - {self.outcome} - {self.created_at.date()}"