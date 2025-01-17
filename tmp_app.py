from fastapi import FastAPI
from datetime import datetime
from sqlalchemy import create_engine
import pandas as pd
import pickle
import hashlib

from schema import PostGet, Response

app = FastAPI()



def load_models():
    model_control_path = "/workdir/user_input/model_control"
    model_control = pickle.load(open(model_control_path, 'rb'))

    model_test_path = "/workdir/user_input/model_test"
    model_test = pickle.load(open(model_test_path, 'rb'))

    return model_control, model_test

def batch_load_sql(query: str) -> pd.DataFrame:
    CHUNKSIZE = 200000
    engine = create_engine(
        "postgresql://robot-startml-ro:pheiph0hahj1Vaif@"
        "postgres.lab.karpov.courses:6432/startml"
    )
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
        return

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
def recommended_posts(id: int, time: datetime, limit: int = 10) -> Response:
    return get_recommended_posts(id, time, limit)
