from typing import Any, Dict, List

from factory import Factory, Sequence
from scheduler.models import BoefjeMeta, RawData


class RawDataFactory(Factory):
    class Meta:
        model = RawData

    id: str = Sequence(lambda n: n)
    boefje_meta: BoefjeMeta = None
    mime_types: List[Dict[str, str]] = []
    secure_hash: str = ""
    hash_retrieval_link: str = ""
