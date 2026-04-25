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
            'business_model': Select2Widget(attrs={'autocomplete': 'off'}),
            'sales_type': Select2Widget(attrs={'autocomplete': 'off'}),
            'parts_type': Select2Widget(attrs={'autocomplete': 'off'}),
            'maintenance_type': Select2Widget(attrs={'autocomplete': 'off'}),
            'corporate_client': Select2Widget(attrs={'autocomplete': 'off'}),
            'government_org': Select2Widget(attrs={'autocomplete': 'off'}),
            'wholesale_company': Select2Widget(attrs={'autocomplete': 'off'}),
            'vehicle_brand': Select2Widget(attrs={'autocomplete': 'off'}),
            'vehicle_model': Select2Widget(attrs={'autocomplete': 'off'}),
            'manufacture_year': Select2Widget(attrs={'autocomplete': 'off'}),
            'glass_position': Select2Widget(attrs={'autocomplete': 'off'}),
            'customer_source': Select2Widget(attrs={'autocomplete': 'off'}),
            'reason': Select2Widget(attrs={'autocomplete': 'off'}),
            # 'wholesale_customer_type': Select2Widget,
            # 'wholesale_shop': Select2Widget,
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        is_admin = (
            self.user and
            hasattr(self.user, 'userprofile') and
            self.user.userprofile.role == 'admin'
        )

        # ── Determine active branch ──────────────────────────────────────────
        # Priority: POST branch (admin changing branch mid-form) →
        #           existing instance branch (edit form) →
        #           user's fixed branch (non-admin)
        branch_id = None
        if self.data.get('branch'):
            branch_id = self.data.get('branch')
        elif self.instance and self.instance.pk and self.instance.branch_id:
            branch_id = self.instance.branch_id
        elif not is_admin and self.user and self.user.userprofile.branch:
            branch_id = self.user.userprofile.branch_id

        # ── Filter branch-specific customer dropdowns ────────────────────────
        branch_customer_fields = {
            'corporate_client': CorporateClient,
            'wholesale_company': WholesaleCompany,
            'government_org':    GovernmentOrganization,
        }
        for field_name, model_class in branch_customer_fields.items():
            if branch_id:
                self.fields[field_name].queryset = model_class.objects.filter(branch_id=branch_id)
            else:
                # No branch selected yet → show empty (prevents leaking other branch data)
                self.fields[field_name].queryset = model_class.objects.none()

        # ── Non-admin: lock branch to their own ─────────────────────────────
        if not is_admin and self.user:
            self.fields['branch'].queryset = Branch.objects.filter(id=self.user.userprofile.branch.id)
            self.fields['branch'].initial = self.user.userprofile.branch
            self.fields['branch'].widget.attrs['disabled'] = 'disabled'
            self.fields['branch'].required = False

        # ── Optional fields ──────────────────────────────────────────────────
        optional_fields = [
            'sales_type', 'parts_type', 'maintenance_type',
            'corporate_client', 'government_org',
            'wholesale_company', 'price', 'document', 'reason', 'expected_price'
        ]
        for field in optional_fields:
            if field in self.fields:
                self.fields[field].required = False

        # ── CSS classes ──────────────────────────────────────────────────────
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-input'