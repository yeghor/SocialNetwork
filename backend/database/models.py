from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

class User(Base):
    pass

class Post(Base):
    pass

class Reply(Base):
    pass