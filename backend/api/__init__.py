# -*- coding: utf-8 -*-
"""
LexAgents - Sistema Multi-Agente de Extracción Legal
https://github.com/686f6c61/lexagents

API Package
Backend FastAPI para LexAgents

Author: 686f6c61
Version: 0.2.0
License: MIT
"""

from .main import app
from .config import settings

__version__ = "0.2.0"
__all__ = ["app", "settings"]
