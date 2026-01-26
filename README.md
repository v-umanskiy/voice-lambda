# Voice Lambda

This Lambda accepts base64 audio from the desktop app, transcribes it with
OpenAI Whisper, and enriches the result with Gemini (summary + cleaned text).

## Architecture Overview

- Input: JSON payload with `audio_base64` and `mime_type`.
- Transcription: OpenAI Whisper (`whisper-1`).
- Enrichment: Gemini (`gemini-2.5-flash` by default) for summary + formatting.
- Output: JSON `{ "text": "..." }`.

## Environment

- `SECRETS_ARN`: Secrets Manager ARN/name that contains JSON like:
  ```json
  {"OPENAI_API_KEY":"sk-...","GEMINI_API_KEY":"..."}
  ```
- `GEMINI_MODEL` (optional): Defaults to `gemini-2.5-flash`.

## Behavior

- Returns a summary line followed by a blank line and the cleaned text.
- Supports Markdown bold and bullet lists in the response.

## Request

Send JSON in the body (API Gateway proxy). Example:

```json
{
  "audio_base64": "<base64 or data URL>",
  "mime_type": "audio/webm"
}
```

Also accepts camelCase keys (`audioBase64`, `mimeType`).

## Health Check

Call `GET /health` to receive `{ "status": "ok" }`.

## Response

```json
{
  "text": "..."
}
```

## Notes

- CORS headers are included in the response.
- Audio is written to `/tmp` before upload to OpenAI.
