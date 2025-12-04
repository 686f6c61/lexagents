# -*- coding: utf-8 -*-
"""
LexAgents - Sistema Multi-Agente de Extracción Legal
https://github.com/686f6c61/lexagents

Módulo de Siglas y Abreviaturas Legales
Expande siglas comunes de leyes españolas a sus nombres completos.
Se utiliza en el agente de extracción y en el exportador.

Author: 686f6c61
Version: 0.2.0
License: MIT
"""

# Mapa de siglas a nombres completos
SIGLAS_LEYES = {
    # Códigos
    "CP": "Código Penal",
    "CC": "Código Civil",
    "CCom": "Código de Comercio",

    # Leyes procesales
    "LECrim": "Ley de Enjuiciamiento Criminal",
    "LEC": "Ley de Enjuiciamiento Civil",
    "LJCA": "Ley de la Jurisdicción Contencioso-Administrativa",

    # Leyes orgánicas importantes
    "LOPJ": "Ley Orgánica del Poder Judicial",
    "LORPM": "Ley Orgánica de Responsabilidad Penal del Menor",
    "LOFCA": "Ley Orgánica de Financiación de las Comunidades Autónomas",
    "LOTC": "Ley Orgánica del Tribunal Constitucional",

    # Constitución
    "CE": "Constitución Española",

    # Leyes administrativas
    "LPAC": "Ley del Procedimiento Administrativo Común de las Administraciones Públicas",
    "LRJSP": "Ley de Régimen Jurídico del Sector Público",
    "LAP": "Ley de Administración Pública",
    "LBRL": "Ley de Bases del Régimen Local",

    # Leyes laborales
    "ET": "Estatuto de los Trabajadores",
    "LISOS": "Ley de Infracciones y Sanciones en el Orden Social",
    "LOLS": "Ley Orgánica de Libertad Sindical",
    "LGSS": "Ley General de la Seguridad Social",

    # Otras leyes importantes
    "TRLSC": "Texto Refundido de la Ley de Sociedades de Capital",
    "LGT": "Ley General Tributaria",
    "LCSP": "Ley de Contratos del Sector Público",
}

# ============================================================================
# LEGISLACIÓN EUROPEA
# ============================================================================

# Siglas de legislación europea
SIGLAS_EUROPEAS = {
    # Protección de datos
    "RGPD": "Reglamento (UE) 2016/679",
    "GDPR": "Reglamento (UE) 2016/679",  # General Data Protection Regulation

    # Derecho internacional privado
    "Roma I": "Reglamento (CE) No 593/2008",
    "Roma II": "Reglamento (CE) No 864/2007",
    "Roma III": "Reglamento (UE) No 1259/2010",
    "Bruselas I": "Reglamento (CE) No 44/2001",
    "Bruselas I bis": "Reglamento (UE) No 1215/2012",
    "Bruselas II bis": "Reglamento (CE) No 2201/2003",

    # Identificación electrónica
    "eIDAS": "Reglamento (UE) No 910/2014",

    # Servicios digitales
    "DSA": "Reglamento (UE) 2022/2065",  # Digital Services Act
    "DMA": "Reglamento (UE) 2022/1925",  # Digital Markets Act

    # Inteligencia Artificial
    "AI Act": "Reglamento (UE) 2024/1689",
    "IA Act": "Reglamento (UE) 2024/1689",

    # Protección de datos sectorial
    "Directiva PIF": "Directiva (UE) 2017/1371",  # Protección Intereses Financieros
    "Directiva PNR": "Directiva (UE) 2016/681",   # Passenger Name Record

    # Servicios de pago
    "PSD2": "Directiva (UE) 2015/2366",  # Payment Services Directive

    # Competencia y ayudas de Estado
    "Reglamento de Concentraciones": "Reglamento (CE) No 139/2004",

    # Otros reglamentos importantes
    "Fiscalía Europea": "Reglamento (UE) 2017/1939",
    "EPPO": "Reglamento (UE) 2017/1939",  # European Public Prosecutor's Office
}

# Mapa de siglas europeas a CELEX
CELEX_CONOCIDOS = {
    "RGPD": "32016R0679",
    "GDPR": "32016R0679",
    "Roma I": "32008R0593",
    "Roma II": "32007R0864",
    "Roma III": "32010R1259",
    "Bruselas I": "32001R0044",
    "Bruselas I bis": "32012R1215",
    "Bruselas II bis": "32003R2201",
    "eIDAS": "32014R0910",
    "DSA": "32022R2065",
    "DMA": "32022R1925",
    "AI Act": "32024R1689",
    "IA Act": "32024R1689",
    "Directiva PIF": "32017L1371",
    "Directiva PNR": "32016L0681",
    "PSD2": "32015L2366",
    "Reglamento de Concentraciones": "32004R0139",
    "Fiscalía Europea": "32017R1939",
    "EPPO": "32017R1939",
}

# Combinar siglas españolas y europeas
SIGLAS_TODAS = {**SIGLAS_LEYES, **SIGLAS_EUROPEAS}

# Mapa de siglas a BOE-IDs conocidos
SIGLAS_BOE_ID = {
    "CP": "BOE-A-1995-25444",
    "CC": "BOE-A-1889-4763",
    "LECrim": "BOE-A-1882-6036",
    "LEC": "BOE-A-2000-323",
    "LOPJ": "BOE-A-1985-12666",
    "CE": "BOE-A-1978-31229",
    "LPAC": "BOE-A-2015-10565",
    "LRJSP": "BOE-A-2015-10566",
    "ET": "BOE-A-2015-11430",
}


def expandir_sigla(sigla: str) -> str:
    """
    Expande una sigla a su nombre completo

    Args:
        sigla: Sigla de la ley (ej: "CP", "LECrim")

    Returns:
        Nombre completo de la ley o la sigla original si no se encuentra
    """
    return SIGLAS_LEYES.get(sigla, sigla)


def obtener_boe_id_por_sigla(sigla: str) -> str:
    """
    Obtiene el BOE-ID de una ley por su sigla

    Args:
        sigla: Sigla de la ley

    Returns:
        BOE-ID o None si no se encuentra
    """
    return SIGLAS_BOE_ID.get(sigla)


def es_sigla_conocida(texto: str) -> bool:
    """
    Verifica si un texto es una sigla conocida

    Args:
        texto: Texto a verificar

    Returns:
        True si es una sigla conocida
    """
    return texto in SIGLAS_LEYES


def procesar_nombre_ley(nombre_ley: str) -> dict:
    """
    Procesa el nombre de una ley y devuelve información enriquecida

    Args:
        nombre_ley: Nombre de la ley (puede ser sigla o nombre completo)

    Returns:
        Dict con:
        - nombre_original: El nombre original
        - nombre_expandido: Nombre expandido si era sigla
        - es_sigla: True si era sigla
        - boe_id_sugerido: BOE-ID si se conoce
    """
    es_sigla = es_sigla_conocida(nombre_ley)

    return {
        "nombre_original": nombre_ley,
        "nombre_expandido": expandir_sigla(nombre_ley) if es_sigla else nombre_ley,
        "es_sigla": es_sigla,
        "boe_id_sugerido": obtener_boe_id_por_sigla(nombre_ley) if es_sigla else None
    }


# Referencias contextuales que necesitan resolución
REFERENCIAS_CONTEXTUALES = [
    "la presente ley",
    "esta ley",
    "dicha ley",
    "la citada ley",
    "el presente código",
    "este código",
    "la presente norma",
    "el presente reglamento",
    "esta norma",
    "el presente real decreto",
    "la presente ley orgánica",
]


def es_referencia_contextual(texto: str) -> bool:
    """
    Verifica si un texto es una referencia contextual que necesita resolución

    Args:
        texto: Texto a verificar

    Returns:
        True si es una referencia contextual
    """
    texto_lower = texto.lower().strip()
    return any(ref in texto_lower for ref in REFERENCIAS_CONTEXTUALES)


# ============================================================================
# FUNCIONES PARA LEGISLACIÓN EUROPEA
# ============================================================================

def es_sigla_europea(texto: str) -> bool:
    """
    Verifica si un texto es una sigla de legislación europea conocida

    Args:
        texto: Texto a verificar

    Returns:
        True si es una sigla europea conocida

    Ejemplo:
        >>> es_sigla_europea("RGPD")
        True
        >>> es_sigla_europea("Roma I")
        True
        >>> es_sigla_europea("CP")
        False
    """
    return texto in SIGLAS_EUROPEAS


def expandir_sigla_europea(sigla: str) -> str:
    """
    Expande una sigla europea a su nombre completo

    Args:
        sigla: Sigla europea (ej: "RGPD", "Roma I")

    Returns:
        Nombre completo del reglamento/directiva o la sigla original si no se encuentra

    Ejemplo:
        >>> expandir_sigla_europea("RGPD")
        "Reglamento (UE) 2016/679"
        >>> expandir_sigla_europea("eIDAS")
        "Reglamento (UE) No 910/2014"
    """
    return SIGLAS_EUROPEAS.get(sigla, sigla)


def obtener_celex_por_sigla(sigla: str) -> str:
    """
    Obtiene el identificador CELEX de una sigla europea

    Args:
        sigla: Sigla europea

    Returns:
        CELEX o None si no se encuentra

    Ejemplo:
        >>> obtener_celex_por_sigla("RGPD")
        "32016R0679"
        >>> obtener_celex_por_sigla("Roma I")
        "32008R0593"
    """
    return CELEX_CONOCIDOS.get(sigla)


def es_legislacion_europea(texto: str) -> bool:
    """
    Detecta si un texto se refiere a legislación europea

    Verifica si el texto contiene:
    - Palabras clave: "Reglamento (UE)", "Directiva (UE)", etc.
    - Siglas europeas conocidas: RGPD, eIDAS, etc.

    Args:
        texto: Texto a analizar

    Returns:
        True si parece ser legislación europea

    Ejemplo:
        >>> es_legislacion_europea("Artículo 17 del RGPD")
        True
        >>> es_legislacion_europea("Reglamento (UE) 2016/679")
        True
        >>> es_legislacion_europea("Artículo 138 del CP")
        False
    """
    texto_lower = texto.lower()

    # Patrones de legislación europea
    patrones_europeos = [
        "reglamento (ue)",
        "reglamento (ce)",
        "reglamento ue",
        "reglamento ce",
        "directiva (ue)",
        "directiva (ce)",
        "directiva ue",
        "directiva ce",
        "decisión (ue)",
        "decisión (ce)",
    ]

    # Verificar patrones
    if any(patron in texto_lower for patron in patrones_europeos):
        return True

    # Verificar siglas europeas conocidas
    for sigla in SIGLAS_EUROPEAS.keys():
        # Buscar sigla como palabra completa (con límites de palabra)
        import re
        if re.search(r'\b' + re.escape(sigla) + r'\b', texto, re.IGNORECASE):
            return True

    return False


def procesar_nombre_ley_completo(nombre_ley: str) -> dict:
    """
    Procesa el nombre de una ley (española o europea) y devuelve información enriquecida

    Args:
        nombre_ley: Nombre de la ley (puede ser sigla o nombre completo)

    Returns:
        Dict con:
        - nombre_original: El nombre original
        - nombre_expandido: Nombre expandido si era sigla
        - es_sigla: True si era sigla
        - es_europea: True si es legislación europea
        - boe_id_sugerido: BOE-ID si se conoce (español)
        - celex_sugerido: CELEX si se conoce (europeo)

    Ejemplo:
        >>> procesar_nombre_ley_completo("RGPD")
        {
            'nombre_original': 'RGPD',
            'nombre_expandido': 'Reglamento (UE) 2016/679',
            'es_sigla': True,
            'es_europea': True,
            'boe_id_sugerido': None,
            'celex_sugerido': '32016R0679'
        }
    """
    # Verificar si es sigla europea
    if es_sigla_europea(nombre_ley):
        return {
            "nombre_original": nombre_ley,
            "nombre_expandido": expandir_sigla_europea(nombre_ley),
            "es_sigla": True,
            "es_europea": True,
            "boe_id_sugerido": None,
            "celex_sugerido": obtener_celex_por_sigla(nombre_ley)
        }

    # Verificar si es sigla española
    if es_sigla_conocida(nombre_ley):
        return {
            "nombre_original": nombre_ley,
            "nombre_expandido": expandir_sigla(nombre_ley),
            "es_sigla": True,
            "es_europea": False,
            "boe_id_sugerido": obtener_boe_id_por_sigla(nombre_ley),
            "celex_sugerido": None
        }

    # No es sigla, verificar si es europea por contenido
    es_europea = es_legislacion_europea(nombre_ley)

    return {
        "nombre_original": nombre_ley,
        "nombre_expandido": nombre_ley,
        "es_sigla": False,
        "es_europea": es_europea,
        "boe_id_sugerido": None,
        "celex_sugerido": None
    }
