from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, REAL
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    name = Column(String(50))
    surname = Column(String(50))
    password = Column(String(50))
    email = Column(String(30), unique=True)


class Category(Base):
    __tablename__ = 'category'
    id = Column(Integer, primary_key=True)
    category_name = Column(String(50))
    owner_id = Column(Integer, ForeignKey('user.id', ondelete='CASCADE'))

    owner = relationship('User')


class Transaction(Base):
    __tablename__ = 'transaction'
    id = Column(Integer, primary_key=True)
    description = Column(String(100))

    category_id = Column(Integer, ForeignKey('category.id', ondelete='CASCADE'))
    owner_id = Column(Integer, ForeignKey('user.id', ondelete='CASCADE'))

    category_type = Column(Integer)
    date = Column(DateTime)
    amount = Column(REAL)

    category = relationship('Category')
    owner = relationship('User')