# -*- coding: utf-8 -*-
"""
LexAgents - Sistema Multi-Agente de Extracción Legal
https://github.com/686f6c61/lexagents

Módulo: Siglas Loader
Carga y formatea las siglas legales del CSV para inyección en prompts

Author: 686f6c61
Version: 0.2.0
License: MIT
"""

import csv
import re
import logging
from pathlib import Path
from typing import List, Dict, Optional
from functools import lru_cache

logger = logging.getLogger(__name__)


class SiglasLoader:
    """Cargador de siglas legales desde CSV"""

    def __init__(self, csv_path: Optional[str] = None):
        """
        Inicializa el cargador

        Args:
            csv_path: Ruta al archivo CSV de siglas (opcional)
        """
        if csv_path is None:
            # Detectar ruta del proyecto automáticamente
            # Desde backend/modules/ -> ../../data/siglas/siglas_legales.csv
            current_file = Path(__file__)
            project_root = current_file.parent.parent.parent  # backend/modules -> backend -> project_root
            csv_path = project_root / "data" / "siglas" / "siglas_legales.csv"

        self.csv_path = Path(csv_path)

    @lru_cache(maxsize=1)
    def cargar_siglas_leyes(self) -> List[Dict[str, str]]:
        """
        Carga siglas que referencian leyes (con patrón Ley X/YYYY)

        NOTA: Este método mantiene compatibilidad con código existente.
        Para cargar TODAS las siglas (incluidas CE, CC, LEC), usa cargar_siglas_todas()

        Returns:
            Lista de dicts con {sigla, ley, descripcion}
        """
        siglas = []

        if not self.csv_path.exists():
            logger.warning(f"Archivo CSV no encontrado: {self.csv_path}")
            return siglas

        try:
            with open(self.csv_path, 'r', encoding='utf-8-sig') as f:  # utf-8-sig to handle BOM
                reader = csv.DictReader(f)

                for row in reader:
                    sigla = row.get('SIGLAS', '').strip()
                    significado = row.get('SIGNIFICADO', '').strip()

                    if not sigla or not significado:
                        continue

                    # Extraer referencias a leyes (Ley X/YYYY)
                    match = re.search(r'(Ley\s+(?:Orgánica\s+)?\d+/\d{4})', significado)

                    if match:
                        ley_ref = match.group(1)

                        siglas.append({
                            'sigla': sigla,
                            'ley': ley_ref,
                            'descripcion': significado
                        })

            logger.info(f"Cargadas {len(siglas)} siglas de leyes desde CSV")

        except Exception as e:
            logger.error(f"Error cargando siglas: {e}")

        return siglas

    @lru_cache(maxsize=1)
    def cargar_siglas_todas(self) -> List[Dict[str, str]]:
        """
        Carga TODAS las siglas legales del CSV, incluyendo las prioritarias

        Incluye:
        - Siglas con patrón Ley X/YYYY (ej: LPAC → Ley 39/2015)
        - Siglas SIN patrón pero críticas (ej: CE, CC, LEC, LJV, LOPJ)

        Returns:
            Lista de dicts con {sigla, descripcion, ley, boe_id, prioridad}
        """
        # Mapeo manual de siglas prioritarias a BOE-IDs
        # Estas son siglas que NO siguen el patrón Ley X/YYYY pero son fundamentales
        SIGLAS_PRIORITARIAS = {
            'CE': {
                'descripcion': 'Constitución Española',
                'boe_id': 'BOE-A-1978-31229',
                'ley': 'Constitución Española'
            },
            'CC': {
                'descripcion': 'Código Civil',
                'boe_id': 'BOE-A-1889-4763',
                'ley': 'Código Civil'
            },
            'CCom': {
                'descripcion': 'Código de Comercio',
                'boe_id': 'BOE-A-1885-6627',
                'ley': 'Código de Comercio'
            },
            'CCo': {
                'descripcion': 'Código de Comercio',
                'boe_id': 'BOE-A-1885-6627',
                'ley': 'Código de Comercio'
            },
            'LEC': {
                'descripcion': 'Ley 1/2000, de Enjuiciamiento Civil',
                'boe_id': 'BOE-A-2000-323',
                'ley': 'Ley 1/2000'
            },
            'LJV': {
                'descripcion': 'Ley 15/2015, de la Jurisdicción Voluntaria',
                'boe_id': 'BOE-A-2015-7391',
                'ley': 'Ley 15/2015'
            },
            'LOPJ': {
                'descripcion': 'Ley Orgánica 6/1985, del Poder Judicial',
                'boe_id': 'BOE-A-1985-12666',
                'ley': 'Ley Orgánica 6/1985'
            },
            'LJCA': {
                'descripcion': 'Ley 29/1998, de la Jurisdicción Contencioso-Administrativa',
                'boe_id': 'BOE-A-1998-16718',
                'ley': 'Ley 29/1998'
            },
            'LPAC': {
                'descripcion': 'Ley 39/2015, del Procedimiento Administrativo Común',
                'boe_id': 'BOE-A-2015-10565',
                'ley': 'Ley 39/2015'
            },
            'LRJSP': {
                'descripcion': 'Ley 40/2015, del Régimen Jurídico del Sector Público',
                'boe_id': 'BOE-A-2015-10566',
                'ley': 'Ley 40/2015'
            },
        }

        siglas = []

        # 1. Agregar siglas prioritarias primero
        for sigla, info in SIGLAS_PRIORITARIAS.items():
            siglas.append({
                'sigla': sigla,
                'descripcion': info['descripcion'],
                'ley': info['ley'],
                'boe_id': info.get('boe_id'),
                'prioridad': 'alta'
            })

        # 2. Cargar siglas del CSV (patrón Ley X/YYYY)
        if not self.csv_path.exists():
            logger.warning(f"Archivo CSV no encontrado: {self.csv_path}")
            return siglas

        try:
            with open(self.csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)

                for row in reader:
                    sigla = row.get('SIGLAS', '').strip()
                    significado = row.get('SIGNIFICADO', '').strip()

                    if not sigla or not significado:
                        continue

                    # Saltar si ya está en prioritarias
                    if sigla in SIGLAS_PRIORITARIAS:
                        continue

                    # Buscar patrón Ley X/YYYY
                    match = re.search(r'(Ley\s+(?:Orgánica\s+)?\d+/\d{4})', significado)

                    if match:
                        ley_ref = match.group(1)
                        siglas.append({
                            'sigla': sigla,
                            'descripcion': significado,
                            'ley': ley_ref,
                            'boe_id': None,
                            'prioridad': 'media'
                        })

            logger.info(f"Cargadas {len(siglas)} siglas totales desde CSV (incluye prioritarias)")

        except Exception as e:
            logger.error(f"Error cargando siglas: {e}")

        return siglas

    def formatear_para_prompt(self, max_siglas: int = 30) -> str:
        """
        Formatea las siglas más comunes para inyección en prompts

        Args:
            max_siglas: Número máximo de siglas a incluir (default: 30)

        Returns:
            String formateado para añadir al prompt
        """
        # CAMBIO: Ahora usa cargar_siglas_todas() para incluir CE, CC, LEC, etc.
        siglas = self.cargar_siglas_todas()

        if not siglas:
            return ""

        # Tomar las primeras N siglas (las prioritarias están primero)
        siglas_top = siglas[:max_siglas]

        texto = "\n**SIGLAS LEGALES CONOCIDAS:**\n"
        texto += "Si encuentras estas siglas en el texto, corresponden a las siguientes leyes:\n\n"

        # Primero mostrar las prioritarias (con BOE-ID)
        texto += "**📌 Siglas prioritarias:**\n"
        for s in siglas_top:
            if s.get('prioridad') == 'alta':
                # Formato: SIGLA → Ley completa (BOE-ID si existe)
                if s.get('boe_id'):
                    texto += f"- {s['sigla']} → {s['descripcion']} (BOE: {s['boe_id']})\n"
                else:
                    texto += f"- {s['sigla']} → {s['descripcion']}\n"

        # Luego las demás
        texto += "\n**Otras siglas comunes:**\n"
        for s in siglas_top:
            if s.get('prioridad') != 'alta':
                texto += f"- {s['sigla']} → {s['ley']}\n"

        texto += f"\n(Total: {len(siglas_top)} siglas principales de {len(siglas)} disponibles)\n"

        return texto

    def obtener_ley_por_sigla(self, sigla: str) -> Optional[str]:
        """
        Obtiene la referencia legal completa de una sigla

        Args:
            sigla: Sigla a buscar (ej: "LPAC", "LRJSP", "CE", "CC")

        Returns:
            Referencia a la ley (ej: "Ley 39/2015", "Constitución Española") o None
        """
        # CAMBIO: Ahora usa cargar_siglas_todas() para incluir CE, CC, LEC, etc.
        siglas = self.cargar_siglas_todas()

        sigla_norm = sigla.upper().strip()

        for s in siglas:
            if s['sigla'].upper() == sigla_norm:
                return s['ley']

        return None


# Instancia global para uso fácil
_siglas_loader = None


def get_siglas_loader() -> SiglasLoader:
    """
    Obtiene una instancia singleton del SiglasLoader

    Returns:
        Instancia de SiglasLoader
    """
    global _siglas_loader

    if _siglas_loader is None:
        _siglas_loader = SiglasLoader()

    return _siglas_loader


# Funciones helper para uso rápido
def cargar_siglas_para_prompt(max_siglas: int = 30) -> str:
    """
    Carga y formatea siglas para inyección en prompts

    Args:
        max_siglas: Número máximo de siglas

    Returns:
        String formateado para añadir al prompt
    """
    loader = get_siglas_loader()
    return loader.formatear_para_prompt(max_siglas)


def obtener_ley_por_sigla(sigla: str) -> Optional[str]:
    """
    Obtiene la referencia legal completa de una sigla

    Args:
        sigla: Sigla a buscar

    Returns:
        Referencia a la ley o None
    """
    loader = get_siglas_loader()
    return loader.obtener_ley_por_sigla(sigla)


# Ejemplo de uso
if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)

    print("=" * 70)
    print("TEST DE SIGLAS LOADER")
    print("=" * 70)

    loader = SiglasLoader()

    # Test 1: Cargar siglas
    print("\n📚 Cargando siglas de leyes...")
    siglas = loader.cargar_siglas_leyes()
    print(f"✅ Cargadas {len(siglas)} siglas")

    # Test 2: Mostrar primeras 10
    print("\n📌 Primeras 10 siglas:")
    for i, s in enumerate(siglas[:10], 1):
        print(f"   {i}. {s['sigla']:15} → {s['ley']}")

    # Test 3: Formatear para prompt
    print("\n📝 Formato para prompt (top 20):")
    print(loader.formatear_para_prompt(20))

    # Test 4: Buscar sigla específica
    print("\n🔍 Buscando siglas específicas:")
    for sigla_test in ['LPAC', 'LRJSP', 'LEC', 'EBEP']:
        ley = loader.obtener_ley_por_sigla(sigla_test)
        if ley:
            print(f"   ✅ {sigla_test} → {ley}")
        else:
            print(f"   ❌ {sigla_test} → No encontrada")

    print("\n" + "=" * 70)
