# -*- coding: utf-8 -*-
"""
LexAgents - Sistema Multi-Agente de Extracción Legal
https://github.com/686f6c61/lexagents

Procesador de Temas
Ejecuta el pipeline dentro del sistema de jobs asíncronos

Author: 686f6c61
Version: 0.2.0
License: MIT
"""

import logging
import asyncio
from pathlib import Path
from typing import Dict, Any
import json
import tempfile

from .models import ProcessRequest
from .config import settings
from .jobs import job_manager

# Imports del pipeline
import sys
sys.path.insert(0, str(settings.BASE_DIR))

from pipeline_optimizado import PipelineOptimizado

logger = logging.getLogger(__name__)


class TemaProcessor:
    """
    Procesador de temas con pipeline optimizado

    Ejecuta el pipeline de manera asíncrona con tracking de progreso
    """

    def __init__(self):
        """Inicializa el procesador"""
        self.pipeline = None
        logger.info("✅ TemaProcessor inicializado")

    async def process(self, job_id: str, request: ProcessRequest) -> Dict[str, Any]:
        """
        Procesa un tema

        Args:
            job_id: ID del job
            request: Request de procesamiento

        Returns:
            Resultado del pipeline
        """
        logger.info(f"🎯 Procesando tema para job {job_id}")

        # Actualizar progreso
        await job_manager.update_progress(job_id, 5.0, "Inicializando pipeline...")

        # Obtener ruta del JSON
        json_path = await self._get_json_path(job_id, request)

        # Actualizar progreso
        await job_manager.update_progress(job_id, 10.0, "JSON preparado, iniciando extracción...")

        # Crear pipeline en hilo separado (CPU-bound)
        # Pasar loop para actualizar progreso desde thread
        loop = asyncio.get_event_loop()
        resultado = await loop.run_in_executor(
            None,
            self._run_pipeline_sync,
            job_id,
            json_path,
            request,
            loop  # Pass event loop for progress updates
        )

        logger.info(f"✅ Procesamiento completado para job {job_id}")

        return resultado

    async def _get_json_path(self, job_id: str, request: ProcessRequest) -> str:
        """
        Obtiene la ruta del JSON a procesar

        Args:
            job_id: ID del job
            request: Request

        Returns:
            Ruta del archivo JSON
        """
        if request.archivo_id:
            # Usar archivo previamente subido
            json_path = settings.UPLOAD_DIR / f"{request.archivo_id}.json"

            if not json_path.exists():
                raise FileNotFoundError(f"Archivo {request.archivo_id} no encontrado")

            return str(json_path)

        elif request.contenido_json:
            # Crear archivo temporal con el JSON
            temp_file = settings.UPLOAD_DIR / f"temp_{job_id}.json"

            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(request.contenido_json, f, ensure_ascii=False, indent=2)

            return str(temp_file)

        else:
            raise ValueError("Debe proporcionar archivo_id o contenido_json")

    def _run_pipeline_sync(
        self,
        job_id: str,
        json_path: str,
        request: ProcessRequest,
        loop: asyncio.AbstractEventLoop
    ) -> Dict[str, Any]:
        """
        Ejecuta el pipeline de manera síncrona

        Se ejecuta en un executor para no bloquear el event loop

        Args:
            job_id: ID del job
            json_path: Ruta del JSON
            request: Request
            loop: Event loop para actualizar progreso

        Returns:
            Resultado del pipeline
        """
        # Crear callback thread-safe para progreso con información detallada de fases
        def progress_callback(percent: float, message: str):
            """Callback que actualiza progreso desde thread sync con info detallada"""
            try:
                # Determinar fase y detalles basándose en el mensaje y porcentaje
                fase_actual = None
                mensaje_tecnico = None
                agentes_activos = []
                stats_parciales = {}

                # Interpretar fase según mensaje/porcentaje
                if percent < 20:
                    fase_actual = "Fase 1: Extracción Inicial"
                    mensaje_tecnico = "3 agentes en paralelo analizando el documento y buscando referencias legales"
                    agentes_activos = ["Agente Conservador (temp=0.1)", "Agente Agresivo (temp=0.4)", "Agente Sabueso (temp=0.4)"]
                elif percent < 35:
                    fase_actual = "Fase 2: Convergencia"
                    mensaje_tecnico = "Los agentes comparan sus resultados para alcanzar consenso sobre las referencias encontradas"
                    agentes_activos = ["Sistema de Convergencia"]
                elif percent < 45:
                    fase_actual = "Fase 3: Resolución de Contexto"
                    mensaje_tecnico = "El agente ContextResolver completa información faltante usando IA"
                    agentes_activos = ["ContextResolver (BETA)"]
                elif percent < 55:
                    fase_actual = "Fase 4: Normalización"
                    mensaje_tecnico = "El Normalizador unifica formato y estructura de todas las referencias"
                    agentes_activos = ["Agente Normalizador"]
                elif percent < 65:
                    fase_actual = "Fase 5: Validación BOE"
                    mensaje_tecnico = "Verificando referencias contra la API del BOE para confirmar su existencia"
                    agentes_activos = ["Agente Validador", "BOE API"]
                elif percent < 75:
                    fase_actual = "Fase 6: Inferencia (BETA)"
                    mensaje_tecnico = "El InferenceAgent sugiere normativa adicional relevante no mencionada explícitamente"
                    agentes_activos = ["InferenceAgent (Gemini 2.5 Pro)"]
                elif percent < 85:
                    fase_actual = "Fase 7: EUR-Lex"
                    mensaje_tecnico = "Procesando y validando normativa europea a través de EUR-Lex"
                    agentes_activos = ["Agente EUR-Lex"]
                elif percent < 95:
                    fase_actual = "Fase 8: Enriquecimiento"
                    mensaje_tecnico = "Obteniendo textos completos de artículos desde el BOE"
                    agentes_activos = ["BOE Article Fetcher"]
                else:
                    fase_actual = "Fase 9: Exportación"
                    mensaje_tecnico = "Generando documentos en múltiples formatos (Word, PDF, TXT, MD)"
                    agentes_activos = ["Exportador"]

                # Actualizar progreso simple
                future1 = asyncio.run_coroutine_threadsafe(
                    job_manager.update_progress(job_id, percent, message),
                    loop
                )

                # Actualizar fase detallada
                future2 = asyncio.run_coroutine_threadsafe(
                    job_manager.update_phase(
                        job_id,
                        fase_actual=fase_actual,
                        mensaje_tecnico=mensaje_tecnico,
                        agentes_activos=agentes_activos,
                        stats_parciales=stats_parciales
                    ),
                    loop
                )
                # No esperamos resultados para no bloquear
            except Exception as e:
                logger.warning(f"Error actualizando progreso: {e}")

        # Crear pipeline con callback
        pipeline = PipelineOptimizado(
            max_rondas_convergencia=request.max_rondas,
            max_workers=request.max_workers,
            use_cache=request.use_cache,
            progress_callback=progress_callback
        )

        # Convertir formatos
        formatos = [f.value for f in request.formatos] if request.exportar else []

        # Ejecutar pipeline
        # NOTA: Aquí usamos asyncio.run_coroutine_threadsafe para actualizar progreso
        # desde el hilo del executor
        informe = pipeline.procesar_tema(
            json_path,
            limite_texto=request.limite_texto,
            exportar=request.exportar,
            formatos_export=formatos,
            use_context_agent=request.use_context_agent,
            use_inference_agent=request.use_inference_agent,
            umbral_confianza=request.umbral_confianza
        )

        # Procesar resultado para response
        resultado = self._format_resultado(informe)

        return resultado

    def _format_resultado(self, informe: Dict[str, Any]) -> Dict[str, Any]:
        """
        Formatea el resultado del pipeline para la API

        Args:
            informe: Informe del pipeline

        Returns:
            Resultado formateado
        """
        # Formatear referencias
        referencias = []
        for ref in informe.get('referencias', []):
            ref_formatted = {
                'texto_completo': ref.get('texto_completo', ''),
                'tipo': ref.get('tipo', 'desconocido'),
                'ley': ref.get('ley'),
                'articulo': ref.get('articulo'),
                'confianza': ref.get('confianza', 0),
                '_validada': ref.get('_validada', False),
                'boe_id': ref.get('boe_id'),
                'encontrado_por': ref.get('_metadata', {}).get('encontrado_por')
            }

            # Generar BOE URL si existe
            if ref_formatted['boe_id']:
                ref_formatted['boe_url'] = f"https://www.boe.es/buscar/act.php?id={ref_formatted['boe_id']}"

            referencias.append(ref_formatted)

        # Formatear auditoría
        auditoria = None
        if 'auditoria' in informe:
            aud = informe['auditoria']
            cal = aud.get('calificacion_global', {})

            auditoria = {
                'calificacion_global': {
                    'nota': cal.get('nota', 0),
                    'nivel': cal.get('nivel', 'Desconocido'),
                    'emoji': cal.get('emoji', '❓'),
                    'factores': cal.get('factores', {})
                },
                'problemas_detectados': aud.get('problemas_detectados', []),
                'sugerencias': aud.get('sugerencias', [])
            }

        # Construir resultado
        resultado = {
            'tema': informe.get('tema', 'Desconocido'),
            'timestamp': informe.get('timestamp'),
            'tiempo_total_segundos': informe.get('tiempo_total_segundos', 0),

            'total_referencias': informe.get('total_referencias', 0),
            'referencias_validadas': informe.get('referencias_validadas', 0),
            'tasa_validacion': informe.get('tasa_validacion', 0.0),
            'convergencia_alcanzada': informe.get('convergencia_alcanzada', False),
            'rondas_convergencia': informe.get('rondas_convergencia', 0),

            'calificacion_global': informe.get('calificacion_global', 0),
            'auditoria': auditoria,

            'referencias': referencias,

            'archivos_exportados': informe.get('archivos_exportados', {}),
            'metricas_performance': informe.get('metricas_performance', {})
        }

        return resultado


# Instancia global del procesador
tema_processor = TemaProcessor()
