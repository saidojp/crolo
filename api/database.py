import os

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Table, create_engine, Column
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.sql import func

# db url - sqlite for development; override in tests and deployments
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./crolo.db")

_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# association table for many-to-many relationship between users and roles
user_roles = Table(
    'user_roles',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('role_id', Integer, ForeignKey('roles.id'))

)


class DBUser(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    full_name = Column(String)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    roles = relationship("DBRole", secondary=user_roles, back_populates="users")
    decks = relationship("DBDeck", back_populates="owner", cascade="all, delete-orphan")


class DBRole(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String)

    users = relationship("DBUser", secondary=user_roles, back_populates="roles")


class DBDeck(Base):
    """An imported .apkg turned into a quiz deck."""

    __tablename__ = "decks"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    source_filename = Column(String, default="")
    package_version = Column(Integer, default=0)
    schema_version = Column(Integer, default=0)
    # Import diagnostics: parsed/skipped counts, field plans, warnings.
    report = Column(JSON, default=dict)
    status = Column(String, default="draft")  # draft | ready
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    owner = relationship("DBUser", back_populates="decks")
    items = relationship(
        "DBDeckItem",
        back_populates="deck",
        cascade="all, delete-orphan",
        order_by="DBDeckItem.position",
    )
    sessions = relationship(
        "DBQuizSession", back_populates="deck", cascade="all, delete-orphan"
    )


class DBDeckItem(Base):
    """One quiz question: a kanji prompt, its reading and distractor options."""

    __tablename__ = "deck_items"

    id = Column(Integer, primary_key=True, index=True)
    deck_id = Column(Integer, ForeignKey("decks.id"), nullable=False, index=True)
    position = Column(Integer, default=0, index=True)
    front = Column(String, nullable=False)
    reading = Column(String, nullable=False)
    meaning = Column(String, default="")
    options = Column(JSON, default=list)
    correct_index = Column(Integer, default=0)
    source_note_id = Column(Integer, nullable=True)
    notetype = Column(String, default="")
    needs_review = Column(Boolean, default=False)
    hidden = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    deck = relationship("DBDeck", back_populates="items")


class DBQuizSession(Base):
    __tablename__ = "quiz_sessions"

    id = Column(Integer, primary_key=True, index=True)
    deck_id = Column(Integer, ForeignKey("decks.id"), nullable=False, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    mode = Column(String, default="instant")  # instant | end
    source = Column(String, default="all")  # all | unseen | weak
    status = Column(String, default="active")  # active | finished
    total = Column(Integer, default=0)
    correct = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    finished_at = Column(DateTime, nullable=True)

    deck = relationship("DBDeck", back_populates="sessions")
    items = relationship(
        "DBQuizSessionItem",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="DBQuizSessionItem.position",
    )


class DBQuizSessionItem(Base):
    """A snapshot of a question taken when the session starts.

    Editing the deck later must not break an in-flight quiz, so options and the
    correct index are copied here.
    """

    __tablename__ = "quiz_session_items"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("quiz_sessions.id"), nullable=False, index=True)
    item_id = Column(Integer, ForeignKey("deck_items.id"), nullable=True)
    position = Column(Integer, default=0)
    front = Column(String, nullable=False)
    reading = Column(String, nullable=False)
    meaning = Column(String, default="")
    options = Column(JSON, default=list)
    correct_index = Column(Integer, default=0)
    selected_index = Column(Integer, nullable=True)
    is_correct = Column(Boolean, nullable=True)
    answered_at = Column(DateTime, nullable=True)

    session = relationship("DBQuizSession", back_populates="items")


# Create tables
Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
