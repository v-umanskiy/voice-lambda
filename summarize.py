import os
import re

from google import genai


_PROMPT = (
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


def summarize_transcript(transcript: str, api_key: str) -> str:
    gemini_model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=gemini_model,
        contents=f"{_PROMPT}\n\nTranscript:\n{transcript}",
    )
    formatted_text = response.text or ""
    return re.sub(r"^(\s*)[*•]\s+", r"\1- ", formatted_text, flags=re.MULTILINE)
