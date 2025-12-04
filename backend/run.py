# -*- coding: utf-8 -*-
"""
LexAgents - Sistema Multi-Agente de Extracción Legal
https://github.com/686f6c61/lexagents

Script de inicio del servidor LexAgents
Ejecutar con: python run.py

Author: 686f6c61
Version: 0.2.0
License: MIT
"""

import uvicorn
from api.config import settings

if __name__ == "__main__":
    print("=" * 80)
    print("🚀 INICIANDO SERVIDOR DE DESARROLLO")
    print("=" * 80)
    print(f"📦 {settings.API_TITLE} v{settings.API_VERSION}")
    print(f"🌐 http://localhost:8000")
    print(f"📚 Docs: http://localhost:8000/docs")
    print("=" * 80)

    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
