import os
from decimal import Decimal
import pandas as pd
from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from .models import BulkImportJob, Invoice, Shipment, Warehouse


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def generate_shipment_invoice_pdf(self, shipment_id: int):
    """Asynchronously computes GST totals and renders a downloadable PDF tax invoice."""
    try:
        shipment = Shipment.objects.select_related("origin_warehouse").get(id=shipment_id)
        subtotal = Decimal(shipment.freight_amount)
        gst_amount = (subtotal * Decimal(shipment.tax_rate_percent) / Decimal("100")).quantize(Decimal("0.01"))
        total_amount = subtotal + gst_amount

        invoice, _ = Invoice.objects.get_or_create(
            shipment=shipment,
            defaults={
                "invoice_number": f"INV-{shipment.tracking_id}",
                "subtotal": subtotal,
                "gst_amount": gst_amount,
                "total_amount": total_amount,
            },
        )

        os.makedirs(os.path.join(settings.MEDIA_ROOT, "invoices"), exist_ok=True)
        filename = f"{invoice.invoice_number}.pdf"
        filepath = os.path.join(settings.MEDIA_ROOT, "invoices", filename)

        c = canvas.Canvas(filepath, pagesize=A4)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, 780, "SMARTFLEET LOGISTICS - TAX INVOICE")
        c.setFont("Helvetica", 11)
        c.drawString(50, 750, f"Invoice Number: {invoice.invoice_number}")
        c.drawString(50, 730, f"Tracking ID: {shipment.tracking_id}")
        c.drawString(50, 710, f"Origin Warehouse: {shipment.origin_warehouse.name} ({shipment.origin_warehouse.city})")
        c.drawString(50, 690, f"Destination City: {shipment.destination_city}")
        c.drawString(50, 670, f"Vehicle Number: {shipment.vehicle_number}")
        c.line(50, 655, 540, 655)
        c.drawString(50, 630, f"Freight Subtotal: INR {subtotal}")
        c.drawString(50, 610, f"GST ({shipment.tax_rate_percent}%): INR {gst_amount}")
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, 585, f"Grand Total: INR {total_amount}")
        c.save()

        invoice.subtotal = subtotal
        invoice.gst_amount = gst_amount
        invoice.total_amount = total_amount
        invoice.pdf_file.name = f"invoices/{filename}"
        invoice.is_generated = True
        invoice.generated_at = timezone.now()
        invoice.save()

        cache.delete("logistics:dashboard_metrics")
        return {"invoice_number": invoice.invoice_number, "status": "GENERATED"}
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True)
def process_bulk_shipment_file(self, job_id: str):
    """Ingests CSV/Excel shipment manifests in background with row-level validation."""
    job = BulkImportJob.objects.get(id=job_id)
    job.status = BulkImportJob.JobStatus.PROCESSING
    job.save(update_fields=["status"])

    errors = []
    created_count = 0

    try:
        file_path = job.uploaded_file.path
        df = pd.read_excel(file_path) if file_path.endswith((".xlsx", ".xls")) else pd.read_csv(file_path)
        job.total_rows = len(df)

        warehouses = {w.code: w for w in Warehouse.objects.all()}

        for idx, row in df.iterrows():
            row_num = idx + 2
            try:
                wh_code = str(row["warehouse_code"]).strip()
                warehouse = warehouses.get(wh_code)
                if not warehouse:
                    raise ValueError(f"Unknown warehouse_code '{wh_code}'")

                with transaction.atomic():
                    Shipment.objects.update_or_create(
                        tracking_id=str(row["tracking_id"]).strip(),
                        defaults={
                            "origin_warehouse": warehouse,
                            "destination_city": str(row["destination_city"]).strip(),
                            "vehicle_number": str(row["vehicle_number"]).strip(),
                            "cargo_weight_kg": Decimal(str(row["cargo_weight_kg"])),
                            "freight_amount": Decimal(str(row["freight_amount"])),
                            "expected_delivery": pd.to_datetime(row["expected_delivery"], utc=True),
                            "created_by": job.uploaded_by,
                        },
                    )
                created_count += 1
            except Exception as row_err:
                errors.append({"row": row_num, "error": str(row_err)})

        job.processed_rows = created_count
        job.error_log = errors
        job.status = BulkImportJob.JobStatus.COMPLETED
        job.completed_at = timezone.now()
        job.save()
        cache.delete("logistics:dashboard_metrics")
    except Exception as fatal_err:
        job.status = BulkImportJob.JobStatus.FAILED
        job.error_log = [{"row": 0, "error": str(fatal_err)}]
        job.completed_at = timezone.now()
        job.save()


@shared_task
def flag_overdue_shipments():
    """Periodic Celery Beat task that flags delayed shipments and invalidates Redis cache."""
    now = timezone.now()
    updated = Shipment.objects.filter(
        status__in=[Shipment.Status.PENDING, Shipment.Status.IN_TRANSIT],
        expected_delivery__lt=now,
    ).update(status=Shipment.Status.DELAYED)

    if updated:
        cache.delete("logistics:dashboard_metrics")
    return {"flagged_overdue": updated}
