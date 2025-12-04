# -*- coding: utf-8 -*-
"""
LexAgents - Sistema Multi-Agente de Extracción Legal
https://github.com/686f6c61/lexagents

ContextResolverAgent - Resuelve referencias incompletas usando contexto con IA
IMPORTANTE: Este agente convierte referencias con confianza < 100% en referencias
completas al 100% usando análisis contextual con IA.
Ejemplo:
Input: "ART. 2" (confianza: 80%, sin ley)

Author: 686f6c61
Version: 0.2.0
License: MIT
"""

import json
import logging
import re
from typing import Dict, List, Any, Optional
from datetime import datetime
from .base_agent import BaseAgent
from modules.legal_abbreviations import SIGLAS_LEYES, SIGLAS_BOE_ID

logger = logging.getLogger(__name__)


class ContextResolverAgent(BaseAgent):
    """
    Agente que resuelve referencias incompletas usando contexto del documento

    Características:
    - Detecta referencias con confianza < 100%
    - Localiza posición en texto original
    - Extrae chunk de contexto inteligente
    - Usa IA para inferir la ley correspondiente
    - Actualiza referencias a confianza 100%
    """

    def __init__(self, api_key: str = None):
        """
        Inicializa el ContextResolverAgent

        Args:
            api_key: API key de Gemini (opcional)
        """
        super().__init__(
            nombre="ContextResolver",
            modelo="gemini-2.0-flash-exp",
            temperatura=0.2,  # Balanceado para análisis contextual
            api_key=api_key
        )

        logger.info(f"✅ {self.nombre} inicializado")

    def procesar(self, entrada: Dict) -> Dict:
        """
        Resuelve referencias incompletas usando contexto del documento

        Args:
            entrada = {
                'referencias': List[Dict],  # Todas las referencias
                'texto_original': str       # Texto completo del documento
            }

        Returns:
            {
                'referencias_resueltas': List[Dict],  # Con leyes completadas
                'resueltas': int,                     # Cantidad mejorada
                'no_resueltas': int,                  # No se pudo mejorar
                'metricas': {
                    'tiempo_segundos': float,
                    'llamadas_ia': int,
                    'confianza_promedio_antes': float,
                    'confianza_promedio_despues': float
                }
            }
        """
        referencias = entrada.get('referencias', [])
        texto_original = entrada.get('texto_original', '')

        if not referencias:
            return self._resultado_vacio()

        logger.info(f"🧠 Analizando {len(referencias)} referencias para resolución contextual...")

        inicio = datetime.now()

        # 1. Filtrar referencias incompletas (confianza < 100%)
        refs_completas = []
        refs_incompletas = []

        for ref in referencias:
            confianza = ref.get('confianza', 100)
            if confianza < 100:
                refs_incompletas.append(ref)
            else:
                refs_completas.append(ref)

        logger.info(f"   Referencias completas (100%): {len(refs_completas)}")
        logger.info(f"   Referencias incompletas (<100%): {len(refs_incompletas)}")

        if not refs_incompletas:
            logger.info("✅ Todas las referencias ya están al 100%")
            return {
                'referencias_resueltas': referencias,
                'resueltas': 0,
                'no_resueltas': 0,
                'metricas': {
                    'tiempo_segundos': 0,
                    'llamadas_ia': 0,
                    'confianza_promedio_antes': 100,
                    'confianza_promedio_despues': 100
                }
            }

        # 2. Calcular confianza promedio antes
        confianzas_antes = [r.get('confianza', 100) for r in refs_incompletas]
        confianza_antes = sum(confianzas_antes) / len(confianzas_antes) if confianzas_antes else 100

        # 3. Procesar referencias incompletas en batches
        batch_size = 10
        referencias_mejoradas = []
        llamadas_ia = 0

        for i in range(0, len(refs_incompletas), batch_size):
            batch = refs_incompletas[i:i + batch_size]

            logger.info(f"   Procesando batch {i//batch_size + 1}/{(len(refs_incompletas)-1)//batch_size + 1} ({len(batch)} refs)...")

            try:
                # Extraer contextos
                contextos = self._extraer_contextos(batch, texto_original)

                if not contextos:
                    logger.warning(f"   No se pudo extraer contexto para este batch")
                    referencias_mejoradas.extend(batch)  # Mantener originales
                    continue

                # Construir prompt
                prompt = self._construir_prompt(contextos)

                # Llamar a IA
                respuesta = self.generar_contenido(prompt, self._get_system_instruction())
                llamadas_ia += 1

                # Parsear respuesta
                batch_resuelto = self._parsear_respuesta(respuesta, batch)
                referencias_mejoradas.extend(batch_resuelto)

            except Exception as e:
                logger.error(f"   Error procesando batch: {e}")
                referencias_mejoradas.extend(batch)  # Mantener originales

        # 4. SEGUNDA PASADA: Resolver referencias que aún están < 100%
        referencias_segunda_pasada = []
        refs_aun_incompletas = []

        for ref in referencias_mejoradas:
            if ref.get('confianza', 0) < 100:
                refs_aun_incompletas.append(ref)
            else:
                referencias_segunda_pasada.append(ref)

        if refs_aun_incompletas:
            logger.info(f"   🔄 Segunda pasada para {len(refs_aun_incompletas)} referencias aún < 100%...")

            try:
                # Usar contexto MÁS AMPLIO (3000 chars) + contexto del documento completo
                contexto_documento = texto_original[:5000]  # Primeros 5000 chars del documento

                # Extraer ley principal del documento
                ley_principal = self._detectar_ley_principal_documento(contexto_documento)

                # Procesar con contexto ampliado
                for ref in refs_aun_incompletas:
                    # Si detectamos ley principal y la ref no tiene info contradictoria, asignarla
                    if ley_principal and not ref.get('ley'):
                        ref['ley'] = ley_principal
                        ref['confianza'] = 100
                        ref['_contexto_resuelto'] = True
                        ref['_razonamiento_contexto'] = f"Asignado por contexto del documento completo (ley principal: {ley_principal})"
                        logger.debug(f"   ✅ Segunda pasada: {ref.get('texto_completo', '')[:40]} → {ley_principal} (100%)\"")
                    elif ref.get('confianza', 0) >= 95:
                        # Si tiene 95%+, subir a 100% (casi seguro)
                        ref['confianza'] = 100
                        logger.debug(f"   ✅ Promovido a 100%: {ref.get('texto_completo', '')[:40]} (era {ref.get('confianza')}%)")

                    referencias_segunda_pasada.append(ref)

            except Exception as e:
                logger.error(f"   Error en segunda pasada: {e}")
                referencias_segunda_pasada.extend(refs_aun_incompletas)

        # 5. Combinar referencias completas + mejoradas
        referencias_finales = refs_completas + referencias_segunda_pasada

        # 6. Calcular métricas
        resueltas = sum(1 for r in referencias_mejoradas if r.get('confianza', 0) == 100)
        no_resueltas = len(referencias_mejoradas) - resueltas

        confianzas_despues = [r.get('confianza', 100) for r in referencias_mejoradas]
        confianza_despues = sum(confianzas_despues) / len(confianzas_despues) if confianzas_despues else 100

        tiempo = (datetime.now() - inicio).total_seconds()

        logger.info(f"✅ Resueltas: {resueltas}/{len(refs_incompletas)} ({resueltas/len(refs_incompletas)*100:.1f}%)")
        logger.info(f"   Confianza antes: {confianza_antes:.1f}% → después: {confianza_despues:.1f}%")
        logger.info(f"   Tiempo: {tiempo:.2f}s")
        logger.info(f"   Llamadas IA: {llamadas_ia}")

        return {
            'referencias_resueltas': referencias_finales,
            'resueltas': resueltas,
            'no_resueltas': no_resueltas,
            'metricas': {
                'tiempo_segundos': tiempo,
                'llamadas_ia': llamadas_ia,
                'confianza_promedio_antes': confianza_antes,
                'confianza_promedio_despues': confianza_despues
            }
        }

    def _extraer_contextos(self, referencias: List[Dict], texto_original: str) -> List[Dict]:
        """
        Extrae contextos para cada referencia

        Args:
            referencias: Referencias a procesar
            texto_original: Texto completo del documento

        Returns:
            Lista de dicts con {referencia, contexto, posicion}
        """
        contextos = []

        for ref in referencias:
            # Buscar posición en texto original
            posicion = self._encontrar_posicion(ref, texto_original)

            if posicion is None:
                logger.debug(f"   No se encontró posición para: {ref.get('texto_completo', '')[:50]}")
                continue

            # Extraer chunk de contexto (1500 chars para mejor contexto)
            chunk = self._extraer_chunk(texto_original, posicion, ventana=1500)

            contextos.append({
                'referencia': ref,
                'contexto': chunk,
                'posicion': posicion
            })

        return contextos

    def _encontrar_posicion(self, referencia: Dict, texto: str) -> Optional[int]:
        """
        Encuentra la posición de una referencia en el texto

        Args:
            referencia: Referencia a buscar
            texto: Texto donde buscar

        Returns:
            Posición (índice) o None
        """
        texto_ref = referencia.get('texto_completo', '')
        if not texto_ref:
            return None

        # Intentar match exacto
        patron = re.escape(texto_ref)
        match = re.search(patron, texto, re.IGNORECASE)

        if match:
            return match.start()

        # Intentar con variaciones (sin mayúsculas, etc)
        patron_flexible = texto_ref.replace('.', r'\.?').replace(' ', r'\s+')
        match = re.search(patron_flexible, texto, re.IGNORECASE)

        return match.start() if match else None

    def _extraer_chunk(self, texto: str, posicion: int, ventana: int = 1500) -> str:
        """
        Extrae chunk de contexto alrededor de una posición

        Args:
            texto: Texto completo
            posicion: Posición central
            ventana: Caracteres antes/después (default: 1500 para capturar más contexto)

        Returns:
            Chunk de contexto
        """
        inicio = max(0, posicion - ventana)
        fin = min(len(texto), posicion + ventana)

        chunk = texto[inicio:fin]

        # Agregar elipsis si es necesario
        if inicio > 0:
            chunk = "..." + chunk
        if fin < len(texto):
            chunk = chunk + "..."

        return chunk

    def _get_system_instruction(self) -> str:
        """Instrucciones de sistema para la IA"""
        # Generar mapeo dinámico de siglas desde el módulo
        siglas_texto = "\n".join([f"- {sigla} = {nombre}" for sigla, nombre in SIGLAS_LEYES.items()])

        return f"""Eres un experto en legislación española especializado en análisis contextual de documentos legales.

Tu tarea es identificar a qué LEY pertenece cada artículo basándote en el contexto proporcionado.

REGLAS CRÍTICAS PARA CONFIANZA 100%:
- Si el documento CLARAMENTE trata sobre una ley específica (ej: documento sobre LJV), todos los artículos sin ley explícita pertenecen a esa ley → confianza 100
- Si ves menciones repetidas de una ley en el contexto amplio → confianza 100
- Si el artículo aparece en una sección que claramente habla de una ley → confianza 100
- Si el contexto dice "artículo X de la [LEY]" → confianza 100
- Si el contexto menciona siglas (LJV, CE, LEC, LOPJ, CP, LECrim, etc.) de forma consistente → confianza 100

REFERENCIAS CONTEXTUALES QUE DEBES RESOLVER:
- "la presente ley" / "esta ley" / "dicha ley" → Identifica la ley principal del documento o del contexto cercano
- "el presente código" / "este código" → Identifica el código (CP, CC, etc.)
- "la presente norma" / "esta norma" → Identifica la norma del contexto
- "la citada ley" / "la mencionada ley" → Busca la ley mencionada anteriormente en el contexto

IMPORTANTE: Cuando veas "la presente ley", "esta ley", etc., NO las copies literalmente. Debes identificar a qué ley específica se refieren basándote en el contexto del documento.

SOLO asigna confianza < 100 si:
- Hay AMBIGÜEDAD real entre múltiples leyes
- El contexto es completamente insuficiente (muy raro con 1500 chars)
- Detectas información CONTRADICTORIA

MAPEO COMPLETO DE SIGLAS LEGALES:
{siglas_texto}

IMPORTANTE: Sé DECISIVO. Si el contexto te da suficiente información para identificar la ley, asigna confianza 100. No seas conservador innecesariamente.

NOMBRES COMPLETOS: Siempre devuelve nombres completos de leyes, no siglas. Por ejemplo:
- "CP" → "Código Penal" o "Ley Orgánica 10/1995, de 23 de noviembre, del Código Penal"
- "LECrim" → "Ley de Enjuiciamiento Criminal"
- "LOPJ" → "Ley Orgánica 6/1985, de 1 de julio, del Poder Judicial"

Devuelve SOLO JSON, sin texto adicional."""

    def _construir_prompt(self, contextos: List[Dict]) -> str:
        """
        Construye prompt para que IA resuelva múltiples artículos
        """
        contextos_str = ""

        for i, ctx in enumerate(contextos, 1):
            ref = ctx['referencia']
            contextos_str += f"""
Referencia {i}:
- Texto original: "{ref.get('texto_completo', 'N/A')}"
- Artículo: {ref.get('articulo', 'N/A')}
- Ley actual: {ref.get('ley', 'DESCONOCIDA')}
- Confianza actual: {ref.get('confianza', 0)}%

CONTEXTO (fragmento donde aparece):
{ctx['contexto']}

---
"""

        prompt = f"""Identifica a qué LEY pertenece cada artículo basándote en el contexto proporcionado.

REFERENCIAS A RESOLVER ({len(contextos)} total):

{contextos_str}

INSTRUCCIONES:
1. Para cada referencia, lee su contexto cuidadosamente
2. Identifica menciones de leyes en el contexto
3. Determina la ley más probable
4. Asigna confianza según la claridad del contexto

FORMATO DE SALIDA (JSON):
```json
{{
  "resoluciones": [
    {{
      "index": 1,
      "ley_identificada": "Ley 15/2015",
      "confianza": 100,
      "razonamiento": "El contexto menciona 'LJV' y la sección trata sobre jurisdicción voluntaria"
    }},
    ...
  ]
}}
```

Responde SOLO con el JSON, sin texto adicional."""

        return prompt

    def _parsear_respuesta(self, respuesta: str, referencias_originales: List[Dict]) -> List[Dict]:
        """
        Parsea respuesta de IA y actualiza referencias
        """
        try:
            # Limpiar markdown
            respuesta_limpia = respuesta.replace('```json', '').replace('```', '').strip()

            # Parsear JSON
            datos = json.loads(respuesta_limpia)
            resoluciones = datos.get('resoluciones', [])

            # Crear copia de referencias para actualizar
            referencias_actualizadas = []

            for i, ref in enumerate(referencias_originales):
                ref_copia = ref.copy()

                # Buscar resolución correspondiente (index es 1-based)
                resolucion = next((r for r in resoluciones if r.get('index', 0) == i + 1), None)

                if resolucion and resolucion.get('ley_identificada'):
                    # Actualizar con ley identificada
                    ley = resolucion['ley_identificada']
                    conf = resolucion.get('confianza', 90)

                    ref_copia['ley'] = ley
                    ref_copia['confianza'] = conf
                    ref_copia['_contexto_resuelto'] = True
                    ref_copia['_razonamiento_contexto'] = resolucion.get('razonamiento', '')

                    # Actualizar texto_completo si es solo artículo
                    if ref_copia.get('articulo') and not ref_copia.get('ley'):
                        art = ref_copia['articulo']
                        ref_copia['texto_completo'] = f"Artículo {art} de la {ley}"

                    logger.debug(f"✅ Resuelto: {ref.get('texto_completo', '')[:40]} → {ley} (conf: {conf}%)")
                else:
                    # No se pudo resolver
                    logger.debug(f"❌ No resuelto: {ref.get('texto_completo', '')[:40]}")

                referencias_actualizadas.append(ref_copia)

            return referencias_actualizadas

        except json.JSONDecodeError as e:
            logger.error(f"Error parseando JSON: {e}")
            logger.error(f"Respuesta raw: {respuesta[:500]}...")
            return referencias_originales

        except Exception as e:
            logger.error(f"Error inesperado en parseo: {e}")
            return referencias_originales

    def _detectar_ley_principal_documento(self, contexto_documento: str) -> Optional[str]:
        """
        Detecta la ley principal de un documento usando IA

        Args:
            contexto_documento: Primeros ~5000 caracteres del documento

        Returns:
            Nombre de la ley principal o None
        """
        try:
            prompt = f"""Analiza este fragmento del inicio de un documento legal y determina cuál es la LEY PRINCIPAL que se está tratando.

CONTEXTO DEL DOCUMENTO:
{contexto_documento}

INSTRUCCIONES:
- Identifica la ley que se menciona MÁS FRECUENTEMENTE
- Busca títulos, encabezados o secciones que indiquen el tema principal
- Si ves "LJV" o "Ley 15/2015" repetidamente → es Ley 15/2015
- Si ves "CE" o "Constitución" → es Constitución Española
- Si ves "LOPJ" → es Ley Orgánica 6/1985

FORMATO DE SALIDA (JSON):
```json
{{
  "ley_principal": "Ley 15/2015",
  "confianza": 95,
  "razonamiento": "El documento menciona 'LJV' 10 veces y tiene secciones sobre jurisdicción voluntaria"
}}
```

Si NO hay una ley principal clara, devuelve:
```json
{{
  "ley_principal": null,
  "confianza": 0,
  "razonamiento": "El documento trata múltiples leyes sin predominio claro"
}}
```

Responde SOLO con JSON."""

            respuesta = self.generar_contenido(
                prompt,
                "Experto en identificar la ley principal de documentos legales españoles."
            )

            # Parsear respuesta
            respuesta_limpia = respuesta.replace('```json', '').replace('```', '').strip()
            datos = json.loads(respuesta_limpia)

            ley = datos.get('ley_principal')
            confianza = datos.get('confianza', 0)

            if ley and confianza >= 80:
                logger.info(f"   📚 Ley principal detectada: {ley} (confianza: {confianza}%)")
                return ley

            return None

        except Exception as e:
            logger.error(f"   Error detectando ley principal: {e}")
            return None

    def _resultado_vacio(self) -> Dict:
        """Retorna resultado vacío"""
        return {
            'referencias_resueltas': [],
            'resueltas': 0,
            'no_resueltas': 0,
            'metricas': {
                'tiempo_segundos': 0,
                'llamadas_ia': 0,
                'confianza_promedio_antes': 0,
                'confianza_promedio_despues': 0
            }
        }
