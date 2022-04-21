import logging
from typing import Any

from scheduler import context


class Ranker:
    def __init__(self, ctx: context.AppContext) -> None:
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.ctx: context.AppContext = ctx

    def rank(self, obj: Any) -> int:
        raise NotImplementedError()
