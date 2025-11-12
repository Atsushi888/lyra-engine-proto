from __future__ import annotations
from enum import IntEnum

class Role(IntEnum):
    GUEST = 0
    USER  = 1
    ADMIN = 2
    DEV   = 3  # 任意
