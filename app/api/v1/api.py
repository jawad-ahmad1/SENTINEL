"""
V1 API router aggregator — wires all endpoint modules together.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, employees, reports

api_router = APIRouter()

# Auth (login, refresh, user management)
api_router.include_router(auth.router)

# Employees, scan, breaks
api_router.include_router(employees.router)

# Reports, analytics, health, status
api_router.include_router(reports.router)
