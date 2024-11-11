import pandas as pd
from sqlalchemy import create_engine
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
import pickle
from category_encoders import TargetEncoder
from catboost import CatBoostClassifier

db_url = "postgresql://robot-startml-ro:pheiph0hahj1Vaif@postgres.lab.karpov.courses:6432/startml"
engine = create_engine(db_url)

def load_user_data():
    query = """
    SELECT user_id, age, gender, city, country, exp_group, os, source
    FROM user_data;
    """

    conn = engine.connect().execution_options(stream_results=True)
    user_data = pd.read_sql(query, conn)
    conn.close()

    return user_data

def load_post_data():
    query = """
    SELECT post_id, text, topic
    FROM post_text_df;
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

post_data = post_data.drop(columns=['text'])
feed_data = feed_data.drop(columns=['timestamp'])

def merge_data(user_data, post_data, feed_data):

    merged_data = feed_data.merge(user_data, on='user_id', how='left')
    merged_data = merged_data.merge(post_data, on='post_id', how='left')
    
    return merged_data

merged_data = merge_data(user_data, post_data, feed_data)
merged_data = merged_data.drop(columns=['user_id', 'post_id'])

categorical_features = ['city', 'source', 'os', 'gender', 'country', 'exp_group', 'topic']

# categorical_features_OHE = ['source', 'os', 'gender', 'country', 'exp_group', 'topic']
# categorical_features_TE  = ['city']

# t = [
#     ('OneHotEncoder', OneHotEncoder(), categorical_features_OHE),
#     ('MeanTargetEncoder', TargetEncoder(), categorical_features_TE)
# ]

# column_transformer = ColumnTransformer(transformers=t)

X = merged_data.drop(columns=['target'])
y = merged_data['target']

# X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# model = Pipeline(steps=[
#     ('column_transformer', column_transformer),
#     ('classifier', xgb.XGBClassifier(objective='binary:logistic', eval_metric='logloss'))
# ])

model = CatBoostClassifier()

model.fit(X, y, categorical_features)

filename = 'model.pkl'
pickle.dump(model, open(filename, 'wb'))
