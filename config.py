import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
BASE = Path(__file__).parent


def _list(name, default=""):
    return [x.strip() for x in os.getenv(name, default).split(",") if x.strip()]


BOT_TOKEN = os.environ["BOT_TOKEN"]
OWNER_ID = int(os.environ["OWNER_ID"])

LLM_API_KEY=os.getenv("LLM_API_KEY", "")
LLM_BASE_URL=os.getenv("LLM_BASE_URL", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-3.8-flash")
SCORE_MODEL=os.getenv("SCORE_MODEL") or LLM_MODEL

HH_QUERIES = _list("HH_QUERIES", "тестировщик QAб python разработчик,telegram бот,junior/moddle python,")
HH_USER_AGENT = os.getenv("HH_USER_AGENT", "job-agent/1.0 (vladislavbarysev85@gmail.com)")
HH_TOKEN = os.getenv("HH_TOKEN", "")
HH_RESUME_ID = os.getenv("HH_RESUME_ID", "")

TG_API_ID = int(os.getenv("TG_API_ID") or 0)
TG_API_HASH = os.getenv("TG_API_HASH", "")
TG_CHANNELS = _list("TG_CHANNELS")

CHECK_INTERVAL_MIN = int(os.getenv("CHECK_INTERVAL_MIN", "10"))
MIN_SCORE = int(os.getenv("MIN_SCORE", "6"))
DAILY_APPLY_LIMIT = int(os.getenv("DAILY_APPLY_LIMIT", "15"))

DB_PATH = str(BASE / "jobs.db")
PROFILE = (BASE / "profile.txt").read_text(encoding="utf-8")

# Грубый предфильтр, чтобы не тратить токены на мусор. Правь под себя.
INCLUDE = _list(
    "INCLUDE",
    "python,питон,telegram,телеграм,бот,bot,qa,тестировщик,tester,junior,middle,"
    "django,fastapi,flask,парсер,парсинг,сайт,верстка,wordpress,автоматизация,aiogram",
)
EXCLUDE = _list(
    "EXCLUDE",
    "senior,сеньор,lead,тимлид,team lead,1с,java ,c#,.net,golang,ruby,"
    "ios ,android,devops,data scientist,только офис",
)
