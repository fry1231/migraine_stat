from sqlalchemy import \
    Boolean, Column, ForeignKey, \
    Integer, Float, String, DateTime, Time, Date, BigInteger, SmallInteger
from sqlalchemy.orm import relationship
import datetime
from sqlalchemy.orm import declarative_base


Base = declarative_base()


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
    latitude = Column(Float)
    longitude = Column(Float)

    paincases = relationship("PainCase", cascade="all, delete-orphan")
    druguses = relationship("DrugUse", cascade="all, delete-orphan")
    drugs = relationship("Drug", cascade="all, delete-orphan")
    pressures = relationship("Pressure", cascade="all, delete-orphan")


class PainCase(Base):
    __tablename__ = "pains"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date)
    durability = Column(SmallInteger)
    intensity = Column(SmallInteger)
    aura = Column(Boolean)
    provocateurs = Column(String)
    symptoms = Column(String)
    description = Column(String)

    owner_id = Column(BigInteger, ForeignKey("users.telegram_id", ondelete='CASCADE'))
    medecine_taken = relationship("DrugUse", lazy='joined', cascade="all, delete-orphan")


class DrugUse(Base):
    __tablename__ = "druguses"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date)
    amount = Column(String)
    drugname = Column(String)

    owner_id = Column(BigInteger, ForeignKey("users.telegram_id", ondelete='CASCADE'))
    paincase_id = Column(Integer, ForeignKey("pains.id", ondelete='CASCADE'))


class Pressure(Base):
    __tablename__ = "pressures"

    id = Column(Integer, primary_key=True, index=True)
    datetime = Column(DateTime)
    systolic = Column(SmallInteger)
    diastolic = Column(SmallInteger)
    pulse = Column(SmallInteger)

    owner_id = Column(BigInteger, ForeignKey("users.telegram_id", ondelete='CASCADE'))


class Drug(Base):
    __tablename__ = "drugs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    daily_max = Column(Float)
    is_painkiller = Column(Boolean)
    is_temp_reducer = Column(Boolean)

    owner_id = Column(BigInteger, ForeignKey("users.telegram_id", ondelete='CASCADE'))


# Tables with information from deleted users, for statistics and reports
class SavedUser(Base):
    __tablename__ = "saved_users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger)
    first_name = Column(String)
    user_name = Column(String)
    joined = Column(Date)
    deleted = Column(Date)
    timezone = Column(String)
    language = Column(String(2))
    latitude = Column(Float)
    longitude = Column(Float)

    @staticmethod
    def copy_from(user: User):
        return SavedUser(
            telegram_id=user.telegram_id,
            first_name=user.first_name,
            user_name=user.user_name,
            joined=user.joined,
            deleted=datetime.date.today(),
            timezone=user.timezone,
            language=user.language,
            latitude=user.latitude,
            longitude=user.longitude
        )


class SavedPainCase(Base):
    __tablename__ = "saved_pains"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date)
    durability = Column(SmallInteger)
    intensity = Column(SmallInteger)
    aura = Column(Boolean)
    provocateurs = Column(String)
    symptoms = Column(String)
    description = Column(String)

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


class SavedDrugUse(Base):
    __tablename__ = "saved_druguses"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date)
    amount = Column(String)
    drugname = Column(String)

    owner_id = Column(BigInteger)
    paincase_id = Column(Integer, ForeignKey("saved_pains.id", ondelete='CASCADE'))

    @staticmethod
    def copy_from(druguse: DrugUse):
        return SavedDrugUse(
            date=druguse.date,
            amount=druguse.amount,
            drugname=druguse.drugname,
            owner_id=druguse.owner_id
        )


class SavedPressure(Base):
    __tablename__ = "saved_pressures"

    id = Column(Integer, primary_key=True, index=True)
    datetime = Column(DateTime)
    systolic = Column(SmallInteger)
    diastolic = Column(SmallInteger)
    pulse = Column(SmallInteger)

    owner_id = Column(BigInteger)

    @staticmethod
    def copy_from(pressure: Pressure):
        return SavedPressure(
            datetime=pressure.datetime,
            systolic=pressure.systolic,
            diastolic=pressure.diastolic,
            pulse=pressure.pulse,
            owner_id=pressure.owner_id
        )


class Statistics(Base):
    __tablename__ = "statistics"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date)
    new_users = Column(SmallInteger)
    deleted_users = Column(SmallInteger)
    active_users = Column(SmallInteger)
    super_active_users = Column(SmallInteger)
    paincases = Column(Integer)
    druguses = Column(Integer)
    pressures = Column(Integer)
    medications = Column(Integer)
