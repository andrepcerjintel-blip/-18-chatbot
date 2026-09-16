from __future__ import annotations

import pytest

from app.character.manager import CharacterManager, ProtectedFieldError, UnsafeCharacterError
from app.models.character import MIN_CHARACTER_AGE
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


def test_minimum_age_is_21_not_18(db_session):
    """O piso de idade permanece 21, deliberadamente acima do minimo legal
    de 18: uma margem de seguranca contra personagens "18 anos" com
    aparencia ambigua. Ver SECURITY.md."""
    assert MIN_CHARACTER_AGE == 21

    with pytest.raises(Exception):
        _valid_payload(age=18)
    with pytest.raises(Exception):
        _valid_payload(age=20)

    manager = CharacterManager(db_session)
    character = manager.create(_valid_payload(age=21))
    assert character.age == 21


def test_youthful_appearance_blocked_even_with_adult_age(db_session):
    """Idade declarada >= 21 NAO autoriza, por si so, uma aparencia
    infantil/adolescente -- o Safety Engine verifica isso de forma
    independente da idade."""
    manager = CharacterManager(db_session)
    payload = _valid_payload(
        age=25,
        body_description="corpo pré-púbere, sem desenvolvimento corporal",
        distinctive_features="rosto infantil",
    )
    with pytest.raises(UnsafeCharacterError):
        manager.create(payload)


def test_declared_age_cannot_bypass_youthful_appearance_description(db_session):
    """Cobre explicitamente a tentativa de usar idade declarada para
    contornar uma aparencia juvenil descrita em texto livre."""
    manager = CharacterManager(db_session)
    payload = _valid_payload(
        age=22,
        appearance="aparenta ser bem mais nova do que realmente é, apesar da idade",
    )
    with pytest.raises(UnsafeCharacterError):
        manager.create(payload)


def test_adult_appearance_with_adult_age_is_allowed(db_session):
    manager = CharacterManager(db_session)
    character = manager.create(
        _valid_payload(age=28, appearance="mulher adulta, traços maduros, altura 1.75m")
    )
    assert character.age == 28


def test_update_cannot_inject_youthful_appearance(db_session):
    manager = CharacterManager(db_session)
    character = manager.create(_valid_payload(age=30))

    with pytest.raises(UnsafeCharacterError):
        manager.update(
            character.id,
            CharacterUpdate(body_description="corpo infantil, rosto de bebê"),
        )
