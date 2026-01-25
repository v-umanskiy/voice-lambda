from openai import OpenAI


def transcribe_audio(audio_path: str, api_key: str) -> str:
    client = OpenAI(api_key=api_key)
    with open(audio_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="json",
        )

    return transcription.get("text") if isinstance(transcription, dict) else transcription.text
