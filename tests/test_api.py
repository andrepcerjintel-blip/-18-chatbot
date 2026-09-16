from __future__ import annotations


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["media_provider"]["name"] == "null"


def test_create_character_api(client):
    resp = client.post(
        "/characters",
        json={"name": "Luna", "age": 24, "gender": "female"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["age"] == 24
    assert body["synthetic"] is True


def test_create_character_rejects_minor(client):
    resp = client.post(
        "/characters",
        json={"name": "Teste", "age": 15, "gender": "female"},
    )
    assert resp.status_code == 422


def test_create_conversation_and_chat_api(client):
    char_resp = client.post("/characters", json={"name": "Luna", "age": 24, "gender": "female"})
    character_id = char_resp.json()["id"]

    conv_resp = client.post("/conversations", json={"character_id": character_id})
    assert conv_resp.status_code == 201
    conversation_id = conv_resp.json()["id"]

    chat_resp = client.post("/chat", json={"conversation_id": conversation_id, "message": "oi"})
    assert chat_resp.status_code == 200
    body = chat_resp.json()
    assert body["intent"] == "CHAT"
    assert body["safety_decision"] == "ALLOW"


def test_image_request_api_returns_not_configured(client):
    char_resp = client.post("/characters", json={"name": "Luna", "age": 24, "gender": "female"})
    character_id = char_resp.json()["id"]
    conv_resp = client.post("/conversations", json={"character_id": character_id})
    conversation_id = conv_resp.json()["id"]

    chat_resp = client.post("/chat", json={"conversation_id": conversation_id, "message": "manda uma foto"})
    assert chat_resp.status_code == 200
    body = chat_resp.json()
    assert body["intent"] == "IMAGE_REQUEST"
    assert body["media"]["status"] == "MEDIA_PROVIDER_NOT_CONFIGURED"


def test_create_male_character_api(client):
    resp = client.post(
        "/characters",
        json={"name": "Marco", "age": 27, "gender": "male"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["gender"] == "male"
    assert body["synthetic"] is True
    assert body["identity_origin"] == "synthetic_generation"


def test_create_character_requires_gender(client):
    resp = client.post("/characters", json={"name": "Sem Genero", "age": 24})
    assert resp.status_code == 422


def test_create_character_rejects_unsupported_gender(client):
    resp = client.post("/characters", json={"name": "Teste", "age": 24, "gender": "unknown"})
    assert resp.status_code == 422


def test_hardware_endpoint(client):
    resp = client.get("/hardware")
    assert resp.status_code == 200
    body = resp.json()
    assert "vendor" in body
    assert "backend" in body


def test_create_character_rejects_youthful_appearance_despite_adult_age(client):
    """Idade declarada adulta (25) nao basta: a aparencia descrita e
    verificada de forma independente e bloqueia a criacao."""
    resp = client.post(
        "/characters",
        json={
            "name": "Teste",
            "age": 25,
            "gender": "female",
            "body_description": "corpo pré-púbere, rosto infantil",
        },
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body["detail"]["status"] == "UNSAFE_REQUEST"
    assert "YOUTHFUL_APPEARANCE" in body["detail"]["reasons"]


def test_update_character_rejects_injected_youthful_appearance(client):
    resp = client.post("/characters", json={"name": "Luna", "age": 30, "gender": "female"})
    character_id = resp.json()["id"]

    patch_resp = client.patch(
        f"/characters/{character_id}",
        json={"distinctive_features": "corpo infantil, sem desenvolvimento corporal"},
    )
    assert patch_resp.status_code == 422
    assert patch_resp.json()["detail"]["status"] == "UNSAFE_REQUEST"
