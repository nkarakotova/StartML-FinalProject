from typing import List

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from database.database import SessionLocal
from database.models.user import User
from database.models.post import Post
from database.models.feed import Feed
from schemas.schema import UserGet, PostGet, FeedGet

app = FastAPI()



def get_db():
    with SessionLocal() as db:
        return db



@app.get("/user/{id}", response_model=UserGet)
def get_user(id: int, db: Session = Depends(get_db)):
    result = db.query(User).filter(User.id==id).first()
    if result is None:
        raise HTTPException(status_code=404, detail="user not found")
    
    return result



@app.get("/post/{id}", response_model=PostGet)
def get_post(id: int, db: Session = Depends(get_db)):
    result = db.query(Post).filter(Post.id==id).first()
    if result is None:
        raise HTTPException(status_code=404, detail="post not found")
    
    return result



@app.get("/user/{id}/feed", response_model=List[FeedGet])
def get_user_feed(id: int, limit: int = 10, db: Session = Depends(get_db)):
    result = db.query(Feed).filter(Feed.user_id==id).order_by(desc(Feed.time)).limit(limit).all()
    if result is None:
        raise HTTPException(status_code=200)
    
    return result



@app.get("/post/{id}/feed", response_model=List[FeedGet])
def get_post_feed(id: int, limit: int = 10, db: Session = Depends(get_db)):
    result = db.query(Feed).filter(Feed.post_id==id).order_by(desc(Feed.time)).limit(limit).all()
    if result is None:
        raise HTTPException(status_code=200)
    
    return result



@app.get("/post/recommendations/", response_model=List[PostGet])
def get_post_recommendations(id: int, limit: int = 10, db: Session = Depends(get_db)):
    result = db.query(
        Post.id, Post.text, Post.topic
    ).join(
        Feed, Feed.post_id == Post.id 
    ).filter(
        Feed.action == "like"
    ).group_by(
        Post.id
    ).order_by(
        desc(func.count(Feed.post_id))
    ).limit(limit).all()

    return result
