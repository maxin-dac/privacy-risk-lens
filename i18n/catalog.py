import json
from pathlib import Path

_BASE = Path(__file__).parent
_LANGS = ("fr", "en")
_C = {lg: json.loads((_BASE / f"{lg}.json").read_text(encoding="utf-8")) for lg in _LANGS}

def t(key, lang="fr"):
    cur = _C.get(lang, _C["fr"])
    node = cur.get(key)
    if node is None:
        node = _C["fr"].get(key, key)
    return node if isinstance(node, str) else key