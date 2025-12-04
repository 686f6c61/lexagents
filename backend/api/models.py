# -*- coding: utf-8 -*-
"""
LexAgents - Sistema Multi-Agente de Extracción Legal
https://github.com/686f6c61/lexagents

Modelos Pydantic para API
Requests, responses y validación de datos

Author: 686f6c61
Version: 0.2.0
License: MIT
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ============================================================================
# ENUMS
# ============================================================================

class JobStatus(str, Enum):
    """Estado de un job de procesamiento"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExportFormat(str, Enum):
    """Formatos de exportación disponibles"""
    MARKDOWN = "md"
    TEXT = "txt"
    WORD = "docx"
    PDF = "pdf"


# ============================================================================
# REQUESTS
# ============================================================================

class ProcessRequest(BaseModel):
    """
    Request para procesar un tema

    El tema puede venir como:
    - archivo_id: ID de archivo previamente subido
    - contenido_json: JSON directo del tema
    """
    archivo_id: Optional[str] = Field(None, description="ID del archivo JSON subido")
    contenido_json: Optional[Dict[str, Any]] = Field(None, description="Contenido JSON directo")

    # Configuración del pipeline
    max_rondas: int = Field(3, ge=1, le=10, description="Máximo de rondas de convergencia")
    max_workers: int = Field(4, ge=1, le=8, description="Workers paralelos")
    use_cache: bool = Field(False, description="Usar cache de API (desmarcado por defecto)")
    use_context_agent: bool = Field(True, description="Usar agente de contexto para resolver referencias incompletas")
    use_inference_agent: bool = Field(False, description="Usar agente de inferencia para sugerir normativa relacionada (BETA)")
    umbral_confianza: int = Field(70, ge=50, le=95, description="Umbral mínimo de confianza para incluir referencias")
    limite_texto: Optional[int] = Field(None, ge=1000, description="Límite de caracteres (opcional)")

    # Exportación
    exportar: bool = Field(True, description="Exportar resultados")
    formatos: List[ExportFormat] = Field(
        [ExportFormat.MARKDOWN, ExportFormat.TEXT, ExportFormat.WORD],
        description="Formatos de exportación"
    )

    @validator('contenido_json', 'archivo_id')
    def check_input(cls, v, values):
        """Validar que se proporcione al menos un input"""
        if 'archivo_id' in values and 'contenido_json' in values:
            if not values.get('archivo_id') and not values.get('contenido_json'):
                raise ValueError('Debe proporcionar archivo_id o contenido_json')
        return v


class JobQueryRequest(BaseModel):
    """Request para consultar un job"""
    job_id: str = Field(..., description="ID del job")


# ============================================================================
# RESPONSES
# ============================================================================

class HealthResponse(BaseModel):
    """Response de health check"""
    status: str = "ok"
    version: str
    timestamp: datetime = Field(default_factory=datetime.now)


class SystemInfoResponse(BaseModel):
    """Response con información completa del sistema"""
    status: str = "ok"
    version: str
    modelo_ia: str  # Se obtiene del config
    gemini_conectado: bool  # Si la API KEY está configurada
    agentes: List[str] = [
        "Extractor Conservador (Agente A, temp=0.1)",
        "Extractor Agresivo (Agente B, temp=0.4)",
        "Extractor Sabueso (Agente C, temp=0.4)",
        "Resolver de Contexto (BETA)",
        "Resolver de Títulos",
        "Normalizador",
        "Validador BOE",
        "Extractor EUR-Lex (temp=0.1)",
        "Agente de Inferencia (BETA, temp=0.1)"
    ]
    agentes_activos: bool  # True si Gemini está conectado
    boe_conectado: bool
    boe_url: str = "https://www.boe.es/datosabiertos/api/legislacion-consolidada"
    eurlex_conectado: bool
    eurlex_url: str = "https://eur-lex.europa.eu"
    max_rondas: int
    max_workers: int
    timestamp: datetime = Field(default_factory=datetime.now)


class UploadResponse(BaseModel):
    """Response de upload de archivo"""
    archivo_id: str = Field(..., description="ID único del archivo")
    nombre_original: str = Field(..., description="Nombre original del archivo")
    tamaño_bytes: int = Field(..., description="Tamaño en bytes")
    timestamp: datetime = Field(default_factory=datetime.now)
    mensaje: str = "Archivo subido exitosamente"


class ReferenciaResponse(BaseModel):
    """Una referencia legal extraída"""
    texto_completo: str
    tipo: str
    ley: Optional[str] = None
    articulo: Optional[str] = None
    confianza: int
    validada: bool = Field(False, alias="_validada")
    boe_id: Optional[str] = None
    boe_url: Optional[str] = None
    encontrado_por: Optional[str] = None

    class Config:
        populate_by_name = True


class CalificacionResponse(BaseModel):
    """Calificación de calidad del análisis"""
    nota: float = Field(..., ge=0, le=10)
    nivel: str
    emoji: str
    factores: Dict[str, float]


class AuditoriaResponse(BaseModel):
    """Respuesta de auditoría de calidad"""
    calificacion_global: CalificacionResponse
    problemas_detectados: List[Dict[str, Any]]
    sugerencias: List[str]


class ProcessResponse(BaseModel):
    """
    Response de procesamiento de tema

    Incluye todos los resultados del pipeline
    """
    job_id: str
    status: JobStatus

    # Resultados (solo si completed)
    tema: Optional[str] = None
    timestamp: Optional[datetime] = None
    tiempo_total_segundos: Optional[float] = None

    # Pipeline
    total_referencias: Optional[int] = None
    referencias_validadas: Optional[int] = None
    tasa_validacion: Optional[float] = None
    convergencia_alcanzada: Optional[bool] = None
    rondas_convergencia: Optional[int] = None

    # Auditoría
    calificacion_global: Optional[float] = None
    auditoria: Optional[AuditoriaResponse] = None

    # Referencias
    referencias: Optional[List[ReferenciaResponse]] = None

    # Archivos exportados
    archivos_exportados: Optional[Dict[str, str]] = None

    # Métricas de performance
    metricas_performance: Optional[Dict[str, Any]] = None

    # Error (solo si failed)
    error: Optional[str] = None
    error_detalle: Optional[str] = None

    class Config:
        use_enum_values = True


class JobStatusResponse(BaseModel):
    """Response de estado de un job"""
    job_id: str
    status: JobStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: float = Field(0.0, ge=0.0, le=100.0, description="Progreso en %")
    mensaje: Optional[str] = None

    # Información detallada de progreso (NUEVO)
    fase_actual: Optional[str] = None
    mensaje_tecnico: Optional[str] = None
    agentes_activos: Optional[List[str]] = None
    stats_parciales: Optional[Dict[str, Any]] = None

    # Resultado (solo si completed)
    resultado: Optional[ProcessResponse] = None

    # Error (solo si failed)
    error: Optional[str] = None

    class Config:
        use_enum_values = True


class ListJobsResponse(BaseModel):
    """Response de listado de jobs"""
    total: int
    jobs: List[JobStatusResponse]


class StatsResponse(BaseModel):
    """Estadísticas del sistema"""
    total_jobs: int
    jobs_completados: int
    jobs_fallidos: int
    jobs_activos: int
    tasa_exito: float
    tiempo_promedio_segundos: float
    total_referencias_extraidas: int
    timestamp: datetime = Field(default_factory=datetime.now)


class ErrorResponse(BaseModel):
    """Response de error"""
    error: str
    detalle: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class ArchivoInfo(BaseModel):
    """Información de un archivo JSON disponible"""
    nombre: str = Field(..., description="Nombre del archivo")
    ruta_relativa: str = Field(..., description="Ruta relativa desde data/json/")
    tamaño_bytes: int = Field(..., description="Tamaño en bytes")
    fecha_modificacion: datetime = Field(..., description="Última modificación")


class ListArchivosResponse(BaseModel):
    """Response de listado de archivos JSON"""
    total: int
    archivos: List[ArchivoInfo]
    directorio: str = "data/json/"


# ============================================================================
# MODELOS INTERNOS
# ============================================================================

class Job(BaseModel):
    """
    Modelo interno de un job de procesamiento

    Usado para tracking en el sistema
    """
    job_id: str
    status: JobStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Request original
    request: ProcessRequest

    # Resultado
    resultado: Optional[Dict[str, Any]] = None

    # Error
    error: Optional[str] = None
    error_detalle: Optional[str] = None

    # Progress tracking
    progress: float = 0.0  # 0-100
    mensaje: Optional[str] = None

    # Información detallada de progreso (NUEVO)
    fase_actual: Optional[str] = None  # ej: "Fase 1: Extracción Inicial"
    mensaje_tecnico: Optional[str] = None  # ej: "3 agentes en paralelo buscando referencias..."
    agentes_activos: Optional[List[str]] = None  # ej: ["Agente A", "Agente B", "Agente C"]
    stats_parciales: Optional[Dict[str, Any]] = None  # ej: {"referencias_encontradas": 15}

    class Config:
        use_enum_values = True
