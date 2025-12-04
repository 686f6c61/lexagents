# -*- coding: utf-8 -*-
"""
LexAgents - Sistema Multi-Agente de Extracción Legal
https://github.com/686f6c61/lexagents

Módulo de seguridad para LexAgents API
Incluye:
- Autenticación por API key
- Rate limiting
- Validación de paths

Author: 686f6c61
Version: 0.2.0
License: MIT
"""

import time
import logging
from typing import Optional, Dict
from collections import defaultdict
from pathlib import Path

from fastapi import Request, HTTPException, Depends
from fastapi.security import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from .config import settings

logger = logging.getLogger(__name__)


# ============================================================================
# AUTENTICACIÓN POR API KEY
# ============================================================================

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: Optional[str] = Depends(api_key_header)) -> bool:
    """
    Verifica la API key del request.

    Si API_KEY no está configurada en settings, permite todas las peticiones.
    Si está configurada, requiere que coincida.
    """
    # Si no hay API key configurada, permitir todo (modo desarrollo)
    if not settings.API_KEY:
        return True

    # Si hay API key configurada, validar
    if not api_key:
        logger.warning("Petición sin API key")
        raise HTTPException(
            status_code=401,
            detail="API key requerida. Incluye header 'X-API-Key'"
        )

    if api_key != settings.API_KEY:
        logger.warning(f"API key inválida: {api_key[:8]}...")
        raise HTTPException(
            status_code=403,
            detail="API key inválida"
        )

    return True


# ============================================================================
# RATE LIMITING
# ============================================================================

class RateLimiter:
    """
    Rate limiter simple basado en IP.

    Almacena contadores en memoria (se reinician al reiniciar el servidor).
    Para producción, usar Redis.
    """

    def __init__(self, requests_per_minute: int = 10):
        self.requests_per_minute = requests_per_minute
        self.requests: Dict[str, list] = defaultdict(list)

    def is_allowed(self, client_ip: str) -> bool:
        """
        Verifica si el cliente puede hacer otra petición.

        Returns:
            True si está permitido, False si excede el límite
        """
        now = time.time()
        minute_ago = now - 60

        # Limpiar peticiones antiguas
        self.requests[client_ip] = [
            t for t in self.requests[client_ip] if t > minute_ago
        ]

        # Verificar límite
        if len(self.requests[client_ip]) >= self.requests_per_minute:
            return False

        # Registrar petición
        self.requests[client_ip].append(now)
        return True

    def get_remaining(self, client_ip: str) -> int:
        """Retorna peticiones restantes para este cliente"""
        now = time.time()
        minute_ago = now - 60

        current_requests = [
            t for t in self.requests[client_ip] if t > minute_ago
        ]

        return max(0, self.requests_per_minute - len(current_requests))


# Instancia global del rate limiter
rate_limiter = RateLimiter(requests_per_minute=settings.RATE_LIMIT_PER_MINUTE)


def get_client_ip(request: Request) -> str:
    """Obtiene la IP del cliente, considerando proxies"""
    # Verificar headers de proxy
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    return request.client.host if request.client else "unknown"


async def check_rate_limit(request: Request) -> bool:
    """
    Dependency para verificar rate limit.

    Lanza HTTPException si se excede el límite.
    """
    client_ip = get_client_ip(request)

    if not rate_limiter.is_allowed(client_ip):
        remaining = rate_limiter.get_remaining(client_ip)
        logger.warning(f"Rate limit excedido para {client_ip}")
        raise HTTPException(
            status_code=429,
            detail=f"Demasiadas peticiones. Límite: {settings.RATE_LIMIT_PER_MINUTE}/minuto. Espera un momento."
        )

    return True


# ============================================================================
# VALIDACIÓN DE PATHS
# ============================================================================

def validate_path_within_directory(file_path: Path, allowed_dir: Path) -> bool:
    """
    Valida que un path esté dentro de un directorio permitido.

    Previene ataques de path traversal (../../etc/passwd).

    Args:
        file_path: Path a validar
        allowed_dir: Directorio permitido

    Returns:
        True si el path es válido

    Raises:
        HTTPException si el path está fuera del directorio permitido
    """
    try:
        # Resolver paths absolutos
        resolved_path = file_path.resolve()
        resolved_dir = allowed_dir.resolve()

        # Verificar que el path está dentro del directorio
        if not str(resolved_path).startswith(str(resolved_dir)):
            logger.warning(f"Path traversal detectado: {file_path} fuera de {allowed_dir}")
            raise HTTPException(
                status_code=403,
                detail="Acceso denegado"
            )

        return True

    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        logger.error(f"Error validando path: {e}")
        raise HTTPException(status_code=400, detail="Path inválido")


# ============================================================================
# MIDDLEWARE DE SEGURIDAD
# ============================================================================

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware que añade cabeceras de seguridad HTTP a todas las respuestas.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # Cabeceras de seguridad
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Cache control para APIs
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
            response.headers["Pragma"] = "no-cache"

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware de rate limiting para endpoints sensibles.
    """

    # Endpoints que requieren rate limiting estricto
    RATE_LIMITED_PATHS = [
        "/api/v1/process",
        "/api/v1/upload",
    ]

    async def dispatch(self, request: Request, call_next) -> Response:
        # Solo aplicar rate limiting a endpoints sensibles
        if any(request.url.path.startswith(path) for path in self.RATE_LIMITED_PATHS):
            client_ip = get_client_ip(request)

            if not rate_limiter.is_allowed(client_ip):
                logger.warning(f"Rate limit excedido para {client_ip} en {request.url.path}")
                return Response(
                    content='{"detail": "Demasiadas peticiones. Espera un momento."}',
                    status_code=429,
                    media_type="application/json"
                )

        return await call_next(request)


# ============================================================================
# VALIDACIÓN DE CONTENIDO DE ARCHIVOS
# ============================================================================

# Magic bytes para tipos de archivo comunes
MAGIC_BYTES = {
    'pdf': b'%PDF',
    'docx': b'PK\x03\x04',  # ZIP (DOCX es un ZIP)
    'zip': b'PK\x03\x04',
}


def validate_file_content(content: bytes, expected_extension: str) -> bool:
    """
    Valida que el contenido del archivo coincida con su extensión.

    Args:
        content: Contenido del archivo
        expected_extension: Extensión esperada (sin punto)

    Returns:
        True si el contenido parece válido

    Raises:
        HTTPException si el contenido no coincide con la extensión
    """
    ext = expected_extension.lower().lstrip('.')

    # Para texto plano y markdown, cualquier contenido es válido
    if ext in ('txt', 'md', 'json'):
        return True

    # Verificar magic bytes
    if ext in MAGIC_BYTES:
        expected_magic = MAGIC_BYTES[ext]
        if not content.startswith(expected_magic):
            logger.warning(f"Contenido no coincide con extensión {ext}")
            raise HTTPException(
                status_code=400,
                detail=f"El contenido del archivo no parece ser un {ext.upper()} válido"
            )

    return True
