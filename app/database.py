import os
import motor.motor_asyncio
from dotenv import load_dotenv

load_dotenv()

client = motor.motor_asyncio.AsyncIOMotorClient(os.environ["MONGODB_URL"], uuidRepresentation="standard")
db = client['Bushe']


async def fetch_one(collection, courier_id):
    document = await db[collection].find_one({"courier_id": courier_id})
    return document


async def fetch_all(collection, model):
    items = []
    cursor = db[collection].find({})
    async for document in cursor:
        items.append(model(**document))
    return items


async def fetch_all_id(collection):
    items = []
    cursor = db[collection].find({})
    async for document in cursor:
        items.append(document)
    return items


async def create_one(collection, model):
    document = model
    result = await db[collection].insert_one(document)
    return document


async def update_one(collection, courier_id, field, value):
    document = await db[collection].update_one({"courier_id": courier_id}, {"$set": {field: value}})
    return document


async def update_order_status(state, location):
    await db["orders"].update_one({"location": location}, {"$set": {"state": state}})
    document = await db["orders"].find_one({"location": location})
    return document


async def remove_one(collection, courier_id):
    await db[collection].delete_one({"courier_id": courier_id})
    return True
