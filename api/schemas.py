from pydantic import BaseModel
from datetime import datetime


class UserIn(BaseModel):
    first_name: str
    last_name: str
    mail: str
    age: int
    address: str


class UserOut(BaseModel):
    first_name: str
    last_name: str


class WeatherIn(BaseModel):
    city: str
    date: str
    day: str
    description: str
    degree: float


class WeatherOut(BaseModel):
    date: str
    day: str
    description: str
    degree: float


class User(BaseModel):
    id: int
    name: str = "John Doe"
    signup_ts: datetime | None = None
    friends: list[int] = []

# Example:
# external_data = {
#     "id": "123",
#     "signup_ts": "2017-06-01 12:22",
#     "friends": [1, "2", b"3"],
# }
# user = User(**external_data)
