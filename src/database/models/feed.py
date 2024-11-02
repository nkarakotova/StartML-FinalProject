from sqlalchemy import Column, Integer, String, TIMESTAMP, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
from user import User
from post import Post



class Feed(Base):
    __tablename__ = "feed_action"

    action = Column(String)
    post_id = Column(Integer, ForeignKey("post.id"), primary_key=True)
    post = relationship("Post")
    time = Column(TIMESTAMP)
    user_id = Column(Integer, ForeignKey("user.id"), primary_key=True)
    user = relationship("User")
