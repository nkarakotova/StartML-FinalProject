from sqlalchemy import Column, Integer, String, TIMESTAMP, ForeignKey
from sqlalchemy.orm import relationship
from database.database import Base
from database.models.user import User
from database.models.post import Post



class Feed(Base):
    __tablename__ = "feed_action"

    action = Column(String)
    post_id = Column(Integer, ForeignKey("post.id"), primary_key=True)
    post = relationship("Post")
    time = Column(TIMESTAMP)
    user_id = Column(Integer, ForeignKey("user.id"), primary_key=True)
    user = relationship("User")
