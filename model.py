from pydantic import BaseModel
from typing import Optional


class Order(BaseModel):
    location: str
    latitude: float
    longitude: float
    fio: str
    items: list[str]
    courier_id: Optional[int] = None
    state: Optional[str] = "new"


class Courier(BaseModel):
    fio: str
    latitude: float
    longitude: float
    available: bool
    orders: Optional[list[Order]] = []
    courier_id: int


class OrderGroup(BaseModel):
    courier_id: Optional[int] = None
    orders: list[Order]
    state: str
