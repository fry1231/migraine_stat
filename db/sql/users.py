import datetime

from sqlalchemy import select, func, and_, delete, update

from db.sql import get_session
from db.redis.crud import update_everyday_report
from db.models import User, PainCase, DrugUse, Pressure, SavedPainCase, SavedDrugUse, SavedUser, SavedPressure, Drug
from db.redis.models import PydanticUser


async def create_user(telegram_id: int,
                      first_name: str = None,
                      last_name: str = None,
                      user_name: str = None,
                      language: str = 'ru') -> User:
    async with get_session() as session:
        db_user = User(
            telegram_id=telegram_id,
            first_name=first_name,
            last_name=last_name,
            user_name=user_name,
            joined=datetime.date.today(),
            language=language
        )
        session.add(db_user)
        await update_everyday_report(new_users=[
            PydanticUser(
                telegram_id=telegram_id,
                first_name=first_name,
                last_name=last_name,
                user_name=user_name,
                language=language
            )
        ])
    return db_user


async def get_user(telegram_id: int) -> User | None:
    async with get_session() as session:
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await session.scalars(stmt)
        db_user = result.first()
    return db_user


async def get_users(active: bool = False,
                    super_active: bool = False,
                    return_count: bool = False) -> list[User] | int:
    async with get_session() as session:
        if return_count:
            stmt = select(func.count()).select_from(User)
        else:
            stmt = select(User)

        if super_active:
            date_from = datetime.date.today() - datetime.timedelta(days=31)
            stmt = stmt.where(
                User.telegram_id.in_(
                    select(PainCase.owner_id)
                    .where(PainCase.date >= date_from)
                )
            )
        elif active:
            stmt = stmt.where(
                User.telegram_id.in_(
                    select(PainCase.owner_id)
                )
            )

        if return_count:
            result = await session.scalar(stmt)
            return result

        result = await session.scalars(stmt)
        users = result.unique().all()
    return users


async def get_users_where(last_notified: datetime.datetime = None,
                          notify_every: int = None,
                          joined: datetime.date = None,
                          timezone: str = None,
                          language: str = None,
                          utc_notify_at: datetime.time = None) -> list[User]:
    clauses = []
    if last_notified:
        clauses.append(User.last_notified == last_notified)
    if notify_every:
        clauses.append(User.notify_every == notify_every)
    if joined:
        clauses.append(User.joined == joined)
    if timezone:
        clauses.append(User.timezone == timezone)
    if language:
        clauses.append(User.language == language)
    if utc_notify_at:
        clauses.append(User.utc_notify_at == utc_notify_at)
    async with get_session() as session:
        stmt = select(User).where(*clauses)
        result = await session.scalars(stmt)
        users = result.all()
    return users


async def users_by_notif_hour(notif_hour_utc: int) -> list[User]:
    async with get_session() as session:
        stmt = select(User).where(
            and_(
                User.notify_every != -1,
                User.utc_notify_at == datetime.time(notif_hour_utc, 0)
            )
        )
        result = await session.scalars(stmt)
        user_list = result.all()
    return user_list


async def change_user_props(telegram_id: int,
                            first_name: str = None,
                            user_name: str = None,
                            timezone: str = None,
                            language: str = None,
                            notify_every: int = None,
                            utc_notify_at: datetime.time = None,
                            latitude: float = None,
                            longitude: float = None) -> User:
    async with get_session() as session:
        result = await session.scalars(select(User).where(User.telegram_id == telegram_id))
        db_user = result.first()
        if first_name:
            db_user.first_name = first_name
        if user_name:
            db_user.user_name = user_name
        if timezone:
            db_user.timezone = timezone
        if language:
            db_user.language = language
        if notify_every:
            db_user.notify_every = notify_every
        if utc_notify_at:
            db_user.utc_notify_at = utc_notify_at
        if latitude and longitude:
            db_user.latitude = latitude
            db_user.longitude = longitude
    return db_user


async def delete_user(telegram_id: int) -> bool:
    async with get_session() as session:
        result = await session.scalars(select(User).where(User.telegram_id == telegram_id))
        db_user: User = result.first()

        # Get all user pains, druguses, pressures
        result = await session.scalars(select(PainCase).where(PainCase.owner_id == telegram_id))
        user_pains: list[PainCase] = result.unique().all()
        associated_druguses: list[DrugUse] = []
        for pain in user_pains:
            for du in pain.medecine_taken:
                associated_druguses.append(du)
        # Child druguses of paincases
        associated_druguses_ids: list[int] = [el.id for el in associated_druguses]
        # Druguses, nonassociated with paincases
        result = await session.scalars(
            select(DrugUse)
            .where(and_(
                DrugUse.owner_id == telegram_id,
                DrugUse.id.not_in(associated_druguses_ids))
            ))
        nonassoc_druguses: list[DrugUse] = result.all()
        # Pressures
        result = await session.scalars(select(Pressure).where(Pressure.owner_id == telegram_id))
        pressures: list[Pressure] = result.all()

        # Drugs
        result = await session.scalars(select(Drug).where(Drug.owner_id == telegram_id))
        drugs: list[Drug] = result.all()

        # Save them to "Saved..." tables
        to_add: list[SavedPainCase | SavedDrugUse | SavedUser] = []
        to_add += [SavedUser.copy_from(db_user)]
        to_add += [SavedPainCase.copy_from(el) for el in user_pains]
        to_add += [SavedDrugUse.copy_from(el) for el in nonassoc_druguses]
        to_add += [SavedPressure.copy_from(el) for el in pressures]
        session.add_all(to_add)

        await update_everyday_report(
            deleted_users=[
                PydanticUser(
                    telegram_id=db_user.telegram_id,
                    first_name=db_user.first_name,
                    last_name=None,
                    user_name=db_user.user_name,
                    language=db_user.language,
                    n_paincases=len(user_pains),
                    n_druguses=len(associated_druguses) + len(nonassoc_druguses),
                    n_pressures=len(pressures),
                    n_medications=len(drugs)
                )]
        )
        # Cascade delete user and associated objects from the main tables
        await session.execute(
            delete(User)
            .where(User.telegram_id == telegram_id)
        )
        return True


async def batch_change_last_notified(telegram_ids: list[int],
                                     time_notified: datetime.datetime) -> None:
    async with get_session() as session:
        stmt = (
            update(User)
            .where(User.telegram_id.in_(telegram_ids))
            .values(last_notified=time_notified)
        )
        await session.execute(stmt)
