import base64
import json
import mimetypes
import os
import re
import uuid

import google.generativeai as genai
from openai import OpenAI

from secrets import get_api_config


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
        client = OpenAI(api_key=config["openai_api_key"])
        try:
            with open(audio_path, "rb") as audio_file:
                transcription = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="json",
                )

            text = (
                transcription.get("text") if isinstance(transcription, dict) else transcription.text
            )
            prompt = (
                "You will receive a transcript of a voice memo. "
                "Return a cleaned, well-formatted version with corrected syntax and "
                "highlight important items with formatting where appropriate. "
                "Output must be exactly two blocks separated by a line break: "
                "(1) summary, blank line, (2) cleaned text. "
                "Summary line must be in the same language as the input and prefixed "
                "with a local equivalent of \"Summary:\" (e.g., \"Zusammenfassung:\", "
                "\"Резюме:\", \"Resumen:\"). "
                "Then add a blank line and the cleaned text. "
                "Use only Markdown bold (**...**) and bullet lists; no headings, "
                "no code blocks, no links, no tables, no HTML. "
                "Respond in the same language as the original message."
            )

            genai.configure(api_key=config["gemini_api_key"])
            gemini_model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
            model = genai.GenerativeModel(gemini_model)
            response = model.generate_content(f"{prompt}\n\nTranscript:\n{text}")
            formatted_text = response.text or ""
            formatted_text = re.sub(r"^(\s*)[*•]\s+", r"\1- ", formatted_text, flags=re.MULTILINE)
            return _response(200, {"text": formatted_text})
        finally:
            if audio_path and os.path.exists(audio_path):
                os.remove(audio_path)
    except Exception as exc:
        return _response(500, {"error": str(exc)})
