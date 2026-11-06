"""Deck import, listing and question editing."""

from __future__ import annotations

from typing import cast

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

import deck_crud
from apkg import ApkgError, import_apkg
from auth import get_current_active_user
from database import get_db
from models import (
    BulkItemUpdate,
    DeckDetail,
    DeckItem,
    DeckItemCreate,
    DeckItemPage,
    DeckItemUpdate,
    DeckRename,
    DeckSummary,
    User,
)

router = APIRouter(prefix="/decks", tags=["decks"])

MAX_UPLOAD_BYTES = 100 * 1024 * 1024

_ERROR_STATUS = {
    "empty_file": status.HTTP_400_BAD_REQUEST,
    "not_a_zip": status.HTTP_400_BAD_REQUEST,
    "corrupt_archive": status.HTTP_400_BAD_REQUEST,
    "corrupt_collection": status.HTTP_400_BAD_REQUEST,
    "unsupported_version": status.HTTP_422_UNPROCESSABLE_CONTENT,
    "collection_too_large": status.HTTP_413_CONTENT_TOO_LARGE,
    "file_too_large": status.HTTP_413_CONTENT_TOO_LARGE,
    "too_many_notes": status.HTTP_413_CONTENT_TOO_LARGE,
    "no_usable_cards": status.HTTP_422_UNPROCESSABLE_CONTENT,
    "zstd_unavailable": status.HTTP_500_INTERNAL_SERVER_ERROR,
}


def _require_deck(db: Session, deck_id: int, owner) -> "object":
    deck = deck_crud.get_deck(db, deck_id, cast(int, owner.id))
    if deck is None:
        raise HTTPException(status_code=404, detail="Deck not found")
    return deck


def _require_item(db: Session, deck, item_id: int):
    item = deck_crud.get_item(db, deck, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Question not found")
    return item


def _summary(db: Session, deck) -> DeckSummary:
    stats = deck_crud.deck_stats(db, deck)
    return DeckSummary(
        id=deck.id,
        title=deck.title,
        status=deck.status,
        total_items=cast(int, stats["total_items"]),
        quiz_ready=cast(int, stats["quiz_ready"]),
        needs_review=cast(int, stats["needs_review"]),
        hidden=cast(int, stats["hidden"]),
        source_filename=deck.source_filename or "",
        package_version=deck.package_version or 0,
        schema_version=deck.schema_version or 0,
        created_at=deck.created_at.isoformat() if deck.created_at else None,
        updated_at=deck.updated_at.isoformat() if deck.updated_at else None,
        last_played_at=(
            stats["last_played_at"].isoformat() if stats["last_played_at"] else None
        ),
        accuracy=cast(float | None, stats["accuracy"]),
        sessions_completed=cast(int, stats["sessions_completed"]),
    )


@router.post("/import", response_model=DeckDetail, status_code=status.HTTP_201_CREATED)
async def import_deck(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not (file.filename or "").lower().endswith((".apkg", ".colpkg")):
        raise HTTPException(status_code=400, detail="Upload an .apkg or .colpkg file")

    raw = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="The file is too large")

    try:
        result = import_apkg(raw, filename=file.filename or "")
    except ApkgError as exc:
        raise HTTPException(
            status_code=_ERROR_STATUS.get(exc.code, status.HTTP_400_BAD_REQUEST),
            detail=exc.message,
        )

    report = result.summary()
    deck = deck_crud.create_deck(
        db,
        owner=current_user,
        title=result.deck_name,
        source_filename=file.filename or "",
        package_version=result.archive.version,
        schema_version=result.collection.schema_version,
        report=report,
        items=[
            {
                "front": item.front,
                "reading": item.reading,
                "meaning": item.meaning,
                "options": item.options,
                "correct_index": item.correct_index,
                "source_note_id": item.source_note_id,
                "notetype": item.notetype,
                "needs_review": item.needs_review,
            }
            for item in result.items
        ],
    )
    return DeckDetail(deck=_summary(db, deck), report=report)


@router.get("", response_model=list[DeckSummary])
def list_decks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    decks = deck_crud.list_decks(db, cast(int, current_user.id))
    return [_summary(db, deck) for deck in decks]


@router.get("/{deck_id}", response_model=DeckDetail)
def get_deck(
    deck_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    deck = _require_deck(db, deck_id, current_user)
    return DeckDetail(deck=_summary(db, deck), report=dict(deck.report or {}))


@router.patch("/{deck_id}", response_model=DeckSummary)
def rename_deck(
    deck_id: int,
    payload: DeckRename,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    deck = _require_deck(db, deck_id, current_user)
    title = payload.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="Title cannot be empty")
    deck_crud.rename_deck(db, deck, title)
    return _summary(db, deck)


@router.delete("/{deck_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_deck(
    deck_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    deck = _require_deck(db, deck_id, current_user)
    deck_crud.delete_deck(db, deck)


@router.post("/{deck_id}/publish", response_model=DeckSummary)
def publish_deck(
    deck_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    deck = _require_deck(db, deck_id, current_user)
    stats = deck_crud.deck_stats(db, deck)
    if not stats["quiz_ready"]:
        raise HTTPException(
            status_code=400,
            detail="This deck has no ready questions yet",
        )
    deck_crud.publish_deck(db, deck)
    return _summary(db, deck)


@router.get("/{deck_id}/items", response_model=DeckItemPage)
def list_items(
    deck_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    search: str = "",
    filter: str = Query("all", pattern="^(all|ready|review|hidden|missing_meaning)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    deck = _require_deck(db, deck_id, current_user)
    items, total = deck_crud.list_items(
        db, deck, page=page, page_size=page_size, search=search, filter_by=filter
    )
    return DeckItemPage(
        items=[DeckItem(**deck_crud.item_to_dict(item)) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.patch("/{deck_id}/items", response_model=DeckItemPage)
def bulk_update_items(
    deck_id: int,
    payload: BulkItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    deck = _require_deck(db, deck_id, current_user)
    updated = []
    try:
        for item_id, update in payload.updates:
            item = _require_item(db, deck, item_id)
            updated.append(deck_crud.apply_item_update(db, deck, item, update))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return DeckItemPage(
        items=[DeckItem(**deck_crud.item_to_dict(item)) for item in updated],
        total=len(updated),
        page=1,
        page_size=len(updated),
    )


@router.post("/{deck_id}/items", response_model=DeckItem, status_code=201)
def create_item(
    deck_id: int,
    payload: DeckItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    from apkg.japanese import has_kanji, is_valid_reading

    deck = _require_deck(db, deck_id, current_user)
    if not has_kanji(payload.front):
        raise HTTPException(status_code=400, detail="The prompt must contain kanji")
    if not is_valid_reading(payload.reading):
        raise HTTPException(status_code=400, detail="The reading must be hiragana")
    item = deck_crud.add_item(
        db,
        deck,
        front=payload.front,
        reading=payload.reading,
        meaning=payload.meaning,
        options=payload.options,
        correct_index=payload.correct_index,
    )
    return DeckItem(**deck_crud.item_to_dict(item))


@router.patch("/{deck_id}/items/{item_id}", response_model=DeckItem)
def update_item(
    deck_id: int,
    item_id: int,
    payload: DeckItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    from apkg.japanese import is_valid_reading

    deck = _require_deck(db, deck_id, current_user)
    item = _require_item(db, deck, item_id)
    if payload.reading is not None and not is_valid_reading(payload.reading.strip()):
        raise HTTPException(status_code=400, detail="The reading must be hiragana")
    try:
        item = deck_crud.apply_item_update(db, deck, item, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return DeckItem(**deck_crud.item_to_dict(item))


@router.delete("/{deck_id}/items/{item_id}", status_code=204)
def delete_item(
    deck_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    deck = _require_deck(db, deck_id, current_user)
    item = _require_item(db, deck, item_id)
    deck_crud.delete_item(db, item)


@router.post("/{deck_id}/items/{item_id}/regenerate", response_model=DeckItem)
def regenerate_item(
    deck_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    deck = _require_deck(db, deck_id, current_user)
    item = _require_item(db, deck, item_id)
    item = deck_crud.regenerate_item_options(db, deck, item)
    return DeckItem(**deck_crud.item_to_dict(item))
