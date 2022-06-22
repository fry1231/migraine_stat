from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from .database import Base


class User(Base):
    __tablename__ = "users"

    telegram_id = Column(Integer, primary_key=True, index=True)
    last_notified = Column(DateTime, default=datetime.min)
    notify_every = Column(Integer, default=-1)
    first_name = Column(String)
    user_name = Column(String)

    paincases = relationship("PainCase", back_populates="owner")
    druguses = relationship("DrugUse", back_populates="owner")


class PainCase(Base):
    __tablename__ = "pains"

    id = Column(Integer, primary_key=True, index=True)
    datetime = Column(DateTime)
    durability = Column(Integer)
    intensity = Column(Integer)
    aura = Column(Boolean)
    provocateurs = Column(String)
    symptoms = Column(String)
    description = Column(String)
    owner_id = Column(Integer, ForeignKey("users.telegram_id"))

    owner = relationship("User", back_populates="paincases")
    medecine_taken = relationship("DrugUse", back_populates="paincase")


class DrugUse(Base):
    __tablename__ = "druguses"

    id = Column(Integer, primary_key=True, index=True)
    datetime = Column(DateTime)
    amount = Column(Integer)
    owner_id = Column(Integer, ForeignKey("users.telegram_id"))
    drugname = Column(String, ForeignKey("drugs.name"))
    paincase_id = Column(Integer, ForeignKey("pains.id"))

    drug = relationship("Drug", uselist=False)
    owner = relationship("User", back_populates="druguses")
    paincase = relationship("PainCase", back_populates="medecine_taken")


class Drug(Base):
    __tablename__ = "drugs"

    name = Column(String, primary_key=True, index=True)
    daily_max = Column(Integer)
    is_painkiller = Column(Boolean)
    is_temp_reducer = Column(Boolean)
