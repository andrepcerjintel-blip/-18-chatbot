from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.character.manager import CharacterManager, ProtectedFieldError, UnsafeCharacterError
from app.schemas.character import CharacterCreate, CharacterRead, CharacterUpdate

router = APIRouter(prefix="/characters", tags=["characters"])


@router.post("", response_model=CharacterRead, status_code=201)
def create_character(payload: CharacterCreate, db: Session = Depends(get_db)):
    manager = CharacterManager(db)
    try:
        character = manager.create(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except UnsafeCharacterError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "status": "UNSAFE_REQUEST",
                "message": "Character definition rejected: age and/or described appearance failed the safety check.",
                "reasons": [r.value for r in exc.result.reasons],
            },
        ) from exc
    return character


@router.get("", response_model=list[CharacterRead])
def list_characters(db: Session = Depends(get_db)):
    return CharacterManager(db).list()


@router.get("/{character_id}", response_model=CharacterRead)
def get_character(character_id: str, db: Session = Depends(get_db)):
    character = CharacterManager(db).get(character_id)
    if character is None:
        raise HTTPException(status_code=404, detail="character not found")
    return character


@router.patch("/{character_id}", response_model=CharacterRead)
def update_character(character_id: str, payload: CharacterUpdate, db: Session = Depends(get_db)):
    manager = CharacterManager(db)
    try:
        return manager.update(character_id, payload)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ProtectedFieldError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except UnsafeCharacterError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "status": "UNSAFE_REQUEST",
                "message": "Character update rejected: resulting appearance failed the safety check.",
                "reasons": [r.value for r in exc.result.reasons],
            },
        ) from exc
