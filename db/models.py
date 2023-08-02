from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from pydantic import BaseModel

from .database import Base


class NewUser(BaseModel):
    """
    Used for serialization for rabbitmq
    """
    first_name: str = ''
    last_name: str = None
    user_name: str = None


class User(Base):
    __tablename__ = "users"

    telegram_id = Column(Integer, primary_key=True, index=True)   # Add -1 user to match the common (owner_id=-1) drugs owner
    last_notified = Column(DateTime, default=datetime.min)
    notify_every = Column(Integer, default=-1)
    first_name = Column(String)
    user_name = Column(String)

    paincases = relationship("PainCase", back_populates="owner")
    druguses = relationship("DrugUse", back_populates="owner")
    drugs = relationship("Drug", back_populates="owner")


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
    amount = Column(Integer)    # Change to string while migrating to postgres
    owner_id = Column(Integer, ForeignKey("users.telegram_id"))
    drugname = Column(String, ForeignKey("drugs.name"))   # Foreign key mismatch, should be drugs.id
    paincase_id = Column(Integer, ForeignKey("pains.id"))

    drug = relationship("Drug", uselist=False)
    owner = relationship("User", back_populates="druguses")
    paincase = relationship("PainCase", back_populates="medecine_taken")


class Drug(Base):
    __tablename__ = "drugs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    daily_max = Column(Integer)
    is_painkiller = Column(Boolean)
    is_temp_reducer = Column(Boolean)
    owner_id = Column(Integer, ForeignKey("users.telegram_id"))

    owner = relationship("User", back_populates="drugs")
