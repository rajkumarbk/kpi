from rest_framework import serializers
from .models import Transaction

class TransactionSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    vehicle_brand_name = serializers.CharField(source='vehicle_brand.name', read_only=True)
    business_model_name = serializers.CharField(source='business_model.name', read_only=True)
    reason_name = serializers.CharField(source='reason.name', read_only=True, default=None)

    class Meta:
        model = Transaction
        fields = '__all__'