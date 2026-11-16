# SmartFleet – Async Logistics, Bulk Ingestion & Billing API

Production-ready **Django REST Framework (DRF)** backend engineered with **Celery**, **Redis**, **PostgreSQL**, **ReportLab**, and **Docker Compose**.

## Key Architecture & Features
- **Asynchronous Task Processing (Celery + Redis):** Offloads heavy CSV/Excel shipment ingestion (`Pandas`) and GST-compliant PDF tax invoice generation (`ReportLab`) to background Celery workers.
- **Scheduled SLA Monitoring (Celery Beat):** Automatically audits in-transit shipments every 30 minutes to flag overdue deliveries.
- **High-Speed Caching & Query Optimization:** Uses Redis caching with write-through invalidation on KPI analytics endpoints and `select_related` + composite PostgreSQL indexes to eliminate N+1 queries.
- **Security & API Docs:** JWT authentication (`SimpleJWT`), custom Role-Based Access Control (`IsManagerOrReadOnly`), API rate throttling, and interactive OpenAPI/Swagger documentation (`/api/docs/`).

## Quick Start with Docker Compose
```bash
cp .env.example .env
docker-compose up --build -d
docker-compose exec web python manage.py createsuperuser
```
Access Swagger UI at: `http://localhost:8000/api/docs/`

## Running Automated Tests
```bash
docker-compose exec web pytest
```
