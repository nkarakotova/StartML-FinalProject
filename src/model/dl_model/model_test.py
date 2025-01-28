import os
import pandas as pd
from sqlalchemy import create_engine
import pickle
from catboost import CatBoostClassifier

db_url = f"postgresql://{os.getenv('PG_USER', '')}:{os.getenv('PG_PASS', '')}@{os.getenv('PG_HOST')}:{os.getenv('PG_PORT')}/{os.getenv('PG_DB')}"
engine = create_engine(db_url)

def load_user_data():
    query = """
    SELECT *
    FROM user_data;
    """

    conn = engine.connect().execution_options(stream_results=True)
    user_data = pd.read_sql(query, conn)
    conn.close()

    return user_data

def load_post_data():
    query = """
    SELECT *
    FROM post_process_features_dl;
    """

    conn = engine.connect().execution_options(stream_results=True)
    post_data = pd.read_sql(query, conn)
    conn.close()
    
    return post_data

def load_feed_data():
    CHUNKSIZE = 100000

    query = """
    SELECT timestamp, user_id, post_id,
    CASE 
        WHEN action = 'like' THEN 1
        ELSE target
    END AS target
    FROM feed_data
    WHERE NOT (action = 'view' AND target = 1)
    LIMIT 5000000;
    """

    conn = engine.connect().execution_options(stream_results=True)
    chunks = []

    for chunk_dataframe in pd.read_sql(query, conn, chunksize=CHUNKSIZE):
        chunks.append(chunk_dataframe)
    conn.close()

    return pd.concat(chunks, ignore_index=True)

user_data = load_user_data()
post_data = load_post_data()
feed_data = load_feed_data()

# Различия с ml_model (обработка в research/research_text.ipynb)

post_data = post_data.drop(columns=['text'])

# !Различия с ml_model

feed_data['timestamp'] = pd.to_datetime(feed_data['timestamp'])

feed_data['hour'] = feed_data['timestamp'].dt.hour
feed_data = feed_data.drop(columns=['timestamp'])

def merge_data(user_data, post_data, feed_data):

    merged_data = feed_data.merge(user_data, on='user_id', how='left')
    merged_data = merged_data.merge(post_data, on='post_id', how='left')
    
    return merged_data

merged_data = merge_data(user_data, post_data, feed_data)
merged_data = merged_data.drop(columns=['user_id', 'post_id'])

categorical_features = ['topic', 'hour', 'city', 'country', 'exp_group', 'gender', 'source', 'os']

X = merged_data.drop(columns=['target'])
all_features = categorical_features + [col for col in X.columns if col not in categorical_features]
X = X[all_features]

y = merged_data['target']

print(X['topic'].unique)

model = CatBoostClassifier(iterations=100,
                           depth=6,
                           learning_rate=0.1)

model.fit(X, y, categorical_features)

filename = 'model_test.pkl'
pickle.dump(model, open(filename, 'wb'))
