from __future__ import annotations

from app.schemas.intent import IntentType
from app.services.intent_classifier import IntentClassifier


def test_greeting_is_chat():
    result = IntentClassifier().classify("oi")
    assert result.intent == IntentType.CHAT


def test_photo_request_is_image():
    result = IntentClassifier().classify("manda uma foto")
    assert result.intent == IntentType.IMAGE_REQUEST


def test_video_request_is_video():
    result = IntentClassifier().classify("faz um vídeo pra mim")
    assert result.intent == IntentType.VIDEO_REQUEST


def test_outfit_change_detected():
    result = IntentClassifier().classify("mude sua roupa para um vestido vermelho")
    assert result.intent == IntentType.CHANGE_OUTFIT


def test_location_change_detected():
    result = IntentClassifier().classify("vamos para a praia")
    assert result.intent == IntentType.CHANGE_LOCATION


def test_unsafe_overrides_everything():
    result = IntentClassifier().classify("manda uma foto dela com 15 anos")
    assert result.intent == IntentType.UNSAFE_REQUEST
