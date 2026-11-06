from pydantic import BaseModel, Field
from typing import Optional


class User(BaseModel):
    id: Optional[int] = None
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: Optional[bool] = None
    roles: list[str] = Field(default_factory=list)


class UserInDB(User):
    hashed_password: str


class UserCreate(BaseModel):
    username: str
    email: str
    full_name: str
    password: str


# --- Decks -----------------------------------------------------------------


class DeckItem(BaseModel):
    id: int
    position: int
    front: str
    reading: str
    meaning: str
    options: list[str]
    correct_index: int
    needs_review: bool
    hidden: bool


class DeckSummary(BaseModel):
    id: int
    title: str
    status: str
    total_items: int
    quiz_ready: int
    needs_review: int
    hidden: int
    source_filename: str
    package_version: int
    schema_version: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    last_played_at: Optional[str] = None
    accuracy: Optional[float] = None
    sessions_completed: int = 0


class DeckDetail(BaseModel):
    deck: DeckSummary
    report: dict


class DeckItemPage(BaseModel):
    items: list[DeckItem]
    total: int
    page: int
    page_size: int


class DeckItemUpdate(BaseModel):
    front: Optional[str] = None
    reading: Optional[str] = None
    meaning: Optional[str] = None
    options: Optional[list[str]] = None
    correct_index: Optional[int] = None
    needs_review: Optional[bool] = None
    hidden: Optional[bool] = None


class DeckItemCreate(BaseModel):
    front: str
    reading: str
    meaning: str = ""
    options: Optional[list[str]] = None
    correct_index: Optional[int] = None


class DeckRename(BaseModel):
    title: str


class BulkItemUpdate(BaseModel):
    updates: list[tuple[int, DeckItemUpdate]]


# --- Quiz ------------------------------------------------------------------


class SessionCreate(BaseModel):
    mode: str = "instant"
    source: str = "all"
    count: Optional[int] = None
    # Explicit question selection, used for "retry mistakes".
    item_ids: Optional[list[int]] = None


class SessionItem(BaseModel):
    id: int
    item_id: Optional[int] = None
    position: int
    front: str
    options: list[str]
    selected_index: Optional[int] = None
    is_correct: Optional[bool] = None
    # Only present once the answer has been submitted (or the session finished).
    reading: Optional[str] = None
    meaning: Optional[str] = None
    correct_index: Optional[int] = None


class SessionState(BaseModel):
    id: int
    deck_id: int
    deck_title: str
    mode: str
    source: str
    status: str
    total: int
    answered: int
    correct: int
    items: list[SessionItem]


class AnswerRequest(BaseModel):
    item_id: int
    selected_index: int


class AnswerResponse(BaseModel):
    item_id: int
    selected_index: int
    correct: bool
    correct_index: int
    reading: str
    meaning: str
    answered: int
    correct_count: int
    total: int


class AnswerBatchItem(BaseModel):
    item_id: int
    selected_index: int


class AnswerBatchRequest(BaseModel):
    answers: list[AnswerBatchItem]
