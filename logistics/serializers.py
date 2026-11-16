from rest_framework import serializers
from .models import Warehouse, Shipment, BulkImportJob, Invoice


class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warehouse
        fields = "__all__"


class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = [
            "id",
            "invoice_number",
            "subtotal",
            "gst_amount",
            "total_amount",
            "pdf_file",
            "is_generated",
            "generated_at",
        ]


class ShipmentSerializer(serializers.ModelSerializer):
    warehouse_code = serializers.CharField(source="origin_warehouse.code", read_only=True)
    invoice = InvoiceSerializer(read_only=True)

    class Meta:
        model = Shipment
        fields = [
            "id",
            "tracking_id",
            "origin_warehouse",
            "warehouse_code",
            "destination_city",
            "vehicle_number",
            "cargo_weight_kg",
            "freight_amount",
            "tax_rate_percent",
            "status",
            "expected_delivery",
            "invoice",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class BulkImportJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = BulkImportJob
        fields = [
            "id",
            "uploaded_file",
            "celery_task_id",
            "status",
            "total_rows",
            "processed_rows",
            "error_log",
            "created_at",
            "completed_at",
        ]
        read_only_fields = [
            "id",
            "celery_task_id",
            "status",
            "total_rows",
            "processed_rows",
            "error_log",
            "created_at",
            "completed_at",
        ]
