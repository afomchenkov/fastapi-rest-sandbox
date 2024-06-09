from celery.result import AsyncResult
from crud import crud_error_message, crud_get_user, crud_get_weather
from database import engine
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from models import Base
from tasks import task_add_user, task_add_weather
from enum import Enum
import httpx
import logging
import cache

# import os
# from dotenv import load_dotenv
# load_dotenv()
# CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND')

fake_items_db = [{"item_name": "Foo"}, {"item_name": "Bar"}, {"item_name": "Baz"}]


class ModelName(str, Enum):
    alexnet = "alexnet"
    resnet = "resnet"
    lenet = "lenet"


logging.basicConfig(
    format="%(asctime)s - %(message)s", datefmt="%d-%b-%y %H:%M:%S", level="DEBUG"
)
log = logging.getLogger(__name__)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="FastAPI Redis Celery Sandbox")


@app.on_event("startup")
async def startup_event():
    log.debug("Server started: http://0.0.0.0:8000")
    keys = cache.Keys()
    await cache.initialize_redis(keys)


@app.get("/")
async def healthcheck():
    """
    Healthcheck
    """
    log.debug("Healthcheck called")
    return {"running": True}


@app.get("/files/{file_path:path}")
async def read_file(file_path: str):
    return {"file_path": file_path}


# query params: http://127.0.0.1:8000/items/?skip=0&limit=10
@app.get("/items/")
async def read_items(skip: int = 0, limit: int = 10):
    return fake_items_db[skip : skip + limit]


@app.get("/items/{item_id}")
async def read_item(item_id: str, q: str | None = None):
    if q:
        return {"item_id": item_id, "q": q}
    return {"item_id": item_id}


@app.post("/refresh")
async def refresh(
    background_tasks: BackgroundTasks, keys: cache.Keys = Depends(cache.make_keys)
):
    async with httpx.AsyncClient() as client:
        data = await client.get(cache.SENTIMENT_API_URL)

    await cache.persist(keys, data.json())
    data = cache.calculate_three_hours_of_data(keys)
    background_tasks.add_task(cache.set_cache, data, keys)

    return data


@app.get("/is-bitcoin-lit")
async def bitcoin(
    background_tasks: BackgroundTasks, keys: cache.Keys = Depends(cache.make_keys)
):
    data = cache.get_cache(keys)

    if not data:
        data = cache.calculate_three_hours_of_data(keys)
        background_tasks.add_task(cache.set_cache, data, keys)

    return data


@app.post("/users/{count}/{delay}", status_code=201)
def add_user(count: int, delay: int):
    """
    Get random user data from randomuser.me/api and
    add database using Celery. Uses Redis as Broker
    and Postgres as Backend.
    """
    task = task_add_user.delay(count, delay)
    return {"task_id": task.id}


@app.post("/users/{count}", status_code=201)
def add_user_default_delay(count: int):
    """
    Get random user data from randomuser.me/api add
    database using Celery. Uses Redis as Broker
    and Postgres as Backend. (Delay = 10 sec)
    """
    return add_user(count, 10)


@app.get("/users/{user_id}")
def get_user(user_id: int):
    """
    Get user from database.
    """
    user = crud_get_user(user_id)
    if user:
        return user
    else:
        raise HTTPException(404, crud_error_message(f"No user found for id: {user_id}"))


@app.post("/weathers/{city}/{delay}", status_code=201)
def add_weather(city: str, delay: int):
    """
    Get weather data from api.collectapi.com/weather
    and add database using Celery. Uses Redis as Broker
    and Postgres as Backend.
    """
    task = task_add_weather.delay(city, delay)
    return {"task_id": task.id}


@app.post("/weathers/{city}", status_code=201)
def add_weather_default_delay(city: str):
    """
    Get weather data from api.collectapi.com/weather
    and add database using Celery. Uses Redis as Broker
    and Postgres as Backend. (Delay = 10 sec)
    """
    return add_weather(city, 10)


@app.get("/weathers/{city}")
def get_weather(city: str):
    """
    Get weather from database.
    """
    weather = crud_get_weather(city.lower())
    if weather:
        return weather
    else:
        raise HTTPException(
            404, crud_error_message(f"No weather found for city: {city}")
        )


@app.get("/tasks/{task_id}")
def task_status(task_id: str):
    """
    Get task status.
    PENDING (waiting for execution or unknown task id)
    STARTED (task has been started)
    SUCCESS (task executed successfully)
    FAILURE (task execution resulted in exception)
    RETRY (task is being retried)
    REVOKED (task has been revoked)
    """
    task = AsyncResult(task_id)
    state = task.state

    if state == "FAILURE":
        error = str(task.result)
        response = {
            "state": state,
            "error": error,
        }
    else:
        response = {
            "state": state,
        }
    return response
