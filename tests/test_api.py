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
        json={"name": "Luna", "age": 24, "gender": "feminino"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["age"] == 24
    assert body["synthetic"] is True


def test_create_character_rejects_minor(client):
    resp = client.post(
        "/characters",
        json={"name": "Teste", "age": 15, "gender": "feminino"},
    )
    assert resp.status_code == 422


def test_create_conversation_and_chat_api(client):
    char_resp = client.post("/characters", json={"name": "Luna", "age": 24, "gender": "feminino"})
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
    char_resp = client.post("/characters", json={"name": "Luna", "age": 24, "gender": "feminino"})
    character_id = char_resp.json()["id"]
    conv_resp = client.post("/conversations", json={"character_id": character_id})
    conversation_id = conv_resp.json()["id"]

    chat_resp = client.post("/chat", json={"conversation_id": conversation_id, "message": "manda uma foto"})
    assert chat_resp.status_code == 200
    body = chat_resp.json()
    assert body["intent"] == "IMAGE_REQUEST"
    assert body["media"]["status"] == "MEDIA_PROVIDER_NOT_CONFIGURED"
