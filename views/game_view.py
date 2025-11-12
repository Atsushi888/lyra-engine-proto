# views/game_view.py
from __future__ import annotations
import streamlit as st
from lyra_engine import LyraEngine

class GameView:
    def __init__(self) -> None:
        self.engine = LyraEngine()

    def render(self) -> None:
        self.engine.render()
