# -*- coding: utf-8 -*-
"""
LexAgents - Sistema Multi-Agente de Extracción Legal
https://github.com/686f6c61/lexagents

Sistema de Convergencia Iterativa
Coordina múltiples agentes extractores hasta alcanzar convergencia
(cuando todos los agentes devuelven 0 referencias nuevas).

Author: 686f6c61
Version: 0.2.0
License: MIT
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# Permitir imports relativos cuando se ejecuta como script
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from agents.extractor_agent_a import ExtractorAgentA
    from agents.extractor_agent_b import ExtractorAgentB
    from agents.extractor_agent_c import ExtractorAgentC
else:
    from .extractor_agent_a import ExtractorAgentA
    from .extractor_agent_b import ExtractorAgentB
    from .extractor_agent_c import ExtractorAgentC

logger = logging.getLogger(__name__)


class SistemaConvergencia:
    """
    Sistema de convergencia iterativa para extracción de referencias legales

    Ejecuta múltiples agentes en rondas sucesivas hasta que:
    1. Todos los agentes devuelven 0 referencias nuevas (convergencia alcanzada)
    2. Se alcanza el número máximo de rondas
    """

    def __init__(
        self,
        max_rondas: int = 7,  # Aumentado de 5 a 7
        umbral_confianza_minima: int = 60,
        api_key: Optional[str] = None,
        parallel: bool = True
    ):
        """
        Inicializa el sistema de convergencia con 3 agentes

        Args:
            max_rondas: Número máximo de rondas de convergencia (default: 7)
            umbral_confianza_minima: Confianza mínima para incluir una referencia (0-100)
            api_key: API key de Gemini
            parallel: Ejecutar agentes en paralelo (True) o secuencial (False)
        """
        self.max_rondas = max_rondas
        self.umbral_confianza_minima = umbral_confianza_minima
        self.parallel = parallel

        # Inicializar 3 agentes
        self.agente_a = ExtractorAgentA(api_key=api_key)
        self.agente_b = ExtractorAgentB(api_key=api_key)
        self.agente_c = ExtractorAgentC(api_key=api_key)  # NUEVO: Sabueso no contaminado

        # Estado
        self.referencias_totales = []
        self.historial_rondas = []

        # Mapeo de normalizaciones para deduplicación semántica
        self.mapeo_siglas = {
            'CE': 'constitución española',
            'CC': 'código civil',
            'LEC': 'ley 1/2000',
            'LPAC': 'ley 39/2015',
            'LRJSP': 'ley 40/2015',
            'LOPJ': 'ley orgánica 6/1985',
            'LJCA': 'ley 29/1998',
            'LJV': 'ley 15/2015',
            'TRET': 'estatuto trabajadores',
            'ET': 'estatuto trabajadores',
            'CP': 'código penal',
            'LECrim': 'ley enjuiciamiento criminal',
            'LOPA': 'ley orgánica policía',
            # Más siglas comunes...
        }

        logger.info("✅ Sistema de convergencia inicializado (3 agentes)")
        logger.info(f"   - Agentes: A (conservador), B (agresivo), C (sabueso)")
        logger.info(f"   - Max rondas: {max_rondas}")
        logger.info(f"   - Umbral confianza: {umbral_confianza_minima}")
        logger.info(f"   - Modo: {'PARALELO ⚡' if parallel else 'SECUENCIAL'}")

    def ejecutar(self, texto: str) -> Dict[str, Any]:
        """
        Ejecuta el sistema de convergencia sobre un texto

        Args:
            texto: Texto del tema a procesar

        Returns:
            Dict con:
                - 'referencias': List[Dict] - Todas las referencias encontradas
                - 'total_referencias': int - Total de referencias únicas
                - 'total_rondas': int - Número de rondas ejecutadas
                - 'convergencia_alcanzada': bool - Si se alcanzó convergencia
                - 'historial': List[Dict] - Historial de cada ronda
                - 'metricas': Dict - Métricas de los agentes
        """
        logger.info("=" * 60)
        logger.info("🚀 INICIANDO SISTEMA DE CONVERGENCIA")
        logger.info("=" * 60)
        logger.info(f"Texto: {len(texto)} caracteres")

        # Resetear estado
        self.referencias_totales = []
        self.historial_rondas = []

        inicio = datetime.now()

        # Ejecutar rondas de convergencia
        for ronda in range(1, self.max_rondas + 1):
            logger.info(f"\n{'='*60}")
            logger.info(f"🔄 RONDA {ronda}/{self.max_rondas}")
            logger.info(f"{'='*60}")

            resultado_ronda = self._ejecutar_ronda(texto, ronda)

            self.historial_rondas.append(resultado_ronda)

            # Verificar convergencia
            if resultado_ronda['convergencia_alcanzada']:
                logger.info(f"\n✅ CONVERGENCIA ALCANZADA EN RONDA {ronda}")
                break

        # Calcular tiempo total
        tiempo_total = (datetime.now() - inicio).total_seconds()

        # Filtrar por umbral de confianza
        referencias_filtradas = self._filtrar_por_confianza(self.referencias_totales)

        # Resultado final
        resultado = {
            'referencias': referencias_filtradas,
            'total_referencias': len(referencias_filtradas),
            'total_rondas': len(self.historial_rondas),
            'convergencia_alcanzada': self.historial_rondas[-1]['convergencia_alcanzada'],
            'historial': self.historial_rondas,
            'metricas': {
                'tiempo_total_segundos': tiempo_total,
                'agente_a': self.agente_a.obtener_metricas(),
                'agente_b': self.agente_b.obtener_metricas(),
            },
            'timestamp': datetime.now().isoformat()
        }

        logger.info(f"\n{'='*60}")
        logger.info("🎉 CONVERGENCIA COMPLETADA")
        logger.info(f"{'='*60}")
        logger.info(f"📊 Referencias totales encontradas: {len(referencias_filtradas)}")
        logger.info(f"📊 Rondas ejecutadas: {len(self.historial_rondas)}")
        logger.info(f"📊 Tiempo total: {tiempo_total:.2f}s")
        logger.info(f"📊 Convergencia: {'✅ SÍ' if resultado['convergencia_alcanzada'] else '❌ NO'}")

        return resultado

    def _ejecutar_ronda(self, texto: str, numero_ronda: int) -> Dict[str, Any]:
        """
        Ejecuta una ronda de convergencia con 3 agentes y deduplicación semántica

        Args:
            texto: Texto a procesar
            numero_ronda: Número de la ronda

        Returns:
            Dict con resultados de la ronda
        """
        logger.info(f"Referencias acumuladas: {len(self.referencias_totales)}")

        # Preparar entrada para agentes
        entrada = {
            'texto': texto,
            'ronda': numero_ronda,
            'referencias_previas': self.referencias_totales.copy()
        }

        # Total ANTES de esta ronda
        total_antes = len(self.referencias_totales)

        if self.parallel:
            # ===  MODO PARALELO CON 3 AGENTES ===
            logger.info(f"\n⚡ Ejecutando A, B y C EN PARALELO...")

            # Ejecutar 3 agentes simultáneamente
            with ThreadPoolExecutor(max_workers=3) as executor:
                # Lanzar los 3 agentes
                future_a = executor.submit(self.agente_a.procesar, entrada)
                future_b = executor.submit(self.agente_b.procesar, entrada)
                future_c = executor.submit(self.agente_c.procesar, entrada)  # NUEVO

                # Esperar resultados
                resultado_a = future_a.result()
                resultado_b = future_b.result()
                resultado_c = future_c.result()  # NUEVO

            logger.info(f"   └─ {self.agente_a.nombre}: {resultado_a['total']} candidatas")
            logger.info(f"   └─ {self.agente_b.nombre}: {resultado_b['total']} candidatas")
            logger.info(f"   └─ {self.agente_c.nombre}: {resultado_c['total']} candidatas")  # NUEVO

        else:
            # === MODO SECUENCIAL CON 3 AGENTES ===
            logger.info(f"\n🤖 Ejecutando {self.agente_a.nombre}...")
            resultado_a = self.agente_a.procesar(entrada)
            logger.info(f"   └─ {resultado_a['total']} candidatas")

            logger.info(f"\n🤖 Ejecutando {self.agente_b.nombre}...")
            resultado_b = self.agente_b.procesar(entrada)
            logger.info(f"   └─ {resultado_b['total']} candidatas")

            logger.info(f"\n🤖 Ejecutando {self.agente_c.nombre}...")
            resultado_c = self.agente_c.procesar(entrada)  # NUEVO
            logger.info(f"   └─ {resultado_c['total']} candidatas")

        # === COMBINAR referencias de los 3 agentes ===
        referencias_ronda = (
            resultado_a['referencias'] +
            resultado_b['referencias'] +
            resultado_c['referencias']  # NUEVO
        )

        logger.info(f"\n🔍 Referencias candidatas totales: {len(referencias_ronda)}")

        # === DEDUPLICACIÓN SEMÁNTICA ===
        referencias_unicas = self._deduplicar_semanticamente(referencias_ronda)
        logger.info(f"🔍 Referencias únicas (después de dedup semántica): {len(referencias_unicas)}")

        # === AGREGAR SOLO LAS NUEVAS ===
        for ref in referencias_unicas:
            # Determinar qué agente la encontró (prioridad: A > B > C)
            if ref in resultado_a['referencias']:
                agente = self.agente_a.nombre
            elif ref in resultado_b['referencias']:
                agente = self.agente_b.nombre
            else:
                agente = self.agente_c.nombre

            # Agregar si NO es duplicado
            if not self._es_duplicado(ref):
                ref['_metadata'] = {
                    'encontrado_por': agente,
                    'ronda': numero_ronda,
                    'timestamp': datetime.now().isoformat()
                }
                self.referencias_totales.append(ref)

        # Total DESPUÉS de esta ronda
        total_despues = len(self.referencias_totales)

        # Referencias REALMENTE NUEVAS
        referencias_realmente_nuevas = total_despues - total_antes

        # === CONVERGENCIA: ¿Hay leyes NUEVAS? ===
        convergencia_alcanzada = (referencias_realmente_nuevas == 0)

        logger.info(f"\n📊 Resumen Ronda {numero_ronda}:")
        logger.info(f"   - Agente A: {resultado_a['total']} candidatas")
        logger.info(f"   - Agente B: {resultado_b['total']} candidatas")
        logger.info(f"   - Agente C: {resultado_c['total']} candidatas")  # NUEVO
        logger.info(f"   - Total candidatas: {len(referencias_ronda)}")
        logger.info(f"   - Únicas (dedup semántica): {len(referencias_unicas)}")
        logger.info(f"   - Realmente NUEVAS: {referencias_realmente_nuevas}")
        logger.info(f"   - Total acumuladas: {total_despues}")
        logger.info(f"   - Convergencia: {'✅' if convergencia_alcanzada else '❌'}")

        return {
            'ronda': numero_ronda,
            'resultado_agente_a': resultado_a,
            'resultado_agente_b': resultado_b,
            'resultado_agente_c': resultado_c,  # NUEVO
            'total_candidatas': len(referencias_ronda),
            'referencias_unicas': len(referencias_unicas),
            'referencias_nuevas': referencias_realmente_nuevas,
            'total_acumuladas': total_despues,
            'convergencia_alcanzada': convergencia_alcanzada
        }

    def _agregar_referencias(
        self,
        referencias: List[Dict],
        agente: str,
        ronda: int
    ):
        """
        Agrega referencias a la lista total, evitando duplicados

        Args:
            referencias: Referencias a agregar
            agente: Nombre del agente que las encontró
            ronda: Número de ronda
        """
        for ref in referencias:
            # Agregar metadata de trazabilidad
            ref['_metadata'] = {
                'encontrado_por': agente,
                'ronda': ronda,
                'timestamp': datetime.now().isoformat()
            }

            # Verificar duplicado antes de agregar
            if not self._es_duplicado(ref):
                self.referencias_totales.append(ref)

    def _es_duplicado(self, referencia: Dict) -> bool:
        """
        Verifica si una referencia ya existe en la lista total

        Args:
            referencia: Referencia a verificar

        Returns:
            True si es duplicado, False si no
        """
        texto_nuevo = (referencia.get('texto_completo') or '').lower().strip()
        ley_nueva = (referencia.get('ley') or '').lower().strip()

        for ref_existente in self.referencias_totales:
            texto_existente = (ref_existente.get('texto_completo') or '').lower().strip()
            ley_existente = (ref_existente.get('ley') or '').lower().strip()

            # Considerar duplicado si coincide el texto completo o la ley
            if texto_nuevo and texto_nuevo == texto_existente:
                return True
            if ley_nueva and ley_nueva == ley_existente:
                return True

        return False

    def _filtrar_por_confianza(self, referencias: List[Dict]) -> List[Dict]:
        """
        Filtra referencias por umbral de confianza

        Args:
            referencias: Lista de referencias

        Returns:
            Lista de referencias filtradas
        """
        filtradas = [
            ref for ref in referencias
            if ref.get('confianza', 100) >= self.umbral_confianza_minima
        ]

        if len(filtradas) < len(referencias):
            logger.info(
                f"🔍 Filtradas {len(referencias) - len(filtradas)} referencias "
                f"por umbral de confianza ({self.umbral_confianza_minima})"
            )

        return filtradas

    def _deduplicar_semanticamente(self, referencias: List[Dict]) -> List[Dict]:
        """
        Deduplica referencias considerando variaciones semánticas usando IA

        Ejemplos de duplicados semánticos que la IA debe detectar:
        - "CE art.1" = "Constitución Española artículo 1"
        - "LEC" = "Ley 1/2000" = "Ley de Enjuiciamiento Civil"
        - "art. 24 CE" = "artículo 24 de la Constitución"
        - "TRET" = "Estatuto de los Trabajadores" = "ET"

        Returns:
            Lista sin duplicados semánticos
        """
        if len(referencias) <= 1:
            return referencias

        # Para listas pequeñas (<20), usar IA
        # Para listas grandes, usar deduplicación simple y luego IA en ambiguas
        if len(referencias) <= 20:
            return self._deduplicar_con_ia(referencias)
        else:
            # Primero deduplicación simple por texto exacto
            unicas_simples = self._deduplicar_simple(referencias)

            # Si aún quedan muchas, agrupar por similitud y usar IA
            if len(unicas_simples) > 20:
                return unicas_simples  # Por ahora, retornar sin IA para no saturar
            else:
                return self._deduplicar_con_ia(unicas_simples)

    def _deduplicar_simple(self, referencias: List[Dict]) -> List[Dict]:
        """
        Deduplicación simple por texto exacto (sin IA)
        """
        unicas = []
        textos_vistos = set()

        for ref in referencias:
            texto = ref.get('texto_completo', '').lower().strip()
            if texto and texto not in textos_vistos:
                textos_vistos.add(texto)
                unicas.append(ref)

        duplicados = len(referencias) - len(unicas)
        if duplicados > 0:
            logger.debug(f"Dedup simple: {duplicados} duplicados exactos eliminados")

        return unicas

    def _deduplicar_con_ia(self, referencias: List[Dict]) -> List[Dict]:
        """
        Usa IA para detectar duplicados semánticos

        Args:
            referencias: Lista de referencias (máx 20 recomendado)

        Returns:
            Lista sin duplicados semánticos
        """
        if len(referencias) <= 1:
            return referencias

        logger.info(f"🤖 Usando IA para deduplicar {len(referencias)} referencias...")

        try:
            # Construir prompt para IA
            prompt = self._construir_prompt_deduplicacion(referencias)

            # Llamar a IA usando uno de los agentes existentes
            # Reutilizamos la IA del agente A (más conservador)
            import google.genai as genai

            model = genai.GenerativeModel(
                model_name="gemini-2.0-flash-exp",
                generation_config={"temperature": 0.1}
            )

            response = model.generate_content(prompt)
            respuesta = response.text

            # Parsear respuesta
            indices_unicos = self._parsear_respuesta_deduplicacion(respuesta, len(referencias))

            # Filtrar referencias
            unicas = [referencias[i] for i in indices_unicos if i < len(referencias)]

            duplicados = len(referencias) - len(unicas)
            if duplicados > 0:
                logger.info(f"🔍 IA detectó {duplicados} duplicados semánticos")

            return unicas

        except Exception as e:
            logger.warning(f"Error en deduplicación con IA: {e}. Usando dedup simple.")
            return self._deduplicar_simple(referencias)

    def _construir_prompt_deduplicacion(self, referencias: List[Dict]) -> str:
        """
        Construye prompt para que IA identifique duplicados semánticos
        """
        # Ejemplos de siglas conocidas (solo como ayuda, NO como mapeo)
        ejemplos_siglas = """
Ejemplos de siglas legales comunes (solo como referencia):
- CE = Constitución Española
- CC = Código Civil
- LEC = Ley de Enjuiciamiento Civil = Ley 1/2000
- LPAC = Ley del Procedimiento Administrativo Común = Ley 39/2015
- TRET o ET = Estatuto de los Trabajadores
- LOPJ = Ley Orgánica del Poder Judicial
- CP = Código Penal
"""

        # Listar referencias
        lista_refs = ""
        for i, ref in enumerate(referencias):
            texto = ref.get('texto_completo', 'N/A')
            ley = ref.get('ley', 'N/A')
            articulo = ref.get('articulo', 'N/A')
            lista_refs += f"{i}. \"{texto}\" (ley: {ley}, art: {articulo})\n"

        prompt = f"""Analiza estas {len(referencias)} referencias legales y detecta cuáles son DUPLICADOS SEMÁNTICOS.

Dos referencias son duplicados si se refieren a la MISMA ley y artículo, aunque estén escritas diferente.

{ejemplos_siglas}

REFERENCIAS A ANALIZAR:
{lista_refs}

EJEMPLOS DE DUPLICADOS:
- "CE art.1" y "Constitución Española artículo 1" → SON DUPLICADOS (misma ley y artículo)
- "LEC art.5" y "Ley 1/2000 artículo 5" → SON DUPLICADOS
- "TRET art.10" y "Estatuto de los Trabajadores artículo 10" → SON DUPLICADOS
- "Ley 13/2009" y "Ley 13/2009, de 3 de noviembre" → SON DUPLICADOS (misma ley)

EJEMPLOS DE NO DUPLICADOS:
- "CE art.1" y "CE art.2" → NO SON DUPLICADOS (diferentes artículos)
- "Ley 13/2009" y "Ley 14/2009" → NO SON DUPLICADOS (diferentes leyes)

TAREA:
Identifica los índices de las referencias ÚNICAS (sin duplicados).
Si hay duplicados, elige UNA de ellas (la más completa).

FORMATO DE SALIDA (JSON):
```json
{{
  "indices_unicos": [0, 2, 5, 7],
  "explicacion": "Se eliminaron duplicados: ref 1 es duplicado de 0, ref 3 es duplicado de 2..."
}}
```

Responde SOLO con el JSON, sin texto adicional."""

        return prompt

    def _parsear_respuesta_deduplicacion(self, respuesta: str, total_refs: int) -> List[int]:
        """
        Parsea respuesta de IA para obtener índices únicos
        """
        import re
        import json

        try:
            # Limpiar markdown
            respuesta_limpia = respuesta.replace('```json', '').replace('```', '').strip()

            # Parsear JSON
            data = json.loads(respuesta_limpia)
            indices = data.get('indices_unicos', [])

            # Validar índices
            indices_validos = [i for i in indices if 0 <= i < total_refs]

            return indices_validos

        except Exception as e:
            logger.warning(f"Error parseando respuesta de deduplicación: {e}")
            # Fallback: retornar todos los índices (no deduplicar)
            return list(range(total_refs))

    def obtener_estadisticas(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del sistema de convergencia

        Returns:
            Dict con estadísticas detalladas
        """
        if not self.historial_rondas:
            return {'error': 'No se ha ejecutado ninguna convergencia'}

        # Referencias por agente
        refs_por_agente = {}
        for ref in self.referencias_totales:
            agente = ref.get('_metadata', {}).get('encontrado_por', 'desconocido')
            refs_por_agente[agente] = refs_por_agente.get(agente, 0) + 1

        # Referencias por ronda
        refs_por_ronda = {}
        for ref in self.referencias_totales:
            ronda = ref.get('_metadata', {}).get('ronda', 0)
            refs_por_ronda[f'ronda_{ronda}'] = refs_por_ronda.get(f'ronda_{ronda}', 0) + 1

        # Distribución de confianza
        confianzas = [ref.get('confianza', 0) for ref in self.referencias_totales]
        confianza_promedio = sum(confianzas) / len(confianzas) if confianzas else 0

        return {
            'total_referencias': len(self.referencias_totales),
            'total_rondas': len(self.historial_rondas),
            'referencias_por_agente': refs_por_agente,
            'referencias_por_ronda': refs_por_ronda,
            'confianza_promedio': confianza_promedio,
            'convergencia_alcanzada': self.historial_rondas[-1]['convergencia_alcanzada'],
        }


# Función helper para ejecución rápida
def extraer_referencias_convergencia(texto: str, max_rondas: int = 5) -> Dict[str, Any]:
    """
    Función helper para ejecutar convergencia de manera simple

    Args:
        texto: Texto del tema
        max_rondas: Número máximo de rondas

    Returns:
        Dict con resultados de la convergencia
    """
    sistema = SistemaConvergencia(max_rondas=max_rondas)
    return sistema.ejecutar(texto)


# Ejemplo de uso
if __name__ == "__main__":
    import sys
    from pathlib import Path
    from dotenv import load_dotenv
    import os

    # Cargar variables de entorno
    env_path = Path(__file__).parent.parent / ".env"
    load_dotenv(env_path)

    # Verificar API key
    if not os.getenv('GEMINI_API_KEY'):
        print("❌ Error: GEMINI_API_KEY no encontrada en .env")
        sys.exit(1)

    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s'
    )

    print("=" * 60)
    print("🧪 TEST DEL SISTEMA DE CONVERGENCIA")
    print("=" * 60)

    # Texto de prueba
    texto_prueba = """
    El artículo 24 de la Constitución Española reconoce el derecho a la tutela judicial efectiva.

    La Ley 39/2015, de 1 de octubre, del Procedimiento Administrativo Común de las Administraciones
    Públicas (LPAC), establece en su artículo 23.2.b que son interesados en el procedimiento quienes
    sin haber iniciado el procedimiento, tengan derechos que puedan resultar afectados.

    Según el Real Decreto 203/2021, de 30 de marzo, por el que se aprueba el Reglamento de actuación
    y funcionamiento del sector público por medios electrónicos, las Administraciones deben garantizar
    la interoperabilidad.

    La LEC regula el proceso civil, mientras que la LJCA se ocupa del contencioso-administrativo.
    """

    # Ejecutar convergencia
    sistema = SistemaConvergencia(max_rondas=3)
    resultado = sistema.ejecutar(texto_prueba)

    # Mostrar resultados
    print(f"\n{'='*60}")
    print("📊 RESULTADOS")
    print(f"{'='*60}")
    print(f"\n✅ Referencias encontradas: {resultado['total_referencias']}")
    print(f"✅ Rondas ejecutadas: {resultado['total_rondas']}")
    print(f"✅ Convergencia: {'SÍ' if resultado['convergencia_alcanzada'] else 'NO'}")

    print(f"\n📋 Referencias:")
    for i, ref in enumerate(resultado['referencias'][:10], 1):  # Primeras 10
        print(f"\n{i}. {ref.get('texto_completo', 'N/A')}")
        print(f"   Tipo: {ref.get('tipo', 'N/A')}")
        print(f"   Ley: {ref.get('ley', 'N/A')}")
        print(f"   Confianza: {ref.get('confianza', 'N/A')}")
        print(f"   Encontrado por: {ref.get('_metadata', {}).get('encontrado_por', 'N/A')}")

    if len(resultado['referencias']) > 10:
        print(f"\n... y {len(resultado['referencias']) - 10} referencias más")

    # Estadísticas
    stats = sistema.obtener_estadisticas()
    print(f"\n📊 Estadísticas:")
    print(f"   Referencias por agente: {stats['referencias_por_agente']}")
    print(f"   Confianza promedio: {stats['confianza_promedio']:.1f}")

    print(f"\n{'='*60}")
    print("✅ TEST COMPLETADO")
    print(f"{'='*60}")
