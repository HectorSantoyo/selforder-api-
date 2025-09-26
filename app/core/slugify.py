# app/core/slugify.py
import re
import unicodedata

_slug_re = re.compile(r"[^a-z0-9]+")
_hyphens_re = re.compile(r"-+")


def slugify(value: str) -> str:
    if not value:
        return ""
    # normaliza: quita acentos, pasa a ascii/minúsculas y compacta guiones
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    value = value.lower().strip()
    value = _slug_re.sub("-", value)
    value = _hyphens_re.sub("-", value).strip("-")
    return value
