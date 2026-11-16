from django.contrib import admin
from .models import Warehouse, Shipment, BulkImportJob, Invoice

admin.site.register(Warehouse)
admin.site.register(Shipment)
admin.site.register(BulkImportJob)
admin.site.register(Invoice)
