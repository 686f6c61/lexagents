# -*- coding: utf-8 -*-
"""
LexAgents - Sistema Multi-Agente de Extracción Legal
https://github.com/686f6c61/lexagents

Agente 1A: Extractor Conservador de Referencias Legales
Extrae referencias legales con alta precisión (temperatura baja).
Solo incluye referencias de las que está completamente seguro.

Author: 686f6c61
Version: 0.2.0
License: MIT
"""

import json
import logging
import re
from typing import Dict, List, Any
from .base_agent import BaseAgent
from modules.siglas_loader import cargar_siglas_para_prompt

logger = logging.getLogger(__name__)


class ExtractorAgentA(BaseAgent):
    """
    Agente extractor CONSERVADOR de referencias legales

    Características:
    - Temperatura: 0.1 (muy conservador)
    - Solo extrae referencias explícitas y claras
    - Alta precisión, puede tener menor recall
    - Incluye contexto de cada referencia
    """

    def __init__(self, api_key: str = None):
        """
        Inicializa el Agente 1A (Conservador)

        Args:
            api_key: API key de Gemini (opcional)
        """
        super().__init__(
            nombre="Agente1A-Conservador",
            modelo="gemini-2.0-flash-exp",
            temperatura=0.1,  # Muy conservador
            api_key=api_key
        )

    def procesar(self, entrada: Dict[str, Any]) -> Dict[str, Any]:
        """
        Procesa un texto y extrae referencias legales conservadoramente

        Args:
            entrada: Dict con:
                - 'texto': str - Texto del tema a procesar
                - 'ronda': int - Número de ronda de convergencia (opcional)
                - 'referencias_previas': List[Dict] - Referencias ya encontradas (opcional)

        Returns:
            Dict con:
                - 'referencias': List[Dict] - Referencias encontradas
                - 'total': int - Total de referencias
                - 'agente': str - Nombre del agente
                - 'ronda': int - Número de ronda
        """
        texto = entrada.get('texto', '')
        ronda = entrada.get('ronda', 1)
        referencias_previas = entrada.get('referencias_previas', [])

        logger.info(f"[{self.nombre}] Procesando texto (ronda {ronda})")
        logger.info(f"[{self.nombre}] Texto: {len(texto)} caracteres")
        logger.info(f"[{self.nombre}] Referencias previas: {len(referencias_previas)}")

        # Construir prompt
        prompt = self._construir_prompt(texto, ronda, referencias_previas)

        # System instruction
        system_instruction = self._get_system_instruction()

        # Llamar a Gemini
        try:
            respuesta_raw = self.generar_contenido(prompt, system_instruction)

            # Parsear respuesta JSON
            referencias = self._parsear_respuesta(respuesta_raw)

            # Filtrar referencias ya encontradas
            if referencias_previas:
                referencias_nuevas = self._filtrar_duplicados(referencias, referencias_previas)
            else:
                referencias_nuevas = referencias

            logger.info(f"[{self.nombre}] Encontradas {len(referencias_nuevas)} referencias nuevas")

            return {
                'referencias': referencias_nuevas,
                'total': len(referencias_nuevas),
                'agente': self.nombre,
                'ronda': ronda,
                'temperatura': self.temperatura
            }

        except Exception as e:
            logger.error(f"[{self.nombre}] Error en procesamiento: {e}")
            return {
                'referencias': [],
                'total': 0,
                'agente': self.nombre,
                'ronda': ronda,
                'error': str(e)
            }

    def _get_system_instruction(self) -> str:
        """Devuelve la instrucción de sistema para el agente"""
        return """Eres un asistente legal especializado en extracción de referencias legales para oposiciones del Estado español.

Tu tarea es identificar TODAS las referencias legales (leyes, artículos, reales decretos, constitución, etc.) mencionadas en textos de temas de oposiciones.

REGLAS CRÍTICAS:
1. SOLO incluye referencias que aparezcan EXPLÍCITAMENTE en el texto
2. NO inventes ni deduzcas referencias que no estén escritas
3. NO incluyas referencias genéricas como "la ley" sin especificar cuál
4. SÉ EXTREMADAMENTE CONSERVADOR: en caso de duda, NO incluyas la referencia
5. Extrae el texto EXACTO de la referencia tal como aparece

IMPORTANTE: Devuelve SOLO JSON válido, sin texto adicional."""

    def _construir_prompt(
        self,
        texto: str,
        ronda: int,
        referencias_previas: List[Dict]
    ) -> str:
        """
        Construye el prompt para Gemini

        Args:
            texto: Texto del tema
            ronda: Número de ronda
            referencias_previas: Referencias ya encontradas

        Returns:
            Prompt formateado
        """
        # Truncar texto si es muy largo (Gemini tiene límite)
        max_chars = 50000  # ~12,500 tokens
        if len(texto) > max_chars:
            texto = texto[:max_chars] + "\n\n[... texto truncado ...]"
            logger.warning(f"[{self.nombre}] Texto truncado a {max_chars} caracteres")

        prompt = f"""Analiza el siguiente texto de un tema de oposiciones y extrae TODAS las referencias legales.

TEXTO A ANALIZAR:
---
{texto}
---

RONDA DE EXTRACCIÓN: {ronda}

"""

        # Si hay referencias previas, mencionarlas para evitar duplicados
        if referencias_previas and ronda > 1:
            refs_previas_str = "\n".join([
                f"- {ref.get('texto_completo', ref.get('texto', 'N/A'))}"
                for ref in referencias_previas[:10]  # Solo primeras 10
            ])

            prompt += f"""REFERENCIAS YA ENCONTRADAS (no las repitas):
{refs_previas_str}
{"... y más" if len(referencias_previas) > 10 else ""}

TAREA: Encuentra NUEVAS referencias que NO estén en la lista anterior.

"""

        # Inyectar siglas legales conocidas
        siglas_text = cargar_siglas_para_prompt(max_siglas=20)
        if siglas_text:
            prompt += f"\n{siglas_text}\n"

        prompt += """FORMATO DE RESPUESTA (JSON):
```json
{
  "referencias": [
    {
      "texto_completo": "Artículo 24 de la Constitución Española",
      "tipo": "artículo",
      "ley": "Constitución Española",
      "articulo": "24",
      "contexto": "El artículo 24 de la Constitución Española reconoce el derecho...",
      "confianza": 100
    },
    {
      "texto_completo": "Ley 39/2015, de 1 de octubre, del Procedimiento Administrativo Común",
      "tipo": "ley",
      "ley": "Ley 39/2015",
      "fecha": "1 de octubre de 2015",
      "nombre_completo": "del Procedimiento Administrativo Común de las Administraciones Públicas",
      "contexto": "La Ley 39/2015 establece...",
      "confianza": 100
    },
    {
      "texto_completo": "artículo 23.2.b de la LPAC",
      "tipo": "artículo",
      "ley": "LPAC",
      "articulo": "23.2.b",
      "contexto": "Según el artículo 23.2.b de la LPAC...",
      "confianza": 95
    }
  ]
}
```

TIPOS DE REFERENCIAS A BUSCAR:
- Leyes (Ley X/YYYY)
- Real Decreto (RD X/YYYY, Real Decreto X/YYYY)
- Artículos de leyes (Artículo X de la Ley Y)
- Constitución Española (artículos específicos)
- Reglamentos
- Directivas UE
- Tratados internacionales
- Siglas (LPAC, LRJSP, LEC, LJCA, etc.)

NIVEL DE CONFIANZA:
- 100: Referencia completamente explícita
- 90-99: Referencia muy clara
- 80-89: Referencia clara pero puede tener ambigüedad menor
- NO incluyas referencias con confianza < 80

Responde SOLO con el JSON, sin texto adicional antes o después."""

        return prompt

    def _parsear_respuesta(self, respuesta_raw: str) -> List[Dict]:
        """
        Parsea la respuesta JSON de Gemini

        Args:
            respuesta_raw: Texto de respuesta de Gemini

        Returns:
            Lista de referencias extraídas
        """
        try:
            # Extraer JSON del markdown si está envuelto en ```json
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', respuesta_raw, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Intentar buscar cualquier JSON en la respuesta
                json_match = re.search(r'\{.*"referencias".*\}', respuesta_raw, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    json_str = respuesta_raw

            # Parsear JSON
            data = json.loads(json_str)
            referencias = data.get('referencias', [])

            logger.debug(f"[{self.nombre}] Parseadas {len(referencias)} referencias")

            return referencias

        except json.JSONDecodeError as e:
            logger.error(f"[{self.nombre}] Error parseando JSON: {e}")
            logger.error(f"[{self.nombre}] Respuesta raw: {respuesta_raw[:500]}...")

            # Intento de recuperación: buscar referencias manualmente
            return self._parsear_respuesta_fallback(respuesta_raw)

    def _parsear_respuesta_fallback(self, respuesta_raw: str) -> List[Dict]:
        """
        Intenta parsear la respuesta si el JSON está malformado

        Args:
            respuesta_raw: Respuesta de Gemini

        Returns:
            Lista de referencias (puede estar vacía)
        """
        logger.warning(f"[{self.nombre}] Usando parseo fallback")

        referencias = []

        # Buscar patrones de leyes
        patrones_ley = [
            r'Ley\s+(\d+/\d{4})',
            r'Real\s+Decreto\s+(\d+/\d{4})',
            r'RD\s+(\d+/\d{4})',
        ]

        for patron in patrones_ley:
            matches = re.finditer(patron, respuesta_raw, re.IGNORECASE)
            for match in matches:
                referencias.append({
                    'texto_completo': match.group(0),
                    'tipo': 'ley',
                    'ley': match.group(1),
                    'confianza': 80,
                    'contexto': '(extraído por fallback)'
                })

        logger.info(f"[{self.nombre}] Fallback encontró {len(referencias)} referencias")

        return referencias

    def _filtrar_duplicados(
        self,
        referencias_nuevas: List[Dict],
        referencias_previas: List[Dict]
    ) -> List[Dict]:
        """
        Filtra referencias duplicadas

        Args:
            referencias_nuevas: Nuevas referencias encontradas
            referencias_previas: Referencias ya encontradas antes

        Returns:
            Lista de referencias únicas
        """
        # Crear set de textos completos previos (normalizados)
        textos_previos = set()
        for ref in referencias_previas:
            texto = (ref.get('texto_completo') or ref.get('texto') or '').lower().strip()
            if texto:
                textos_previos.add(texto)

        # Filtrar duplicados
        referencias_unicas = []
        for ref in referencias_nuevas:
            texto = (ref.get('texto_completo') or ref.get('texto') or '').lower().strip()
            if texto and texto not in textos_previos:
                referencias_unicas.append(ref)
                textos_previos.add(texto)  # Agregar para evitar duplicados internos

        logger.debug(
            f"[{self.nombre}] Filtrados duplicados: "
            f"{len(referencias_nuevas)} → {len(referencias_unicas)}"
        )

        return referencias_unicas
