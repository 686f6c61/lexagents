# -*- coding: utf-8 -*-
"""
LexAgents - Sistema Multi-Agente de Extracción Legal
https://github.com/686f6c61/lexagents

LexAgents API
Backend FastAPI para el sistema de extracción de referencias legales
con convergencia iterativa multi-agente.
Versión: 2.0.0

Author: 686f6c61
Version: 0.2.0
License: MIT
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from .config import settings
from .routes import router
from .models import ErrorResponse
from .security import SecurityHeadersMiddleware, RateLimitMiddleware

# Configurar logging
from pathlib import Path
from logging.handlers import RotatingFileHandler

# Crear directorio de logs si no existe
LOG_DIR = Path(__file__).parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "api.log"

# Formato de logs
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

def setup_logging():
    """Configura el logging para escribir a archivo y consola"""
    # Obtener el logger root
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Limpiar handlers existentes para evitar duplicados
    root_logger.handlers.clear()

    # Handler para archivo con rotacion
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))

    # Handler para consola
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))

    # Añadir handlers
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    return logging.getLogger(__name__)

# Inicializar logging
logger = setup_logging()
logger.info(f"Logs guardados en: {LOG_FILE}")


# ============================================================================
# LIFECYCLE
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Maneja el ciclo de vida de la aplicación

    Startup: Inicialización
    Shutdown: Limpieza
    """
    # Startup
    logger.info("=" * 80)
    logger.info("🚀 INICIANDO LEXAGENTS API")
    logger.info("=" * 80)
    logger.info(f"📦 Versión: {settings.API_VERSION}")
    logger.info(f"📂 Data dir: {settings.DATA_DIR}")
    logger.info(f"📤 Upload dir: {settings.UPLOAD_DIR}")
    logger.info(f"📥 Results dir: {settings.RESULTS_DIR}")
    logger.info(f"💾 Cache dir: {settings.CACHE_DIR}")
    logger.info(f"⚙️  Max workers: {settings.MAX_WORKERS}")
    logger.info(f"🔄 Max rondas: {settings.MAX_RONDAS_CONVERGENCIA}")
    logger.info(f"🔐 Autenticación: {'Activada' if settings.API_KEY else 'Desactivada'}")
    logger.info(f"🚦 Rate limit: {settings.RATE_LIMIT_PER_MINUTE}/min")
    logger.info(f"🏭 Modo producción: {'Sí' if settings.PRODUCTION else 'No'}")
    logger.info("=" * 80)

    yield

    # Shutdown
    logger.info("=" * 80)
    logger.info("🛑 CERRANDO LEXAGENTS API")
    logger.info("=" * 80)


# ============================================================================
# APP
# ============================================================================

app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description=settings.API_DESCRIPTION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)


# ============================================================================
# MIDDLEWARE
# ============================================================================

# Cabeceras de seguridad (primero para que se aplique a todas las respuestas)
app.add_middleware(SecurityHeadersMiddleware)

# Rate limiting para endpoints sensibles
app.add_middleware(RateLimitMiddleware)

# CORS (restringido a métodos y headers necesarios)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key"],
)


# Logging de requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Middleware para logging de requests"""
    logger.info(f"→ {request.method} {request.url.path}")

    response = await call_next(request)

    logger.info(f"← {request.method} {request.url.path} - {response.status_code}")

    return response


# ============================================================================
# EXCEPTION HANDLERS
# ============================================================================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handler para errores de validación de Pydantic
    """
    logger.warning(f"❌ Error de validación: {exc.errors()}")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Error de validación",
            "detalle": exc.errors()
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Handler global para excepciones no capturadas.

    En modo producción, no expone detalles del error.
    """
    logger.error(f"❌ Error no manejado: {exc}", exc_info=True)

    # En producción, no exponer detalles internos
    if settings.PRODUCTION:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Error interno del servidor",
                "detalle": "Ha ocurrido un error. Contacta al administrador."
            }
        )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Error interno del servidor",
            "detalle": str(exc)
        }
    )


# ============================================================================
# ROUTES
# ============================================================================

# Incluir todas las rutas
app.include_router(router, prefix="/api/v1")


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """
    Endpoint raíz

    Información básica de la API
    """
    return {
        "nombre": settings.API_TITLE,
        "version": settings.API_VERSION,
        "descripcion": settings.API_DESCRIPTION,
        "docs": "/docs",
        "redoc": "/redoc",
        "openapi": "/openapi.json",
        "endpoints": {
            "health": "/api/v1/health",
            "upload": "/api/v1/upload",
            "process": "/api/v1/process",
            "jobs": "/api/v1/jobs",
            "stats": "/api/v1/stats"
        }
    }


# ============================================================================
# STARTUP MESSAGE
# ============================================================================

if __name__ == "__main__":
    import uvicorn

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
