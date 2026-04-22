from django import forms
from .models import (
    Transaction, Branch, BusinessModel, SalesType, PartsType,
    VehicleBrand, VehicleModel, ManufactureYear, GlassPosition,
    CustomerSource, WholesaleCustomerType, WholesaleCompany,
    WholesaleShop, MaintenanceType, Reason, CorporateClient,
    GovernmentOrganization
)
from django_select2.forms import Select2Widget #type: ignore
from django.contrib.auth.forms import AuthenticationForm
import datetime

class LoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Username'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': 'Password'}))

class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = '__all__'
        widgets = {
            'branch': Select2Widget,
            'business_model': Select2Widget,
            'sales_type': Select2Widget,
            'parts_type': Select2Widget,
            'maintenance_type': Select2Widget,
            'corporate_client': Select2Widget,
            'government_org': Select2Widget,
            # 'wholesale_customer_type': Select2Widget,
            'wholesale_company': Select2Widget,
            # 'wholesale_shop': Select2Widget,
            'vehicle_brand': Select2Widget,
            'vehicle_model': Select2Widget,
            'manufacture_year': Select2Widget,
            'glass_position': Select2Widget,
            'customer_source': Select2Widget,
            'reason': Select2Widget,
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Set initial manufacture year to current year
        # current_year = datetime.datetime.now().year
        # year_obj = ManufactureYear.objects.filter(year=current_year).first()
        # if year_obj:
        #     self.fields['manufacture_year'].initial = year_obj.id

        # Restrict branch for non-admin users
        if self.user and hasattr(self.user, 'userprofile') and self.user.userprofile.role != 'admin':
            self.fields['branch'].queryset = Branch.objects.filter(id=self.user.userprofile.branch.id)
            self.fields['branch'].initial = self.user.userprofile.branch
            self.fields['branch'].widget = forms.HiddenInput()

        # Make conditional fields not required initially
        optional_fields = [
            'sales_type', 'parts_type', 'maintenance_type',
            'corporate_client', 'government_org',
            'wholesale_company',
            'price', 'document', 'reason', 'expected_price'
        ]
        for field in optional_fields:
            if field in self.fields:
                self.fields[field].required = False

        # Add CSS classes
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-input'