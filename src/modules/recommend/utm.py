from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def slug_from_url(url: str) -> str | None:
    path = urlsplit(url).path.strip("/")
    if not path:
        return None
    return path.split("/")[-1]


def with_utm(
    url: str,
    *,
    source: str = "tg_bot",
    medium: str = "telegram",
    campaign: str | None = None,
    content: str | None = None,
) -> str:
    if not url or url == "—":
        return url
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    if query.get("utm_source") != source:
        query["utm_source"] = source
    if medium and "utm_medium" not in query:
        query["utm_medium"] = medium
    if campaign and "utm_campaign" not in query:
        query["utm_campaign"] = campaign
    if content and "utm_content" not in query:
        query["utm_content"] = content
    new_query = urlencode(query)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, new_query, parts.fragment))
