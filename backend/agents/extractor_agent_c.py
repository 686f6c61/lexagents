# -*- coding: utf-8 -*-
"""
LexAgents - Sistema Multi-Agente de Extracción Legal
https://github.com/686f6c61/lexagents

Agente 1C: Extractor "Sabueso" - No Contaminado
Extrae referencias legales SIN conocimiento previo de siglas.
Busca menciones en lenguaje natural que otros agentes podrían pasar por alto.

Author: 686f6c61
Version: 0.2.0
License: MIT
"""

import json
import logging
import re
from typing import Dict, List, Any
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class ExtractorAgentC(BaseAgent):
    """
    Agente extractor "SABUESO" - No contaminado por siglas

    Características:
    - Temperatura: 0.4 (balanceado)
    - NO recibe mapeo de siglas (busca sin sesgos)
    - Enfocado en menciones en lenguaje natural
    - Captura referencias como:
      * "el Código establece"
      * "según la Constitución"
      * "el Estatuto prevé"
      * "la normativa vigente"
      * "el Reglamento dispone"
    - Mayor cobertura que A y B en referencias no estándar
    """

    def __init__(self, api_key: str = None):
        """
        Inicializa el Agente 1C (Sabueso)

        Args:
            api_key: API key de Gemini (opcional)
        """
        super().__init__(
            nombre="Agente1C-Sabueso",
            modelo="gemini-2.0-flash-exp",
            temperatura=0.4,  # Balanceado: más agresivo que A, más conservador que B
            api_key=api_key
        )

    def procesar(self, entrada: Dict[str, Any]) -> Dict[str, Any]:
        """
        Procesa un texto y extrae referencias legales sin conocimiento de siglas

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
        return """Eres un experto en extracción de referencias legales españolas.

Tu especialidad es encontrar referencias que otros sistemas podrían pasar por alto,
especialmente aquellas mencionadas en LENGUAJE NATURAL sin formato estándar.

EJEMPLOS DE REFERENCIAS A CAPTURAR:
✅ "según el Código Civil"
✅ "la Constitución establece"
✅ "el Estatuto de los Trabajadores prevé"
✅ "conforme a la normativa procesal"
✅ "el artículo 24 reconoce el derecho"
✅ "el Reglamento dispone"
✅ "la Ley Orgánica del Poder Judicial"
✅ "el texto refundido"
✅ "Ley 13/2009"
✅ "Real Decreto 203/2021"
✅ "según establece el artículo primero"

TAMBIÉN CAPTURA:
- Menciones genéricas si se pueden identificar ("el Código" → probablemente Código Civil)
- Referencias por contexto ("el artículo 117" en contexto judicial → CE)
- Normas sin número específico pero identificables

NO CAPTURES:
❌ Referencias a doctrina o jurisprudencia (STC, STS, etc.)
❌ Citas de libros o autores
❌ Referencias completamente genéricas sin posibilidad de identificar

REGLAS:
1. Extrae el texto EXACTO de la referencia
2. Identifica el tipo de norma (ley, código, constitución, real decreto, etc.)
3. Si puedes inferir la ley completa del contexto, hazlo
4. Sé más inclusivo que conservador: captura referencias aunque tengan ambigüedad
5. En caso de duda razonable, incluye la referencia con confianza media

IMPORTANTE: Devuelve SOLO JSON válido, sin texto adicional."""

    def _construir_prompt(
        self,
        texto: str,
        ronda: int,
        referencias_previas: List[Dict]
    ) -> str:
        """
        Construye el prompt para Gemini (SIN inyección de siglas)

        Args:
            texto: Texto del tema
            ronda: Número de ronda
            referencias_previas: Referencias ya encontradas

        Returns:
            Prompt formateado
        """
        # Truncar texto si es muy largo
        max_chars = 50000  # ~12,500 tokens
        if len(texto) > max_chars:
            texto = texto[:max_chars] + "\n\n[... texto truncado ...]"
            logger.warning(f"[{self.nombre}] Texto truncado a {max_chars} caracteres")

        prompt = f"""Analiza el siguiente texto y extrae TODAS las referencias legales,
especialmente aquellas mencionadas en lenguaje natural que otros extractores
podrían haber pasado por alto.

TEXTO A ANALIZAR:
---
{texto}
---

RONDA DE EXTRACCIÓN: {ronda}

"""

        # Si hay referencias previas, mencionarlas
        if referencias_previas and ronda > 1:
            refs_previas_str = "\n".join([
                f"- {ref.get('texto_completo', ref.get('texto', 'N/A'))}"
                for ref in referencias_previas[:10]
            ])

            prompt += f"""REFERENCIAS YA ENCONTRADAS (no las repitas):
{refs_previas_str}
{"... y más" if len(referencias_previas) > 10 else ""}

TAREA: Encuentra NUEVAS referencias que NO estén en la lista anterior.
Especialmente busca menciones en lenguaje natural.

"""

        # NOTA: NO inyectamos siglas aquí - el agente debe trabajar sin sesgos

        prompt += """FORMATO DE RESPUESTA (JSON):
```json
{
  "referencias": [
    {
      "texto_completo": "el Código Civil",
      "tipo": "codigo",
      "ley": "Código Civil",
      "articulo": null,
      "contexto": "El Código Civil establece en su articulado...",
      "confianza": 85
    },
    {
      "texto_completo": "la Constitución Española",
      "tipo": "constitucion",
      "ley": "Constitución Española",
      "articulo": null,
      "contexto": "La Constitución Española reconoce el derecho...",
      "confianza": 95
    },
    {
      "texto_completo": "artículo 117 de la Constitución",
      "tipo": "artículo",
      "ley": "Constitución Española",
      "articulo": "117",
      "contexto": "El artículo 117 de la Constitución establece...",
      "confianza": 100
    },
    {
      "texto_completo": "Ley 13/2009",
      "tipo": "ley",
      "ley": "Ley 13/2009",
      "articulo": null,
      "contexto": "La Ley 13/2009 regula...",
      "confianza": 100
    },
    {
      "texto_completo": "el Estatuto de los Trabajadores",
      "tipo": "estatuto",
      "ley": "Estatuto de los Trabajadores",
      "articulo": null,
      "contexto": "Según el Estatuto de los Trabajadores...",
      "confianza": 90
    }
  ]
}
```

TIPOS DE REFERENCIAS A BUSCAR:
- Leyes (Ley X/YYYY o "la Ley de...")
- Real Decreto (RD X/YYYY o "el Real Decreto de...")
- Artículos de leyes
- Constitución Española (incluso si solo dice "la Constitución")
- Códigos (Civil, Penal, Procesal, etc.)
- Estatutos
- Reglamentos
- Directivas UE
- Tratados internacionales
- Normativa administrativa

NIVEL DE CONFIANZA:
- 100: Referencia completamente explícita y clara
- 90-99: Referencia muy clara, mínima ambigüedad
- 80-89: Referencia identificable con contexto
- 70-79: Inferencia razonable desde contexto
- 60-69: Ambigüedad moderada pero probablemente correcta
- NO incluyas referencias con confianza < 60

IMPORTANTE: Sé MÁS INCLUSIVO que los extractores conservadores.
Si hay una mención razonable a legislación, inclúyela aunque no esté
en formato estándar.

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

        # Buscar patrones comunes
        patrones = [
            (r'Ley\s+(\d+/\d{4})', 'ley'),
            (r'Real\s+Decreto\s+(?:Legislativo\s+)?(\d+/\d{4})', 'real_decreto'),
            (r'RD\s+(\d+/\d{4})', 'real_decreto'),
            (r'Constitución\s+Española', 'constitucion'),
            (r'Código\s+(Civil|Penal)', 'codigo'),
        ]

        for patron, tipo in patrones:
            matches = re.finditer(patron, respuesta_raw, re.IGNORECASE)
            for match in matches:
                referencias.append({
                    'texto_completo': match.group(0),
                    'tipo': tipo,
                    'ley': match.group(0),
                    'confianza': 75,
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
        Filtra referencias que ya existen en la lista previa

        Args:
            referencias_nuevas: Referencias encontradas en esta ronda
            referencias_previas: Referencias de rondas anteriores

        Returns:
            Solo referencias nuevas (no duplicadas)
        """
        filtradas = []

        # Crear conjunto de textos previos (normalizados)
        textos_previos = set()
        for ref in referencias_previas:
            texto = ref.get('texto_completo', ref.get('texto', ''))
            if texto:
                # Normalizar: lowercase y sin espacios múltiples
                texto_norm = ' '.join(texto.lower().split())
                textos_previos.add(texto_norm)

        # Filtrar duplicados
        for ref in referencias_nuevas:
            texto = ref.get('texto_completo', ref.get('texto', ''))
            if texto:
                texto_norm = ' '.join(texto.lower().split())

                if texto_norm not in textos_previos:
                    filtradas.append(ref)
                    textos_previos.add(texto_norm)  # Agregar para evitar duplicados internos
                else:
                    logger.debug(f"[{self.nombre}] Duplicado filtrado: {texto[:50]}")

        return filtradas
