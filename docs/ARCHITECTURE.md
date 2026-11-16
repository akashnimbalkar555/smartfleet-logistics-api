# SmartFleet – System Architecture & Engineering Guide

> For the downloadable offline PDF version, see [ARCHITECTURE.pdf](./ARCHITECTURE.pdf).

## 1. High-Level System Architecture

```mermaid
flowchart LR
    Client["Client / Swagger UI"] -->|JWT Auth + REST| Web["Web Container\n(Django + DRF + Gunicorn)"]
    Web <-->|ORM / Indexes| DB[("PostgreSQL 16\n(Primary DB)")]
    Web <-->|KPI Cache / Broker| Redis[("Redis 7\n(Cache & Broker)")]
    Redis -->|Async Tasks| Worker["Celery Worker\n(Pandas + ReportLab)"]
    Beat["Celery Beat\n(Every 30 Mins)"] -->|Scheduled Task| Redis
    Worker <-->|Atomic Writes| DB