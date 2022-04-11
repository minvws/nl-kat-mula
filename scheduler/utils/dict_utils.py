from typing import Any, Dict, List


def deep_get(d: Dict, keys: List[str]) -> Any:
    if not keys or d is None:
        return d
    return deep_get(d.get(keys[0]), keys[1:])
