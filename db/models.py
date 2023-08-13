from sqlalchemy import \
    Boolean, Column, ForeignKey, Integer, Float, String, DateTime, Time, Date, BigInteger, SmallInteger
from sqlalchemy.orm import relationship
import datetime
from pydantic import BaseModel
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import declarative_mixin


Base = declarative_base()


class NewUser(BaseModel):
    """
    Used for serialization for rabbitmq
    """
    first_name: str = ''
    last_name: str = None
    user_name: str = None


class User(Base):
    __tablename__ = "users"

    telegram_id = Column(BigInteger, primary_key=True, index=True, unique=True)   # Add -1 user to match the common (owner_id=-1) drugs owner
    last_notified = Column(DateTime, default=datetime.datetime.min)
    notify_every = Column(SmallInteger, default=-1)
    first_name = Column(String)
    user_name = Column(String)
    joined = Column(Date)
    timezone = Column(String, default='Europe/Moscow')
    language = Column(String(2), default='ru')
    utc_notify_at = Column(Time, default=datetime.time(18, 0))

    paincases = relationship("PainCase", cascade="all, delete-orphan")
    druguses = relationship("DrugUse", cascade="all, delete-orphan")
    drugs = relationship("Drug", cascade="all, delete-orphan")


@declarative_mixin
class _PainCase:
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date)
    durability = Column(SmallInteger)
    intensity = Column(SmallInteger)
    aura = Column(Boolean)
    provocateurs = Column(String)
    symptoms = Column(String)
    description = Column(String)


class PainCase(_PainCase, Base):
    __tablename__ = "pains"
    owner_id = Column(BigInteger, ForeignKey("users.telegram_id"))
    medecine_taken = relationship("DrugUse", lazy='joined', cascade="all, delete-orphan")


@declarative_mixin
class _DrugUse:
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date)
    amount = Column(String)
    drugname = Column(String)


class DrugUse(_DrugUse, Base):
    __tablename__ = "druguses"
    owner_id = Column(BigInteger, ForeignKey("users.telegram_id"))
    paincase_id = Column(Integer, ForeignKey("pains.id"))


class Drug(Base):
    __tablename__ = "drugs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    daily_max = Column(Float)
    is_painkiller = Column(Boolean)
    is_temp_reducer = Column(Boolean)

    owner_id = Column(BigInteger, ForeignKey("users.telegram_id"))


# Tables with information from deleted users, for statistics and reports
class SavedPainCase(_PainCase, Base):
    __tablename__ = "saved_pains"

    owner_id = Column(BigInteger)
    medecine_taken = relationship("SavedDrugUse", lazy='joined', cascade='all, delete-orphan')

    __mapper_args__ = {
        "polymorphic_identity": "SavedPainCase",
    }

    @staticmethod
    def copy_from(paincase: PainCase):
        return SavedPainCase(
            date=paincase.date,
            durability=paincase.durability,
            intensity=paincase.intensity,
            aura=paincase.aura,
            provocateurs=paincase.provocateurs,
            symptoms=paincase.symptoms,
            description=paincase.description,
            owner_id=paincase.owner_id,
            medecine_taken=[SavedDrugUse.copy_from(du) for du in paincase.medecine_taken]
        )


class SavedDrugUse(_DrugUse, Base):
    __tablename__ = "saved_druguses"

    owner_id = Column(BigInteger)
    paincase_id = Column(Integer, ForeignKey("saved_pains.id"))

    @staticmethod
    def copy_from(druguse: DrugUse):
        return SavedDrugUse(
            date=druguse.date,
            amount=druguse.amount,
            drugname=druguse.drugname,
            owner_id=druguse.owner_id
        )
