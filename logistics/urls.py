from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import WarehouseViewSet, ShipmentViewSet, BulkImportViewSet, DashboardAnalyticsView

router = DefaultRouter()
router.register(r"warehouses", WarehouseViewSet, basename="warehouse")
router.register(r"shipments", ShipmentViewSet, basename="shipment")
router.register(r"bulk-imports", BulkImportViewSet, basename="bulk-import")

urlpatterns = [
    path("", include(router.urls)),
    path("analytics/dashboard/", DashboardAnalyticsView.as_view(), name="dashboard-analytics"),
]
