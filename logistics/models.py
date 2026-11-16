import uuid
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Warehouse(models.Model):
    code = models.CharField(max_length=20, unique=True, db_index=True)
    name = models.CharField(max_length=120)
    city = models.CharField(max_length=80, db_index=True)
    capacity_units = models.PositiveIntegerField(default=10000)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.code} - {self.name}"


class Shipment(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending Dispatch"
        IN_TRANSIT = "IN_TRANSIT", "In Transit"
        DELIVERED = "DELIVERED", "Delivered"
        DELAYED = "DELAYED", "Delayed / Overdue"
        CANCELLED = "CANCELLED", "Cancelled"

    tracking_id = models.CharField(max_length=32, unique=True, db_index=True)
    origin_warehouse = models.ForeignKey(
        Warehouse, on_delete=models.PROTECT, related_name="outbound_shipments"
    )
    destination_city = models.CharField(max_length=80, db_index=True)
    vehicle_number = models.CharField(max_length=25, db_index=True)
    cargo_weight_kg = models.DecimalField(max_digits=10, decimal_places=2)
    freight_amount = models.DecimalField(max_digits=12, decimal_places=2)
    tax_rate_percent = models.DecimalField(max_digits=5, decimal_places=2, default=18.00)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    expected_delivery = models.DateTimeField(db_index=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "expected_delivery"]),
            models.Index(fields=["origin_warehouse", "status"]),
        ]

    def __str__(self):
        return self.tracking_id


class BulkImportJob(models.Model):
    class JobStatus(models.TextChoices):
        QUEUED = "QUEUED", "Queued"
        PROCESSING = "PROCESSING", "Processing"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    uploaded_file = models.FileField(upload_to="imports/")
    celery_task_id = models.CharField(max_length=100, blank=True, default="")
    status = models.CharField(max_length=20, choices=JobStatus.choices, default=JobStatus.QUEUED)
    total_rows = models.PositiveIntegerField(default=0)
    processed_rows = models.PositiveIntegerField(default=0)
    error_log = models.JSONField(default=list, blank=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)


class Invoice(models.Model):
    shipment = models.OneToOneField(Shipment, on_delete=models.CASCADE, related_name="invoice")
    invoice_number = models.CharField(max_length=40, unique=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    gst_amount = models.DecimalField(max_digits=12, decimal_places=2)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    pdf_file = models.FileField(upload_to="invoices/", null=True, blank=True)
    is_generated = models.BooleanField(default=False)
    generated_at = models.DateTimeField(null=True, blank=True)
