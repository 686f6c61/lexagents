# -*- coding: utf-8 -*-
"""
LexAgents - Sistema Multi-Agente de Extracción Legal
https://github.com/686f6c61/lexagents

Módulo 2: Buscador de BOE-IDs
Busca leyes en la API del BOE y devuelve sus identificadores únicos (BOE-A-YYYY-NNNNN)
Implementa estrategias de búsqueda con fallback y caché local.

Author: 686f6c61
Version: 0.2.0
License: MIT
"""

import re
import requests
import json
import logging
from typing import Optional, Dict, List
from pathlib import Path
from datetime import datetime, timedelta
import time

logger = logging.getLogger(__name__)


class BOESearcher:
    """Buscador de BOE-IDs para leyes españolas"""

    def __init__(self, cache_dir: str = "../../data/cache"):
        """
        Inicializa el buscador

        Args:
            cache_dir: Directorio para caché de búsquedas
        """
        self.base_url = "https://www.boe.es"
        self.api_base = f"{self.base_url}/datosabiertos/api/legislacion-consolidada"

        # Caché local
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "boe_ids_cache.json"
        self.cache = self._cargar_cache()

        # Retry config
        self.max_retries = 3
        self.retry_delay = 1  # segundos

    def _cargar_cache(self) -> Dict:
        """Carga el caché de BOE-IDs desde disco"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Error cargando caché: {e}")
                return {}
        return {}

    def _guardar_cache(self):
        """Guarda el caché de BOE-IDs a disco"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error guardando caché: {e}")

    def buscar_ley(
        self,
        referencia: str,
        año: Optional[str] = None,
        titulo_completo: Optional[str] = None
    ) -> Optional[str]:
        """
        Busca una ley y devuelve su BOE-ID

        Args:
            referencia: Nombre de la ley (ej: "Ley 39/2015" o "LPAC")
            año: Año opcional para afinar búsqueda
            titulo_completo: Título completo oficial (ej: "Ley 39/2015, de 1 de octubre...")

        Returns:
            BOE-ID en formato BOE-A-YYYY-NNNNN o None si no se encuentra
        """
        # Normalizar referencia
        ref_normalizada = self._normalizar_referencia(referencia)
        cache_key = f"{ref_normalizada}_{año}_{titulo_completo[:30] if titulo_completo else ''}"

        # Buscar en caché
        if cache_key in self.cache:
            logger.info(f"✅ BOE-ID en caché: {self.cache[cache_key]}")
            return self.cache[cache_key]

        logger.info(f"🔍 Buscando BOE-ID para: {referencia}")

        # Estrategia 0: Búsqueda directa en mapeo de siglas/nombres
        # (para CE, CC, LEC, LOPJ, LJV, etc.)
        boe_id = self._buscar_en_mapeo_siglas(referencia)

        # Estrategia 0.5: Búsqueda por título completo (NUEVO)
        if not boe_id and titulo_completo:
            logger.info(f"   🔍 Intentando con título completo: {titulo_completo[:80]}...")
            boe_id = self._buscar_por_titulo_completo(titulo_completo)

        # Estrategia 1: Búsqueda directa con año
        if not boe_id:
            boe_id = self._buscar_con_año(ref_normalizada, año)

        # Estrategia 2: Búsqueda sin año (si no se encontró)
        if not boe_id and año:
            logger.info("   Intentando sin año específico...")
            boe_id = self._buscar_sin_año(ref_normalizada)

        # Estrategia 3: Búsqueda por patrón de Ley X/YYYY
        if not boe_id:
            boe_id = self._buscar_por_patron(referencia)

        # Guardar en caché si se encontró
        if boe_id:
            self.cache[cache_key] = boe_id
            self._guardar_cache()
            logger.info(f"✅ BOE-ID encontrado: {boe_id}")
        else:
            logger.warning(f"❌ No se encontró BOE-ID para: {referencia}")

        return boe_id

    def _normalizar_referencia(self, referencia: str) -> str:
        """Normaliza una referencia legal para búsqueda"""
        # Limpiar espacios extra
        ref = re.sub(r'\s+', ' ', referencia.strip())

        # Normalizar formato de números
        ref = re.sub(r'nº\s*', '', ref, flags=re.IGNORECASE)
        ref = re.sub(r'núm\.\s*', '', ref, flags=re.IGNORECASE)

        return ref

    def _buscar_en_mapeo_siglas(self, referencia: str) -> Optional[str]:
        """
        Busca directamente en el mapeo de siglas y nombres completos

        Este mapeo incluye: CE, CC, LEC, LOPJ, LJV, etc.

        Args:
            referencia: Referencia a buscar (puede ser sigla o nombre completo)

        Returns:
            BOE-ID si se encuentra, None en caso contrario
        """
        # Mapeo de siglas y nombres completos a BOE-IDs
        mapeo_siglas = {
            # Constitución Española
            "constitución española": "BOE-A-1978-31229",
            "constitución": "BOE-A-1978-31229",
            "ce": "BOE-A-1978-31229",

            # Código Civil
            "código civil": "BOE-A-1889-4763",
            "cc": "BOE-A-1889-4763",

            # Código de Comercio
            "código de comercio": "BOE-A-1885-6627",
            "ccom": "BOE-A-1885-6627",
            "cco": "BOE-A-1885-6627",

            # Ley de Enjuiciamiento Civil (actual y antigua)
            "lec": "BOE-A-2000-323",
            "ley de enjuiciamiento civil": "BOE-A-2000-323",
            "ley de enjuiciamiento civil de 1881": "BOE-A-1881-813",
            "ley 1/2000": "BOE-A-2000-323",

            # Ley de Jurisdicción Voluntaria
            "ljv": "BOE-A-2015-7391",
            "ley 15/2015": "BOE-A-2015-7391",
            "jurisdicción voluntaria": "BOE-A-2015-7391",

            # Ley Orgánica del Poder Judicial
            "lopj": "BOE-A-1985-12666",
            "ley orgánica del poder judicial": "BOE-A-1985-12666",
            "ley orgánica 6/1985": "BOE-A-1985-12666",

            # LPAC y LRJSP
            "lpac": "BOE-A-2015-10565",
            "lrjsp": "BOE-A-2015-10566",
            "ley 39/2015": "BOE-A-2015-10565",
            "ley 40/2015": "BOE-A-2015-10566",

            # Jurisdicción Contencioso-Administrativa
            "ljca": "BOE-A-1998-16718",
            "ley 29/1998": "BOE-A-1998-16718",

            # Protección del Menor
            "ley orgánica 1/1996": "BOE-A-1996-1069",
        }

        # Normalizar referencia para búsqueda
        ref_norm = referencia.lower().strip()

        # Buscar directamente
        if ref_norm in mapeo_siglas:
            boe_id = mapeo_siglas[ref_norm]
            logger.debug(f"✅ BOE-ID encontrado en mapeo de siglas: {boe_id}")
            return boe_id

        return None

    def _buscar_con_año(self, referencia: str, año: Optional[str]) -> Optional[str]:
        """Busca usando la API del BOE con año específico"""
        if not año:
            return None

        # Extraer tipo y número de ley
        tipo_num = self._extraer_tipo_numero(referencia)
        if not tipo_num:
            return None

        tipo, numero = tipo_num

        # Construir BOE-ID estimado (patrón común)
        # Ley 39/2015 → BOE-A-2015-10565
        # Necesitamos el número de BOE, que normalmente se asigna por orden

        # Por ahora, intentamos buscar directamente
        # En una implementación completa, consultaríamos la API de búsqueda del BOE

        return self._consultar_api_boe(tipo, numero, año)

    def _buscar_sin_año(self, referencia: str) -> Optional[str]:
        """Busca sin especificar año (puede devolver múltiples resultados)"""
        # Extraer tipo y número
        tipo_num = self._extraer_tipo_numero(referencia)
        if not tipo_num:
            return None

        tipo, numero = tipo_num

        # Buscar en años recientes (últimos 30 años)
        año_actual = datetime.now().year
        for año in range(año_actual, año_actual - 30, -1):
            boe_id = self._consultar_api_boe(tipo, numero, str(año))
            if boe_id:
                return boe_id

        return None

    def _buscar_por_patron(self, referencia: str) -> Optional[str]:
        """Busca usando patrones conocidos de referencias legales"""
        # Patrón: Ley 39/2015
        match = re.search(r'Ley\s+(\d+)/(\d{4})', referencia, re.IGNORECASE)
        if match:
            numero = match.group(1)
            año = match.group(2)
            return self._consultar_api_boe("Ley", numero, año)

        # Patrón: Real Decreto 123/2020
        match = re.search(r'Real\s+Decreto\s+(\d+)/(\d{4})', referencia, re.IGNORECASE)
        if match:
            numero = match.group(1)
            año = match.group(2)
            return self._consultar_api_boe("Real Decreto", numero, año)

        # Patrón: RD 123/2020
        match = re.search(r'RD\s+(\d+)/(\d{4})', referencia, re.IGNORECASE)
        if match:
            numero = match.group(1)
            año = match.group(2)
            return self._consultar_api_boe("Real Decreto", numero, año)

        return None

    def _buscar_por_titulo_completo(self, titulo_completo: str) -> Optional[str]:
        """
        Busca un BOE-ID usando el título completo oficial de la ley

        Args:
            titulo_completo: Título completo como "Ley 13/2009, de 3 de noviembre..."

        Returns:
            BOE-ID si se encuentra
        """
        try:
            # Extraer año del título
            match_anno = re.search(r'(?:de\s+)?(\d{4})', titulo_completo)
            anno = match_anno.group(1) if match_anno else None

            # Extraer número de ley
            match_ley = re.search(r'Ley\s+(\d+/\d{4})', titulo_completo, re.IGNORECASE)
            if match_ley:
                ley_numero = match_ley.group(1)
                numero, año_ley = ley_numero.split('/')
                return self._consultar_api_boe("Ley", numero, año_ley)

            # Real Decreto Legislativo
            match_rdl = re.search(r'Real\s+Decreto\s+Legislativo\s+(\d+/\d{4})', titulo_completo, re.IGNORECASE)
            if match_rdl:
                rd_numero = match_rdl.group(1)
                numero, año_rd = rd_numero.split('/')
                return self._consultar_api_boe("Real Decreto Legislativo", numero, año_rd)

            # Real Decreto
            match_rd = re.search(r'Real\s+Decreto\s+(\d+/\d{4})', titulo_completo, re.IGNORECASE)
            if match_rd:
                rd_numero = match_rd.group(1)
                numero, año_rd = rd_numero.split('/')
                return self._consultar_api_boe("Real Decreto", numero, año_rd)

            # Ley Orgánica
            match_lo = re.search(r'Ley\s+Orgánica\s+(\d+/\d{4})', titulo_completo, re.IGNORECASE)
            if match_lo:
                lo_numero = match_lo.group(1)
                numero, año_lo = lo_numero.split('/')
                return self._consultar_api_boe("Ley Orgánica", numero, año_lo)

            # Constitución Española
            if 'constitución' in titulo_completo.lower():
                return "BOE-A-1978-31229"

            # Código Civil
            if 'código civil' in titulo_completo.lower():
                return "BOE-A-1889-4763"

            # Código Penal
            if 'código penal' in titulo_completo.lower():
                return "BOE-A-1995-25444"

            logger.debug(f"No se pudo extraer BOE-ID del título: {titulo_completo[:80]}")
            return None

        except Exception as e:
            logger.error(f"Error buscando por título completo: {e}")
            return None

    def _extraer_tipo_numero(self, referencia: str) -> Optional[tuple]:
        """
        Extrae tipo de norma y número de una referencia

        Returns:
            Tupla (tipo, numero) o None
        """
        # Ley 39/2015
        match = re.search(r'(Ley)\s+(\d+/\d{4})', referencia, re.IGNORECASE)
        if match:
            return (match.group(1), match.group(2))

        # Real Decreto 123/2020
        match = re.search(r'(Real\s+Decreto)\s+(\d+/\d{4})', referencia, re.IGNORECASE)
        if match:
            return (match.group(1), match.group(2))

        # RD 123/2020
        match = re.search(r'(RD)\s+(\d+/\d{4})', referencia, re.IGNORECASE)
        if match:
            return ("Real Decreto", match.group(2))

        return None

    def _consultar_api_boe(self, tipo: str, numero: str, año: str) -> Optional[str]:
        """
        Consulta la API del BOE para obtener el BOE-ID

        Args:
            tipo: Tipo de norma (Ley, Real Decreto, etc.)
            numero: Número de la norma
            año: Año de publicación

        Returns:
            BOE-ID o None
        """
        # Mapeo manual de leyes conocidas (las más comunes en oposiciones)
        # Esto sirve como fallback rápido cuando la API no responde
        # o para acelerar búsquedas de leyes muy frecuentes
        mapeo_conocido = {
            # Leyes administrativas (las MÁS importantes en oposiciones)
            ("Ley", "39/2015"): "BOE-A-2015-10565",  # LPAC - Procedimiento Administrativo
            ("Ley", "40/2015"): "BOE-A-2015-10566",  # LRJSP - Régimen Jurídico Sector Público
            ("Ley", "30/1992"): "BOE-A-1992-26318",  # Antigua LRJAP-PAC (derogada)

            # Leyes procesales
            ("Ley", "1/2000"): "BOE-A-2000-323",      # LEC - Enjuiciamiento Civil
            ("Ley", "29/1998"): "BOE-A-1998-16718",   # LJCA - Jurisdicción Contencioso-Admin
            ("Ley", "15/2015"): "BOE-A-2015-7391",    # LJV - Jurisdicción Voluntaria

            # Organización administrativa
            ("Ley", "6/1997"): "BOE-A-1997-8392",     # LOFAGE - Organización y Funcionamiento AGE
            ("Ley", "50/1997"): "BOE-A-1997-25336",   # LG - Ley del Gobierno

            # Hacienda y presupuesto
            ("Ley", "47/2003"): "BOE-A-2003-21614",   # LGP - Ley General Presupuestaria
            ("Ley", "58/2003"): "BOE-A-2003-23186",   # LGT - Ley General Tributaria

            # Función pública
            ("Ley", "7/2007"): "BOE-A-2007-7788",     # EBEP - Estatuto Básico Empleado Público

            # Leyes laborales
            ("Real Decreto Legislativo", "2/2015"): "BOE-A-2015-11430",  # ET - Estatuto Trabajadores
            ("Ley", "31/1995"): "BOE-A-1995-24292",   # LPRL - Prevención Riesgos Laborales

            # Leyes orgánicas
            ("Ley Orgánica", "6/1985"): "BOE-A-1985-12666",  # LOPJ - Poder Judicial
            ("Ley Orgánica", "2/1979"): "BOE-A-1979-23709",  # LOTC - Tribunal Constitucional
            ("Ley Orgánica", "1/1996"): "BOE-A-1996-1069",   # Protección Jurídica del Menor

            # Contratos
            ("Ley", "9/2017"): "BOE-A-2017-12902",    # LCSP - Contratos Sector Público

            # Régimen local
            ("Ley", "7/1985"): "BOE-A-1985-5392",     # LBRL - Bases Régimen Local

            # Reglamentos importantes
            ("Real Decreto", "203/2021"): "BOE-A-2021-5032",  # Actuación automatizada

            # Códigos y leyes históricas fundamentales
            ("Real Decreto", "24/7/1889"): "BOE-A-1889-4763",  # Código Civil
        }

        # Mapeo de siglas y nombres completos a BOE-IDs
        # Este mapeo se consulta ANTES que el mapeo por (tipo, numero)
        mapeo_siglas_nombres = {
            # Constitución Española
            "constitución española": "BOE-A-1978-31229",
            "constitución": "BOE-A-1978-31229",
            "ce": "BOE-A-1978-31229",

            # Código Civil
            "código civil": "BOE-A-1889-4763",
            "cc": "BOE-A-1889-4763",

            # Código de Comercio
            "código de comercio": "BOE-A-1885-6627",
            "ccom": "BOE-A-1885-6627",
            "cco": "BOE-A-1885-6627",

            # Ley de Enjuiciamiento Civil (actual y antigua)
            "lec": "BOE-A-2000-323",
            "ley de enjuiciamiento civil": "BOE-A-2000-323",
            "ley de enjuiciamiento civil de 1881": "BOE-A-1881-813",
            "ley 1/2000": "BOE-A-2000-323",

            # Ley de Jurisdicción Voluntaria
            "ljv": "BOE-A-2015-7391",
            "ley 15/2015": "BOE-A-2015-7391",
            "jurisdicción voluntaria": "BOE-A-2015-7391",

            # Ley Orgánica del Poder Judicial
            "lopj": "BOE-A-1985-12666",
            "ley orgánica del poder judicial": "BOE-A-1985-12666",
            "ley orgánica 6/1985": "BOE-A-1985-12666",

            # LPAC y LRJSP (ya están en mapeo_conocido pero agregamos siglas)
            "lpac": "BOE-A-2015-10565",
            "lrjsp": "BOE-A-2015-10566",

            # Jurisdicción Contencioso-Administrativa
            "ljca": "BOE-A-1998-16718",

            # Protección del Menor
            "ley orgánica 1/1996": "BOE-A-1996-1069",
        }

        # Normalizar tipo
        tipo_norm = tipo.lower().strip()
        if tipo_norm in ["rd", "real decreto"]:
            tipo_norm = "real decreto"

        # PRIMERO: Buscar en mapeo de siglas/nombres (más flexible)
        # Intentar con diferentes normalizaciones
        busquedas_siglas = [
            f"{tipo} {numero}".lower().strip(),  # "ley 39/2015"
            f"{tipo} {numero}/{año}".lower().strip(),  # "ley 39/2015"
            numero.lower().strip(),  # "39/2015"
        ]

        for busqueda in busquedas_siglas:
            if busqueda in mapeo_siglas_nombres:
                boe_id = mapeo_siglas_nombres[busqueda]
                if self._verificar_boe_id(boe_id):
                    logger.debug(f"✅ BOE-ID encontrado en mapeo de siglas: {boe_id}")
                    return boe_id

        # SEGUNDO: Buscar en mapeo conocido por (tipo, numero)
        key = (tipo.title(), numero)
        if key in mapeo_conocido:
            boe_id = mapeo_conocido[key]

            # Verificar que existe (con retry)
            if self._verificar_boe_id(boe_id):
                logger.debug(f"✅ BOE-ID encontrado en mapeo conocido: {boe_id}")
                return boe_id

        # TERCERO: Si no está en mapeos, buscar en la API del BOE
        logger.info(f"🔍 Buscando en API del BOE: {tipo} {numero}/{año}")
        return self._buscar_en_api_boe(tipo, numero, año)

    def _buscar_en_api_boe(self, tipo: str, numero: str, año: str) -> Optional[str]:
        """
        Búsqueda en API del BOE usando el parámetro query

        Según documentación oficial del BOE (APIconsolidada.pdf):
        El endpoint /datosabiertos/api/legislacion-consolidada SOPORTA búsquedas
        usando el parámetro 'query' con estructura JSON.

        Ejemplo:
        GET /datosabiertos/api/legislacion-consolidada?query={"query":{"query_string":{"query":"numero_oficial:39/2015"}}}

        Args:
            tipo: Tipo de norma (Ley, Real Decreto, etc.)
            numero: Número (ej: "39/2015" o "39")
            año: Año

        Returns:
            BOE-ID si se encuentra (formato: BOE-A-YYYY-NNNNN), o None
        """
        try:
            # Construir número completo en formato X/YYYY
            if '/' not in numero:
                numero_completo = f"{numero}/{año}"
            else:
                numero_completo = numero

            logger.info(f"   Buscando en API BOE: numero_oficial:{numero_completo}")

            # Construir query JSON según documentación oficial
            query_json = {
                "query": {
                    "query_string": {
                        "query": f"numero_oficial:{numero_completo}"
                    }
                }
            }

            # Hacer petición a la API
            url = self.api_base
            params = {
                'query': json.dumps(query_json),
                'limit': 5  # Primeros 5 resultados (por si hay múltiples versiones)
            }
            headers = {
                'Accept': 'application/xml'
            }

            response = requests.get(url, params=params, headers=headers, timeout=15)

            if response.status_code == 200:
                # Parsear respuesta XML para extraer identificador
                boe_id = self._parsear_resultado_busqueda(response.content, tipo)
                if boe_id:
                    logger.info(f"   ✅ BOE-ID encontrado en API: {boe_id}")
                    return boe_id
                else:
                    logger.warning(f"   ⚠️ API respondió OK pero no se encontró {tipo} {numero_completo}")
            else:
                logger.warning(f"   ⚠️ API respondió con status {response.status_code}")

        except requests.exceptions.RequestException as e:
            logger.warning(f"   ⚠️ Error de red al consultar API BOE: {e}")
        except Exception as e:
            logger.error(f"   ❌ Error inesperado en búsqueda API: {e}")

        return None

    def _parsear_resultado_busqueda(self, xml_content: bytes, tipo_buscado: str) -> Optional[str]:
        """
        Parsea la respuesta XML de la API de búsqueda y extrae el identificador (BOE-ID)

        Args:
            xml_content: Contenido XML de la respuesta
            tipo_buscado: Tipo de norma que se buscó (para filtrar si hay múltiples)

        Returns:
            BOE-ID (formato: BOE-A-YYYY-NNNNN) o None
        """
        try:
            from xml.etree import ElementTree as ET

            root = ET.fromstring(xml_content)

            # La estructura real es: <response><data><item>...
            # Buscar todos los items en la respuesta
            items = root.findall('.//item')

            if not items:
                logger.debug(f"   No se encontraron items en la respuesta XML")
                return None

            logger.debug(f"   Encontrados {len(items)} resultados en API")

            # Recorrer items y buscar el identificador
            for idx, item in enumerate(items):
                # Buscar el campo identificador
                identificador_elem = item.find('identificador')

                if identificador_elem is not None and identificador_elem.text:
                    boe_id = identificador_elem.text.strip()
                    logger.debug(f"   Item {idx + 1}: identificador encontrado = {boe_id}")

                    # Validar formato BOE-ID (BOE-A-YYYY-NNNNN)
                    if not re.match(r'BOE-[A-Z]-\d{4}-\d+', boe_id):
                        logger.debug(f"      ⚠️ Formato inválido, saltando...")
                        continue

                    # Buscar el título para verificar tipo
                    titulo_elem = item.find('titulo')
                    titulo = titulo_elem.text if titulo_elem is not None and titulo_elem.text else ""

                    if titulo:
                        logger.debug(f"      Título: {titulo[:80]}...")

                        # Verificar tipo (Ley, Real Decreto, etc.)
                        tipo_norm = tipo_buscado.lower().strip()
                        titulo_lower = titulo.lower()

                        logger.debug(f"      Comparando tipo_norm='{tipo_norm}' con titulo_lower='{titulo_lower[:50]}...'")

                        # Mapeo de tipos
                        if tipo_norm in ["ley", "ley orgánica"]:
                            if "ley" in titulo_lower:
                                logger.debug(f"      ✅ Match! Tipo Ley encontrado en título")
                                return boe_id
                            else:
                                logger.debug(f"      ❌ No match: 'ley' no está en título")
                        elif tipo_norm in ["real decreto", "rd", "real decreto legislativo", "rdl"]:
                            if "real decreto" in titulo_lower:
                                logger.debug(f"      ✅ Match! Tipo Real Decreto encontrado en título")
                                return boe_id
                            else:
                                logger.debug(f"      ❌ No match: 'real decreto' no está en título")
                        else:
                            # Si no podemos verificar tipo, devolver el primero
                            logger.debug(f"      ⚠️ Tipo '{tipo_norm}' no reconocido, devolviendo de todas formas")
                            return boe_id
                    else:
                        # Si no hay título, devolver el primero que tenga formato válido
                        logger.debug(f"      ⚠️ Sin título, devolviendo de todas formas")
                        return boe_id
                else:
                    logger.debug(f"   Item {idx + 1}: identificador NO encontrado o vacío")

            logger.warning(f"   No se encontró identificador válido que coincida con tipo '{tipo_buscado}' en {len(items)} items")
            return None

        except ET.ParseError as e:
            logger.error(f"   ❌ Error parseando XML: {e}")
            return None
        except Exception as e:
            logger.error(f"   ❌ Error inesperado parseando respuesta: {e}")
            import traceback
            logger.error(f"   Traceback: {traceback.format_exc()}")
            return None

    def agregar_desde_csv(self, csv_path: str):
        """
        Agrega leyes al mapeo desde el CSV de siglas

        Útil para pre-cargar las leyes más comunes de competitive exams

        Args:
            csv_path: Ruta al CSV de siglas legales
        """
        try:
            import csv

            logger.info(f"Cargando leyes desde CSV: {csv_path}")
            count = 0

            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Buscar leyes con número oficial en el CSV
                    # Ejemplo: "Ley 39/2015, de 1 de octubre..."
                    significado = row.get('SIGNIFICADO', '')

                    match = re.search(r'(Ley|Real Decreto)\s+(\d+/\d{4})', significado)
                    if match:
                        sigla = row.get('SIGLAS', '').strip()
                        logger.debug(f"   Encontrada: {sigla} -> {significado[:50]}...")
                        # Aquí podríamos buscar el BOE-ID y agregarlo
                        # Por ahora, solo lo registramos
                        count += 1

            logger.info(f"Se encontraron {count} leyes en el CSV")

        except Exception as e:
            logger.error(f"Error cargando CSV: {e}")

    def _verificar_boe_id(self, boe_id: str) -> bool:
        """
        Verifica que un BOE-ID existe consultando la API

        Args:
            boe_id: ID a verificar (ej: BOE-A-2015-10565)

        Returns:
            True si existe, False si no
        """
        url = f"{self.api_base}/id/{boe_id}"
        headers = {
            'Accept': 'application/xml'
        }

        for intento in range(self.max_retries):
            try:
                response = requests.get(url, headers=headers, timeout=10)

                if response.status_code == 200:
                    logger.debug(f"✅ BOE-ID verificado: {boe_id}")
                    return True
                elif response.status_code == 404:
                    logger.debug(f"❌ BOE-ID no encontrado: {boe_id}")
                    return False
                else:
                    logger.warning(f"⚠️ Status code inesperado: {response.status_code}")

            except requests.exceptions.RequestException as e:
                logger.warning(f"Error en intento {intento + 1}/{self.max_retries}: {e}")
                if intento < self.max_retries - 1:
                    time.sleep(self.retry_delay * (intento + 1))

        logger.error(f"❌ No se pudo verificar BOE-ID después de {self.max_retries} intentos")
        return False

    def buscar_multiple(self, referencias: List[str]) -> Dict[str, Optional[str]]:
        """
        Busca múltiples referencias en lote

        Args:
            referencias: Lista de referencias a buscar

        Returns:
            Dict {referencia: boe_id}
        """
        resultados = {}

        for ref in referencias:
            # Extraer año si está en la referencia
            match = re.search(r'/(\d{4})', ref)
            año = match.group(1) if match else None

            boe_id = self.buscar_ley(ref, año)
            resultados[ref] = boe_id

            # Rate limiting (evitar saturar la API)
            time.sleep(0.5)

        return resultados

    def agregar_mapeo_manual(self, referencia: str, boe_id: str):
        """
        Agrega un mapeo manual al caché

        Útil para leyes que no se encuentran automáticamente
        """
        ref_normalizada = self._normalizar_referencia(referencia)
        self.cache[ref_normalizada] = boe_id
        self._guardar_cache()
        logger.info(f"✅ Mapeo manual agregado: {referencia} → {boe_id}")


def buscar_boe_id(referencia: str, año: Optional[str] = None) -> Optional[str]:
    """
    Función helper para buscar un BOE-ID

    Args:
        referencia: Referencia legal (ej: "Ley 39/2015")
        año: Año opcional

    Returns:
        BOE-ID o None
    """
    searcher = BOESearcher()
    return searcher.buscar_ley(referencia, año)


# Ejemplo de uso
if __name__ == "__main__":
    import sys

    # Test básico
    searcher = BOESearcher()

    print("=" * 60)
    print("🔍 TEST DE BÚSQUEDA DE BOE-IDs")
    print("=" * 60)

    # Casos de prueba
    casos_prueba = [
        ("Ley 39/2015", "2015"),
        ("Ley 40/2015", "2015"),
        ("LPAC", "2015"),
        ("LEC", "2000"),
    ]

    for referencia, año in casos_prueba:
        print(f"\n🔎 Buscando: {referencia}")
        print("-" * 40)

        boe_id = searcher.buscar_ley(referencia, año)

        if boe_id:
            print(f"✅ Encontrado: {boe_id}")
            print(f"   URL: https://www.boe.es/buscar/act.php?id={boe_id}")
        else:
            print(f"❌ No encontrado")

    print("\n" + "=" * 60)
    print("✅ TEST COMPLETADO")
    print("=" * 60)
