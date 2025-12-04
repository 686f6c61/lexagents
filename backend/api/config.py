# -*- coding: utf-8 -*-
"""
LexAgents - Sistema Multi-Agente de Extracción Legal
https://github.com/686f6c61/lexagents

Configuración del Backend FastAPI
Variables de entorno y configuración global

Author: 686f6c61
Version: 0.2.0
License: MIT
"""

from pydantic_settings import BaseSettings
from pathlib import Path
from typing import Optional


class Settings(BaseSettings):
    """
    Configuración de la aplicación

    Usa variables de entorno o valores por defecto
    """

    # API
    API_TITLE: str = "LexAgents - Extracción de referencias legales"
    API_VERSION: str = "0.2.0"
    API_DESCRIPTION: str = "Sistema multi-agente para extracción, validación y organización de referencias legales con integración BOE y EUR-Lex"

    # CORS
    CORS_ORIGINS: list = [
        "http://localhost:3000",  # React dev server
        "http://localhost:5173",  # Vite dev server
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    # Paths
    BASE_DIR: Path = Path(__file__).parent.parent
    DATA_DIR: Path = BASE_DIR.parent / "data"
    JSON_DIR: Path = DATA_DIR / "json"
    UPLOAD_DIR: Path = DATA_DIR / "uploads"
    RESULTS_DIR: Path = DATA_DIR / "results"
    CACHE_DIR: Path = DATA_DIR / "cache"

    # Pipeline
    MAX_RONDAS_CONVERGENCIA: int = 3
    MAX_WORKERS: int = 4
    USE_CACHE: bool = True
    LIMITE_TEXTO_DEFAULT: Optional[int] = None  # Sin límite por defecto

    # Jobs
    MAX_CONCURRENT_JOBS: int = 2
    JOB_TIMEOUT_SECONDS: int = 300  # 5 minutos

    # Gemini API
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.5-pro"

    # Tamaño máximo de upload (10MB)
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024

    # Seguridad
    API_KEY: Optional[str] = None  # API key para autenticación (si None, sin autenticación)
    PRODUCTION: bool = False  # Modo producción (sanitiza errores)
    RATE_LIMIT_PER_MINUTE: int = 10  # Límite de peticiones por minuto

    class Config:
        env_file = ".env"
        case_sensitive = True


# Instancia global de configuración
settings = Settings()

# Crear directorios necesarios
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
settings.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
settings.CACHE_DIR.mkdir(parents=True, exist_ok=True)
