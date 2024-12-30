from sqlalchemy import Column, Integer, String, desc, func

from src.database.database import Base, SessionLocal



class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True)
    age = Column(Integer)
    city = Column(String)
    country = Column(String)
    exp_group = Column(Integer)
    gender = Column(Integer)
    os = Column(String)
    source = Column(String)



if __name__ == "__main__":
    session = SessionLocal()

    results = (
        session.query(User.country, User.os, func.count())
        .filter(User.exp_group == 3)
        .group_by(User.country, User.os)
        .having(func.count() > 100)
        .order_by(desc(func.count()))
        .all()
    )

    print(results)
