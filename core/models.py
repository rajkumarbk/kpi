from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

# ---------- Master Data Models ----------
class Branch(models.Model):
    COMPANY_CHOICES = [
        ('Al Salem', 'Al Salem Auto Glass'),
        ('Watam', 'Watam Auto Glass'),
    ]
    company = models.CharField(max_length=20, choices=COMPANY_CHOICES)
    code = models.CharField(max_length=10, unique=True)  # e.g., 101, W01
    name = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"{self.company} - {self.code}"

    class Meta:
        ordering = ['company', 'code']

class CustomerTypeMaster(models.Model):
    """For the main customer type selection: wholesale, with/without installation, maintenance"""
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

class WholesaleCustomerType(models.Model):
    """Company or Shop for wholesale customers"""
    name = models.CharField(max_length=20)  # Company, Shop

    def __str__(self):
        return self.name

class WholesaleCompany(models.Model):
    """Master list of wholesale companies (when 'Company' selected)"""
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class WholesaleShop(models.Model):
    """Master list of wholesale shops (when 'Shop' selected)"""
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

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

    def __str__(self):
        return str(self.year)

class GlassPosition(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class MaintenanceType(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class Reason(models.Model):
    """Reasons for failure, applicable to different customer types"""
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class CustomerSource(models.Model):
    name = models.CharField(max_length=50, unique=True)  # social media, communication, visit

    def __str__(self):
        return self.name

# ---------- Transaction Model ----------
class Transaction(models.Model):
    # Common fields
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT)
    customer_type = models.ForeignKey(CustomerTypeMaster, on_delete=models.PROTECT)  # wholesale, customer with installation, etc.
    vehicle_brand = models.ForeignKey(VehicleBrand, on_delete=models.PROTECT)
    vehicle_model = models.ForeignKey(VehicleModel, on_delete=models.PROTECT)
    manufacture_year = models.ForeignKey(ManufactureYear, on_delete=models.PROTECT)
    glass_position = models.ForeignKey(GlassPosition, on_delete=models.PROTECT)
    customer_source = models.ForeignKey(CustomerSource, on_delete=models.PROTECT)

    # Conditional fields (nullable)
    # Wholesale specific
    wholesale_customer_type = models.ForeignKey(WholesaleCustomerType, on_delete=models.SET_NULL, null=True, blank=True)
    wholesale_company = models.ForeignKey(WholesaleCompany, on_delete=models.SET_NULL, null=True, blank=True)
    wholesale_shop = models.ForeignKey(WholesaleShop, on_delete=models.SET_NULL, null=True, blank=True)

    # For customer with/without installation, maintenance
    individual_name = models.CharField(max_length=100, blank=True)
    company_name = models.CharField(max_length=100, blank=True)

    # Maintenance specific
    maintenance_type = models.ForeignKey(MaintenanceType, on_delete=models.SET_NULL, null=True, blank=True)

    # Transaction outcome
    OUTCOME_CHOICES = [
        ('success', 'Success'),
        ('fail', 'Fail'),
    ]
    outcome = models.CharField(max_length=10, choices=OUTCOME_CHOICES)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    document = models.FileField(upload_to='documents/', null=True, blank=True)
    note = models.TextField(blank=True)

    # Failure reason
    reason = models.ForeignKey(Reason, on_delete=models.SET_NULL, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.customer_type} - {self.outcome} - {self.created_at.date()}"