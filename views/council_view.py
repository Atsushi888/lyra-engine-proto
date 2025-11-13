# views/council_view.py

from __future__ import annotations

from council.council_manager import CouncilManager


class CouncilView:
    def __init__(self) -> None:
        # ★ 引数は渡さない
        self.manager = CouncilManager()

    def render(self) -> None:
        self.manager.render()
