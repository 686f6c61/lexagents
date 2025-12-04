# -*- coding: utf-8 -*-
"""
LexAgents - Sistema Multi-Agente de Extracción Legal
https://github.com/686f6c61/lexagents

Rutas de la API
Endpoints organizados para:
- Health check
- Upload de archivos
- Procesamiento de temas

Author: 686f6c61
Version: 0.2.0
License: MIT
"""

import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Depends
from fastapi.responses import FileResponse
from pathlib import Path
from datetime import datetime
import shutil
import uuid

from .models import (
    HealthResponse,
    SystemInfoResponse,
    UploadResponse,
    ProcessRequest,
    ProcessResponse,
    JobStatusResponse,
    ListJobsResponse,
    StatsResponse,
    ErrorResponse,
    JobStatus,
    ArchivoInfo,
    ListArchivosResponse
)
from .config import settings
from .jobs import job_manager
from .processor import tema_processor
from .security import verify_api_key, validate_path_within_directory, validate_file_content

logger = logging.getLogger(__name__)

# ============================================================================
# ROUTERS
# ============================================================================

# Router principal
router = APIRouter()

# ============================================================================
# HEALTH CHECK
# ============================================================================

@router.get(
    "/health",
    response_model=HealthResponse,
    tags=["Sistema"],
    summary="Health check del sistema"
)
async def health_check():
    """
    Verifica que el sistema esté funcionando correctamente
    """
    return HealthResponse(
        status="ok",
        version=settings.API_VERSION
    )


@router.get(
    "/system/info",
    response_model=SystemInfoResponse,
    tags=["Sistema"],
    summary="Información completa del sistema"
)
async def system_info():
    """
    Retorna información detallada del sistema:
    - Versión de la API
    - Modelo de IA usado (configurado en .env)
    - Estado de conexión con Gemini (API KEY)
    - Lista de agentes disponibles
    - Estado de conexión con BOE
    - Configuración del pipeline
    """
    # Verificar API KEY de Gemini
    gemini_conectado = False
    if settings.GEMINI_API_KEY and len(settings.GEMINI_API_KEY) > 20:
        gemini_conectado = True
        logger.debug("API KEY de Gemini configurada")
    else:
        logger.warning("API KEY de Gemini NO configurada o inválida")

    # Verificar conexión con BOE
    boe_conectado = False
    try:
        import requests
        # Probar con un endpoint válido de la API (Ley 39/2015 como test)
        response = requests.get(
            "https://www.boe.es/datosabiertos/api/legislacion-consolidada/id/BOE-A-2015-10565",
            headers={"Accept": "application/xml"},
            timeout=5
        )
        boe_conectado = response.status_code == 200
    except Exception as e:
        logger.warning(f"No se pudo conectar con BOE: {e}")
        boe_conectado = False

    # Verificar conexión con EUR-Lex
    eurlex_conectado = False
    try:
        import requests
        # Probar con la página principal de EUR-Lex
        response = requests.get(
            "https://eur-lex.europa.eu/homepage.html",
            timeout=5
        )
        eurlex_conectado = response.status_code == 200
    except Exception as e:
        logger.warning(f"No se pudo conectar con EUR-Lex: {e}")
        eurlex_conectado = False

    return SystemInfoResponse(
        version=settings.API_VERSION,
        modelo_ia=settings.GEMINI_MODEL,
        gemini_conectado=gemini_conectado,
        agentes_activos=gemini_conectado,  # Los agentes solo funcionan si Gemini está conectado
        boe_conectado=boe_conectado,
        eurlex_conectado=eurlex_conectado,
        max_rondas=settings.MAX_RONDAS_CONVERGENCIA,
        max_workers=settings.MAX_WORKERS
    )


# ============================================================================
# UPLOAD DE ARCHIVOS
# ============================================================================

@router.post(
    "/upload",
    response_model=UploadResponse,
    tags=["Archivos"],
    summary="Sube un archivo de tema (JSON, PDF, Word, TXT, MD)",
    dependencies=[Depends(verify_api_key)]
)
async def upload_file(file: UploadFile = File(...)):
    """
    Sube un archivo de tema para procesamiento posterior

    **Formatos soportados:**
    - JSON (.json): Formato estructurado original
    - PDF (.pdf): Documentos PDF
    - Word (.docx): Documentos de Microsoft Word
    - Texto (.txt): Archivos de texto plano
    - Markdown (.md): Archivos markdown

    Los archivos no-JSON se convierten automáticamente a JSON
    para su procesamiento por el pipeline.

    El archivo se guarda con un ID único que puede usarse
    en el endpoint /process
    """
    try:
        # Formatos permitidos
        ALLOWED_EXTENSIONS = {'.json', '.pdf', '.docx', '.txt', '.md'}

        # Validar extensión
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Formato no soportado: {file_extension}. "
                       f"Formatos válidos: {', '.join(ALLOWED_EXTENSIONS)}"
            )

        # Validar tamaño
        content = await file.read()
        if len(content) > settings.MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"Archivo demasiado grande. Máximo: {settings.MAX_UPLOAD_SIZE} bytes"
            )

        # Validar contenido del archivo (magic bytes)
        validate_file_content(content, file_extension)

        # Generar ID único
        archivo_id = str(uuid.uuid4())

        # Guardar archivo original con su extensión
        file_path_original = settings.UPLOAD_DIR / f"{archivo_id}{file_extension}"

        with open(file_path_original, 'wb') as f:
            f.write(content)

        logger.info(f"📤 Archivo subido: {archivo_id} ({file.filename}, {file_extension})")

        # Si NO es JSON, convertir a JSON
        if file_extension != '.json':
            from modules.text_extractor import TextExtractor

            extractor = TextExtractor()

            # Ruta del JSON que se generará
            json_path = settings.UPLOAD_DIR / f"{archivo_id}.json"

            try:
                # Extraer texto
                texto = extractor.extraer_texto(str(file_path_original))

                # Convertir a JSON
                nombre_original = Path(file.filename).stem
                json_tema = extractor.convertir_a_json_tema(texto, nombre_original)

                # Guardar JSON
                import json
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(json_tema, f, ensure_ascii=False, indent=2)

                logger.info(f"   ✅ Convertido a JSON: {json_path.name}")

            except Exception as e:
                logger.error(f"   ❌ Error convirtiendo {file_extension} a JSON: {e}")
                # Limpiar archivo original si falla la conversión
                file_path_original.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=500,
                    detail=f"Error procesando archivo {file_extension}: {str(e)}"
                )

        return UploadResponse(
            archivo_id=archivo_id,
            nombre_original=file.filename,
            tamaño_bytes=len(content)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error subiendo archivo: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/archivos",
    response_model=ListArchivosResponse,
    tags=["Archivos"],
    summary="Lista todos los archivos JSON disponibles"
)
async def listar_archivos():
    """
    Lista todos los archivos JSON en la carpeta data/json/

    Retorna información sobre cada archivo:
    - Nombre del archivo
    - Ruta relativa
    - Tamaño en bytes
    - Fecha de última modificación
    """
    try:
        json_dir = settings.JSON_DIR

        if not json_dir.exists():
            logger.warning(f"Directorio JSON no existe: {json_dir}")
            return ListArchivosResponse(total=0, archivos=[])

        archivos = []
        for file_path in json_dir.glob("*.json"):
            try:
                stat = file_path.stat()

                archivo_info = ArchivoInfo(
                    nombre=file_path.name,
                    ruta_relativa=str(file_path.relative_to(settings.DATA_DIR)),
                    tamaño_bytes=stat.st_size,
                    fecha_modificacion=datetime.fromtimestamp(stat.st_mtime)
                )
                archivos.append(archivo_info)
            except Exception as e:
                logger.warning(f"Error leyendo archivo {file_path.name}: {e}")
                continue

        # Ordenar por fecha de modificación (más recientes primero)
        archivos.sort(key=lambda x: x.fecha_modificacion, reverse=True)

        logger.info(f"📚 Listados {len(archivos)} archivos JSON")

        return ListArchivosResponse(
            total=len(archivos),
            archivos=archivos
        )

    except Exception as e:
        logger.error(f"❌ Error listando archivos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# PROCESAMIENTO
# ============================================================================

@router.post(
    "/process",
    response_model=ProcessResponse,
    tags=["Procesamiento"],
    summary="Procesa un tema (asíncrono)",
    dependencies=[Depends(verify_api_key)]
)
async def process_tema(
    request: ProcessRequest,
    background_tasks: BackgroundTasks
):
    """
    Procesa un tema de manera asíncrona

    El procesamiento se ejecuta en background y retorna
    inmediatamente con un job_id que puede usarse para
    consultar el estado.

    **Request:**
    - `archivo_id`: ID de un archivo previamente subido, o
    - `contenido_json`: JSON directo del tema

    **Configuración del pipeline:**
    - `max_rondas`: Rondas máximas de convergencia (1-10)
    - `max_workers`: Workers paralelos (1-8)
    - `use_cache`: Usar cache de API
    - `limite_texto`: Límite de caracteres (opcional)

    **Exportación:**
    - `exportar`: Si exportar resultados
    - `formatos`: Formatos de exportación (md, txt, docx)

    **Response:**
    Retorna inmediatamente con:
    - `job_id`: ID para consultar estado
    - `status`: "pending" inicialmente
    """
    try:
        # Crear job
        job_id = await job_manager.create_job(request)

        # Iniciar procesamiento en background
        async def process_in_background():
            await job_manager.start_job(job_id, tema_processor.process)

        background_tasks.add_task(process_in_background)

        logger.info(f"🚀 Job creado: {job_id}")

        return ProcessResponse(
            job_id=job_id,
            status=JobStatus.PENDING
        )

    except Exception as e:
        logger.error(f"❌ Error creando job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/process/sync",
    response_model=ProcessResponse,
    tags=["Procesamiento"],
    summary="Procesa un tema (síncrono)",
    dependencies=[Depends(verify_api_key)]
)
async def process_tema_sync(request: ProcessRequest):
    """
    Procesa un tema de manera síncrona

    **ADVERTENCIA:** Esta llamada puede tardar varios minutos.
    Para temas largos se recomienda usar /process (asíncrono).

    Retorna cuando el procesamiento está completo.
    """
    try:
        # Crear job
        job_id = await job_manager.create_job(request)

        # Ejecutar inmediatamente
        await job_manager.start_job(job_id, tema_processor.process)

        # Esperar a que termine
        while True:
            job = await job_manager.get_job(job_id)
            if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                break
            await asyncio.sleep(0.5)

        # Obtener resultado
        job = await job_manager.get_job(job_id)

        if job.status == JobStatus.COMPLETED:
            return ProcessResponse(
                job_id=job_id,
                status=JobStatus.COMPLETED,
                **job.resultado
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=job.error or "Procesamiento fallido"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error procesando tema: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# JOBS
# ============================================================================

@router.get(
    "/jobs/{job_id}",
    response_model=JobStatusResponse,
    tags=["Jobs"],
    summary="Consulta el estado de un job"
)
async def get_job_status(job_id: str):
    """
    Consulta el estado de un job de procesamiento

    **Estados posibles:**
    - `pending`: En cola, esperando ejecución
    - `running`: En ejecución
    - `completed`: Completado exitosamente
    - `failed`: Fallido con error
    - `cancelled`: Cancelado

    **Progress:**
    - `progress`: Progreso en % (0-100)
    - `mensaje`: Mensaje descriptivo del estado actual

    Cuando el estado es `completed`, el campo `resultado`
    contendrá todos los datos del procesamiento.
    """
    job = await job_manager.get_job(job_id)

    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} no encontrado"
        )

    # Construir response
    response = JobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        progress=job.progress,
        mensaje=job.mensaje,
        fase_actual=job.fase_actual,
        mensaje_tecnico=job.mensaje_tecnico,
        agentes_activos=job.agentes_activos,
        stats_parciales=job.stats_parciales
    )

    # Agregar resultado si está completado
    if job.status == JobStatus.COMPLETED and job.resultado:
        response.resultado = ProcessResponse(
            job_id=job_id,
            status=JobStatus.COMPLETED,
            **job.resultado
        )

    # Agregar error si falló
    if job.status == JobStatus.FAILED:
        response.error = job.error

    return response


@router.get(
    "/jobs",
    response_model=ListJobsResponse,
    tags=["Jobs"],
    summary="Lista todos los jobs"
)
async def list_jobs():
    """
    Lista todos los jobs del sistema

    Retorna los jobs ordenados por fecha de creación
    (más recientes primero)
    """
    jobs = await job_manager.get_all_jobs()

    jobs_response = []
    for job in jobs:
        job_resp = JobStatusResponse(
            job_id=job.job_id,
            status=job.status,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            progress=job.progress,
            mensaje=job.mensaje
        )

        if job.status == JobStatus.FAILED:
            job_resp.error = job.error

        jobs_response.append(job_resp)

    return ListJobsResponse(
        total=len(jobs_response),
        jobs=jobs_response
    )


@router.delete(
    "/jobs/{job_id}",
    tags=["Jobs"],
    summary="Cancela un job"
)
async def cancel_job(job_id: str):
    """
    Cancela un job en ejecución o pendiente

    Solo se pueden cancelar jobs en estado `pending` o `running`
    """
    cancelled = await job_manager.cancel_job(job_id)

    if not cancelled:
        raise HTTPException(
            status_code=400,
            detail="No se pudo cancelar el job (puede que ya esté completado)"
        )

    return {"mensaje": f"Job {job_id} cancelado", "job_id": job_id}


# ============================================================================
# DESCARGA DE ARCHIVOS
# ============================================================================

@router.get(
    "/download/{job_id}/{formato}",
    tags=["Archivos"],
    summary="Descarga un archivo exportado",
    dependencies=[Depends(verify_api_key)]
)
async def download_file(job_id: str, formato: str):
    """
    Descarga un archivo exportado de un job completado

    **Formatos disponibles:**
    - `md`: Markdown
    - `txt`: Texto plano
    - `docx`: Word
    - `pdf`: PDF

    El archivo debe existir (el job debe haber completado
    con exportación habilitada)
    """
    # Validar formato
    if formato not in ['md', 'txt', 'docx', 'pdf']:
        raise HTTPException(
            status_code=400,
            detail=f"Formato inválido: {formato}"
        )

    # Obtener job
    job = await job_manager.get_job(job_id)

    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} no encontrado"
        )

    if job.status != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail="El job no ha completado"
        )

    # Obtener ruta del archivo
    archivos = job.resultado.get('archivos_exportados', {})

    # Mapeo de formatos
    formato_map = {
        'md': 'markdown',
        'txt': 'texto',
        'docx': 'word',
        'pdf': 'pdf'
    }

    formato_key = formato_map.get(formato)

    if formato_key not in archivos:
        raise HTTPException(
            status_code=404,
            detail=f"Archivo {formato} no encontrado para este job"
        )

    file_path = Path(archivos[formato_key])

    # Validar que el path esté dentro del directorio de resultados (prevenir path traversal)
    validate_path_within_directory(file_path, settings.RESULTS_DIR)

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Archivo no existe en el sistema"
        )

    # Determinar media type
    media_types = {
        'md': 'text/markdown',
        'txt': 'text/plain',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'pdf': 'application/pdf'
    }

    return FileResponse(
        path=file_path,
        media_type=media_types[formato],
        filename=file_path.name
    )


# ============================================================================
# ESTADÍSTICAS
# ============================================================================

@router.get(
    "/stats",
    response_model=StatsResponse,
    tags=["Sistema"],
    summary="Estadísticas del sistema"
)
async def get_stats():
    """
    Obtiene estadísticas del sistema

    Incluye:
    - Total de jobs procesados
    - Tasa de éxito
    - Tiempo promedio de procesamiento
    - Total de referencias extraídas
    """
    stats = job_manager.get_stats()
    return StatsResponse(**stats)


# ============================================================================
# BOE - OBTENER ARTÍCULOS
# ============================================================================

@router.get(
    "/boe/articulo/{boe_id}/{numero_articulo}",
    tags=["BOE"],
    summary="Obtiene el texto completo de un artículo del BOE"
)
async def get_articulo_boe(boe_id: str, numero_articulo: str):
    """
    Obtiene el texto completo de un artículo específico del BOE

    **Parámetros:**
    - `boe_id`: ID del BOE (ej: "BOE-A-1985-12666" para LOPJ)
    - `numero_articulo`: Número del artículo (ej: "456", "14", "1.2")

    **Response:**
    ```json
    {
        "numero": "456",
        "titulo": "Título del artículo",
        "texto": "Contenido completo del artículo...",
        "boe_id": "BOE-A-1985-12666",
        "url": "https://www.boe.es/buscar/act.php?id=BOE-A-1985-12666#a456"
    }
    ```

    Si no se encuentra el artículo, retorna 404.
    """
    try:
        # Obtener fetcher
        fetcher = get_boe_article_fetcher()

        # Obtener artículo
        articulo = fetcher.obtener_articulo(boe_id, numero_articulo)

        if not articulo:
            raise HTTPException(
                status_code=404,
                detail=f"Artículo {numero_articulo} no disponible en formato estructurado para {boe_id}. " +
                       "Puedes ver la ley completa usando el enlace 'Ver BOE'."
            )

        # Construir URL del BOE
        boe_url = f"https://www.boe.es/buscar/act.php?id={boe_id}#a{articulo['numero']}"

        return {
            "numero": articulo['numero'],
            "titulo": articulo['titulo'],
            "texto": articulo['texto'],
            "boe_id": boe_id,
            "url": boe_url
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error obteniendo artículo {numero_articulo} de {boe_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo artículo: {str(e)}"
        )


# ============================================================================
# CLEANUP
# ============================================================================

@router.post(
    "/admin/cleanup",
    tags=["Admin"],
    summary="Limpia jobs antiguos",
    dependencies=[Depends(verify_api_key)]
)
async def cleanup_jobs(max_age_hours: int = 24):
    """
    Limpia jobs completados/fallidos con más de X horas

    **Parámetros:**
    - `max_age_hours`: Edad máxima en horas (default: 24)

    Solo se limpian jobs en estado `completed`, `failed` o `cancelled`
    """
    await job_manager.cleanup_old_jobs(max_age_hours)
    return {"mensaje": f"Jobs con más de {max_age_hours}h limpiados"}


# Importar asyncio para process_tema_sync
import asyncio

# Importar BOE Article Fetcher
from modules.boe_article_fetcher import get_boe_article_fetcher
