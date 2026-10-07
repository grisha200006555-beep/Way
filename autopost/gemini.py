"""Gemini: генерация сценария и картинок через REST API (без SDK, только stdlib)."""

import base64
import json
import os
import urllib.error
import urllib.request

API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
# Nano Banana Pro — та же модель, что во встроенной генерации картинок бота.
IMAGE_MODEL = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-3-pro-image-preview")
TEXT_MODEL = os.environ.get("GEMINI_TEXT_MODEL", "gemini-2.5-flash")


class GeminiError(RuntimeError):
    pass


def _api_key():
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise GeminiError("Не задан GEMINI_API_KEY")
    return key


def _generate(model, body, timeout=180):
    req = urllib.request.Request(
        f"{API_BASE}/{model}:generateContent",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "x-goog-api-key": _api_key()},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        raise GeminiError(f"Gemini {e.code}: {e.read().decode(errors='replace')[:500]}") from e


def _parts(response):
    candidates = response.get("candidates") or []
    if not candidates:
        raise GeminiError(f"Пустой ответ Gemini: {json.dumps(response)[:500]}")
    return candidates[0].get("content", {}).get("parts", [])


def generate_image(prompt, out_path, aspect_ratio="9:16"):
    """Генерирует вертикальную картинку и сохраняет её в out_path."""
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseModalities": ["IMAGE"],
            "imageConfig": {"aspectRatio": aspect_ratio},
        },
    }
    for part in _parts(_generate(IMAGE_MODEL, body)):
        data = (part.get("inlineData") or part.get("inline_data") or {}).get("data")
        if data:
            with open(out_path, "wb") as f:
                f.write(base64.b64decode(data))
            return out_path
    raise GeminiError("Gemini не вернул картинку (возможно, сработал фильтр безопасности)")


SCENARIO_PROMPT = """Ты делаешь короткий вертикальный ролик для Instagram Reels.
Тема: {topic}

Верни JSON без пояснений в формате:
{{
  "caption": "подпись к посту на русском, 1-3 предложения и 3-5 хэштегов",
  "scenes": [
    {{"text": "короткий текст на экране, до 60 символов", "image_prompt": "подробное описание кадра на английском, вертикальный кадр 9:16, без текста на картинке"}}
  ]
}}
Сцен: {scenes}. Первая сцена — цепляющий хук, последняя — призыв к действию."""


def generate_scenario(topic, scenes=4):
    body = {
        "contents": [{"parts": [{"text": SCENARIO_PROMPT.format(topic=topic, scenes=scenes)}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }
    text = "".join(p.get("text", "") for p in _parts(_generate(TEXT_MODEL, body)))
    try:
        scenario = json.loads(text)
    except json.JSONDecodeError as e:
        raise GeminiError(f"Gemini вернул не JSON: {text[:300]}") from e
    if not scenario.get("scenes"):
        raise GeminiError("В сценарии нет сцен")
    return scenario
