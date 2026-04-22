from django.contrib import admin
from .models import *
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    fields = ('role', 'branch')

class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'get_role', 'get_branch', 'is_staff')

    def get_role(self, obj):
        return obj.userprofile.role if hasattr(obj, 'userprofile') else '-'
    get_role.short_description = 'Role'

    def get_branch(self, obj):
        return obj.userprofile.branch.code if hasattr(obj, 'userprofile') and obj.userprofile.branch else '-'
    get_branch.short_description = 'Branch'

admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('company', 'code', 'name')
    list_filter = ('company',)
    search_fields = ('code', 'name')

# New master admins
@admin.register(BusinessModel)
class BusinessModelAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(SalesType)
class SalesTypeAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(PartsType)
class PartsTypeAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(CorporateClient)
class CorporateClientAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(GovernmentOrganization)
class GovernmentOrganizationAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

# Existing wholesale admins (unchanged)
@admin.register(WholesaleCustomerType)
class WholesaleCustomerTypeAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(WholesaleCompany)
class WholesaleCompanyAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(WholesaleShop)
class WholesaleShopAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

# Vehicle and other masters (unchanged)
@admin.register(VehicleBrand)
class VehicleBrandAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(VehicleModel)
class VehicleModelAdmin(admin.ModelAdmin):
    list_display = ('brand', 'name')
    list_filter = ('brand',)
    search_fields = ('name',)

@admin.register(ManufactureYear)
class ManufactureYearAdmin(admin.ModelAdmin):
    list_display = ('year',)
    ordering = ('-year',)

@admin.register(GlassPosition)
class GlassPositionAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(MaintenanceType)
class MaintenanceTypeAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(Reason)
class ReasonAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(CustomerSource)
class CustomerSourceAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'branch', 'business_model', 'outcome', 'created_at')
    list_filter = ('branch', 'business_model', 'outcome', 'created_at')
    search_fields = ('corporate_client__name', 'government_org__name')
    readonly_fields = ('created_at',)