import scheduler
from fastapi import APIRouter
from scheduler import models

router = APIRouter()


@router.get("/")
async def root():
    return {"message": "hello, world"}


@router.get("/health", response_model=models.ServiceHealth)
async def health() -> models.ServiceHealth:
    return models.ServiceHealth(service="scheduler", healthy=True, version=scheduler.__version__)
