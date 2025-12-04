# -*- coding: utf-8 -*-
"""
LexAgents - Sistema Multi-Agente de Extracción Legal
https://github.com/686f6c61/lexagents

Inference Agent
Detecta conceptos legales y sugiere normas inferidas
Este agente analiza el contenido del documento para detectar conceptos legales
mencionados sin referencia explícita, y sugiere las normas relevantes.
IMPORTANTE: Las referencias inferidas se marcan como BETA y se presentan

Author: 686f6c61
Version: 0.2.0
License: MIT
"""

import logging
from typing import List, Dict, Optional, Set
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

# Imports (sin prefijo backend. porque se ejecuta desde backend/)
try:
    from api.config import settings
    from modules.boe_index_fetcher import get_boe_index_fetcher
except ImportError:
    # Si se ejecuta standalone, se configurará en __main__
    settings = None
    get_boe_index_fetcher = None


class InferenceAgent:
    """
    Agente que infiere referencias legales desde conceptos mencionados

    Workflow:
    1. Detecta conceptos legales en el texto (homicidio, aborto, lesiones, etc.)
    2. Mapea conceptos → leyes + BOE-IDs usando conocimiento de Gemini
    3. Sugiere rangos de artículos relevantes (ej: homicidio → arts. 138-143)
    4. Valida que los artículos existan usando BOEIndexFetcher
    5. Retorna referencias inferidas marcadas como BETA
    """

    def __init__(self, model_name: str = None):
        # IMPORTANTE: SIEMPRE usar modelo del settings (Gemini 2.5 Pro)
        # NO permitir override - debe ser gemini-2.5-pro del .env
        if settings:
            self.model_name = settings.GEMINI_MODEL
        else:
            import os
            self.model_name = os.getenv('GEMINI_MODEL', 'gemini-2.5-pro')

        # Validar que sea gemini-2.5-pro
        if self.model_name != 'gemini-2.5-pro':
            logger.warning(f"⚠️  Modelo incorrecto: {self.model_name}. Forzando gemini-2.5-pro")
            self.model_name = 'gemini-2.5-pro'

        # Crear cliente de Gemini
        import os
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key and settings:
            api_key = settings.GEMINI_API_KEY

        if not api_key:
            raise ValueError("No se pudo obtener GEMINI_API_KEY desde variables de entorno o settings")

        self.client = genai.Client(api_key=api_key)

        # Obtener BOEIndexFetcher
        if get_boe_index_fetcher:
            self.boe_fetcher = get_boe_index_fetcher()
            if self.boe_fetcher is None:
                logger.warning("⚠️  BOEIndexFetcher no disponible - validación de artículos deshabilitada")
        else:
            self.boe_fetcher = None
            logger.warning("⚠️  get_boe_index_fetcher no disponible - validación de artículos deshabilitada")

        logger.info(f"✅ InferenceAgent inicializado (modelo: {self.model_name})")

    def inferir_normas(
        self,
        texto: str,
        referencias_existentes: List[Dict]
    ) -> List[Dict]:
        """
        Infiere normas relevantes desde conceptos en el texto

        Args:
            texto: Contenido del documento (temario de estudio)
            referencias_existentes: Referencias ya extraídas por otros agentes
                                    (para evitar duplicados)

        Returns:
            Lista de referencias inferidas:
            [
                {
                    'ley': 'Ley Orgánica 10/1995, de 23 de noviembre, del Código Penal',
                    'boe_id': 'BOE-A-1995-25444',
                    'articulos': ['138', '139', '140', '141', '142', '143'],
                    'concepto_detectado': 'homicidio',
                    'confianza': 85,  # 0-100
                    'tipo': 'inferida'
                },
                ...
            ]
        """
        logger.info("🔍 Iniciando detección de conceptos legales...")

        # Paso 1: Detectar conceptos legales
        conceptos = self._detectar_conceptos(texto)

        if not conceptos:
            logger.info("   No se detectaron conceptos legales para inferir")
            return []

        logger.info(f"   Detectados {len(conceptos)} conceptos: {', '.join(conceptos)}")

        # Paso 2: Mapear conceptos a leyes + artículos
        referencias_inferidas = []

        for concepto in conceptos:
            logger.info(f"   Mapeando: {concepto}")

            mapeo = self._mapear_concepto_a_ley(concepto, texto)

            if mapeo:
                # Validar que los artículos existan
                validado = self._validar_articulos(mapeo)

                if validado:
                    referencias_inferidas.append(validado)
                    logger.info(f"   ✅ {concepto} → {mapeo['ley']} (arts. {', '.join(mapeo['articulos'])})")
                else:
                    logger.warning(f"   ⚠️  {concepto} → Artículos no validados")

        # Paso 3: Eliminar duplicados con referencias existentes
        referencias_unicas = self._deduplicar(referencias_inferidas, referencias_existentes)

        logger.info(f"✅ Inferencia completa: {len(referencias_unicas)} referencias BETA")

        return referencias_unicas

    def _detectar_conceptos(self, texto: str) -> List[str]:
        """
        Detecta conceptos legales mencionados en el texto

        Ejemplos de conceptos:
        - homicidio, asesinato
        - aborto
        - lesiones, lesiones al feto
        - delitos contra la libertad
        - delitos sexuales
        - etc.
        """
        prompt = f"""Analiza el siguiente texto de un temario de oposiciones.

TAREA: Identifica CONCEPTOS LEGALES mencionados que NO tengan una referencia legal explícita.

Ejemplos de conceptos legales:
- homicidio, asesinato
- aborto
- lesiones, lesiones al feto
- delitos contra la libertad
- delitos contra la libertad sexual
- delitos contra el honor
- delitos de violencia de género
- procedimiento administrativo
- recurso contencioso-administrativo

IMPORTANTE:
- Solo detecta conceptos que claramente se refieran a materias reguladas por leyes españolas
- NO incluyas conceptos que ya tengan una referencia legal explícita (ej: "art. 138 CP")
- Usa terminología jurídica precisa

TEXTO:
{texto[:4000]}

Responde SOLO con una lista de conceptos, uno por línea, sin numeración ni explicaciones.
Si no hay conceptos relevantes, responde: NINGUNO"""

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config={
                    'temperature': 0.3,  # Más conservador
                    'max_output_tokens': 65000
                }
            )

            respuesta = response.text.strip()

            if respuesta == "NINGUNO" or not respuesta:
                return []

            # Parsear conceptos (uno por línea)
            conceptos = [
                linea.strip().strip('-•*').strip()
                for linea in respuesta.split('\n')
                if linea.strip() and not linea.strip().startswith('#')
            ]

            return conceptos[:10]  # Limitar a 10 conceptos máximo

        except Exception as e:
            logger.error(f"❌ Error detectando conceptos: {e}")
            return []

    def _mapear_concepto_a_ley(self, concepto: str, texto: str) -> Optional[Dict]:
        """
        Mapea un concepto legal a una ley específica con artículos sugeridos

        Returns:
            {
                'ley': 'Ley Orgánica 10/1995, del Código Penal',
                'boe_id': 'BOE-A-1995-25444',
                'articulos': ['138', '139', '140'],
                'concepto_detectado': 'homicidio',
                'confianza': 85
            }
        """
        prompt = f"""Eres un experto en legislación española.

CONCEPTO DETECTADO: {concepto}

CONTEXTO DEL TEXTO:
{texto[:2000]}

TAREA: Identifica la ley española que regula este concepto y sugiere los artículos relevantes.

LEYES PRINCIPALES (con BOE-ID):
- Código Penal: BOE-A-1995-25444
- Constitución Española: BOE-A-1978-31229
- Ley 39/2015 (Procedimiento Administrativo): BOE-A-2015-10565
- Ley 40/2015 (Régimen Jurídico Sector Público): BOE-A-2015-10566
- LOPJ (Ley Orgánica del Poder Judicial): BOE-A-1985-12666
- LECrim (Ley de Enjuiciamiento Criminal): BOE-A-1882-6036
- LEC (Ley de Enjuiciamiento Civil): BOE-A-2000-323
- Estatuto de los Trabajadores: BOE-A-2015-11430

Responde EN FORMATO JSON:
{{
    "ley": "Nombre completo de la ley",
    "boe_id": "BOE-A-XXXX-XXXXX",
    "articulos_inicio": "número del primer artículo relevante",
    "articulos_fin": "número del último artículo relevante",
    "confianza": 0-100
}}

IMPORTANTE:
- Solo sugiere leyes si estás MUY SEGURO (confianza >= 70)
- Los artículos deben ser rangos reales de la legislación española
- Ejemplo: homicidio en CP = arts. 138-143
- Ejemplo: jurisdicción voluntaria = arts. 1-20
- Si no estás seguro, responde: {{"confianza": 0}}"""

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config={
                    'temperature': 0.2,
                    'max_output_tokens': 65000
                }
            )

            respuesta = response.text.strip()

            # Extraer JSON (puede venir con ```json o sin él)
            import json
            import re

            # Buscar JSON en la respuesta
            json_match = re.search(r'\{[^}]+\}', respuesta, re.DOTALL)
            if not json_match:
                return None

            datos = json.loads(json_match.group())

            # Validar confianza
            if datos.get('confianza', 0) < 70:
                logger.info(f"   Confianza baja ({datos.get('confianza')}%) para {concepto}")
                return None

            # Generar lista de artículos
            try:
                inicio = int(datos['articulos_inicio'])
                fin = int(datos['articulos_fin'])
                articulos = [str(i) for i in range(inicio, fin + 1)]
            except (KeyError, ValueError):
                logger.warning(f"   Formato de artículos inválido para {concepto}")
                return None

            return {
                'ley': datos['ley'],
                'boe_id': datos['boe_id'],
                'articulos': articulos,
                'concepto_detectado': concepto,
                'confianza': datos['confianza']
            }

        except Exception as e:
            logger.error(f"❌ Error mapeando {concepto}: {e}")
            return None

    def _validar_articulos(self, mapeo: Dict) -> Optional[Dict]:
        """
        Valida que los artículos sugeridos existan en la ley real
        usando BOEIndexFetcher
        """
        # Si no hay fetcher disponible, aceptar los artículos tal cual
        if self.boe_fetcher is None:
            logger.warning(f"   ⚠️  Validación deshabilitada - aceptando artículos sin verificar")
            return {
                'ley': mapeo['ley'],
                'boe_id': mapeo['boe_id'],
                'articulos': mapeo['articulos'],
                'concepto_detectado': mapeo['concepto_detectado'],
                'confianza': mapeo['confianza'],
                'tipo': 'inferida'
            }

        boe_id = mapeo['boe_id']
        articulos_sugeridos = mapeo['articulos']

        # Obtener índice real del BOE
        indice = self.boe_fetcher.obtener_indice(boe_id)

        if not indice:
            logger.warning(f"   No se pudo obtener índice de {boe_id}")
            return None

        # Obtener números de artículos reales
        articulos_reales = {art['numero'] for art in indice['articulos']}

        # Filtrar solo artículos que existan
        articulos_validos = [
            art for art in articulos_sugeridos
            if art in articulos_reales
        ]

        if not articulos_validos:
            logger.warning(f"   Ningún artículo sugerido existe en {boe_id}")
            return None

        # Si existe al menos un 50% de los sugeridos, considerarlo válido
        ratio_validez = len(articulos_validos) / len(articulos_sugeridos)

        if ratio_validez < 0.5:
            logger.warning(f"   Solo {ratio_validez*100:.0f}% de artículos válidos")
            return None

        return {
            'ley': mapeo['ley'],
            'boe_id': boe_id,
            'articulos': articulos_validos,
            'concepto_detectado': mapeo['concepto_detectado'],
            'confianza': mapeo['confianza'],
            'tipo': 'inferida'
        }

    def _deduplicar(
        self,
        inferidas: List[Dict],
        existentes: List[Dict]
    ) -> List[Dict]:
        """
        Elimina referencias inferidas que ya existan en las referencias verificadas

        Criterio de duplicado:
        - Mismo BOE-ID
        - Artículos que se solapen significativamente (>50%)
        """
        # Crear set de (boe_id, articulo) existentes
        existentes_set: Set[tuple] = set()

        for ref in existentes:
            boe_id = ref.get('boe_id', '')
            articulos = ref.get('articulos', [])

            for art in articulos:
                existentes_set.add((boe_id, str(art)))

        # Filtrar inferidas
        unicas = []

        for ref in inferidas:
            boe_id = ref['boe_id']
            articulos = ref['articulos']

            # Contar cuántos artículos ya existen
            articulos_nuevos = [
                art for art in articulos
                if (boe_id, str(art)) not in existentes_set
            ]

            # Si al menos 50% son nuevos, incluir la referencia
            if len(articulos_nuevos) >= len(articulos) * 0.5:
                # Actualizar con solo los artículos nuevos
                ref['articulos'] = articulos_nuevos
                unicas.append(ref)

        return unicas


# =============================================================================
# TESTING (solo si se ejecuta directamente)
# =============================================================================

if __name__ == "__main__":
    import sys
    import os

    # Añadir el directorio padre al path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    # Texto de prueba
    texto_test = """
    TEMA 1: DELITOS CONTRA LAS PERSONAS

    En este tema estudiaremos los diferentes tipos de delitos que atentan
    contra la vida y la integridad física de las personas, incluyendo:

    - Homicidio y sus diferentes formas
    - Asesinato y sus circunstancias agravantes
    - Aborto y legislación aplicable
    - Lesiones dolosas y culposas
    - Lesiones al feto
    - Delitos contra la libertad
    - Delitos contra la integridad moral
    - Delitos contra la libertad e indemnidad sexual

    También veremos los delitos contra el honor, como la calumnia y la injuria.
    """

    # Referencias existentes simuladas (ninguna, para ver qué infiere)
    referencias_existentes = []

    print("\n" + "="*80)
    print("TEST: InferenceAgent")
    print("="*80)

    # Crear agente (se configurará automáticamente desde .env)
    agent = InferenceAgent()

    inferidas = agent.inferir_normas(texto_test, referencias_existentes)

    print(f"\n✅ Referencias inferidas: {len(inferidas)}")

    for ref in inferidas:
        print(f"\n📌 {ref['concepto_detectado']}")
        print(f"   Ley: {ref['ley']}")
        print(f"   BOE: {ref['boe_id']}")
        print(f"   Artículos: {', '.join(ref['articulos'][:5])}{'...' if len(ref['articulos']) > 5 else ''}")
        print(f"   Confianza: {ref['confianza']}%")
