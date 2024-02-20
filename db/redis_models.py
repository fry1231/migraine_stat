from pydantic import BaseModel
from db.models import User


class PydanticUser(BaseModel):
    """
    Notification about a new user or deleted one
    Used as a part of EverydayReport
    """
    telegram_id: int
    first_name: str | None
    last_name: str | None
    user_name: str | None
    language: str | None
    n_paincases: int | None
    n_druguses: int | None
    n_pressures: int | None
    n_medications: int | None


class EverydayReport(BaseModel):
    """
    Report about everyday statistics
    Sent to the admin every day
    """
    n_notified_users: int
    new_users: list[PydanticUser]
    deleted_users: list[PydanticUser]
    n_pains: int
    n_druguses: int
    n_pressures: int
    n_medications: int
