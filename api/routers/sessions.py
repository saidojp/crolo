"""Quiz sessions: start, answer, finish."""

from __future__ import annotations

from typing import cast

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import deck_crud
from auth import get_current_active_user
from database import get_db
from models import (
    AnswerBatchRequest,
    AnswerRequest,
    AnswerResponse,
    SessionCreate,
    SessionItem,
    SessionState,
    User,
)

router = APIRouter(prefix="/sessions", tags=["quiz"])
deck_router = APIRouter(prefix="/decks", tags=["quiz"])


def _require_session(db: Session, session_id: int, owner) -> object:
    session = deck_crud.get_session(db, session_id, cast(int, owner.id))
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


def _state(session) -> SessionState:
    data = deck_crud.session_state(session)
    return SessionState(
        id=cast(int, data["id"]),
        deck_id=cast(int, data["deck_id"]),
        deck_title=cast(str, data["deck_title"]),
        mode=cast(str, data["mode"]),
        source=cast(str, data["source"]),
        status=cast(str, data["status"]),
        total=cast(int, data["total"]),
        answered=cast(int, data["answered"]),
        correct=cast(int, data["correct"]),
        items=[SessionItem(**item) for item in cast(list[dict], data["items"])],    )


def start_deck_session(
    deck_id: int,
    payload: SessionCreate,
    db: Session,
    current_user: User,
) -> SessionState:
    deck = deck_crud.get_deck(db, deck_id, cast(int, current_user.id))
    if deck is None:
        raise HTTPException(status_code=404, detail="Deck not found")
    if deck.status != "ready":
        raise HTTPException(
            status_code=400,
            detail="Review and publish the deck before starting a quiz",
        )
    try:
        session = deck_crud.create_session(db, deck=deck, owner=current_user, payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _state(session)


@deck_router.post("/{deck_id}/sessions", response_model=SessionState, status_code=201)
def start_session(
    deck_id: int,
    payload: SessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return start_deck_session(deck_id, payload, db, current_user)


@router.get("/{session_id}", response_model=SessionState)
def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return _state(_require_session(db, session_id, current_user))


@router.post("/{session_id}/answer", response_model=AnswerResponse)
def answer(
    session_id: int,
    payload: AnswerRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    session = _require_session(db, session_id, current_user)
    if session.mode != "instant":
        raise HTTPException(
            status_code=400,
            detail="Answers are submitted together at the end in this mode",
        )
    try:
        row = deck_crud.answer_item(
            db, session, item_id=payload.item_id, selected_index=payload.selected_index
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Question not found in this session")
    except IndexError:
        raise HTTPException(status_code=400, detail="Invalid option index")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    answered = sum(1 for item in session.items if item.selected_index is not None)
    correct = sum(1 for item in session.items if item.is_correct)
    return AnswerResponse(
        item_id=row.id,
        selected_index=cast(int, row.selected_index),
        correct=bool(row.is_correct),
        correct_index=row.correct_index,
        reading=row.reading,
        meaning=row.meaning or "",
        answered=answered,
        correct_count=correct,
        total=len(session.items),
    )


@router.post("/{session_id}/answers", response_model=SessionState)
def answer_batch(
    session_id: int,
    payload: AnswerBatchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    session = _require_session(db, session_id, current_user)
    if session.mode != "end":
        raise HTTPException(status_code=400, detail="This session uses instant feedback")
    try:
        deck_crud.answer_batch(
            db,
            session,
            [(entry.item_id, entry.selected_index) for entry in payload.answers],
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Question not found in this session")
    except IndexError:
        raise HTTPException(status_code=400, detail="Invalid option index")
    return _state(session)


@router.post("/{session_id}/finish", response_model=SessionState)
def finish(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    session = _require_session(db, session_id, current_user)
    if session.total and any(item.selected_index is None for item in session.items):
        raise HTTPException(
            status_code=400,
            detail="Answer every question before finishing the session",
        )
    deck_crud.finish_session(db, session)
    return _state(session)
