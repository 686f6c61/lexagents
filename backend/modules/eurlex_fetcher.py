# -*- coding: utf-8 -*-
"""
LexAgents - Sistema Multi-Agente de Extracción Legal
https://github.com/686f6c61/lexagents

Módulo para interactuar con EUR-Lex (legislación de la Unión Europea)
Funcionalidades:
- Generación de identificadores CELEX
- Verificación de existencia vía SPARQL
- Generación de URLs a documentos EUR-Lex

Author: 686f6c61
Version: 0.2.0
License: MIT
"""

import re
import logging
import requests
from typing import Dict, Optional, Tuple
from functools import lru_cache
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# ============================================================================
# CONSTANTES
# ============================================================================

EURLEX_SPARQL_ENDPOINT = "https://publications.europa.eu/webapi/rdf/sparql"

# Tipos de actos legislativos UE
TIPO_REGLAMENTO = "R"
TIPO_DIRECTIVA = "L"
TIPO_DECISION = "D"

# Mapeo de palabras clave a tipos CELEX
PALABRAS_TIPO = {
    "reglamento": TIPO_REGLAMENTO,
    "directiva": TIPO_DIRECTIVA,
    "decisión": TIPO_DECISION,
    "decision": TIPO_DECISION,
}

# ============================================================================
# GENERACIÓN DE CELEX
# ============================================================================

def generar_celex(tipo: str, año: int, numero: int) -> str:
    """
    Genera un identificador CELEX para legislación UE

    Formato CELEX: 3YYYYTNNNN
    - 3: Sector (legislación)
    - YYYY: Año (4 dígitos)
    - T: Tipo (R=Reglamento, L=Directiva, D=Decisión)
    - NNNN: Número (4 dígitos con padding)

    Args:
        tipo: Tipo de acto ("R", "L", "D")
        año: Año de publicación (ej: 2016)
        numero: Número del acto (ej: 679)

    Returns:
        Identificador CELEX (ej: "32016R0679" para GDPR)

    Ejemplo:
        >>> generar_celex("R", 2016, 679)
        "32016R0679"
    """
    tipo_upper = tipo.upper()
    if tipo_upper not in ["R", "L", "D"]:
        logger.warning(f"Tipo CELEX desconocido: {tipo}. Usando 'R' por defecto")
        tipo_upper = "R"

    celex = f"3{año}{tipo_upper}{numero:04d}"
    logger.debug(f"CELEX generado: {celex} (tipo={tipo}, año={año}, num={numero})")
    return celex


def extraer_celex_de_texto(texto: str) -> Optional[str]:
    """
    Extrae información de un Reglamento/Directiva UE y genera su CELEX

    Patrones soportados:
    - "Reglamento (UE) 2016/679"
    - "Reglamento UE 2016/679"
    - "Directiva 2016/680"
    - "Directiva (UE) 2016/680"

    Args:
        texto: Texto que contiene la referencia al acto UE

    Returns:
        Identificador CELEX si se puede generar, None en caso contrario

    Ejemplo:
        >>> extraer_celex_de_texto("Reglamento (UE) 2016/679")
        "32016R0679"
    """
    # Patrón para Reglamento (UE), (CE), UE, CE, o "No" seguido de número
    # El formato EUR-Lex puede ser:
    # - "Reglamento (UE) 2016/679" → año 2016, número 679
    # - "Reglamento (CE) No 593/2008" → número 593, año 2008
    # Por tanto, aceptamos ambos formatos: YYYY/NNN o NNN/YYYY
    patron_reglamento = r'Reglamento\s*(?:\(UE\)|\(CE\)|UE|CE)?\s*(?:No|N[oº]|n[oº])?\s*(\d+)/(\d+)'
    match = re.search(patron_reglamento, texto, re.IGNORECASE)

    if match:
        num1 = int(match.group(1))
        num2 = int(match.group(2))

        # Determinar cuál es el año (el de 4 dígitos) y cuál el número
        if num1 >= 1000:  # num1 es el año (ej: 2016/679)
            año, numero = num1, num2
        else:  # num2 es el año (ej: 593/2008)
            numero, año = num1, num2

        celex = generar_celex("R", año, numero)
        logger.debug(f"CELEX extraído de Reglamento: {celex}")
        return celex

    # Patrón para Directiva (UE), (CE), etc.
    patron_directiva = r'Directiva\s*(?:\(UE\)|\(CE\)|UE|CE)?\s*(?:No|N[oº]|n[oº])?\s*(\d+)/(\d+)'
    match = re.search(patron_directiva, texto, re.IGNORECASE)

    if match:
        num1 = int(match.group(1))
        num2 = int(match.group(2))

        if num1 >= 1000:
            año, numero = num1, num2
        else:
            numero, año = num1, num2

        celex = generar_celex("L", año, numero)
        logger.debug(f"CELEX extraído de Directiva: {celex}")
        return celex

    # Patrón para Decisión (UE), (CE), etc.
    patron_decision = r'Decisión\s*(?:\(UE\)|\(CE\)|UE|CE)?\s*(?:No|N[oº]|n[oº])?\s*(\d+)/(\d+)'
    match = re.search(patron_decision, texto, re.IGNORECASE)

    if match:
        num1 = int(match.group(1))
        num2 = int(match.group(2))

        if num1 >= 1000:
            año, numero = num1, num2
        else:
            numero, año = num1, num2

        celex = generar_celex("D", año, numero)
        logger.debug(f"CELEX extraído de Decisión: {celex}")
        return celex

    logger.debug(f"No se pudo extraer CELEX de: {texto[:100]}")
    return None


# ============================================================================
# GENERACIÓN DE URLs
# ============================================================================

def generar_urls_eurlex(celex: str, idioma: str = "ES") -> Dict[str, str]:
    """
    Genera URLs a diferentes formatos del documento en EUR-Lex

    Args:
        celex: Identificador CELEX (ej: "32016R0679")
        idioma: Código de idioma ISO (ej: "ES", "EN", "FR")

    Returns:
        Diccionario con URLs a TXT, PDF, HTML

    Ejemplo:
        >>> generar_urls_eurlex("32016R0679", "ES")
        {
            'txt': 'https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32016R0679',
            'pdf': 'https://eur-lex.europa.eu/legal-content/ES/PDF/?uri=CELEX:32016R0679',
            'html': 'https://eur-lex.europa.eu/legal-content/ES/ALL/?uri=CELEX:32016R0679'
        }
    """
    base_url = f"https://eur-lex.europa.eu/legal-content/{idioma.upper()}"

    urls = {
        'txt': f"{base_url}/TXT/?uri=CELEX:{celex}",
        'pdf': f"{base_url}/PDF/?uri=CELEX:{celex}",
        'html': f"{base_url}/ALL/?uri=CELEX:{celex}",
        'principal': f"{base_url}/TXT/?uri=CELEX:{celex}"  # URL por defecto
    }

    logger.debug(f"URLs generadas para CELEX {celex} en {idioma}")
    return urls


# ============================================================================
# VERIFICACIÓN SPARQL
# ============================================================================

@lru_cache(maxsize=200)
def verificar_celex_existe(celex: str) -> Tuple[bool, Optional[Dict]]:
    """
    Verifica si un CELEX existe en EUR-Lex usando SPARQL

    Consulta el endpoint SPARQL de EUR-Lex para verificar existencia
    y obtener metadatos básicos del documento.

    Args:
        celex: Identificador CELEX (ej: "32016R0679")

    Returns:
        Tupla (existe, metadatos)
        - existe: True si el documento existe
        - metadatos: Dict con título, fecha, tipo (o None si no existe)

    Ejemplo:
        >>> existe, meta = verificar_celex_existe("32016R0679")
        >>> existe
        True
        >>> meta['titulo_es']
        'Reglamento (UE) 2016/679 relativo a la protección de datos...'
    """
    query = f"""
    PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
    PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

    SELECT ?work ?titulo_es ?fecha ?tipo
    WHERE {{
      ?work cdm:resource_legal_id_celex "{celex}" .

      OPTIONAL {{
        ?work cdm:work_has_expression ?expr .
        ?expr cdm:expression_uses_language <http://publications.europa.eu/resource/authority/language/SPA> .
        ?expr cdm:expression_title ?titulo_es .
      }}

      OPTIONAL {{ ?work cdm:work_date_document ?fecha . }}
      OPTIONAL {{ ?work cdm:resource_legal_type ?tipo . }}
    }}
    LIMIT 1
    """

    try:
        response = requests.get(
            EURLEX_SPARQL_ENDPOINT,
            params={
                'query': query,
                'format': 'application/sparql-results+json'
            },
            timeout=10
        )

        if response.status_code != 200:
            logger.warning(f"Error SPARQL para {celex}: HTTP {response.status_code}")
            return False, None

        data = response.json()
        bindings = data.get('results', {}).get('bindings', [])

        if not bindings:
            logger.info(f"CELEX {celex} no encontrado en EUR-Lex")
            return False, None

        result = bindings[0]
        metadatos = {
            'celex': celex,
            'work_uri': result.get('work', {}).get('value'),
            'titulo_es': result.get('titulo_es', {}).get('value'),
            'fecha': result.get('fecha', {}).get('value'),
            'tipo': result.get('tipo', {}).get('value'),
        }

        logger.info(f"✅ CELEX {celex} verificado en EUR-Lex")
        return True, metadatos

    except requests.RequestException as e:
        logger.error(f"Error de red al verificar CELEX {celex}: {e}")
        return False, None
    except Exception as e:
        logger.error(f"Error inesperado al verificar CELEX {celex}: {e}")
        return False, None


# ============================================================================
# OBTENCIÓN DE TÍTULOS
# ============================================================================

@lru_cache(maxsize=200)
def obtener_titulo_completo(celex: str, idioma: str = "ES") -> Optional[str]:
    """
    Obtiene el título completo de un acto legislativo UE

    Hace scraping de la página EUR-Lex para obtener el título oficial.
    Usa caché para minimizar peticiones.

    Args:
        celex: Identificador CELEX
        idioma: Código de idioma (default: "ES")

    Returns:
        Título completo o None si no se puede obtener

    Ejemplo:
        >>> obtener_titulo_completo("32016R0679")
        'Reglamento (UE) 2016/679 del Parlamento Europeo y del Consejo, de 27 de abril de 2016, relativo a la protección de las personas físicas...'
    """
    url = f"https://eur-lex.europa.eu/legal-content/{idioma.upper()}/TXT/?uri=CELEX:{celex}"

    try:
        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            logger.warning(f"No se pudo obtener título para {celex}: HTTP {response.status_code}")
            return None

        soup = BeautifulSoup(response.content, 'html.parser')

        # Buscar título en el HTML
        # EUR-Lex usa diferentes selectores según el tipo de documento
        titulo = None

        # Intento 1: <h1> principal
        h1 = soup.find('h1')
        if h1:
            titulo = h1.get_text(strip=True)

        # Intento 2: Meta tag title
        if not titulo:
            meta_title = soup.find('meta', {'name': 'DC.title'})
            if meta_title:
                titulo = meta_title.get('content', '').strip()

        # Intento 3: Div con clase específica
        if not titulo:
            div_titulo = soup.find('div', {'id': 'document-title'})
            if div_titulo:
                titulo = div_titulo.get_text(strip=True)

        if titulo:
            logger.info(f"✅ Título obtenido para {celex}")
            return titulo
        else:
            logger.warning(f"No se encontró título en la página para {celex}")
            return None

    except requests.RequestException as e:
        logger.error(f"Error de red al obtener título de {celex}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error inesperado al obtener título de {celex}: {e}")
        return None


# ============================================================================
# OBTENCIÓN DE ARTÍCULOS (INVESTIGACIÓN)
# ============================================================================

def obtener_articulo(celex: str, numero_articulo: str, idioma: str = "ES") -> Optional[str]:
    """
    [EXPERIMENTAL] Intenta obtener el texto de un artículo específico

    NOTA: Esta funcionalidad está en fase de investigación.
    EUR-Lex no proporciona una API estructurada para artículos individuales
    como lo hace el BOE. Requiere scraping de HTML.

    Args:
        celex: Identificador CELEX
        numero_articulo: Número del artículo (ej: "17", "5.2")
        idioma: Código de idioma

    Returns:
        Texto del artículo o None si no se puede extraer

    TODO:
        - Investigar estructura HTML de diferentes tipos de actos
        - Implementar parsers específicos para Reglamentos/Directivas
        - Manejar artículos con subapartados
        - Añadir tests con casos conocidos (GDPR art. 17, etc.)
    """
    logger.warning("obtener_articulo() está en fase experimental")

    url = f"https://eur-lex.europa.eu/legal-content/{idioma.upper()}/TXT/HTML/?uri=CELEX:{celex}"

    try:
        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            logger.warning(f"No se pudo obtener HTML para {celex}: HTTP {response.status_code}")
            return None

        soup = BeautifulSoup(response.content, 'html.parser')

        # TODO: Implementar lógica de extracción específica
        # La estructura varía mucho entre documentos
        # Requiere análisis manual de casos

        logger.info("Extracción de artículos EUR-Lex aún no implementada")
        return None

    except Exception as e:
        logger.error(f"Error al obtener artículo {numero_articulo} de {celex}: {e}")
        return None


# ============================================================================
# FUNCIÓN PRINCIPAL DE ENRIQUECIMIENTO
# ============================================================================

def enriquecer_referencia_eurlex(texto_completo: str) -> Optional[Dict]:
    """
    Enriquece una referencia a legislación UE con datos de EUR-Lex

    Esta es la función principal que debería ser llamada desde exportador.py

    Args:
        texto_completo: Texto de la referencia (ej: "Reglamento (UE) 2016/679")

    Returns:
        Dict con datos enriquecidos o None si no se puede procesar

    Ejemplo de salida:
        {
            'celex': '32016R0679',
            'urls': {
                'txt': 'https://eur-lex.europa.eu/...',
                'pdf': 'https://eur-lex.europa.eu/...',
                'html': 'https://eur-lex.europa.eu/...',
                'principal': 'https://eur-lex.europa.eu/...'
            },
            'titulo_completo': 'Reglamento (UE) 2016/679 del Parlamento...',
            'existe': True,
            'metadatos': {...}
        }
    """
    logger.info(f"Enriqueciendo referencia EUR-Lex: {texto_completo[:80]}...")

    # Paso 1: Extraer CELEX del texto
    celex = extraer_celex_de_texto(texto_completo)

    if not celex:
        logger.warning(f"No se pudo extraer CELEX de: {texto_completo}")
        return None

    # Paso 2: Generar URLs
    urls = generar_urls_eurlex(celex, idioma="ES")

    # Paso 3: Verificar existencia (con caché)
    existe, metadatos = verificar_celex_existe(celex)

    if not existe:
        logger.warning(f"CELEX {celex} no existe en EUR-Lex")
        return {
            'celex': celex,
            'urls': urls,
            'existe': False,
            'titulo_completo': None,
            'metadatos': None
        }

    # Paso 4: Obtener título completo (con caché)
    titulo = obtener_titulo_completo(celex, idioma="ES")

    # Paso 5: Devolver datos enriquecidos
    resultado = {
        'celex': celex,
        'urls': urls,
        'existe': existe,
        'titulo_completo': titulo,
        'metadatos': metadatos
    }

    logger.info(f"✅ Referencia EUR-Lex enriquecida: {celex}")
    return resultado


# ============================================================================
# UTILIDADES
# ============================================================================

def limpiar_cache():
    """Limpia los cachés LRU de las funciones"""
    verificar_celex_existe.cache_clear()
    obtener_titulo_completo.cache_clear()
    logger.info("Cachés EUR-Lex limpiados")


def obtener_estadisticas_cache() -> Dict:
    """
    Obtiene estadísticas de uso de caché

    Returns:
        Dict con hits, misses, y tamaño de cada caché
    """
    return {
        'verificar_celex': verificar_celex_existe.cache_info()._asdict(),
        'obtener_titulo': obtener_titulo_completo.cache_info()._asdict()
    }
