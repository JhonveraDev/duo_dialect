"""Consulta web opcional, aislada de la conversación y de la información personal."""

import json
import re
import xml.etree.ElementTree as element_tree
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

HTTP_TIMEOUT_SECONDS = 8.0
MAX_QUERY_LENGTH = 200
NEWS_TERMS = frozenset(
    {"noticia", "noticias", "hoy", "actualidad", "última", "ultimo", "último"}
)


@dataclass(frozen=True, slots=True)
class WebSource:
    """Fuente consultada y apta para ser mencionada por el modelo."""

    title: str
    url: str
    published_at: str = ""


@dataclass(frozen=True, slots=True)
class WebLookupResult:
    """Contexto web breve, separado del conocimiento local."""

    summary: str = ""
    sources: tuple[WebSource, ...] = ()

    def as_prompt_context(self) -> str:
        if not self.summary:
            return ""
        source_lines = "\n".join(
            f"- {source.title}" + (f" ({source.published_at})" if source.published_at else "")
            for source in self.sources
        )
        return (
            "CONTEXTO WEB VERIFICABLE (puede estar desactualizado):\n"
            f"{self.summary}\n\nFUENTES WEB:\n{source_lines}\n"
            "Usa este contexto solo para preguntas generales. Si lo usas, menciona la "
            "fuente por su título y no presentes la información como atemporal."
        )


class WebLookupProvider(Protocol):
    """Proveedor de contexto general que nunca publica mensajes por sí mismo."""

    def lookup(self, query: str) -> WebLookupResult:
        """Busca contexto verificable y devuelve vacío ante errores."""


class DisabledWebLookupProvider:
    """Valor seguro por defecto para pruebas y ejecuciones sin Internet."""

    def lookup(self, query: str) -> WebLookupResult:
        del query
        return WebLookupResult()


HttpOpener = Callable[[Request, float], object]


class PublicWebLookupProvider:
    """Consulta DuckDuckGo para datos generales y Google News RSS para actualidad."""

    def __init__(self, opener: HttpOpener | None = None) -> None:
        self._opener = opener or _open_request

    def lookup(self, query: str) -> WebLookupResult:
        normalized = " ".join(query.split())[:MAX_QUERY_LENGTH]
        if not normalized:
            return WebLookupResult()
        if _is_news_query(normalized):
            result = self._lookup_news(normalized)
            if result.summary:
                return result
        return self._lookup_fact(normalized)

    def _lookup_fact(self, query: str) -> WebLookupResult:
        url = "https://api.duckduckgo.com/?q=" + quote_plus(query) + "&format=json&no_html=1"
        payload = _load_json(self._opener, url)
        if not isinstance(payload, dict):
            return WebLookupResult()
        summary = payload.get("AbstractText", "")
        source_title = payload.get("AbstractSource", "DuckDuckGo")
        source_url = payload.get("AbstractURL", "")
        if not all(isinstance(value, str) for value in (summary, source_title, source_url)):
            return WebLookupResult()
        if not summary.strip() or not source_url.strip():
            return WebLookupResult()
        return WebLookupResult(
            summary=summary.strip(), sources=(WebSource(source_title.strip(), source_url.strip()),)
        )

    def _lookup_news(self, query: str) -> WebLookupResult:
        url = (
            "https://news.google.com/rss/search?q="
            + quote_plus(query)
            + "&hl=es-419&gl=CO&ceid=CO:es-419"
        )
        xml_text = _load_text(self._opener, url)
        if not xml_text:
            return WebLookupResult()
        try:
            root = element_tree.fromstring(xml_text)
        except element_tree.ParseError:
            return WebLookupResult()
        item = root.find("./channel/item")
        if item is None:
            return WebLookupResult()
        title = _child_text(item, "title")
        link = _child_text(item, "link")
        published_at = _child_text(item, "pubDate")
        if not title or not link:
            return WebLookupResult()
        return WebLookupResult(
            summary=title,
            sources=(WebSource("Google News", link, published_at),),
        )


def create_web_lookup(enabled: bool) -> WebLookupProvider:
    """Crea el proveedor configurado sin acoplarlo al dominio."""
    return PublicWebLookupProvider() if enabled else DisabledWebLookupProvider()


def _is_news_query(query: str) -> bool:
    words = {word.casefold() for word in re.findall(r"[\wáéíóúüñ]+", query)}
    return bool(words & NEWS_TERMS)


def _open_request(request: Request, timeout: float) -> object:
    return urlopen(request, timeout=timeout)


def _load_json(opener: HttpOpener, url: str) -> object | None:
    text = _load_text(opener, url)
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _load_text(opener: HttpOpener, url: str) -> str:
    request = Request(url, headers={"User-Agent": "codex-bot/0.1"})
    try:
        response = opener(request, HTTP_TIMEOUT_SECONDS)
        with response:  # type: ignore[union-attr]
            raw = response.read()
    except (OSError, TimeoutError):
        return ""
    if not isinstance(raw, bytes):
        return ""
    return raw.decode("utf-8", errors="replace")


def _child_text(item: element_tree.Element, name: str) -> str:
    child = item.find(name)
    return child.text.strip() if child is not None and child.text else ""