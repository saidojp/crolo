"""Database operations for decks and quiz sessions."""

from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Iterable, Sequence

from sqlalchemy import func
from sqlalchemy.orm import Session

from database import DBDeck, DBDeckItem, DBQuizSession, DBQuizSessionItem, DBUser
from models import DeckItemUpdate, SessionCreate

MAX_OPTIONS = 4


# --- helpers ---------------------------------------------------------------


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _accuracy(correct: int, total: int) -> float | None:
    if not total:
        return None
    return round(correct / total, 4)


def get_deck(db: Session, deck_id: int, owner_id: int) -> DBDeck | None:
    return (
        db.query(DBDeck)
        .filter(DBDeck.id == deck_id, DBDeck.owner_id == owner_id)
        .first()
    )


def list_decks(db: Session, owner_id: int) -> list[DBDeck]:
    return (
        db.query(DBDeck)
        .filter(DBDeck.owner_id == owner_id)
        .order_by(DBDeck.created_at.desc(), DBDeck.id.desc())
        .all()
    )


def deck_stats(db: Session, deck: DBDeck) -> dict[str, object]:
    total = db.query(func.count(DBDeckItem.id)).filter(DBDeckItem.deck_id == deck.id).scalar() or 0
    hidden = (
        db.query(func.count(DBDeckItem.id))
        .filter(DBDeckItem.deck_id == deck.id, DBDeckItem.hidden.is_(True))
        .scalar()
        or 0
    )
    needs_review = (
        db.query(func.count(DBDeckItem.id))
        .filter(DBDeckItem.deck_id == deck.id, DBDeckItem.needs_review.is_(True))
        .scalar()
        or 0
    )
    quiz_ready = max(0, total - hidden - needs_review)

    completed = (
        db.query(DBQuizSession)
        .filter(
            DBQuizSession.deck_id == deck.id,
            DBQuizSession.status == "finished",
        )
        .all()
    )
    answered = 0
    correct = 0
    last_played: datetime | None = None
    for session in completed:
        answered += session.total or 0
        correct += session.correct or 0
        returned_at = session.finished_at or session.created_at
        if returned_at is not None and (last_played is None or returned_at > last_played):
            last_played = returned_at

    return {
        "total_items": total,
        "quiz_ready": quiz_ready,
        "needs_review": needs_review,
        "hidden": hidden,
        "accuracy": _accuracy(correct, answered),
        "sessions_completed": len(completed),
        "last_played_at": last_played,
    }


def item_to_dict(item: DBDeckItem) -> dict[str, object]:
    options = list(item.options or [])
    return {
        "id": item.id,
        "position": item.position,
        "front": item.front,
        "reading": item.reading,
        "meaning": item.meaning or "",
        "options": options,
        "correct_index": item.correct_index or 0,
        "needs_review": bool(item.needs_review),
        "hidden": bool(item.hidden),
    }


# --- deck creation ---------------------------------------------------------


def create_deck(
    db: Session,
    *,
    owner: DBUser,
    title: str,
    source_filename: str,
    package_version: int,
    schema_version: int,
    report: dict,
    items: Sequence[dict],
) -> DBDeck:
    deck = DBDeck(
        owner_id=owner.id,
        title=title,
        source_filename=source_filename,
        package_version=package_version,
        schema_version=schema_version,
        report=report,
        status="draft",
    )
    db.add(deck)
    db.flush()

    for position, data in enumerate(items):
        db.add(
            DBDeckItem(
                deck_id=deck.id,
                position=position,
                front=data["front"],
                reading=data["reading"],
                meaning=data.get("meaning", "") or "",
                options=data.get("options", []),
                correct_index=data.get("correct_index", 0),
                source_note_id=data.get("source_note_id"),
                notetype=data.get("notetype", ""),
                needs_review=bool(data.get("needs_review", False)),
                hidden=bool(data.get("hidden", False)),
            )
        )
    db.commit()
    db.refresh(deck)
    return deck


def publish_deck(db: Session, deck: DBDeck) -> DBDeck:
    deck.status = "ready"
    db.commit()
    db.refresh(deck)
    return deck


def rename_deck(db: Session, deck: DBDeck, title: str) -> DBDeck:
    deck.title = title
    db.commit()
    db.refresh(deck)
    return deck


def delete_deck(db: Session, deck: DBDeck) -> None:
    db.delete(deck)
    db.commit()


# --- item editing ----------------------------------------------------------


def list_items(
    db: Session,
    deck: DBDeck,
    *,
    page: int,
    page_size: int,
    search: str = "",
    filter_by: str = "all",
) -> tuple[list[DBDeckItem], int]:
    query = db.query(DBDeckItem).filter(DBDeckItem.deck_id == deck.id)
    if search.strip():
        pattern = f"%{search.strip()}%"
        query = query.filter(
            DBDeckItem.front.ilike(pattern)
            | DBDeckItem.reading.ilike(pattern)
            | DBDeckItem.meaning.ilike(pattern)
        )
    if filter_by == "review":
        query = query.filter(DBDeckItem.needs_review.is_(True))
    elif filter_by == "hidden":
        query = query.filter(DBDeckItem.hidden.is_(True))
    elif filter_by == "ready":
        query = query.filter(
            DBDeckItem.needs_review.is_(False), DBDeckItem.hidden.is_(False)
        )
    elif filter_by == "missing_meaning":
        query = query.filter(DBDeckItem.meaning == "")

    total = query.count()
    items = (
        query.order_by(DBDeckItem.position, DBDeckItem.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total


def get_item(db: Session, deck: DBDeck, item_id: int) -> DBDeckItem | None:
    return (
        db.query(DBDeckItem)
        .filter(DBDeckItem.id == item_id, DBDeckItem.deck_id == deck.id)
        .first()
    )


def valid_readings_for_front(db: Session, deck: DBDeck, front: str) -> set[str]:
    rows = (
        db.query(DBDeckItem.reading)
        .filter(DBDeckItem.deck_id == deck.id, DBDeckItem.front == front)
        .all()
    )
    return {row[0] for row in rows}


def apply_item_update(
    db: Session,
    deck: DBDeck,
    item: DBDeckItem,
    update: DeckItemUpdate,
) -> DBDeckItem:
    """Apply a partial edit, keeping the correct option in sync with the reading.

    The reading is the single source of truth: an option list is only valid if
    it contains the reading exactly once. Conflicting edits are rejected rather
    than silently dropped.
    """
    from apkg.distractors import validate_options

    old_reading = item.reading
    options = list(item.options or [])

    if update.front is not None:
        item.front = update.front.strip()
    if update.reading is not None:
        item.reading = update.reading.strip()
    if update.meaning is not None:
        item.meaning = update.meaning.strip()
    if update.needs_review is not None:
        item.needs_review = update.needs_review
    if update.hidden is not None:
        item.hidden = update.hidden

    if update.options is not None:
        options = [option.strip() for option in update.options if option.strip()]
        if (
            update.correct_index is not None
            and 0 <= update.correct_index < len(options)
            and options[update.correct_index] != item.reading
            and item.reading in options
        ):
            # Marking another option as correct: move the reading into that slot
            # so the invariant "correct index == reading" always holds.
            correct_slot = update.correct_index
            reading_slot = options.index(item.reading)
            options[correct_slot], options[reading_slot] = (
                options[reading_slot],
                options[correct_slot],
            )
    elif old_reading != item.reading:
        # The reading was edited in place; keep the slot, swap the value.
        if old_reading in options:
            options[options.index(old_reading)] = item.reading
        else:
            options.insert(0, item.reading)
    elif item.reading not in options:
        options.insert(0, item.reading)

    if options:
        problems = validate_options(
            options,
            item.reading,
            valid_readings=valid_readings_for_front(db, deck, item.front) - {item.reading},
        )
        structural = [
            problem
            for problem in problems
            if problem.startswith(
                ("At least", "At most", "Options must", "The correct", "'")
            )
        ]
        if structural:
            raise ValueError(structural[0])
        item.options = options
        item.correct_index = options.index(item.reading)

    db.commit()
    db.refresh(item)
    return item


def regenerate_item_options(db: Session, deck: DBDeck, item: DBDeckItem) -> DBDeckItem:
    """Rebuild distractors for one item from the deck pool."""
    from apkg import distractors

    siblings = db.query(DBDeckItem).filter(DBDeckItem.deck_id == deck.id).all()
    pool: list[str] = []
    seen: set[str] = set()
    by_front: dict[str, set[str]] = {}
    for sibling in siblings:
        by_front.setdefault(sibling.front, set()).add(sibling.reading)
        if sibling.reading not in seen:
            seen.add(sibling.reading)
            pool.append(sibling.reading)

    option_set = distractors.generate_options(item, by_front, pool)
    item.options = option_set.options
    item.correct_index = option_set.correct_index
    db.commit()
    db.refresh(item)
    return item


def add_item(
    db: Session,
    deck: DBDeck,
    *,
    front: str,
    reading: str,
    meaning: str,
    options: list[str] | None,
    correct_index: int | None,
) -> DBDeckItem:
    from apkg import distractors

    siblings = db.query(DBDeckItem).filter(DBDeckItem.deck_id == deck.id).all()
    pool: list[str] = []
    seen: set[str] = set()
    by_front: dict[str, set[str]] = {}
    for sibling in siblings:
        by_front.setdefault(sibling.front, set()).add(sibling.reading)
        if sibling.reading not in seen:
            seen.add(sibling.reading)
            pool.append(sibling.reading)

    if options:
        final_options = list(options)
        final_correct = (
            correct_index
            if correct_index is not None and 0 <= correct_index < len(final_options)
            else (final_options.index(reading) if reading in final_options else 0)
        )
    else:
        stub = type("Stub", (), {"front": front, "reading": reading})
        generated = distractors.generate_options(stub, by_front, pool)
        final_options = generated.options
        final_correct = generated.correct_index

    max_position = (
        db.query(func.max(DBDeckItem.position))
        .filter(DBDeckItem.deck_id == deck.id)
        .scalar()
    )
    item = DBDeckItem(
        deck_id=deck.id,
        position=(max_position or 0) + 1,
        front=front.strip(),
        reading=reading.strip(),
        meaning=meaning.strip(),
        options=final_options,
        correct_index=final_correct,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def delete_item(db: Session, item: DBDeckItem) -> None:
    db.delete(item)
    db.commit()


# --- sessions --------------------------------------------------------------


def _eligible_items(db: Session, deck: DBDeck, source: str) -> list[DBDeckItem]:
    query = db.query(DBDeckItem).filter(
        DBDeckItem.deck_id == deck.id,
        DBDeckItem.hidden.is_(False),
        DBDeckItem.needs_review.is_(False),
    )
    items = query.order_by(DBDeckItem.position, DBDeckItem.id).all()
    if source == "all":
        return items

    history = (
        db.query(DBQuizSessionItem)
        .join(DBQuizSession, DBQuizSession.id == DBQuizSessionItem.session_id)
        .filter(
            DBQuizSession.deck_id == deck.id,
            DBQuizSession.status == "finished",
            DBQuizSessionItem.answered_at.isnot(None),
        )
        .all()
    )

    if source == "unseen":
        seen_ids = {row.item_id for row in history if row.item_id is not None}
        return [item for item in items if item.id not in seen_ids]

    if source == "weak":
        stats: dict[int, list[bool]] = {}
        for row in history:
            if row.item_id is None:
                continue
            stats.setdefault(row.item_id, []).append(bool(row.is_correct))
        weak = []
        for item in items:
            attempts = stats.get(item.id)
            if not attempts:
                continue
            accuracy = sum(attempts) / len(attempts)
            if accuracy <= 0.7:
                weak.append(item)
        return weak

    return items


def create_session(
    db: Session,
    *,
    deck: DBDeck,
    owner: DBUser,
    payload: SessionCreate,
) -> DBQuizSession:
    if payload.mode not in ("instant", "end"):
        raise ValueError("mode must be 'instant' or 'end'")
    if payload.source not in ("all", "unseen", "weak"):
        raise ValueError("source must be 'all', 'unseen' or 'weak'")

    candidates = _eligible_items(db, deck, payload.source)

    if payload.item_ids:
        wanted = set(payload.item_ids)
        candidates = [item for item in candidates if item.id in wanted]
        if not candidates:
            # Retrying questions that were just hidden or flagged still works.
            fallback = (
                db.query(DBDeckItem)
                .filter(DBDeckItem.deck_id == deck.id, DBDeckItem.id.in_(wanted))
                .all()
            )
            candidates = fallback
    elif payload.count is not None:
        count = max(1, payload.count) if candidates else 0
        candidates = random.sample(candidates, min(count, len(candidates)))
    if not candidates:
        raise ValueError("No questions available for this selection")

    session = DBQuizSession(
        deck_id=deck.id,
        owner_id=owner.id,
        mode=payload.mode,
        source=payload.source,
        status="active",
        total=len(candidates),
        correct=0,
    )
    db.add(session)
    db.flush()

    for position, item in enumerate(candidates):
        db.add(
            DBQuizSessionItem(
                session_id=session.id,
                item_id=item.id,
                position=position,
                front=item.front,
                reading=item.reading,
                meaning=item.meaning or "",
                options=list(item.options or []),
                correct_index=item.correct_index or 0,
            )
        )
    db.commit()
    db.refresh(session)
    return session


def get_session(db: Session, session_id: int, owner_id: int) -> DBQuizSession | None:
    return (
        db.query(DBQuizSession)
        .filter(DBQuizSession.id == session_id, DBQuizSession.owner_id == owner_id)
        .first()
    )


def session_state(session: DBQuizSession) -> dict[str, object]:
    """Serialise a session, hiding answers until they are submitted."""
    items: list[dict[str, object]] = []
    finished = session.status == "finished"
    answered = 0
    correct = 0
    for row in session.items:
        is_answered = row.selected_index is not None
        if is_answered:
            answered += 1
            if row.is_correct:
                correct += 1
        reveal = finished or (is_answered and session.mode == "instant")
        item = {
            "id": row.id,
            "item_id": row.item_id,
            "position": row.position,
            "front": row.front,
            "options": list(row.options or []),
            "selected_index": row.selected_index,
            "is_correct": row.is_correct,
            "reading": row.reading if reveal else None,
            "meaning": row.meaning if reveal else None,
            "correct_index": row.correct_index if reveal else None,
        }
        items.append(item)
    return {
        "id": session.id,
        "deck_id": session.deck_id,
        "deck_title": session.deck.title if session.deck else "",
        "mode": session.mode,
        "source": session.source,
        "status": session.status,
        "total": session.total,
        "answered": answered,
        "correct": correct,
        "items": items,
    }


def answer_item(
    db: Session,
    session: DBQuizSession,
    *,
    item_id: int,
    selected_index: int,
) -> DBQuizSessionItem:
    row = next((entry for entry in session.items if entry.id == item_id), None)
    if row is None:
        raise KeyError("item")
    if session.status != "active":
        raise ValueError("This session is already finished")

    options = list(row.options or [])
    if not 0 <= selected_index < len(options):
        raise IndexError("option")

    row.selected_index = selected_index
    row.is_correct = selected_index == row.correct_index
    row.answered_at = _now()
    _sync_session_totals(db, session)
    db.commit()
    db.refresh(row)
    return row


def answer_batch(
    db: Session,
    session: DBQuizSession,
    answers: Iterable[tuple[int, int]],
) -> DBQuizSession:
    by_id = {row.id: row for row in session.items}
    for item_id, selected_index in answers:
        row = by_id.get(item_id)
        if row is None:
            raise KeyError("item")
        options = list(row.options or [])
        if not 0 <= selected_index < len(options):
            raise IndexError("option")
        row.selected_index = selected_index
        row.is_correct = selected_index == row.correct_index
        row.answered_at = _now()
    _sync_session_totals(db, session)
    db.commit()
    db.refresh(session)
    return session


def _sync_session_totals(db: Session, session: DBQuizSession) -> None:
    db.flush()
    answered = [row for row in session.items if row.selected_index is not None]
    session.total = len(session.items)
    session.correct = sum(1 for row in answered if row.is_correct)


def finish_session(db: Session, session: DBQuizSession) -> DBQuizSession:
    if session.status != "finished":
        session.status = "finished"
        session.finished_at = _now()
        _sync_session_totals(db, session)
        db.commit()
        db.refresh(session)
    return session
