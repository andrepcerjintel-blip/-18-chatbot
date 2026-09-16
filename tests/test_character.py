from __future__ import annotations

import pytest

from app.character.manager import CharacterManager, ProtectedFieldError
from app.schemas.character import CharacterCreate, CharacterUpdate


def _valid_payload(**overrides) -> CharacterCreate:
    base = dict(name="Luna", age=24, gender="female")
    base.update(overrides)
    return CharacterCreate(**base)


def test_create_valid_character(db_session):
    manager = CharacterManager(db_session)
    character = manager.create(_valid_payload())
    assert character.age == 24
    assert character.synthetic is True
    assert character.id is not None


def test_rejects_age_below_21():
    with pytest.raises(Exception):
        _valid_payload(age=17)


def test_synthetic_always_true(db_session):
    manager = CharacterManager(db_session)
    character = manager.create(_valid_payload())
    assert character.synthetic is True


def test_protected_fields_not_updatable_via_update_schema(db_session):
    manager = CharacterManager(db_session)
    character = manager.create(_valid_payload())

    # CharacterUpdate schema intentionally has no age/synthetic/id/created_at
    # fields, so this is a structural guarantee, not just a runtime check.
    assert not hasattr(CharacterUpdate(), "age")
    assert not hasattr(CharacterUpdate(), "synthetic")

    updated = manager.update(character.id, CharacterUpdate(name="Luna Silva"))
    assert updated.name == "Luna Silva"
    assert updated.age == 24
    assert updated.synthetic is True


def test_manager_rejects_protected_field_dict_defense_in_depth(db_session):
    manager = CharacterManager(db_session)
    character = manager.create(_valid_payload())

    class FakeUpdate:
        def model_dump(self, exclude_unset=True):
            return {"age": 15}

    with pytest.raises(ProtectedFieldError):
        manager.update(character.id, FakeUpdate())


def test_male_character_is_first_class(db_session):
    manager = CharacterManager(db_session)
    character = manager.create(_valid_payload(gender="male", name="Marco"))
    assert character.gender == "male"
    assert character.synthetic is True
    assert character.age == 24


def test_gender_is_required_no_default(db_session):
    with pytest.raises(Exception):
        CharacterCreate(name="Sem Genero", age=24)


def test_identity_origin_defaults_to_synthetic(db_session):
    manager = CharacterManager(db_session)
    character = manager.create(_valid_payload())
    assert character.identity_origin == "synthetic_generation"
    assert not character.real_person_reference


def test_identity_origin_and_real_person_reference_are_protected(db_session):
    manager = CharacterManager(db_session)
    character = manager.create(_valid_payload())

    assert not hasattr(CharacterUpdate(), "identity_origin")
    assert not hasattr(CharacterUpdate(), "real_person_reference")

    class FakeUpdate:
        def model_dump(self, exclude_unset=True):
            return {"identity_origin": "captured_photo", "real_person_reference": "someone"}

    with pytest.raises(ProtectedFieldError):
        manager.update(character.id, FakeUpdate())
