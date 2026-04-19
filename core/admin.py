from django.contrib import admin
from .models import *
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import UserProfile

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

@admin.register(CustomerTypeMaster)
class CustomerTypeMasterAdmin(admin.ModelAdmin):
    list_display = ('name',)

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
    list_display = ('id', 'branch', 'customer_type', 'outcome', 'created_at')
    list_filter = ('branch', 'customer_type', 'outcome', 'created_at')
    search_fields = ('individual_name', 'company_name')
    readonly_fields = ('created_at',)