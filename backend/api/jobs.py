# -*- coding: utf-8 -*-
"""
LexAgents - Sistema Multi-Agente de Extracción Legal
https://github.com/686f6c61/lexagents

Sistema de Jobs Asíncronos
Gestión de jobs de procesamiento con estado y tracking

Author: 686f6c61
Version: 0.2.0
License: MIT
"""

import asyncio
import uuid
import logging
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
import json

from .models import Job, JobStatus, ProcessRequest
from .config import settings

logger = logging.getLogger(__name__)


class JobManager:
    """
    Gestor de jobs asíncronos

    Maneja el ciclo de vida de jobs:
    - Creación y registro
    - Ejecución asíncrona
    - Tracking de estado
    - Almacenamiento de resultados
    """

    def __init__(self):
        """Inicializa el gestor de jobs"""
        self.jobs: Dict[str, Job] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()

        logger.info("✅ JobManager inicializado")

    async def create_job(self, request: ProcessRequest) -> str:
        """
        Crea un nuevo job

        Args:
            request: Request de procesamiento

        Returns:
            job_id: ID único del job
        """
        async with self._lock:
            job_id = str(uuid.uuid4())

            job = Job(
                job_id=job_id,
                status=JobStatus.PENDING,
                created_at=datetime.now(),
                request=request,
                mensaje="Job creado, esperando ejecución"
            )

            self.jobs[job_id] = job

            logger.info(f"📝 Job creado: {job_id}")

            return job_id

    async def start_job(self, job_id: str, processor_func):
        """
        Inicia la ejecución de un job

        Args:
            job_id: ID del job
            processor_func: Función async que procesa el job
        """
        async with self._lock:
            if job_id not in self.jobs:
                raise ValueError(f"Job {job_id} no existe")

            job = self.jobs[job_id]

            if job.status != JobStatus.PENDING:
                raise ValueError(f"Job {job_id} no está en estado PENDING")

            # Actualizar estado
            job.status = JobStatus.RUNNING
            job.started_at = datetime.now()
            job.mensaje = "Procesamiento iniciado"
            job.progress = 0.0

            logger.info(f"🚀 Job iniciado: {job_id}")

        # Crear tarea asíncrona
        task = asyncio.create_task(
            self._run_job(job_id, processor_func)
        )
        self.running_tasks[job_id] = task

    async def _run_job(self, job_id: str, processor_func):
        """
        Ejecuta un job (interno)

        Args:
            job_id: ID del job
            processor_func: Función de procesamiento
        """
        try:
            # Obtener job
            job = self.jobs[job_id]

            # Ejecutar procesamiento
            logger.info(f"⚙️  Ejecutando job {job_id}...")
            resultado = await processor_func(job_id, job.request)

            # Marcar como completado
            async with self._lock:
                job.status = JobStatus.COMPLETED
                job.completed_at = datetime.now()
                job.resultado = resultado
                job.progress = 100.0
                job.mensaje = "Procesamiento completado exitosamente"

            logger.info(f"✅ Job completado: {job_id}")

        except Exception as e:
            # Marcar como fallido
            async with self._lock:
                job = self.jobs[job_id]
                job.status = JobStatus.FAILED
                job.completed_at = datetime.now()
                job.error = str(e)
                job.error_detalle = repr(e)
                job.mensaje = f"Error: {str(e)}"

            logger.error(f"❌ Job fallido {job_id}: {e}")

        finally:
            # Limpiar tarea
            if job_id in self.running_tasks:
                del self.running_tasks[job_id]

    async def get_job(self, job_id: str) -> Optional[Job]:
        """
        Obtiene un job por ID

        Args:
            job_id: ID del job

        Returns:
            Job o None si no existe
        """
        return self.jobs.get(job_id)

    async def get_all_jobs(self) -> List[Job]:
        """
        Obtiene todos los jobs

        Returns:
            Lista de jobs ordenados por fecha de creación (más recientes primero)
        """
        jobs = list(self.jobs.values())
        jobs.sort(key=lambda j: j.created_at, reverse=True)
        return jobs

    async def cancel_job(self, job_id: str) -> bool:
        """
        Cancela un job en ejecución

        Args:
            job_id: ID del job

        Returns:
            True si se canceló, False si no se pudo cancelar
        """
        async with self._lock:
            if job_id not in self.jobs:
                return False

            job = self.jobs[job_id]

            # Solo se pueden cancelar jobs pending o running
            if job.status not in [JobStatus.PENDING, JobStatus.RUNNING]:
                return False

            # Cancelar tarea si está corriendo
            if job_id in self.running_tasks:
                task = self.running_tasks[job_id]
                task.cancel()
                del self.running_tasks[job_id]

            # Actualizar estado
            job.status = JobStatus.CANCELLED
            job.completed_at = datetime.now()
            job.mensaje = "Job cancelado por el usuario"

            logger.info(f"⛔ Job cancelado: {job_id}")

            return True

    async def update_progress(self, job_id: str, progress: float, mensaje: str = None):
        """
        Actualiza el progreso de un job

        Args:
            job_id: ID del job
            progress: Progreso (0-100)
            mensaje: Mensaje descriptivo opcional
        """
        async with self._lock:
            if job_id in self.jobs:
                job = self.jobs[job_id]
                job.progress = min(100.0, max(0.0, progress))
                if mensaje:
                    job.mensaje = mensaje

    async def update_phase(
        self,
        job_id: str,
        fase_actual: str = None,
        mensaje_tecnico: str = None,
        agentes_activos: List[str] = None,
        stats_parciales: Dict = None,
        progress: float = None
    ):
        """
        Actualiza la información detallada de progreso de un job

        Args:
            job_id: ID del job
            fase_actual: Nombre de la fase (ej: "Fase 1: Extracción Inicial")
            mensaje_tecnico: Mensaje técnico detallado
            agentes_activos: Lista de agentes trabajando
            stats_parciales: Estadísticas parciales
            progress: Progreso opcional (0-100)
        """
        async with self._lock:
            if job_id in self.jobs:
                job = self.jobs[job_id]
                if fase_actual is not None:
                    job.fase_actual = fase_actual
                if mensaje_tecnico is not None:
                    job.mensaje_tecnico = mensaje_tecnico
                if agentes_activos is not None:
                    job.agentes_activos = agentes_activos
                if stats_parciales is not None:
                    job.stats_parciales = stats_parciales
                if progress is not None:
                    job.progress = min(100.0, max(0.0, progress))

    async def cleanup_old_jobs(self, max_age_hours: int = 24):
        """
        Limpia jobs antiguos

        Args:
            max_age_hours: Edad máxima en horas
        """
        async with self._lock:
            now = datetime.now()
            to_delete = []

            for job_id, job in self.jobs.items():
                # Solo limpiar jobs completados/fallidos/cancelados
                if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                    age_hours = (now - job.created_at).total_seconds() / 3600
                    if age_hours > max_age_hours:
                        to_delete.append(job_id)

            for job_id in to_delete:
                del self.jobs[job_id]
                logger.info(f"🗑️  Job limpiado: {job_id}")

            if to_delete:
                logger.info(f"🧹 Limpiados {len(to_delete)} jobs antiguos")

    def get_stats(self) -> Dict:
        """
        Obtiene estadísticas del sistema

        Returns:
            Dict con estadísticas
        """
        jobs = list(self.jobs.values())

        total = len(jobs)
        completados = sum(1 for j in jobs if j.status == JobStatus.COMPLETED)
        fallidos = sum(1 for j in jobs if j.status == JobStatus.FAILED)
        activos = sum(1 for j in jobs if j.status in [JobStatus.PENDING, JobStatus.RUNNING])

        # Calcular tiempo promedio de jobs completados
        tiempos = []
        total_referencias = 0

        for job in jobs:
            if job.status == JobStatus.COMPLETED and job.started_at and job.completed_at:
                tiempo = (job.completed_at - job.started_at).total_seconds()
                tiempos.append(tiempo)

                # Contar referencias si existen
                if job.resultado and 'total_referencias' in job.resultado:
                    total_referencias += job.resultado['total_referencias']

        tiempo_promedio = sum(tiempos) / len(tiempos) if tiempos else 0.0
        tasa_exito = completados / total if total > 0 else 0.0

        return {
            'total_jobs': total,
            'jobs_completados': completados,
            'jobs_fallidos': fallidos,
            'jobs_activos': activos,
            'tasa_exito': tasa_exito,
            'tiempo_promedio_segundos': tiempo_promedio,
            'total_referencias_extraidas': total_referencias
        }


# Instancia global del job manager
job_manager = JobManager()
