from pydantic import BaseModel


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


class StateUpdate(BaseModel):
    """
    State update, sent to 'channel:states' to reflect the changes
    """
    user_id: int
    user_state: str
    action: str    # 'set' or 'unset' or 'refresh'
    incr_value: int


class States(BaseModel):
    """
    All states with names and users, belonging to these states
    """
    state_name: list[int]


class LogUpdate(BaseModel):
    """
    Log update, sent to 'channel:logs' to reflect the changes
    """
    log_record: str
    log_incr_value: int
