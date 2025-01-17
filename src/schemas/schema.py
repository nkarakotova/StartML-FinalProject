from typing import List
from datetime import datetime

from pydantic import BaseModel


class UserGet(BaseModel):
    id: int
    age: int
    city: str
    country: str
    exp_group: int
    gender: int
    os: str
    source: str

    class Config:
        orm_mode = True


class PostGet(BaseModel):
    id: int
    text: str
    topic: str

    class Config:
        orm_mode = True


class Response(BaseModel):
    exp_group: str
    recommendations: List[PostGet]


class FeedGet(BaseModel):
    action: str
    post_id: int
    post: PostGet
    time: datetime
    user_id: int
    user: UserGet

    class Config:
        orm_mode = True
