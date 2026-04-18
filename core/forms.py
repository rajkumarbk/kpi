from django import forms
from .models import Transaction, Branch, CustomerTypeMaster, VehicleBrand, VehicleModel, ManufactureYear, GlassPosition, CustomerSource, WholesaleCustomerType, WholesaleCompany, WholesaleShop, MaintenanceType, Reason
from django_select2.forms import Select2Widget
import datetime
class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = '__all__'
        widgets = {
            'branch': Select2Widget,
            'customer_type': Select2Widget,
            'vehicle_brand': Select2Widget,
            'vehicle_model': Select2Widget,
            'manufacture_year': Select2Widget,
            'glass_position': Select2Widget,
            'customer_source': Select2Widget,
            'wholesale_customer_type': Select2Widget,
            'wholesale_company': Select2Widget,
            'wholesale_shop': Select2Widget,
            'maintenance_type': Select2Widget,
            'reason': Select2Widget,
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        current_year = datetime.datetime.now().year
        year_obj = ManufactureYear.objects.filter(year=current_year).first()
        if year_obj:
            self.fields['manufacture_year'].initial = year_obj.id

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make non-common fields not required initially
        self.fields['wholesale_customer_type'].required = False
        self.fields['wholesale_company'].required = False
        self.fields['wholesale_shop'].required = False
        self.fields['individual_name'].required = False
        self.fields['company_name'].required = False
        self.fields['maintenance_type'].required = False
        self.fields['price'].required = False
        self.fields['document'].required = False
        self.fields['reason'].required = False

        # Add CSS classes for styling (we'll use Tailwind or custom CSS)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-input'