# -*- coding: utf-8 -*-
"""
LexAgents - Sistema Multi-Agente de Extracción Legal
https://github.com/686f6c61/lexagents

TitleResolverAgent - Resuelve títulos completos de leyes usando IA
IMPORTANTE: SIEMPRE usa IA para resolver títulos.
El mapeo de siglas es SOLO para inyectar en el prompt como ayuda, NO para reemplazo directo.

Author: 686f6c61
Version: 0.2.0
License: MIT
"""

import json
import logging
import re
from typing import Dict, List, Any
from datetime import datetime
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class TitleResolverAgent(BaseAgent):
    """
    Agente que resuelve títulos completos oficiales de leyes usando IA

    FILOSOFÍA:
    - SIEMPRE usa IA, nunca hardcodeo directo
    - Las siglas conocidas se inyectan en el prompt como AYUDA
    - La IA debe inferir títulos completos incluso sin siglas
    - Usa contexto del tema para desambiguar

    Ejemplos:
    - "TRET" → IA → "Real Decreto Legislativo 2/2015, de 23 de octubre, ..."
    - "CE" → IA → "Constitución Española de 27 de diciembre de 1978"
    - "Ley 13/2009" → IA → "Ley 13/2009, de 3 de noviembre, de reforma..."
    - "artículo 117" + contexto → IA → "Constitución Española..."
    """

    def __init__(self, api_key: str = None):
        """
        Inicializa el TitleResolverAgent

        Args:
            api_key: API key de Gemini (opcional)
        """
        super().__init__(
            nombre="TitleResolver",
            modelo="gemini-2.0-flash-exp",
            temperatura=0.1,  # Muy conservador para títulos oficiales
            api_key=api_key
        )

        # Cargar siglas conocidas SOLO para inyectar en prompt
        self.siglas_ayuda = self._cargar_siglas_conocidas()

        logger.info(f"✅ {self.nombre} inicializado con {len(self.siglas_ayuda)} siglas de ayuda")

    def _cargar_siglas_conocidas(self) -> Dict[str, str]:
        """
        Carga siglas conocidas SOLO como ayuda al prompt
        NO para reemplazo directo

        Returns:
            Dict con siglas y sus expansiones
        """
        return {
            "CE": "Constitución Española",
            "CC": "Código Civil",
            "CP": "Código Penal",
            "LEC": "Ley de Enjuiciamiento Civil (Ley 1/2000)",
            "LECrim": "Ley de Enjuiciamiento Criminal",
            "LPAC": "Ley del Procedimiento Administrativo Común (Ley 39/2015)",
            "LRJSP": "Ley del Régimen Jurídico del Sector Público (Ley 40/2015)",
            "LOPJ": "Ley Orgánica del Poder Judicial (LO 6/1985)",
            "LJCA": "Ley de la Jurisdicción Contencioso-Administrativa (Ley 29/1998)",
            "LJV": "Ley de la Jurisdicción Voluntaria (Ley 15/2015)",
            "TRET": "Estatuto de los Trabajadores (RDL 2/2015)",
            "ET": "Estatuto de los Trabajadores",
            "LOLS": "Ley Orgánica de Libertad Sindical (LO 11/1985)",
            "LISOS": "Ley de Infracciones y Sanciones del Orden Social (RDL 5/2000)",
            "LGSS": "Ley General de la Seguridad Social (RDL 8/2015)",
            "LGDCU": "Ley General de Consumidores y Usuarios (RDL 1/2007)",
            "LAU": "Ley de Arrendamientos Urbanos (Ley 29/1994)",
            "LH": "Ley Hipotecaria",
            "TRLSC": "Texto Refundido de la Ley de Sociedades de Capital (RDL 1/2010)",
            "LC": "Ley Concursal (Ley 22/2003)",
            # Más siglas comunes...
        }

    def procesar(self, entrada: Dict) -> Dict:
        """
        Resuelve títulos completos de referencias usando IA

        Args:
            entrada = {
                'referencias': List[Dict],  # Referencias a normalizar
                'texto_original': str  # Contexto del tema (opcional)
            }

        Returns:
            {
                'referencias_normalizadas': List[Dict],  # Con ley_titulo_completo
                'resueltas': int,
                'no_resueltas': int,
                'metricas': {
                    'confianza_promedio': float,
                    'tiempo_segundos': float,
                    'llamadas_ia': int
                }
            }
        """
        referencias = entrada.get('referencias', [])
        texto_original = entrada.get('texto_original', '')

        if not referencias:
            return {
                'referencias_normalizadas': [],
                'resueltas': 0,
                'no_resueltas': 0,
                'metricas': {}
            }

        logger.info(f"🔍 Resolviendo títulos de {len(referencias)} referencias con IA...")

        inicio = datetime.now()
        llamadas_ia = 0

        # Procesar en batches de 15 para no saturar el prompt
        batch_size = 15
        referencias_resueltas = []

        for i in range(0, len(referencias), batch_size):
            batch = referencias[i:i + batch_size]

            logger.info(f"   Procesando batch {i//batch_size + 1}/{(len(referencias)-1)//batch_size + 1} ({len(batch)} refs)...")

            # Construir prompt
            prompt = self._construir_prompt(batch, texto_original[:3000])

            try:
                # Llamar a IA
                respuesta = self.generar_contenido(prompt, self._get_system_instruction())
                llamadas_ia += 1

                # Parsear respuesta
                batch_resuelto = self._parsear_respuesta(respuesta, batch)
                referencias_resueltas.extend(batch_resuelto)

            except Exception as e:
                logger.error(f"Error procesando batch: {e}")
                # Agregar referencias sin resolver
                referencias_resueltas.extend(batch)

        # Calcular métricas
        resueltas = sum(1 for r in referencias_resueltas if r.get('_titulo_resuelto'))
        no_resueltas = len(referencias_resueltas) - resueltas

        confianzas = [r.get('_confianza_titulo', 0) for r in referencias_resueltas if r.get('_titulo_resuelto')]
        confianza_promedio = sum(confianzas) / len(confianzas) if confianzas else 0

        tiempo = (datetime.now() - inicio).total_seconds()

        logger.info(f"✅ Resueltas: {resueltas}/{len(referencias)} ({resueltas/len(referencias)*100:.1f}%)")
        logger.info(f"   Confianza promedio: {confianza_promedio:.1f}")
        logger.info(f"   Tiempo: {tiempo:.2f}s")
        logger.info(f"   Llamadas IA: {llamadas_ia}")

        return {
            'referencias_normalizadas': referencias_resueltas,
            'resueltas': resueltas,
            'no_resueltas': no_resueltas,
            'metricas': {
                'confianza_promedio': confianza_promedio,
                'tiempo_segundos': tiempo,
                'llamadas_ia': llamadas_ia
            }
        }

    def _get_system_instruction(self) -> str:
        """Instrucciones de sistema para la IA"""
        return """Eres un experto en legislación española.

Tu tarea es identificar el TÍTULO OFICIAL COMPLETO de cada norma legal,
tal como aparece en el BOE (Boletín Oficial del Estado).

IMPORTANTE:
- Usa tu conocimiento de legislación española
- El título debe incluir: número, fecha y descripción
- Si no estás seguro, asigna confianza baja
- NUNCA inventes títulos

EJEMPLOS:
Input: "TRET"
Output: "Real Decreto Legislativo 2/2015, de 23 de octubre, por el que se aprueba el texto refundido de la Ley del Estatuto de los Trabajadores"
Confianza: 100

Input: "Ley 13/2009"
Output: "Ley 13/2009, de 3 de noviembre, de reforma de la legislación procesal para la implantación de la nueva oficina judicial"
Confianza: 100

Input: "artículo 117 de la Constitución"
Output: "Constitución Española de 27 de diciembre de 1978"
Confianza: 100

Input: "el Código Civil"
Output: "Real Decreto de 24 de julio de 1889, Código Civil"
Confianza: 100

Devuelve SOLO JSON, sin texto adicional."""

    def _construir_prompt(self, referencias: List[Dict], contexto: str) -> str:
        """
        Construye prompt con siglas como AYUDA (no para reemplazo)
        """
        # Inyectar siglas conocidas como AYUDA (primeras 20)
        siglas_str = "\n".join([
            f"  - {sigla}: {nombre}"
            for sigla, nombre in list(self.siglas_ayuda.items())[:20]
        ])

        # Listar referencias
        refs_str = ""
        for i, ref in enumerate(referencias, 1):
            texto = ref.get('texto_completo', 'N/A')
            ley = ref.get('ley', 'N/A')
            refs_str += f"{i}. Texto: \"{texto}\" | Ley identificada: \"{ley}\"\n"

        prompt = f"""Resuelve el TÍTULO OFICIAL COMPLETO de estas referencias legales usando tu conocimiento de legislación española.

CONTEXTO DEL TEMA (para ayudar a desambiguar):
{contexto if contexto else 'No disponible'}

SIGLAS CONOCIDAS (solo como ayuda, NO para reemplazo automático):
{siglas_str}
... y más

REFERENCIAS A RESOLVER ({len(referencias)} total):
{refs_str}

Para cada referencia, identifica:
1. El título oficial COMPLETO tal como aparece en el BOE
2. Nivel de confianza (0-100)
3. Razonamiento breve de cómo lo identificaste

IMPORTANTE:
- Usa tu conocimiento de legislación española
- Si la referencia menciona una sigla (CE, LEC, TRET...), expándela al título completo oficial
- Si menciona "Ley X/YYYY", añade la fecha y descripción completa
- Si solo menciona "artículo X", usa el contexto para identificar la ley
- Asigna confianza alta (90-100) solo si estás muy seguro
- Si no puedes identificar con certeza, asigna confianza baja (<70)

FORMATO DE SALIDA (JSON válido):
```json
{{
  "titulos_resueltos": [
    {{
      "index": 1,
      "titulo_completo": "Constitución Española de 27 de diciembre de 1978",
      "confianza": 100,
      "razonamiento": "CE es la sigla estándar de la Constitución Española"
    }},
    {{
      "index": 2,
      "titulo_completo": "Ley 13/2009, de 3 de noviembre, de reforma de la legislación procesal para la implantación de la nueva oficina judicial",
      "confianza": 100,
      "razonamiento": "Ley 13/2009 identificada por número y año"
    }}
  ]
}}
```

Responde SOLO con el JSON, sin texto adicional antes o después."""

        return prompt

    def _parsear_respuesta(self, respuesta: str, referencias_originales: List[Dict]) -> List[Dict]:
        """
        Parsea respuesta de IA y actualiza referencias con títulos completos
        """
        try:
            # Limpiar markdown
            respuesta_limpia = respuesta.replace('```json', '').replace('```', '').strip()

            # Parsear JSON
            datos = json.loads(respuesta_limpia)
            titulos = datos.get('titulos_resueltos', [])

            # Crear copia de referencias para actualizar
            referencias_actualizadas = []

            for i, ref in enumerate(referencias_originales):
                ref_copia = ref.copy()

                # Buscar título correspondiente (index es 1-based en JSON)
                titulo_info = next((t for t in titulos if t.get('index', 0) == i + 1), None)

                if titulo_info and titulo_info.get('titulo_completo'):
                    # Actualizar con título completo
                    ref_copia['ley_titulo_completo'] = titulo_info['titulo_completo']
                    ref_copia['_titulo_resuelto'] = True
                    ref_copia['_confianza_titulo'] = titulo_info.get('confianza', 0)
                    ref_copia['_razonamiento_titulo'] = titulo_info.get('razonamiento', '')

                    logger.debug(f"✅ Título resuelto: {ref.get('texto_completo', '')[:50]} → {titulo_info['titulo_completo'][:60]}...")
                else:
                    # No se pudo resolver
                    ref_copia['_titulo_resuelto'] = False
                    logger.debug(f"❌ No resuelto: {ref.get('texto_completo', '')[:50]}")

                referencias_actualizadas.append(ref_copia)

            return referencias_actualizadas

        except json.JSONDecodeError as e:
            logger.error(f"Error parseando JSON de títulos: {e}")
            logger.error(f"Respuesta raw: {respuesta[:500]}...")
            return referencias_originales

        except Exception as e:
            logger.error(f"Error inesperado en parseo de títulos: {e}")
            return referencias_originales
