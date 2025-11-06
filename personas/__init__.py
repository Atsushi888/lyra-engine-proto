# personas/__init__.py

from typing import Dict
from . import persona_floria_ja

Persona = persona_floria_ja.Persona  # 型のエイリアス

PERSONA_MAP: Dict[str, object] = {
    "floria_ja": persona_floria_ja,
}

def get_persona(char_id: str) -> Persona:
    mod = PERSONA_MAP[char_id]
    return mod.get_persona()
