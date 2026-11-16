from django.core.cache import cache
from django.db.models import Count, Sum, Q
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Warehouse, Shipment, BulkImportJob
from .permissions import IsManagerOrReadOnly
from .serializers import WarehouseSerializer, ShipmentSerializer, BulkImportJobSerializer
from .tasks import generate_shipment_invoice_pdf, process_bulk_shipment_file


class WarehouseViewSet(viewsets.ModelViewSet):
    queryset = Warehouse.objects.all().order_by("code")
    serializer_class = WarehouseSerializer
    permission_classes = [IsManagerOrReadOnly]


class ShipmentViewSet(viewsets.ModelViewSet):
    serializer_class = ShipmentSerializer
    permission_classes = [IsManagerOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["tracking_id", "destination_city", "vehicle_number", "origin_warehouse__code"]
    ordering_fields = ["created_at", "expected_delivery", "freight_amount"]

    def get_queryset(self):
        # Eliminates N+1 queries via select_related on FK and OneToOne relations
        qs = Shipment.objects.select_related("origin_warehouse", "invoice").all()
        status_param = self.request.query_params.get("status")
        warehouse_code = self.request.query_params.get("warehouse")
        if status_param:
            qs = qs.filter(status=status_param.upper())
        if warehouse_code:
            qs = qs.filter(origin_warehouse__code=warehouse_code)
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
        cache.delete("logistics:dashboard_metrics")

    def perform_update(self, serializer):
        serializer.save()
        cache.delete("logistics:dashboard_metrics")

    @action(detail=True, methods=["post"], url_path="generate-invoice")
    def generate_invoice(self, request, pk=None):
        shipment = self.get_object()
        task = generate_shipment_invoice_pdf.delay(shipment.id)
        return Response(
            {
                "message": "PDF invoice generation queued via Celery.",
                "shipment_id": shipment.id,
                "tracking_id": shipment.tracking_id,
                "task_id": task.id,
            },
            status=status.HTTP_202_ACCEPTED,
        )


class BulkImportViewSet(viewsets.ModelViewSet):
    queryset = BulkImportJob.objects.all().order_by("-created_at")
    serializer_class = BulkImportJobSerializer
    parser_classes = [MultiPartParser, FormParser]
    http_method_names = ["get", "post", "head", "options"]

    def perform_create(self, serializer):
        job = serializer.save(uploaded_by=self.request.user)
        task = process_bulk_shipment_file.delay(str(job.id))
        job.celery_task_id = task.id
        job.save(update_fields=["celery_task_id"])


class DashboardAnalyticsView(APIView):
    """Redis-cached KPI endpoint with automatic cache invalidation on writes."""

    CACHE_KEY = "logistics:dashboard_metrics"
    CACHE_TTL = 300  # 5 minutes

    def get(self, request):
        cached_data = cache.get(self.CACHE_KEY)
        if cached_data:
            return Response({"source": "redis_cache", "data": cached_data})

        aggregates = Shipment.objects.aggregate(
            total_shipments=Count("id"),
            delivered_count=Count("id", filter=Q(status=Shipment.Status.DELIVERED)),
            delayed_count=Count("id", filter=Q(status=Shipment.Status.DELAYED)),
            in_transit_count=Count("id", filter=Q(status=Shipment.Status.IN_TRANSIT)),
            total_revenue=Sum("freight_amount"),
            total_weight_kg=Sum("cargo_weight_kg"),
        )

        payload = {
            "total_shipments": aggregates["total_shipments"] or 0,
            "delivered_count": aggregates["delivered_count"] or 0,
            "delayed_count": aggregates["delayed_count"] or 0,
            "in_transit_count": aggregates["in_transit_count"] or 0,
            "total_revenue_inr": float(aggregates["total_revenue"] or 0),
            "total_cargo_weight_kg": float(aggregates["total_weight_kg"] or 0),
        }
        cache.set(self.CACHE_KEY, payload, timeout=self.CACHE_TTL)
        return Response({"source": "database", "data": payload})
