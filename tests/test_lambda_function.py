import base64
import json
import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import lambda_function


@patch("lambda_function.mimetypes.guess_extension", return_value=".webm")
@patch("lambda_function.uuid.uuid4", return_value="uuid")
def test_decode_audio_payload_defaults_and_audio_base64(
    _uuid4, _guess_extension, tmp_path, monkeypatch
):
    monkeypatch.setattr(
        lambda_function.os.path,
        "join",
        lambda *_parts: str(tmp_path / _parts[-1]),
    )
    payload = {"audio_base64": base64.b64encode(b"hello").decode("utf-8")}

    filepath = lambda_function._decode_audio_payload(payload)

    assert filepath == str(tmp_path / "audio-uuid.webm")
    assert (tmp_path / "audio-uuid.webm").read_bytes() == b"hello"


def test_decode_audio_payload_audio_base64_camelcase(tmp_path, monkeypatch):
    monkeypatch.setattr(
        lambda_function.os.path,
        "join",
        lambda *_parts: str(tmp_path / _parts[-1]),
    )
    payload = {"audioBase64": base64.b64encode(b"camel").decode("utf-8")}

    filepath = lambda_function._decode_audio_payload(payload)

    assert (tmp_path / os.path.basename(filepath)).read_bytes() == b"camel"


def test_decode_audio_payload_data_url(tmp_path, monkeypatch):
    monkeypatch.setattr(
        lambda_function.os.path,
        "join",
        lambda *_parts: str(tmp_path / _parts[-1]),
    )
    encoded = base64.b64encode(b"payload").decode("utf-8")
    payload = {
        "audio_base64": f"data:audio/webm;base64,{encoded}",
        "filename": "clip.webm",
    }

    filepath = lambda_function._decode_audio_payload(payload)

    assert filepath == str(tmp_path / "clip.webm")
    assert (tmp_path / "clip.webm").read_bytes() == b"payload"


def test_decode_audio_payload_missing_audio():
    with pytest.raises(ValueError, match="Missing audio_base64"):
        lambda_function._decode_audio_payload({})


def test_health_check():
    event = {"rawPath": "/health"}

    response = lambda_function.lambda_handler(event, None)

    assert response["statusCode"] == 200
    assert json.loads(response["body"]) == {"status": "ok"}


def test_invalid_json_body():
    event = {"body": "{oops"}

    response = lambda_function.lambda_handler(event, None)

    assert response["statusCode"] == 400
    assert json.loads(response["body"]) == {"error": "Invalid JSON body"}


def test_missing_audio_payload():
    event = {"body": json.dumps({})}

    response = lambda_function.lambda_handler(event, None)

    assert response["statusCode"] == 400
    assert json.loads(response["body"]) == {"error": "Missing audio_base64"}


@patch("lambda_function.os.remove")
@patch("lambda_function.os.path.exists", return_value=True)
@patch("lambda_function.summarize_transcript", return_value="formatted")
@patch("lambda_function.transcribe_audio", return_value="raw")
@patch(
    "lambda_function.get_api_config",
    return_value={"openai_api_key": "oa", "gemini_api_key": "gm"},
)
@patch("lambda_function._decode_audio_payload", return_value="/tmp/audio.webm")
def test_successful_request(
    _decode_audio_payload,
    _get_api_config,
    _transcribe_audio,
    _summarize_transcript,
    _path_exists,
    remove,
):
    payload = {"audioBase64": "Zm9v"}
    encoded_body = base64.b64encode(json.dumps(payload).encode("utf-8")).decode(
        "utf-8"
    )
    event = {"body": encoded_body, "isBase64Encoded": True}

    response = lambda_function.lambda_handler(event, None)

    assert response["statusCode"] == 200
    assert json.loads(response["body"]) == {"text": "formatted"}
    remove.assert_called_once_with("/tmp/audio.webm")


@patch("lambda_function.os.remove")
@patch("lambda_function.os.path.exists", return_value=True)
@patch("lambda_function.summarize_transcript", side_effect=RuntimeError("boom"))
@patch("lambda_function.transcribe_audio", return_value="raw")
@patch(
    "lambda_function.get_api_config",
    return_value={"openai_api_key": "oa", "gemini_api_key": "gm"},
)
@patch("lambda_function._decode_audio_payload", return_value="/tmp/audio.webm")
def test_server_error_still_cleans_up(
    _decode_audio_payload,
    _get_api_config,
    _transcribe_audio,
    _summarize_transcript,
    _path_exists,
    remove,
):
    event = {"body": json.dumps({"audio_base64": "Zm9v"})}

    response = lambda_function.lambda_handler(event, None)

    assert response["statusCode"] == 500
    assert json.loads(response["body"]) == {"error": "boom"}
    remove.assert_called_once_with("/tmp/audio.webm")
