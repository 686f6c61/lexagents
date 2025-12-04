# -*- coding: utf-8 -*-
"""
LexAgents - Sistema Multi-Agente de Extracción Legal
https://github.com/686f6c61/lexagents

Agente 1B: Extractor Agresivo de Referencias Legales
Extrae referencias legales con mayor cobertura (temperatura media).
Busca referencias implícitas, siglas, y menciones indirectas.

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


class ExtractorAgentB(BaseAgent):
    """
    Agente extractor AGRESIVO de referencias legales

    Características:
    - Temperatura: 0.4 (más agresivo que A)
    - Busca referencias explícitas E implícitas
    - Mayor recall, puede tener menor precisión
    - Identifica siglas y abreviaturas
    """

    def __init__(self, api_key: str = None):
        """
        Inicializa el Agente 1B (Agresivo)

        Args:
            api_key: API key de Gemini (opcional)
        """
        super().__init__(
            nombre="Agente1B-Agresivo",
            modelo="gemini-2.0-flash-exp",
            temperatura=0.4,  # Más agresivo
            api_key=api_key
        )

    def procesar(self, entrada: Dict[str, Any]) -> Dict[str, Any]:
        """
        Procesa un texto y extrae referencias legales agresivamente

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
        return """Eres un asistente legal especializado en extracción EXHAUSTIVA de referencias legales para oposiciones del Estado español.

Tu tarea es identificar TODAS las referencias legales, incluyendo las IMPLÍCITAS y las que se mencionan mediante SIGLAS.

REGLAS:
1. Busca referencias EXPLÍCITAS (escritas claramente)
2. Busca referencias IMPLÍCITAS (mencionadas indirectamente)
3. Identifica SIGLAS legales (LPAC, LRJSP, LEC, CE, etc.) y expándelas
4. Detecta referencias a "la ley", "el reglamento", etc. y deduce cuál es según el contexto
5. SÉ MÁS INCLUSIVO: en caso de duda razonable, INCLUYE la referencia
6. Marca el nivel de confianza según cuán explícita sea la referencia

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
        # Truncar texto si es muy largo
        max_chars = 50000  # ~12,500 tokens
        if len(texto) > max_chars:
            texto = texto[:max_chars] + "\n\n[... texto truncado ...]"
            logger.warning(f"[{self.nombre}] Texto truncado a {max_chars} caracteres")

        prompt = f"""Analiza EXHAUSTIVAMENTE el siguiente texto de un tema de oposiciones y extrae TODAS las referencias legales, incluyendo las implícitas.

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
Busca referencias que el agente conservador pudo haber pasado por alto.

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
      "texto_completo": "LPAC",
      "tipo": "sigla",
      "ley": "Ley 39/2015",
      "nombre_completo": "Ley del Procedimiento Administrativo Común de las Administraciones Públicas",
      "contexto": "Según la LPAC, los interesados...",
      "confianza": 95
    },
    {
      "texto_completo": "la Constitución (implícito: artículo 14)",
      "tipo": "artículo",
      "ley": "Constitución Española",
      "articulo": "14",
      "contexto": "El principio de igualdad ante la ley...",
      "confianza": 75,
      "es_implicita": true
    },
    {
      "texto_completo": "Real Decreto 203/2021",
      "tipo": "real_decreto",
      "ley": "Real Decreto 203/2021",
      "fecha": "2021",
      "nombre_completo": "Reglamento de actuación y funcionamiento del sector público por medios electrónicos",
      "contexto": "El RD 203/2021 desarrolla...",
      "confianza": 100
    }
  ]
}
```

TIPOS DE REFERENCIAS A BUSCAR (SÉ EXHAUSTIVO):

1. REFERENCIAS EXPLÍCITAS:
   - Leyes: "Ley 39/2015", "Ley Orgánica 3/2007"
   - Reales Decretos: "Real Decreto 203/2021", "RD 203/2021"
   - Artículos: "artículo 24 de la CE", "art. 23.2.b de la LPAC"
   - Constitución: "Constitución Española", "CE"

2. SIGLAS Y ABREVIATURAS (EXPÁNDELAS):
   - LPAC → Ley 39/2015
   - LRJSP → Ley 40/2015
   - LEC → Ley 1/2000 (Enjuiciamiento Civil)
   - LJCA → Ley 29/1998 (Jurisdicción Contencioso-Administrativa)
   - CE → Constitución Española
   - LRJPAC → Ley 30/1992 (antigua)
   - LAECSP → Ley 11/2007
   - ... y muchas más

3. REFERENCIAS IMPLÍCITAS:
   - "la ley" → deducir cuál según contexto
   - "el reglamento" → identificar cuál
   - "dicha norma" → identificar a qué se refiere
   - "como establece el apartado anterior" → identificar artículo

4. MENCIONES INDIRECTAS:
   - "el derecho a la tutela judicial efectiva" → art. 24 CE
   - "el procedimiento administrativo común" → Ley 39/2015
   - "la jurisdicción contencioso-administrativa" → Ley 29/1998

NIVEL DE CONFIANZA:
- 100: Referencia completamente explícita con número
- 90-99: Referencia muy clara o sigla conocida
- 80-89: Referencia clara pero implícita
- 70-79: Referencia deducida del contexto
- 60-69: Referencia probable pero con ambigüedad
- Incluye referencias con confianza >= 60

INSTRUCCIÓN ESPECIAL:
Busca referencias que un agente conservador podría haber pasado por alto.
Sé más inclusivo y exhaustivo. La validación posterior filtrará falsos positivos.

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

            # Intento de recuperación
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

        # Buscar patrones más agresivamente
        patrones = [
            (r'Ley\s+(?:Orgánica\s+)?(\d+/\d{4})', 'ley'),
            (r'Real\s+Decreto\s+(?:Ley\s+)?(\d+/\d{4})', 'real_decreto'),
            (r'RDL?\s+(\d+/\d{4})', 'real_decreto'),
            (r'\b(LPAC|LRJSP|LEC|LJCA|CE|LAECSP)\b', 'sigla'),
            (r'art(?:ículo|\.)?\s+(\d+(?:\.\d+)?(?:\.[a-z])?)', 'artículo'),
        ]

        for patron, tipo in patrones:
            matches = re.finditer(patron, respuesta_raw, re.IGNORECASE)
            for match in matches:
                referencias.append({
                    'texto_completo': match.group(0),
                    'tipo': tipo,
                    'ley': match.group(1) if match.groups() else match.group(0),
                    'confianza': 70,
                    'contexto': '(extraído por fallback)',
                    'es_implicita': True
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

            # También agregar la ley sin contexto adicional
            ley = (ref.get('ley') or '').lower().strip()
            if ley:
                textos_previos.add(ley)

        # Filtrar duplicados
        referencias_unicas = []
        for ref in referencias_nuevas:
            texto = (ref.get('texto_completo') or ref.get('texto') or '').lower().strip()
            ley = (ref.get('ley') or '').lower().strip()

            # Verificar si es duplicado
            if texto not in textos_previos and ley not in textos_previos:
                referencias_unicas.append(ref)
                textos_previos.add(texto)
                if ley:
                    textos_previos.add(ley)

        logger.debug(
            f"[{self.nombre}] Filtrados duplicados: "
            f"{len(referencias_nuevas)} → {len(referencias_unicas)}"
        )

        return referencias_unicas
