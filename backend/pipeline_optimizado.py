# -*- coding: utf-8 -*-
"""
LexAgents - Sistema Multi-Agente de Extracción Legal
https://github.com/686f6c61/lexagents

Pipeline Optimizado con Paralelización y Cache
Mejoras sobre pipeline_completo.py:
1. Ejecución paralela de agentes extractores
2. Validaciones BOE en paralelo
3. Normalizaciones en paralelo

Author: 686f6c61
Version: 0.2.0
License: MIT
"""

import sys
import logging
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import hashlib
import json
from functools import lru_cache
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Imports de módulos
from modules.html_extractor import HTMLExtractor
from agents.convergencia import SistemaConvergencia
from agents.context_resolver_agent import ContextResolverAgent  # FASE 2.3: Resolución de contexto
from agents.title_resolver_agent import TitleResolverAgent  # FASE 2.5: Resolución de títulos
from agents.normalizer_agent import NormalizerAgent
from agents.validator_agent import ValidatorAgent
from agents.inference_agent import InferenceAgent  # FASE 4.5: Inferencia de normas desde conceptos
from modules.comparador import ComparadorReferencias
from modules.auditor import Auditor
from modules.exportador import Exportador

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Gestor de cache para respuestas de API

    Cache en memoria con persistencia opcional
    """

    def __init__(self, cache_dir: str = None):
        if cache_dir is None:
            base_path = Path(__file__).parent.parent
            cache_dir = base_path / "data" / "cache"

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Cache en memoria
        self.memory_cache = {}

        logger.info(f"✅ Cache Manager iniciado: {self.cache_dir}")

    def get(self, key: str) -> Any:
        """Obtiene un valor del cache"""
        # Primero buscar en memoria
        if key in self.memory_cache:
            logger.debug(f"🎯 Cache HIT (memoria): {key[:30]}...")
            return self.memory_cache[key]

        # Luego en disco
        cache_file = self.cache_dir / f"{key}.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Cargar en memoria
                    self.memory_cache[key] = data
                    logger.debug(f"🎯 Cache HIT (disco): {key[:30]}...")
                    return data
            except Exception as e:
                logger.warning(f"⚠️  Error leyendo cache: {e}")

        return None

    def set(self, key: str, value: Any):
        """Guarda un valor en cache"""
        # Guardar en memoria
        self.memory_cache[key] = value

        # Guardar en disco
        cache_file = self.cache_dir / f"{key}.json"
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(value, f, ensure_ascii=False, indent=2)
            logger.debug(f"💾 Cache SAVE: {key[:30]}...")
        except Exception as e:
            logger.warning(f"⚠️  Error guardando cache: {e}")

    def get_key(self, prefix: str, data: str) -> str:
        """Genera una key única para el cache"""
        hash_obj = hashlib.md5(data.encode('utf-8'))
        return f"{prefix}_{hash_obj.hexdigest()}"


class PipelineOptimizado:
    """
    Pipeline optimizado con paralelización y cache

    Mejoras:
    - Agentes extractores en paralelo
    - Validaciones BOE en paralelo
    - Normalizaciones en paralelo
    - Cache de API calls
    - Monitoreo de performance
    """

    def __init__(
        self,
        max_rondas_convergencia: int = 3,
        umbral_confianza: int = 70,
        max_workers: int = 4,
        use_cache: bool = True,
        progress_callback: callable = None
    ):
        """
        Inicializa el pipeline optimizado

        Args:
            max_rondas_convergencia: Máximo de rondas de convergencia
            umbral_confianza: Umbral mínimo de confianza
            max_workers: Máximo de workers para paralelización
            use_cache: Usar cache para API calls
            progress_callback: Callback para reportar progreso progress_callback(percent, message)
        """
        logger.info("🚀 Inicializando Pipeline Optimizado")

        # Callback de progreso
        self.progress_callback = progress_callback

        # Módulos FASE 2
        self.html_extractor = HTMLExtractor()

        # Sistema FASE 3
        self.sistema_convergencia = SistemaConvergencia(
            max_rondas=max_rondas_convergencia,
            umbral_confianza_minima=umbral_confianza
        )

        # Agentes FASE 3.3 (Resolución de contexto)
        self.context_resolver = ContextResolverAgent()

        # Agentes FASE 3.5 (Resolución de títulos)
        self.title_resolver = TitleResolverAgent()

        # Agentes FASE 4
        self.normalizador = NormalizerAgent()
        self.validador = ValidatorAgent()

        # Agente FASE 4.5 (Inferencia de normas)
        self.inference_agent = InferenceAgent()

        self.comparador = ComparadorReferencias()

        # Módulos FASE 5
        self.auditor = Auditor()
        self.exportador = Exportador()

        # Configuración
        self.max_workers = max_workers
        self.use_cache = use_cache

        # Cache manager
        if use_cache:
            self.cache = CacheManager()

        # Métricas de performance
        self.metricas_performance = {
            'cache_hits': 0,
            'cache_misses': 0,
            'tiempo_por_fase': {}
        }

        logger.info(f"✅ Pipeline optimizado - Max workers: {max_workers}, Cache: {use_cache}")

    def _report_progress(self, percent: float, message: str):
        """
        Reporta progreso si hay callback configurado

        Args:
            percent: Porcentaje de progreso (0-100)
            message: Mensaje descriptivo
        """
        if self.progress_callback:
            try:
                self.progress_callback(percent, message)
            except Exception as e:
                logger.warning(f"Error en callback de progreso: {e}")

    def procesar_tema(
        self,
        json_path: str,
        limite_texto: int = None,
        exportar: bool = True,
        formatos_export: List[str] = None,
        use_context_agent: bool = True,
        use_inference_agent: bool = False,
        umbral_confianza: int = 70
    ) -> Dict[str, Any]:
        """
        Procesa un tema completo con optimizaciones

        Args:
            json_path: Ruta al JSON del tema
            limite_texto: Límite de caracteres (None = sin límite)
            exportar: Exportar resultados a archivos
            formatos_export: Formatos de exportación ['md', 'txt', 'docx', 'pdf']
            use_context_agent: Usar agente de contexto para resolver referencias incompletas
            use_inference_agent: Usar agente de inferencia para sugerir normativa (BETA)
            umbral_confianza: Umbral mínimo de confianza para incluir referencias (50-95)

        Returns:
            Dict con resultados completos del pipeline
        """
        # Guardar configuración para uso interno
        self.umbral_confianza = umbral_confianza
        self.use_inference_agent = use_inference_agent
        logger.info("=" * 80)
        logger.info(f"🎯 PROCESANDO TEMA: {Path(json_path).name}")
        logger.info("=" * 80)

        inicio_total = datetime.now()

        # === FASE 1: Extracción HTML ===
        inicio_fase = datetime.now()
        logger.info("\n📂 FASE 1: Extracción HTML")
        logger.info("-" * 80)
        self._report_progress(15.0, "Extrayendo texto del HTML...")

        resultado_html = self.html_extractor.extraer_de_json(json_path)
        texto_completo = resultado_html['texto_limpio']

        # Limitar si se especifica
        if limite_texto and len(texto_completo) > limite_texto:
            texto_procesado = texto_completo[:limite_texto]
            logger.warning(f"⚠️  Texto truncado a {limite_texto:,} caracteres")
        else:
            texto_procesado = texto_completo

        logger.info(f"✅ Extraídos {len(texto_procesado):,} caracteres")
        self.metricas_performance['tiempo_por_fase']['extraccion'] = \
            (datetime.now() - inicio_fase).total_seconds()

        # === FASE 2: Convergencia Iterativa (Optimizada) ===
        inicio_fase = datetime.now()
        logger.info("\n🔄 FASE 2: Convergencia Iterativa (PARALELA)")
        logger.info("-" * 80)
        self._report_progress(30.0, "Ejecutando convergencia iterativa...")

        resultado_convergencia = self.sistema_convergencia.ejecutar(texto_procesado)

        logger.info(
            f"✅ {resultado_convergencia['total_referencias']} referencias extraídas "
            f"en {resultado_convergencia['total_rondas']} rondas"
        )
        self.metricas_performance['tiempo_por_fase']['convergencia'] = \
            (datetime.now() - inicio_fase).total_seconds()

        # === FASE 2.3: Resolución de Contexto (OPCIONAL) ===
        if use_context_agent:
            inicio_fase = datetime.now()
            logger.info("\n🧠 FASE 2.3: Resolución de Contexto")
            logger.info("-" * 80)
            self._report_progress(35.0, "Resolviendo referencias incompletas con contexto...")

            resultado_contexto = self.context_resolver.procesar({
                'referencias': resultado_convergencia['referencias'],
                'texto_original': texto_procesado
            })

            logger.info(
                f"✅ {resultado_contexto['resueltas']}/{len(resultado_convergencia['referencias'])} "
                f"referencias mejoradas ({resultado_contexto['resueltas']/max(len(resultado_convergencia['referencias']),1)*100:.1f}%)"
            )
            if resultado_contexto['resueltas'] > 0:
                logger.info(
                    f"   Confianza: {resultado_contexto['metricas']['confianza_promedio_antes']:.1f}% → "
                    f"{resultado_contexto['metricas']['confianza_promedio_despues']:.1f}%"
                )
            self.metricas_performance['tiempo_por_fase']['contexto'] = \
                (datetime.now() - inicio_fase).total_seconds()
        else:
            logger.info("\n⏭️  FASE 2.3: Resolución de Contexto (OMITIDA)")
            resultado_contexto = {
                'referencias': resultado_convergencia['referencias'],
                'resueltas': 0,
                'metricas': {
                    'confianza_promedio_antes': 0,
                    'confianza_promedio_despues': 0
                }
            }
            self.metricas_performance['tiempo_por_fase']['contexto'] = 0

        # === FASE 2.5: Resolución de Títulos ===
        inicio_fase = datetime.now()
        logger.info("\n🔍 FASE 2.5: Resolución de Títulos")
        logger.info("-" * 80)
        self._report_progress(40.0, "Resolviendo títulos completos...")

        resultado_titulos = self.title_resolver.procesar({
            'referencias': resultado_contexto['referencias_resueltas'],
            'texto_original': texto_procesado[:3000]
        })

        logger.info(
            f"✅ {resultado_titulos['resueltas']}/{len(resultado_convergencia['referencias'])} "
            f"títulos resueltos ({resultado_titulos['resueltas']/max(len(resultado_convergencia['referencias']),1)*100:.1f}%)"
        )
        logger.info(
            f"   Confianza promedio: {resultado_titulos['metricas']['confianza_promedio']:.1f}"
        )
        self.metricas_performance['tiempo_por_fase']['titulos'] = \
            (datetime.now() - inicio_fase).total_seconds()

        # === FASE 3: Normalización (Paralela) ===
        inicio_fase = datetime.now()
        logger.info("\n📝 FASE 3: Normalización (PARALELA)")
        logger.info("-" * 80)
        self._report_progress(50.0, "Normalizando referencias...")

        referencias = resultado_titulos['referencias_normalizadas']
        referencias_normalizadas = self._normalizar_paralelo(
            referencias,
            contexto=texto_procesado[:2000]
        )

        cambios = sum(1 for ref in referencias_normalizadas if ref.get('_normalizada'))
        logger.info(f"✅ {cambios} referencias normalizadas")

        self.metricas_performance['tiempo_por_fase']['normalizacion'] = \
            (datetime.now() - inicio_fase).total_seconds()

        # === FASE 4: Validación (Paralela) ===
        inicio_fase = datetime.now()
        logger.info("\n✔️  FASE 4: Validación contra BOE (PARALELA)")
        logger.info("-" * 80)
        self._report_progress(65.0, "Validando contra BOE oficial...")

        referencias_validadas = self._validar_paralelo(referencias_normalizadas)

        validadas = sum(1 for ref in referencias_validadas if ref.get('_validada'))
        tasa_validacion = validadas / len(referencias_validadas) if referencias_validadas else 0

        logger.info(
            f"✅ {validadas}/{len(referencias_validadas)} referencias validadas "
            f"({tasa_validacion*100:.1f}%)"
        )

        # Filtrar por umbral de confianza
        total_antes = len(referencias_validadas)
        referencias_validadas = [
            ref for ref in referencias_validadas
            if ref.get('confianza', 0) >= self.umbral_confianza
        ]
        filtradas = total_antes - len(referencias_validadas)
        if filtradas > 0:
            logger.info(
                f"   Filtradas {filtradas} referencias por confianza < {self.umbral_confianza}%"
            )

        self.metricas_performance['tiempo_por_fase']['validacion'] = \
            (datetime.now() - inicio_fase).total_seconds()

        # === FASE 4.5: Inferencia de Normas (BETA) - OPCIONAL ===
        referencias_inferidas = []
        if self.use_inference_agent:
            inicio_fase = datetime.now()
            logger.info("\n🧠 FASE 4.5: Inferencia de Normas (BETA)")
            logger.info("-" * 80)
            self._report_progress(70.0, "Infiriendo normas desde conceptos...")

            referencias_inferidas = self.inference_agent.inferir_normas(
                texto_procesado,
                referencias_validadas
            )

            logger.info(
                f"✅ {len(referencias_inferidas)} referencias inferidas (BETA)"
            )

            if referencias_inferidas:
                logger.info("   Estas referencias se presentarán separadamente como sugerencias")

            self.metricas_performance['tiempo_por_fase']['inferencia'] = \
                (datetime.now() - inicio_fase).total_seconds()
        else:
            logger.info("\n⏭️  FASE 4.5: Inferencia de Normas (OMITIDA)")
            self.metricas_performance['tiempo_por_fase']['inferencia'] = 0

        # === FASE 5: Comparación ===
        inicio_fase = datetime.now()
        logger.info("\n📊 FASE 5: Análisis Comparativo")
        logger.info("-" * 80)
        self._report_progress(75.0, "Analizando comparativa...")

        # Agrupar por agente extractor
        refs_por_agente = {}
        for ref in resultado_convergencia['referencias']:
            agente = ref.get('_metadata', {}).get('encontrado_por', 'desconocido')
            if agente not in refs_por_agente:
                refs_por_agente[agente] = []
            refs_por_agente[agente].append(ref)

        resultado_comparacion = self.comparador.comparar(refs_por_agente)

        logger.info(
            f"✅ Consenso total: {resultado_comparacion['consenso_total']} referencias"
        )
        logger.info(
            f"✅ Acuerdo promedio: {resultado_comparacion['metricas']['acuerdo_promedio']:.1f}%"
        )

        self.metricas_performance['tiempo_por_fase']['comparacion'] = \
            (datetime.now() - inicio_fase).total_seconds()

        # === FASE 6: Auditoría ===
        inicio_fase = datetime.now()
        logger.info("\n🔍 FASE 6: Auditoría de Calidad")
        logger.info("-" * 80)
        self._report_progress(85.0, "Ejecutando auditoría de calidad...")

        metricas_pipeline = {
            'convergencia_alcanzada': resultado_convergencia['convergencia_alcanzada'],
            'total_rondas': resultado_convergencia['total_rondas'],
            'tiempo_total_segundos': (datetime.now() - inicio_total).total_seconds()
        }

        informe_auditoria = self.auditor.auditar(
            referencias_validadas,
            metricas_pipeline
        )

        cal = informe_auditoria['calificacion_global']
        logger.info(f"✅ Calificación: {cal['emoji']} {cal['nota']}/10 - {cal['nivel']}")

        self.metricas_performance['tiempo_por_fase']['auditoria'] = \
            (datetime.now() - inicio_fase).total_seconds()

        # === FASE 7: Exportación ===
        archivos_exportados = {}
        if exportar:
            inicio_fase = datetime.now()
            logger.info("\n📤 FASE 7: Exportación de Resultados")
            logger.info("-" * 80)
            self._report_progress(95.0, "Exportando resultados...")

            tema_nombre = Path(json_path).stem

            archivos_exportados = self.exportador.exportar_todo(
                referencias_validadas,
                informe_auditoria,
                metricas_pipeline,
                tema=tema_nombre,
                formatos=formatos_export,
                referencias_inferidas=referencias_inferidas
            )

            for formato, ruta in archivos_exportados.items():
                logger.info(f"✅ {formato.upper()}: {Path(ruta).name}")

            self.metricas_performance['tiempo_por_fase']['exportacion'] = \
                (datetime.now() - inicio_fase).total_seconds()

        # === Informe Final ===
        tiempo_total = (datetime.now() - inicio_total).total_seconds()

        # Estadísticas de cache
        if self.use_cache:
            total_requests = self.metricas_performance['cache_hits'] + \
                           self.metricas_performance['cache_misses']
            if total_requests > 0:
                hit_rate = self.metricas_performance['cache_hits'] / total_requests * 100
                logger.info(f"\n💾 Cache: {hit_rate:.1f}% hit rate")

        informe_final = self._generar_informe_final(
            tema=Path(json_path).name,
            texto_length=len(texto_procesado),
            referencias=referencias_validadas,
            referencias_inferidas=referencias_inferidas,
            convergencia=resultado_convergencia,
            comparacion=resultado_comparacion,
            auditoria=informe_auditoria,
            validadas=validadas,
            tasa_validacion=tasa_validacion,
            tiempo_total=tiempo_total,
            archivos_exportados=archivos_exportados
        )

        # Reportar progreso completado
        self._report_progress(100.0, "Procesamiento completado")

        return informe_final

    def _normalizar_paralelo(
        self,
        referencias: List[Dict],
        contexto: str
    ) -> List[Dict]:
        """
        Normaliza referencias en paralelo

        Args:
            referencias: Lista de referencias
            contexto: Contexto del tema

        Returns:
            Lista de referencias normalizadas
        """
        # Si hay pocas referencias, no vale la pena paralelizar
        if len(referencias) < 5:
            resultado = self.normalizador.procesar({
                'referencias': referencias,
                'contexto': contexto
            })
            return resultado['referencias_normalizadas']

        # Dividir referencias en batches
        batch_size = max(1, len(referencias) // self.max_workers)
        batches = [
            referencias[i:i + batch_size]
            for i in range(0, len(referencias), batch_size)
        ]

        logger.info(f"🔀 Normalizando {len(referencias)} refs en {len(batches)} batches")

        # Procesar batches en paralelo
        referencias_normalizadas = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            for batch in batches:
                future = executor.submit(
                    self._normalizar_batch,
                    batch,
                    contexto
                )
                futures.append(future)

            # Recopilar resultados
            for future in as_completed(futures):
                try:
                    batch_result = future.result()
                    referencias_normalizadas.extend(batch_result)
                except Exception as e:
                    logger.error(f"❌ Error en normalización paralela: {e}")

        return referencias_normalizadas

    def _normalizar_batch(self, batch: List[Dict], contexto: str) -> List[Dict]:
        """Normaliza un batch de referencias"""
        resultado = self.normalizador.procesar({
            'referencias': batch,
            'contexto': contexto
        })
        return resultado['referencias_normalizadas']

    def _validar_paralelo(self, referencias: List[Dict]) -> List[Dict]:
        """
        Valida referencias en paralelo contra BOE

        Args:
            referencias: Lista de referencias

        Returns:
            Lista de referencias validadas
        """
        # Si hay pocas referencias, no vale la pena paralelizar
        if len(referencias) < 5:
            resultado = self.validador.procesar({'referencias': referencias})
            return resultado['referencias_validadas']

        logger.info(f"🔀 Validando {len(referencias)} referencias en paralelo")

        # Validar cada referencia en paralelo
        referencias_validadas = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {}
            for i, ref in enumerate(referencias):
                future = executor.submit(self._validar_referencia, ref)
                futures[future] = i

            # Recopilar resultados manteniendo el orden
            resultados = [None] * len(referencias)
            for future in as_completed(futures):
                idx = futures[future]
                try:
                    ref_validada = future.result()
                    resultados[idx] = ref_validada
                except Exception as e:
                    logger.error(f"❌ Error validando referencia {idx}: {e}")
                    resultados[idx] = referencias[idx]  # Mantener original si falla

        return [r for r in resultados if r is not None]

    def _validar_referencia(self, referencia: Dict) -> Dict:
        """Valida una referencia individual"""
        resultado = self.validador.procesar({'referencias': [referencia]})
        return resultado['referencias_validadas'][0]

    def _generar_informe_final(
        self,
        tema: str,
        texto_length: int,
        referencias: List[Dict],
        referencias_inferidas: List[Dict],
        convergencia: Dict,
        comparacion: Dict,
        auditoria: Dict,
        validadas: int,
        tasa_validacion: float,
        tiempo_total: float,
        archivos_exportados: Dict
    ) -> Dict[str, Any]:
        """Genera el informe final consolidado"""
        return {
            'tema': tema,
            'timestamp': datetime.now().isoformat(),
            'tiempo_total_segundos': tiempo_total,

            # Optimizaciones
            'optimizado': True,
            'max_workers': self.max_workers,
            'cache_habilitado': self.use_cache,
            'metricas_performance': self.metricas_performance,

            # Datos de entrada
            'texto_procesado_chars': texto_length,

            # Resultados de convergencia
            'total_referencias': convergencia['total_referencias'],
            'convergencia_alcanzada': convergencia['convergencia_alcanzada'],
            'rondas_convergencia': convergencia['total_rondas'],

            # Resultados de validación
            'referencias_validadas': validadas,
            'tasa_validacion': tasa_validacion,

            # Resultados de inferencia (BETA)
            'referencias_inferidas': referencias_inferidas,
            'total_inferidas': len(referencias_inferidas),

            # Resultados de comparación
            'consenso_total': comparacion['consenso_total'],
            'consenso_parcial': comparacion['consenso_parcial'],
            'acuerdo_promedio': comparacion['metricas']['acuerdo_promedio'],

            # Auditoría
            'auditoria': auditoria,
            'calificacion_global': auditoria['calificacion_global']['nota'],

            # Referencias completas (ambas secciones)
            'referencias': referencias,  # Referencias verificadas

            # Archivos exportados
            'archivos_exportados': archivos_exportados,

            # Métricas de agentes
            'metricas_agentes': convergencia['metricas'],

            # Comparación detallada
            'comparacion_detallada': comparacion
        }

    def mostrar_informe(self, informe: Dict[str, Any]):
        """Muestra el informe en consola de manera formateada"""
        print("\n" + "=" * 80)
        print("📊 INFORME FINAL DEL PIPELINE OPTIMIZADO")
        print("=" * 80)

        print(f"\n📄 Tema: {informe['tema']}")
        print(f"📅 Timestamp: {informe['timestamp']}")
        print(f"⏱️  Tiempo total: {informe['tiempo_total_segundos']:.2f}s")

        # Optimizaciones
        print(f"\n⚡ Optimizaciones:")
        print(f"   - Max workers: {informe['max_workers']}")
        print(f"   - Cache: {'✅ Habilitado' if informe['cache_habilitado'] else '❌ Deshabilitado'}")

        # Tiempos por fase
        if 'tiempo_por_fase' in informe['metricas_performance']:
            print(f"\n⏱️  Tiempos por fase:")
            for fase, tiempo in informe['metricas_performance']['tiempo_por_fase'].items():
                print(f"   - {fase.title()}: {tiempo:.2f}s")

        print(f"\n📝 Datos de Entrada:")
        print(f"   - Texto procesado: {informe['texto_procesado_chars']:,} caracteres")

        print(f"\n🔄 Convergencia:")
        print(f"   - Referencias extraídas: {informe['total_referencias']}")
        print(f"   - Rondas: {informe['rondas_convergencia']}")
        print(f"   - Convergencia: {'✅ SÍ' if informe['convergencia_alcanzada'] else '❌ NO'}")

        print(f"\n✔️  Validación:")
        print(f"   - Referencias validadas: {informe['referencias_validadas']}/{informe['total_referencias']}")
        print(f"   - Tasa de validación: {informe['tasa_validacion']*100:.1f}%")

        print(f"\n📊 Comparación:")
        print(f"   - Consenso total: {informe['consenso_total']}")
        print(f"   - Consenso parcial: {informe['consenso_parcial']}")
        print(f"   - Acuerdo promedio: {informe['acuerdo_promedio']:.1f}%")

        # Auditoría
        cal = informe['auditoria']['calificacion_global']
        print(f"\n🔍 Auditoría:")
        print(f"   - Calificación: {cal['emoji']} {cal['nota']}/10 - {cal['nivel']}")
        print(f"   - Factores:")
        print(f"     • Confianza: {cal['factores']['confianza']:.1f}/10")
        print(f"     • Validación: {cal['factores']['validacion']:.1f}/10")
        print(f"     • Cobertura: {cal['factores']['cobertura']:.1f}/10")

        # Archivos exportados
        if informe.get('archivos_exportados'):
            print(f"\n📤 Archivos exportados:")
            for formato, ruta in informe['archivos_exportados'].items():
                print(f"   - {formato.upper()}: {Path(ruta).name}")

        print(f"\n📋 Referencias Validadas (primeras 10):")
        print("-" * 80)

        for i, ref in enumerate(informe['referencias'][:10], 1):
            print(f"\n{i}. {ref.get('texto_completo', 'N/A')}")
            print(f"   └─ Tipo: {ref.get('tipo', 'N/A')}")

            if ref.get('ley'):
                print(f"   └─ Ley: {ref['ley']}")

            if ref.get('_validada'):
                print(f"   └─ ✅ VALIDADA")
                if ref.get('boe_id'):
                    print(f"   └─ BOE-ID: {ref['boe_id']}")
            else:
                print(f"   └─ ❌ NO VALIDADA")

            print(f"   └─ Confianza: {ref.get('confianza', 'N/A')}%")

        if len(informe['referencias']) > 10:
            print(f"\n... y {len(informe['referencias']) - 10} referencias más")

        print("\n" + "=" * 80)


# Ejemplo de uso
if __name__ == "__main__":
    print("=" * 80)
    print("🧪 TEST DEL PIPELINE OPTIMIZADO")
    print("=" * 80)

    # Buscar tema JSON
    data_dir = Path(__file__).parent.parent / "data" / "json"
    json_files = list(data_dir.glob("*.json"))

    if not json_files:
        print("❌ No hay archivos JSON en data/json")
        sys.exit(1)

    # Usar el primer tema
    json_path = str(json_files[0])

    # Ejecutar pipeline optimizado
    pipeline = PipelineOptimizado(
        max_rondas_convergencia=2,  # Solo 2 rondas para test rápido
        max_workers=4,  # 4 workers paralelos
        use_cache=True  # Cache habilitado
    )

    informe = pipeline.procesar_tema(
        json_path,
        limite_texto=15000,  # Limitar para rapidez
        exportar=True,
        formatos_export=['md', 'txt', 'docx']
    )

    # Mostrar informe
    pipeline.mostrar_informe(informe)

    print("\n✅ PIPELINE OPTIMIZADO COMPLETADO CON ÉXITO")
