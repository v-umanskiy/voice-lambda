# Voice Transcription Lambda

AWS Lambda handler that accepts base64 audio from a Next.js UI, sends it to OpenAI Whisper, and returns text.

## Environment

- `OPENAI_SECRET_ID`: Secrets Manager ID/ARN/name that contains JSON like:
  ```json
  {"OPENAI_API_KEY":"sk-..."}
  ```
- `OPENAI_CHAT_MODEL` (optional): Defaults to `gpt-4o-mini`.

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
