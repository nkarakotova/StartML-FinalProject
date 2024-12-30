from sqlalchemy import Column, Integer, String, desc

from src.database.database import Base, SessionLocal



class Post(Base):
    __tablename__ = "post"

    id = Column(Integer, primary_key=True)
    text = Column(String)
    topic = Column(String)



if __name__ == "__main__":
    session = SessionLocal()

    results = (
        session.query(Post.id)
        .filter(Post.topic == "business")
        .order_by(desc(Post.id))
        .limit(10)
        .all()
    )

    res = [x.id for x in results]
    print(res)
