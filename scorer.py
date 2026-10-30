import json
import logging
import re
import time

from openai import AsyncOpenAI

from config import (EXCLUDE, INCLUDE, LLM_API_KEY, LLM_BASE_URL, LLM_MODEL,
                    PROFILE, SCORE_MODEL)

log = logging.getLogger("scorer")

# Работает с любым OpenAI-совместимым API: DeepSeek, Gemini, Groq, OpenRouter, OpenAI.
llm = (
    AsyncOpenAI(
        api_key=LLM_API_KEY,
        base_url=LLM_BASE_URL or None,
        timeout=35.5,      # ждем 35 секунд
        max_retries=0      # БЕЗ повторов (сразу выдаем ошибку)
    )
    if LLM_API_KEY
    else None
)
_fails = 0
_pause_until = 0.0

def passes(text: str) -> bool:
    t = text.lower()
    if any(x in t for x in EXCLUDE):
        return False
    return any(x in t for x in INCLUDE)


async def _ask(prompt: str, max_tokens: int, model: str = None) -> str:
    r = await llm.chat.completions.create(
        model=model or LLM_MODEL,
        max_tokens=max_tokens,
        temperature=0.4,
        messages=[{"role": "user", "content": prompt}],  # type: ignore
    )
    text = (r.choices[0].message.content or "").strip()
    # некоторые модели выводят рассуждения в <think>…</think>
    return re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()


async def score(text: str) -> tuple[int, str]:
    global _fails, _pause_until
    if not llm or time.time() < _pause_until:
        return 0, "без нейросети (недоступна или не задана)"
    prompt = (
        f"Профиль кандидата:\n{PROFILE}\n\nВакансия:\n{text[:4500]}\n\n"
        "Оцени, насколько вакансия подходит кандидату, от 1 до 10. "
        "Учитывай удалёнку, уровень (junior/middle), стек, честность условий. "
        "Если это явно скам, работа за процент или схема, ставь 1-2. "
        'Ответь ТОЛЬКО JSON: {"score": число, "reason": "одна короткая фраза по-русски"}'
    )
    try:
        raw = await _ask(prompt, 300, SCORE_MODEL)
        m = re.search(r"\{.*}", raw, re.S)
        data = json.loads(m.group(0))
        _fails = 0
        return int(data["score"]), str(data["reason"])[:200]
    except Exception as e:
        log.warning("score error: %s", e)
        msg = str(e)

        # 1) Если это 429 (лимит) — вытаскиваем retryDelay и ставим паузу на него
        if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
            m = re.search(r"retry in ([\d.]+)s", msg) or re.search(r"retryDelay\D*(\d+)s", msg)
            wait = float(m.group(1)) if m else 60.0
            _pause_until = time.time() + wait
            _fails = 0
            log.warning("Gemini 429: пауза %.0f сек", wait)
            return 0, f"лимит Gemini, пауза {int(wait)}с"

        # 2) Остальные ошибки (сеть, 5xx) — старая логика с 3 попытками
        _fails += 1
        if _fails >= 3:
            _pause_until = time.time() + 600
            _fails = 0
            log.warning("Нейросеть недоступна, пауза 10 минут")
        return 0, "без оценки нейросетью (ошибка API)"

async def letter(text: str) -> str:
    global _fails, _pause_until
    if not llm:
        return "Не задан LLM_API_KEY: письмо сгенерировать нельзя. Добавьте ключ в .env."
    if time.time() < _pause_until:
        return f"Нейросеть на паузе ещё {int(_pause_until - time.time())}с, попробуй позже."
    prompt = (
        f"Профиль кандидата:\n{PROFILE}\n\nВакансия:\n{text[:4500]}\n\n"
        "Напиши короткое сопроводительное письмо (500-800 знаков) по-русски. Требования:\n"
        "- обратись по-человечески, без канцелярита и шаблонных фраз;\n"
        "- сразу зацепи конкретным требованием из вакансии и скажи, чем из реального опыта кандидата это закрывается;\n"
        "- упомяни GitHub github.com/valdik305, если это уместно;\n"
        "- ничего не выдумывай: только факты из профиля;\n"
        "- в конце готовность выполнить тестовое задание или созвониться.\n"
        "Верни только текст письма."
    )
    try:
        return await _ask(prompt, 700)
    except Exception as e:
        log.warning("letter error: %s", e)
        msg = str(e)
        if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
            m = re.search(r"retry in ([\d.]+)s", msg) or re.search(r"retryDelay\D*(\d+)s", msg)
            wait = float(m.group(1)) if m else 60.0
            _pause_until = time.time() + wait
            log.warning("Gemini 429: пауза %.0f сек", wait)
            return f"⚠️ Лимит Gemini. Попробуй через {int(wait)} секунд."
        return f"⚠️ Ошибка генерации: {e}"