import asyncio
import html
import logging
import re

import httpx

from config import HH_QUERIES, HH_RESUME_ID, HH_TOKEN, HH_USER_AGENT

log = logging.getLogger("hh")
API = "https://api.hh.ru"


def _headers() -> dict:
    h = {"User-Agent": HH_USER_AGENT, "HH-User-Agent": HH_USER_AGENT}
    if HH_TOKEN:
        h["Authorization"] = f"Bearer {HH_TOKEN}"
    return h


def _clean(t: str) -> str:
    t = re.sub(r"<[^>]+>", " ", t or "")
    return re.sub(r"\s+", " ", html.unescape(t)).strip()


async def fetch_new(known) -> list[dict]:
    """Возвращает свежие вакансии (за последние сутки), которых ещё нет в базе."""
    out, seen = [], set()
    async with httpx.AsyncClient(headers=_headers(), timeout=25) as c:
        for q in HH_QUERIES:
            try:
                r = await c.get(
                    f"{API}/vacancies",
                    params={
                        "text": q,
                        "schedule": "remote",
                        "period": 1,
                        "per_page": 50,
                        "order_by": "publication_time",
                    },
                )
            except httpx.HTTPError as e:
                log.warning("hh search error: %s", e)
                continue
            if r.status_code != 200:
                log.warning("hh search %s -> %s %s", q, r.status_code, r.text[:200])
                continue
            for it in r.json().get("items", []):
                uid = f"hh:{it['id']}"
                if uid in seen or known(uid):
                    continue
                seen.add(uid)
                text = ""
                try:
                    d = await c.get(f"{API}/vacancies/{it['id']}")
                    if d.status_code == 200:
                        text = _clean(d.json().get("description"))
                except httpx.HTTPError:
                    pass
                sal = it.get("salary") or {}
                sal_s = ""
                if sal:
                    sal_s = f"\nЗарплата: {sal.get('from') or ''}-{sal.get('to') or ''} {sal.get('currency') or ''}"
                out.append(
                    {
                        "uid": uid,
                        "source": "hh",
                        "title": it.get("name", ""),
                        "company": (it.get("employer") or {}).get("name", ""),
                        "url": it.get("alternate_url", ""),
                        "text": f"{it.get('name','')}{sal_s}\n{text}"[:6000],
                    }
                )
            await asyncio.sleep(0.7)
    return out


async def apply(vacancy_id: str, message: str) -> tuple[bool, str]:
    """Отклик через API. Нужны HH_TOKEN (токен пользователя) и HH_RESUME_ID."""
    if not (HH_TOKEN and HH_RESUME_ID):
        return False, "Не заданы HH_TOKEN / HH_RESUME_ID"
    async with httpx.AsyncClient(headers=_headers(), timeout=25) as c:
        r = await c.post(
            f"{API}/negotiations",
            data={"vacancy_id": vacancy_id, "resume_id": HH_RESUME_ID, "message": message},
        )
    ok = r.status_code in (200, 201, 204)
    return ok, "" if ok else f"{r.status_code}: {r.text[:300]}"
