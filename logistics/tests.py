from datetime import timedelta
from decimal import Decimal
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from .models import Warehouse, Shipment
from .tasks import flag_overdue_shipments

User = get_user_model()


@pytest.mark.django_db
def test_shipment_creation_and_overdue_task(settings):
    settings.CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
    admin = User.objects.create_superuser("admin", "admin@example.com", "pass1234")
    wh = Warehouse.objects.create(code="WH-MUM-01", name="Mumbai Hub", city="Mumbai")

    client = APIClient()
    client.force_authenticate(user=admin)

    past_due = (timezone.now() - timedelta(hours=3)).isoformat()
    res = client.post(
        "/api/v1/shipments/",
        {
            "tracking_id": "TRK-9001",
            "origin_warehouse": wh.id,
            "destination_city": "Pune",
            "vehicle_number": "MH01AB1234",
            "cargo_weight_kg": "1250.50",
            "freight_amount": "18500.00",
            "expected_delivery": past_due,
        },
        format="json",
    )
    assert res.status_code == 201

    result = flag_overdue_shipments()
    assert result["flagged_overdue"] == 1
    shipment = Shipment.objects.get(tracking_id="TRK-9001")
    assert shipment.status == Shipment.Status.DELAYED
