from typing import List

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from datetime import datetime
from sqlalchemy import create_engine
import pandas as pd
import os
import pickle
import hashlib

from src.database.database import SessionLocal
from src.database.models.user import User
from src.database.models.post import Post
from src.database.models.feed import Feed
from src.schemas.schema import UserGet, PostGet, FeedGet, Response

app = FastAPI()

SQLALCHEMY_DATABASE_URL = f"postgresql://{os.getenv('PG_USER', '')}:{os.getenv('PG_PASS', '')}@{os.getenv('PG_HOST')}:{os.getenv('PG_PORT')}/{os.getenv('PG_DB')}"



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



# @app.get("/post/recommendations/", response_model=List[PostGet])
# def get_post_recommendations(id: int, limit: int = 10, db: Session = Depends(get_db)):
#     result = db.query(
#         Post.id, Post.text, Post.topic
#     ).join(
#         Feed, Feed.post_id == Post.id 
#     ).filter(
#         Feed.action == "like"
#     ).group_by(
#         Post.id
#     ).order_by(
#         desc(func.count(Feed.post_id))
#     ).limit(limit).all()

#     return result



def get_model_path(path: str) -> str:
    if os.environ.get("IS_LMS") == "1":
        MODEL_PATH = '/workdir/user_input/model'
    else:
        MODEL_PATH = path
    return MODEL_PATH

def load_models():
    model_control_path = get_model_path("src/model/ml_model/model_control.pkl")
    model_control = pickle.load(open(model_control_path, 'rb'))

    model_test_path = get_model_path("src/model/dl_model/model_test.pkl")
    model_test = pickle.load(open(model_test_path, 'rb'))

    return model_control, model_test

def batch_load_sql(query: str) -> pd.DataFrame:
    CHUNKSIZE = 200000
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    conn = engine.connect().execution_options(stream_results=True)
    chunks = []
    for chunk_dataframe in pd.read_sql(query, conn, chunksize=CHUNKSIZE):
        chunks.append(chunk_dataframe)
    conn.close()
    return pd.concat(chunks, ignore_index=True)

def load_features():
    user_query = """
    SELECT * 
    FROM user_data;
    """
    users = batch_load_sql(user_query)

    post_query = """
    SELECT *
    FROM post_process_features;
    """
    posts = batch_load_sql(post_query)

    post_dl_query = """
    SELECT *
    FROM post_process_features_dl;
    """
    posts_dl = batch_load_sql(post_dl_query)

    feed_query = """
    SELECT distinct user_id, post_id
    FROM feed_data
    WHERE action = 'like';
    """
    likes = batch_load_sql(feed_query)

    return users, posts, posts_dl, likes


def get_exp_group(user_id: int) -> str:
    temp_exp_group = int(int(hashlib.md5((str(user_id) + 'my_salt').encode()).hexdigest(), 16) % 100)
    if temp_exp_group <= 50:
        exp_group = 'control'
    elif temp_exp_group > 50:
        exp_group = 'test'
    return exp_group


model_control, model_test = load_models()
users_features, posts_ml_features, posts_dl_features, likes = load_features()

def get_recommended_posts(id: int, time: datetime, limit: int):

    exp_group = get_exp_group(id)
    if exp_group == 'control':
        posts_features = posts_ml_features
        model = model_control
    elif exp_group == 'test':
        posts_features = posts_dl_features
        model = model_test
    else:
        raise HTTPException(status_code=404, detail="group not found")

    user_features = users_features.loc[users_features.user_id == id]
    user_features = user_features.drop('user_id', axis=1)
    
    user_features['key'] = 1
    posts_features['key'] = 1

    user_posts_features = posts_features.drop('text', axis=1).merge(user_features, on='key').drop('key', axis=1).set_index('post_id')
    user_posts_features["hour"] = time.hour

    categorical_features = ['topic', 'hour', 'city', 'country', 'exp_group', 'gender', 'source', 'os']

    all_features = categorical_features + [col for col in user_posts_features.columns if col not in categorical_features]
    user_posts_features = user_posts_features[all_features]
    
    predicts = model.predict_proba(user_posts_features)[:, 1]
    user_posts_features['predicts'] = predicts
    
    user_likes = likes[likes.user_id == id].post_id.values

    user_not_likes = user_posts_features[~user_posts_features.index.isin(user_likes)]
    
    recommended_posts = user_not_likes.sort_values('predicts')[-limit:].index
    
    return {"exp_group": exp_group,
            "recommendations":
    [
        PostGet(**{
            "id":    i,
            "text":  posts_features[posts_features.post_id == i].text.values[0],
            "topic": posts_features[posts_features.post_id == i].topic.values[0]
        }) for i in recommended_posts
    ]}

@app.get("/post/recommendations/", response_model=Response)
def recommended_posts(id: int, time: datetime, limit: int = 10, db: Session = Depends(get_db)) -> Response:
    result = db.query(User).filter(User.id==id).first()
    if result is None:
        raise HTTPException(status_code=404, detail="user not found")
    
    return get_recommended_posts(id, time, limit)
