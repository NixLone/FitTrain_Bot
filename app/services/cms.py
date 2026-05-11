from __future__ import annotations

from typing import Any

import httpx

from app.config import get_settings

settings = get_settings()


class CmsMagicLinkError(Exception):
    pass


async def create_cms_magic_link(*, staff_telegram_id: int) -> str:
    url = f"{settings.cms_api_url.rstrip('/')}/auth/magic-links"
    payload: dict[str, Any] = {"staff_telegram_id": staff_telegram_id}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, json=payload)
    except httpx.HTTPError as exc:
        raise CmsMagicLinkError("CMS API is unavailable") from exc

    if response.status_code >= 400:
        detail = None
        try:
            detail = response.json().get("detail")
        except Exception:
            detail = response.text
        raise CmsMagicLinkError(str(detail or "Failed to create magic link"))

    data = response.json()
    link = data.get("url")
    if not link:
        raise CmsMagicLinkError("CMS returned empty login URL")
    return str(link)
