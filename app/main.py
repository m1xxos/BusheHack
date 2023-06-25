import math
import random
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.model import (
    Courier,
    Order,
    OrderGroup
)
from app.database import (
    fetch_one,
    fetch_all,
    create_one,
    update_order_status,
    remove_one,
    db, update_one
)

app = FastAPI()

origins = [
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def calculate_distance(point1, point2):
    # Вычисление расстояния между двумя точками
    lat1, lon1 = point1['latitude'], point1['longitude']
    lat2, lon2 = point2['latitude'], point2['longitude']
    radius = 6371  # Радиус Земли в километрах
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = radius * c
    return distance


def group_delivery_points(delivery_points, num_groups, max_iterations):
    # Инициализация групп точек доставки
    groups = [[] for _ in range(num_groups)]

    # Распределение точек доставки в группы
    for point in delivery_points:
        min_distance = float('inf')
        best_group = None

        for i, group in enumerate(groups):
            distance = sum(calculate_distance(point, p) for p in group)
            if distance < min_distance:
                min_distance = distance
                best_group = i

        groups[best_group].append(point)

    # Оптимизация группировки точек доставки с помощью алгоритма симулированного отжига
    best_distance = sum(sum(calculate_distance(point1, point2) for point1 in group for point2 in group)
                        for group in groups)

    for _ in range(max_iterations):
        group_idx = random.randint(0, num_groups - 1)
        point_idx = random.randint(0, len(groups[group_idx]) - 1)
        point = groups[group_idx].pop(point_idx)

        min_distance = float('inf')
        best_group = None

        for i, group in enumerate(groups):
            distance = sum(calculate_distance(point, p) for p in group)
            if distance < min_distance:
                min_distance = distance
                best_group = i

        groups[best_group].append(point)

        total_distance = sum(sum(calculate_distance(point1, point2) for point1 in group for point2 in group)
                             for group in groups)

        if total_distance < best_distance:
            best_distance = total_distance
        else:
            groups[best_group].remove(point)
            groups[group_idx].append(point)

    return groups


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/couriers", response_model=list[Courier])
async def get_couriers():
    couriers = await fetch_all("couriers", Courier)
    return couriers


@app.post("/couriers", response_model=Courier)
async def create_courier(courier: Courier):
    courier = await create_one("couriers", courier.dict())
    return courier


@app.get("/couriers/{courier_id}/orders", response_model=list[Order])
async def get_courier_orders(courier_id: int):
    items = []
    orders = db["orders"].find({"courier_id": courier_id})
    async for document in orders:
        items.append(Order(**document))
    return items


@app.get("/couriers/{courier_id}/", response_model=Courier)
async def get_courier(courier_id: int):
    courier = await fetch_one("couriers", courier_id)
    return courier


@app.get("/orders", response_model=list[Order])
async def get_orders():
    orders = await fetch_all("orders", Order)
    return orders


@app.get("/order_groups", response_model=list[OrderGroup])
async def get_orders():
    orders = await fetch_all("order_groups", OrderGroup)
    return orders


@app.post("/orders", response_model=Order)
async def create_order(order: Order):
    order = await create_one("orders", order.dict())
    return order


@app.post("/optimize_orders")
async def optimize_orders(num_groups: int):
    orders = await fetch_all("orders", Order)
    try:
        groups = group_delivery_points([order.dict() for order in orders if order.state != "processing"], num_groups, 1000)
        for l in groups:
            for d in l:
                d.update((k, "processing") for k, v in d.items() if v == "new")
                new_state = await update_order_status("processing", d["location"])
        orders = [await create_one("order_groups", OrderGroup(courier_id=None, orders=group, state="processing").dict()) for group in groups]
    except Exception as e:
        raise HTTPException(404, f"нету новых заказов {e}")
    return groups


@app.get("/assign_couriers")
async def assign_couriers():
    couriers_list = []
    couriers = db["couriers"].find({"available": True})
    orders = await db["order_groups"].find({"courier_id": None}).to_list(None)
    i = 0
    try:
        async for courier in couriers:
            new_orders = []
            for order in orders[i]["orders"]:
                new_order = await db["orders"].update_one({"location": order["location"]}, {"$set": {"state": "assigned", "courier_id": courier["courier_id"]}})
                new_order = await db["orders"].find_one({"location": order["location"]})
                new_orders.append(new_order)
            new_courier = await db["couriers"].update_one({"courier_id": courier["courier_id"]}, {"$set": {"available": False, "orders": new_orders}})
            new_order_group = await db["order_groups"].update_one({"_id": orders[i]['_id']}, {"$set": {"courier_id": courier["courier_id"], "state": "assigned", "orders": new_orders}})
            couriers_list.append(new_courier.raw_result)
            i += 1
    except Exception as e:
        raise HTTPException(404, f"нету курьеров или заказов чё, {e}")
    return "Заказы распределены"


@app.get("/reset_orders")
async def reset_orders():
    orders = await db["orders"].update_many({}, {"$set": {"state": "new", "courier_id": None}})
    return "Заказы обновлены"


@app.get("/reset_couriers")
async def reset_couriers():
    courier = await db["couriers"].update_many({}, {"$set": {"available": True, "orders": []}})
    return "курьеры обновлены"


@app.get("/reset_order_groups")
async def reset_order_groups():
    order_groups = await db["order_groups"].drop()
    return "группы заказов обновлены"
