"""Datasets router — returns available dataset catalogue."""
from fastapi import APIRouter
from typing import List
from models.schemas import DatasetInfo

router = APIRouter(tags=["datasets"])

DATASETS: List[DatasetInfo] = [
    DatasetInfo(id="ireland", label="Ireland Constellation", flag="🇮🇪",
                description="Ireland telecom subscriber & revenue analytics", available=True),
    DatasetInfo(id="mi", label="MI Constellation", flag="🇺🇸",
                description="Market Intelligence Constellation", available=True),
    DatasetInfo(id="germany", label="Germany Constellation", flag="🇩🇪",
                description="Germany telecom analytics", available=True),
    DatasetInfo(id="uk", label="UK Constellation", flag="🇬🇧",
                description="UK market analytics", available=True),
    DatasetInfo(id="finance", label="Finance Analytics", flag="💹",
                description="Enterprise finance & P&L analytics", available=True),
    DatasetInfo(id="customer", label="Customer Analytics", flag="👥",
                description="Customer 360 & segmentation analytics", available=True),
]


@router.get("/datasets", response_model=List[DatasetInfo])
async def list_datasets():
    return DATASETS
