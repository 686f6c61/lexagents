# -*- coding: utf-8 -*-
"""
LexAgents - Sistema Multi-Agente de Extracción Legal
https://github.com/686f6c61/lexagents

Agente 3: Validador contra BOE
Valida referencias legales contra la base de datos del BOE:
- Busca BOE-IDs para leyes
- Verifica existencia de normativa
- Valida artículos (básico)

Author: 686f6c61
Version: 0.2.0
License: MIT
"""

import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
import sys

# Manejar imports de manera flexible
try:
    from .base_agent import BaseAgent
    from ..modules.boe_searcher import BOESearcher
    from ..modules.boe_downloader import BOEDownloader
except (ImportError, ValueError):
    # Si falla el import relativo, usar absoluto
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from agents.base_agent import BaseAgent
    from modules.boe_searcher import BOESearcher
    from modules.boe_downloader import BOEDownloader

logger = logging.getLogger(__name__)


class ValidatorAgent(BaseAgent):
    """
    Agente validador de referencias legales contra el BOE

    Características:
    - Busca BOE-IDs para cada referencia
    - Verifica existencia en el BOE
    - Valida formato de artículos
    - Marca confianza de validación
    """

    def __init__(self, api_key: str = None, cache_dir: str = None, verificar_articulos: bool = True):
        """
        Inicializa el Agente Validador

        Args:
            api_key: API key de Gemini (opcional, para validaciones complejas)
            cache_dir: Directorio de caché para BOE searcher
            verificar_articulos: Si verificar existencia real de artículos en BOE (default: True)
        """
        super().__init__(
            nombre="Agente3-Validador",
            modelo="gemini-2.0-flash-exp",
            temperatura=0.1,  # Muy conservador para validación
            api_key=api_key
        )

        # Inicializar directorios por defecto si no se especifican
        if cache_dir is None:
            base_path = Path(__file__).parent.parent.parent
            cache_dir = str(base_path / "data" / "cache")

        self.boe_searcher = BOESearcher(cache_dir=cache_dir)

        # Inicializar BOE Downloader para verificación de artículos
        self.verificar_articulos = verificar_articulos
        if verificar_articulos:
            boe_html_cache = str(Path(cache_dir) / "boe_html")
            self.boe_downloader = BOEDownloader(cache_dir=boe_html_cache)
            logger.info(f"✅ {self.nombre} inicializado con BOE Searcher + BOE Downloader (verificación de artículos)")
        else:
            self.boe_downloader = None
            logger.info(f"✅ {self.nombre} inicializado con BOE Searcher (sin verificación de artículos)")

    def procesar(self, entrada: Dict[str, Any]) -> Dict[str, Any]:
        """
        Procesa y valida una lista de referencias

        Args:
            entrada: Dict con:
                - 'referencias': List[Dict] - Referencias a validar

        Returns:
            Dict con:
                - 'referencias_validadas': List[Dict]
                - 'total': int
                - 'validadas': int
                - 'no_validadas': int
                - 'agente': str
        """
        referencias = entrada.get('referencias', [])

        logger.info(f"[{self.nombre}] Validando {len(referencias)} referencias")

        referencias_validadas = []
        validadas_count = 0
        no_validadas_count = 0

        for ref in referencias:
            ref_validada = self._validar_referencia(ref)
            referencias_validadas.append(ref_validada)

            if ref_validada.get('_validada'):
                validadas_count += 1
            else:
                no_validadas_count += 1

        logger.info(
            f"[{self.nombre}] Validadas: {validadas_count}/{len(referencias)} "
            f"({validadas_count/len(referencias)*100:.1f}%)"
        )

        return {
            'referencias_validadas': referencias_validadas,
            'total': len(referencias_validadas),
            'validadas': validadas_count,
            'no_validadas': no_validadas_count,
            'tasa_validacion': validadas_count / len(referencias) if referencias else 0,
            'agente': self.nombre
        }

    def _validar_referencia(self, referencia: Dict) -> Dict:
        """
        Valida una referencia individual

        Args:
            referencia: Referencia a validar

        Returns:
            Referencia con metadata de validación
        """
        ref_validada = referencia.copy()

        # Inicializar metadata de validación
        if '_metadata_validacion' not in ref_validada:
            ref_validada['_metadata_validacion'] = {}

        validacion = ref_validada['_metadata_validacion']

        # 1. Extraer información de la ley
        ley_info = self._extraer_info_ley(referencia)

        if not ley_info:
            validacion['validada'] = False
            validacion['motivo'] = 'No se pudo extraer información de ley'
            ref_validada['_validada'] = False
            return ref_validada

        # 2. Buscar BOE-ID
        boe_id = self._buscar_boe_id(ley_info)

        if boe_id:
            validacion['validada'] = True
            validacion['boe_id'] = boe_id
            validacion['boe_url'] = f"https://www.boe.es/buscar/act.php?id={boe_id}"
            ref_validada['boe_id'] = boe_id
            ref_validada['_validada'] = True

            logger.debug(f"✅ Validada: {ley_info.get('referencia')} → {boe_id}")

        else:
            validacion['validada'] = False
            validacion['motivo'] = 'No se encontró BOE-ID'
            ref_validada['_validada'] = False

            logger.debug(f"❌ No validada: {ley_info.get('referencia')}")

        # 3. Validar artículo (si existe)
        if ref_validada.get('articulo'):
            articulo_valido = self._validar_formato_articulo(ref_validada['articulo'])
            validacion['articulo_formato_valido'] = articulo_valido

            # 4. Verificar artículo en BOE (si tenemos BOE-ID y verificación habilitada)
            if boe_id and self.verificar_articulos:
                verificacion_boe = self._verificar_articulo_en_boe(boe_id, ref_validada['articulo'])

                # Agregar resultados de verificación BOE
                validacion['articulo_verificado_boe'] = verificacion_boe['verificado_boe']
                validacion['articulo_existe_boe'] = verificacion_boe['existe']

                if verificacion_boe['existe']:
                    validacion['articulo_texto_oficial'] = verificacion_boe['texto_oficial']
                    ref_validada['texto_oficial_boe'] = verificacion_boe['texto_oficial']
                    logger.debug(f"   ✅ Artículo {ref_validada['articulo']} EXISTE en BOE")
                elif verificacion_boe['existe'] is False:
                    # CRÍTICO: El artículo NO existe en el BOE oficial
                    ref_validada['_validada'] = False
                    validacion['validada'] = False
                    validacion['motivo'] = f"Artículo {ref_validada['articulo']} NO existe en el BOE oficial"
                    logger.warning(f"   ⚠️ ALUCINACIÓN DETECTADA: Artículo {ref_validada['articulo']} NO existe en {boe_id}")

                if verificacion_boe.get('error'):
                    validacion['error_verificacion'] = verificacion_boe['error']

        return ref_validada

    def _extraer_info_ley(self, referencia: Dict) -> Optional[Dict]:
        """
        Extrae información estructurada de una referencia

        Args:
            referencia: Referencia a procesar

        Returns:
            Dict con info de la ley o None
        """
        # Prioridad a ley normalizada si existe
        ley = referencia.get('ley_normalizada') or referencia.get('ley')

        if not ley:
            # Intentar extraer del texto completo
            texto = referencia.get('texto_completo', '')
            ley = self._extraer_ley_de_texto(texto)

        if not ley:
            return None

        # Extraer año si está presente
        import re
        match = re.search(r'(\d{4})', ley)
        año = match.group(1) if match else None

        # Incluir título completo si existe (agregado por TitleResolverAgent)
        titulo_completo = referencia.get('ley_titulo_completo')

        return {
            'referencia': ley,
            'año': año,
            'tipo': referencia.get('tipo', 'desconocido'),
            'titulo_completo': titulo_completo  # Para mejorar búsqueda en BOE
        }

    def _extraer_ley_de_texto(self, texto: str) -> Optional[str]:
        """
        Intenta extraer una referencia de ley de un texto

        Args:
            texto: Texto a procesar

        Returns:
            Referencia extraída o None
        """
        import re

        # Patrones de leyes
        patrones = [
            r'Ley\s+(?:Orgánica\s+)?(\d+/\d{4})',
            r'Real\s+Decreto\s+(?:Ley\s+)?(\d+/\d{4})',
            r'Constitución\s+Española',
        ]

        for patron in patrones:
            match = re.search(patron, texto, re.IGNORECASE)
            if match:
                return match.group(0)

        return None

    def _buscar_boe_id(self, ley_info: Dict) -> Optional[str]:
        """
        Busca el BOE-ID de una ley usando BOESearcher

        Args:
            ley_info: Info de la ley

        Returns:
            BOE-ID o None
        """
        referencia = ley_info['referencia']
        año = ley_info.get('año')
        titulo_completo = ley_info.get('titulo_completo')

        try:
            # Pasar título completo para mejorar precisión de búsqueda (FASE 5)
            boe_id = self.boe_searcher.buscar_ley(
                referencia=referencia,
                año=año,
                titulo_completo=titulo_completo
            )
            return boe_id
        except Exception as e:
            logger.error(f"Error buscando BOE-ID para {referencia}: {e}")
            return None

    def _validar_formato_articulo(self, articulo: str) -> bool:
        """
        Valida que el formato de un artículo sea correcto

        Args:
            articulo: Número de artículo (ej: "23", "23.2", "23.2.b")

        Returns:
            True si el formato es válido, False si no
        """
        import re

        # Patrón: dígitos opcionalmente seguidos de .dígitos y opcionalmente .letra
        patron = r'^\d+(?:\.\d+)?(?:\.[a-z])?$'

        return bool(re.match(patron, str(articulo)))

    def _verificar_articulo_en_boe(self, boe_id: str, articulo: str) -> Dict[str, Any]:
        """
        Verifica que un artículo existe realmente en el BOE oficial

        Args:
            boe_id: ID del BOE (ej: BOE-A-2015-10565)
            articulo: Número de artículo a verificar (ej: "39", "23.2")

        Returns:
            Dict con:
                - existe: bool - Si el artículo existe
                - texto_oficial: str - Texto del artículo (si existe)
                - verificado_boe: bool - Si se verificó contra BOE
                - error: str - Mensaje de error (si falló)
        """
        if not self.verificar_articulos or not self.boe_downloader:
            return {
                'existe': None,
                'texto_oficial': None,
                'verificado_boe': False,
                'error': 'Verificación de artículos deshabilitada'
            }

        try:
            # Descargar ley del BOE (usa caché si está disponible)
            existe = self.boe_downloader.verificar_articulo_existe(boe_id, articulo)

            if existe:
                # Obtener texto oficial del artículo
                texto_oficial = self.boe_downloader.obtener_texto_articulo(boe_id, articulo)

                return {
                    'existe': True,
                    'texto_oficial': texto_oficial,
                    'verificado_boe': True,
                    'error': None
                }
            else:
                return {
                    'existe': False,
                    'texto_oficial': None,
                    'verificado_boe': True,
                    'error': f'Artículo {articulo} NO existe en {boe_id}'
                }

        except Exception as e:
            logger.error(f"Error verificando artículo {articulo} en {boe_id}: {e}")
            return {
                'existe': None,
                'texto_oficial': None,
                'verificado_boe': False,
                'error': str(e)
            }

    def validar_lote(self, referencias: List[Dict]) -> List[Dict]:
        """
        Valida un lote de referencias de manera eficiente

        Args:
            referencias: Lista de referencias

        Returns:
            Lista de referencias validadas
        """
        return self.procesar({'referencias': referencias})['referencias_validadas']

    def obtener_estadisticas_validacion(self, referencias: List[Dict]) -> Dict[str, Any]:
        """
        Obtiene estadísticas de validación de un conjunto de referencias

        Args:
            referencias: Referencias a analizar

        Returns:
            Dict con estadísticas
        """
        validadas = sum(1 for ref in referencias if ref.get('_validada'))
        no_validadas = len(referencias) - validadas

        con_boe_id = sum(1 for ref in referencias if ref.get('boe_id'))
        con_articulo_valido = sum(
            1 for ref in referencias
            if ref.get('_metadata_validacion', {}).get('articulo_formato_valido')
        )

        return {
            'total': len(referencias),
            'validadas': validadas,
            'no_validadas': no_validadas,
            'tasa_validacion': validadas / len(referencias) if referencias else 0,
            'con_boe_id': con_boe_id,
            'con_articulo_valido': con_articulo_valido
        }


# Función helper
def validar_referencias(
    referencias: List[Dict],
    cache_dir: str = None
) -> List[Dict]:
    """
    Función helper para validar referencias

    Args:
        referencias: Lista de referencias a validar
        cache_dir: Directorio de caché (opcional)

    Returns:
        Lista de referencias validadas
    """
    agente = ValidatorAgent(cache_dir=cache_dir)
    return agente.validar_lote(referencias)


# Ejemplo de uso
if __name__ == "__main__":
    from dotenv import load_dotenv
    import os

    # Cargar .env
    env_path = Path(__file__).parent.parent / ".env"
    load_dotenv(env_path)

    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s: %(message)s'
    )

    print("=" * 60)
    print("🧪 TEST DEL AGENTE VALIDADOR")
    print("=" * 60)

    # Referencias de prueba
    referencias_prueba = [
        {
            'texto_completo': 'Ley 39/2015',
            'tipo': 'ley',
            'ley': 'Ley 39/2015',
            'ley_normalizada': 'Ley 39/2015'
        },
        {
            'texto_completo': 'Ley 40/2015',
            'tipo': 'ley',
            'ley': 'Ley 40/2015',
            'ley_normalizada': 'Ley 40/2015'
        },
        {
            'texto_completo': 'Artículo 24 de la Constitución Española',
            'tipo': 'articulo',
            'ley': 'Constitución Española',
            'articulo': '24'
        },
        {
            'texto_completo': 'Ley 999/9999',  # No existe
            'tipo': 'ley',
            'ley': 'Ley 999/9999'
        }
    ]

    # Validar
    agente = ValidatorAgent()
    resultado = agente.procesar({'referencias': referencias_prueba})

    print(f"\n✅ Total: {resultado['total']}")
    print(f"✅ Validadas: {resultado['validadas']}")
    print(f"❌ No validadas: {resultado['no_validadas']}")
    print(f"📊 Tasa de validación: {resultado['tasa_validacion']*100:.1f}%")

    print(f"\n📋 Referencias Validadas:")
    print("-" * 60)

    for i, ref in enumerate(resultado['referencias_validadas'], 1):
        print(f"\n{i}. {ref.get('texto_completo')}")

        if ref.get('_validada'):
            print(f"   └─ ✅ VALIDADA")
            print(f"   └─ BOE-ID: {ref.get('boe_id')}")
            if ref.get('_metadata_validacion', {}).get('boe_url'):
                print(f"   └─ URL: {ref['_metadata_validacion']['boe_url']}")
        else:
            print(f"   └─ ❌ NO VALIDADA")
            motivo = ref.get('_metadata_validacion', {}).get('motivo', 'Desconocido')
            print(f"   └─ Motivo: {motivo}")

    # Estadísticas
    stats = agente.obtener_estadisticas_validacion(resultado['referencias_validadas'])
    print(f"\n📊 Estadísticas:")
    print(f"   - Total referencias: {stats['total']}")
    print(f"   - Con BOE-ID: {stats['con_boe_id']}")
    print(f"   - Con artículo válido: {stats['con_articulo_valido']}")

    print("\n" + "=" * 60)
    print("✅ TEST COMPLETADO")
    print("=" * 60)
