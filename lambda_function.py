import base64
import json
import mimetypes
import os
import uuid

from secrets import get_api_config
from summarize import summarize_transcript
from transcription import transcribe_audio


def _response(status_code, payload):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Methods": "POST,OPTIONS",
        },
        "body": json.dumps(payload),
    }


def _decode_audio_payload(payload):
    audio_base64 = payload.get("audio_base64") or payload.get("audioBase64")
    mime_type = payload.get("mime_type") or payload.get("mimeType") or "audio/webm"

    if not audio_base64:
        raise ValueError("Missing audio_base64")

    if audio_base64.startswith("data:"):
        header, encoded = audio_base64.split(",", 1)
        if ";base64" in header:
            audio_base64 = encoded

    audio_bytes = base64.b64decode(audio_base64)
    extension = mimetypes.guess_extension(mime_type) or ".webm"
    filename = payload.get("filename") or f"audio-{uuid.uuid4()}{extension}"
    filepath = os.path.join("/tmp", filename)

    with open(filepath, "wb") as audio_file:
        audio_file.write(audio_bytes)

    return filepath


def lambda_handler(event, _context):
    path = event.get("rawPath") or event.get("path") or ""
    if path.endswith("/health"):
        return _response(200, {"status": "ok"})

    body = event.get("body") or ""
    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode("utf-8")

    try:
        payload = json.loads(body) if isinstance(body, str) else body
    except json.JSONDecodeError:
        return _response(400, {"error": "Invalid JSON body"})

    try:
        audio_path = _decode_audio_payload(payload)
    except ValueError as exc:
        return _response(400, {"error": str(exc)})

    try:
        config = get_api_config()
        try:
            text = transcribe_audio(audio_path, config["openai_api_key"])
            formatted_text = summarize_transcript(text, config["gemini_api_key"])
            return _response(200, {"text": formatted_text})
        finally:
            if audio_path and os.path.exists(audio_path):
                os.remove(audio_path)
    except Exception as exc:
        return _response(500, {"error": str(exc)})
