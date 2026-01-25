import base64
import json
import mimetypes
import os
import uuid

import boto3
from openai import OpenAI

_secrets_client = boto3.client("secretsmanager")


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


def _get_secret():
    secret_id = os.environ.get("SECRETS_ARN") or os.environ.get("OPENAI_SECRET_ID")
    if not secret_id:
        raise RuntimeError("Missing SECRETS_ARN env var")

    secret_value = _secrets_client.get_secret_value(SecretId=secret_id)
    secret_string = secret_value.get("SecretString")
    if not secret_string:
        raise RuntimeError("SecretString is empty")

    return json.loads(secret_string)


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
        secret = _get_secret()
        api_key = secret.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY missing from secret")

        client = OpenAI(api_key=api_key)
        with open(audio_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="json",
            )

        text = transcription.get("text") if isinstance(transcription, dict) else transcription.text

        chat_model = os.environ.get("OPENAI_CHAT_MODEL", "gpt-4o-mini")
        prompt = (
            "You will receive a transcript of a voice memo. "
            "Return a cleaned, well-formatted version with corrected syntax and "
            "highlight important items with formatting where appropriate. "
            "Start with a short summary line in the same language as the input. "
            "Then add a blank line and the cleaned text. "
            "Use only Markdown bold (**...**) and bullet lists; no headings, "
            "no code blocks, no links, no tables, no HTML. "
            "Respond in the same language as the original message."
        )

        completion = client.chat.completions.create(
            model=chat_model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": text},
            ],
            temperature=0.2,
        )
        formatted_text = completion.choices[0].message.content
        return _response(200, {"text": formatted_text})
    except Exception as exc:
        return _response(500, {"error": str(exc)})
