# -*- coding: utf-8 -*-
"""
LexAgents - Sistema Multi-Agente de Extracción Legal
https://github.com/686f6c61/lexagents

Agentes de IA para extracción, normalización y validación de referencias legales

Author: 686f6c61
Version: 0.2.0
License: MIT
"""

from .base_agent import BaseAgent
from .extractor_agent_a import ExtractorAgentA
from .extractor_agent_b import ExtractorAgentB

__all__ = [
    'BaseAgent',
    'ExtractorAgentA',
    'ExtractorAgentB',
]
