# -*- coding: utf-8 -*-
"""
LexAgents - Sistema Multi-Agente de Extracción Legal
https://github.com/686f6c61/lexagents

Módulo Comparador de Referencias
Compara referencias extraídas por diferentes agentes:
- Detecta consenso entre agentes
- Identifica discrepancias
- Genera métricas de confianza

Author: 686f6c61
Version: 0.2.0
License: MIT
"""

import logging
from typing import Dict, List, Any, Set
from collections import Counter

logger = logging.getLogger(__name__)


class ComparadorReferencias:
    """
    Comparador de referencias entre múltiples agentes

    Analiza:
    - Referencias encontradas por todos los agentes (consenso total)
    - Referencias encontradas por algunos agentes (consenso parcial)
    - Referencias únicas de cada agente
    - Métricas de acuerdo
    """

    def __init__(self):
        """Inicializa el comparador"""
        pass

    def comparar(self, referencias_por_agente: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """
        Compara referencias de múltiples agentes

        Args:
            referencias_por_agente: Dict {nombre_agente: [referencias]}

        Returns:
            Dict con análisis comparativo
        """
        logger.info("🔍 Comparando referencias entre agentes")

        # Normalizar keys de referencias para comparación
        refs_normalizadas = self._normalizar_para_comparacion(referencias_por_agente)

        # Analizar consenso
        consenso = self._analizar_consenso(refs_normalizadas)

        # Identificar únicas de cada agente
        unicas = self._identificar_unicas(refs_normalizadas)

        # Calcular métricas
        metricas = self._calcular_metricas(refs_normalizadas, consenso)

        # Generar informe
        informe = {
            'total_agentes': len(referencias_por_agente),
            'consenso_total': consenso['total'],
            'consenso_parcial': consenso['parcial'],
            'unicas_por_agente': unicas,
            'metricas': metricas,
            'referencias_por_agente': {
                agente: len(refs)
                for agente, refs in referencias_por_agente.items()
            }
        }

        logger.info(f"✅ Comparación completada:")
        logger.info(f"   - Consenso total: {consenso['total']} referencias")
        logger.info(f"   - Consenso parcial: {consenso['parcial']} referencias")
        logger.info(f"   - Acuerdo promedio: {metricas['acuerdo_promedio']:.1f}%")

        return informe

    def _normalizar_para_comparacion(
        self,
        referencias_por_agente: Dict[str, List[Dict]]
    ) -> Dict[str, Set[str]]:
        """
        Normaliza referencias para comparación

        Convierte cada referencia a una clave normalizada
        """
        refs_normalizadas = {}

        for agente, referencias in referencias_por_agente.items():
            keys = set()

            for ref in referencias:
                key = self._generar_key_comparacion(ref)
                keys.add(key)

            refs_normalizadas[agente] = keys

        return refs_normalizadas

    def _generar_key_comparacion(self, referencia: Dict) -> str:
        """
        Genera una clave única para comparar referencias

        Args:
            referencia: Referencia a procesar

        Returns:
            String clave normalizada
        """
        # Priorizar ley normalizada o BOE-ID
        if referencia.get('boe_id'):
            return f"BOE:{referencia['boe_id']}"

        ley = referencia.get('ley_normalizada') or referencia.get('ley') or ''
        articulo = referencia.get('articulo') or ''

        # Normalizar a minúsculas y quitar espacios
        ley_norm = ley.lower().strip().replace(' ', '')
        articulo_norm = articulo.lower().strip()

        if articulo_norm:
            return f"{ley_norm}:art{articulo_norm}"
        else:
            return ley_norm

    def _analizar_consenso(
        self,
        refs_normalizadas: Dict[str, Set[str]]
    ) -> Dict[str, Any]:
        """
        Analiza el consenso entre agentes

        Returns:
            Dict con referencias de consenso total y parcial
        """
        todas_las_refs = set()
        for refs in refs_normalizadas.values():
            todas_las_refs.update(refs)

        # Contar en cuántos agentes aparece cada referencia
        contador = Counter()
        for refs in refs_normalizadas.values():
            for ref in refs:
                contador[ref] += 1

        total_agentes = len(refs_normalizadas)

        # Consenso total: todas las agentes están de acuerdo
        consenso_total = [
            ref for ref, count in contador.items()
            if count == total_agentes
        ]

        # Consenso parcial: al menos 2 agentes pero no todos
        consenso_parcial = [
            ref for ref, count in contador.items()
            if 2 <= count < total_agentes
        ]

        return {
            'total': len(consenso_total),
            'parcial': len(consenso_parcial),
            'referencias_consenso_total': consenso_total,
            'referencias_consenso_parcial': consenso_parcial,
            'contador': contador
        }

    def _identificar_unicas(
        self,
        refs_normalizadas: Dict[str, Set[str]]
    ) -> Dict[str, int]:
        """
        Identifica referencias únicas de cada agente

        Returns:
            Dict {agente: num_referencias_unicas}
        """
        unicas = {}

        for agente, refs_agente in refs_normalizadas.items():
            # Referencias de otros agentes
            refs_otros = set()
            for otro_agente, refs_otro in refs_normalizadas.items():
                if otro_agente != agente:
                    refs_otros.update(refs_otro)

            # Referencias únicas de este agente
            unicas_agente = refs_agente - refs_otros
            unicas[agente] = len(unicas_agente)

        return unicas

    def _calcular_metricas(
        self,
        refs_normalizadas: Dict[str, Set[str]],
        consenso: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calcula métricas de comparación

        Returns:
            Dict con métricas
        """
        total_agentes = len(refs_normalizadas)

        if total_agentes == 0:
            return {}

        # Acuerdo promedio (% de referencias con consenso)
        total_referencias_unicas = len(set().union(*refs_normalizadas.values()))

        if total_referencias_unicas > 0:
            acuerdo_promedio = (
                (consenso['total'] + consenso['parcial']) /
                total_referencias_unicas * 100
            )
        else:
            acuerdo_promedio = 0

        # Cobertura de cada agente vs consenso total
        cobertura = {}
        if consenso['referencias_consenso_total']:
            for agente, refs in refs_normalizadas.items():
                refs_consenso_encontradas = len(
                    refs & set(consenso['referencias_consenso_total'])
                )
                cobertura[agente] = (
                    refs_consenso_encontradas /
                    len(consenso['referencias_consenso_total']) * 100
                )

        return {
            'acuerdo_promedio': acuerdo_promedio,
            'total_referencias_unicas': total_referencias_unicas,
            'cobertura_consenso': cobertura
        }

    def generar_informe_detallado(
        self,
        referencias_por_agente: Dict[str, List[Dict]]
    ) -> str:
        """
        Genera un informe textual detallado de la comparación

        Args:
            referencias_por_agente: Referencias por agente

        Returns:
            String con informe formateado
        """
        comparacion = self.comparar(referencias_por_agente)

        informe = []
        informe.append("=" * 60)
        informe.append("📊 INFORME DE COMPARACIÓN DE AGENTES")
        informe.append("=" * 60)

        informe.append(f"\n🤖 Agentes analizados: {comparacion['total_agentes']}")

        informe.append(f"\n📋 Referencias por agente:")
        for agente, total in comparacion['referencias_por_agente'].items():
            informe.append(f"   - {agente}: {total} referencias")

        informe.append(f"\n✅ Consenso Total: {comparacion['consenso_total']} referencias")
        informe.append(f"⚠️  Consenso Parcial: {comparacion['consenso_parcial']} referencias")

        informe.append(f"\n🎯 Úncias por agente:")
        for agente, unicas in comparacion['unicas_por_agente'].items():
            informe.append(f"   - {agente}: {unicas} únicas")

        metricas = comparacion['metricas']
        informe.append(f"\n📊 Métricas:")
        informe.append(f"   - Total referencias únicas: {metricas['total_referencias_unicas']}")
        informe.append(f"   - Acuerdo promedio: {metricas['acuerdo_promedio']:.1f}%")

        if metricas.get('cobertura_consenso'):
            informe.append(f"\n📈 Cobertura del consenso:")
            for agente, cobertura in metricas['cobertura_consenso'].items():
                informe.append(f"   - {agente}: {cobertura:.1f}%")

        informe.append("\n" + "=" * 60)

        return "\n".join(informe)


# Función helper
def comparar_referencias(
    referencias_por_agente: Dict[str, List[Dict]]
) -> Dict[str, Any]:
    """
    Función helper para comparar referencias

    Args:
        referencias_por_agente: Dict {agente: [referencias]}

    Returns:
        Dict con análisis comparativo
    """
    comparador = ComparadorReferencias()
    return comparador.comparar(referencias_por_agente)


# Ejemplo de uso
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s'
    )

    print("=" * 60)
    print("🧪 TEST DEL COMPARADOR")
    print("=" * 60)

    # Referencias de prueba
    refs_agente_a = [
        {'ley': 'Ley 39/2015', 'texto_completo': 'LPAC'},
        {'ley': 'Ley 40/2015', 'texto_completo': 'LRJSP'},
        {'ley': 'Constitución Española', 'articulo': '24'},
    ]

    refs_agente_b = [
        {'ley': 'Ley 39/2015', 'texto_completo': 'Ley 39/2015'},  # Misma
        {'ley': 'Ley 40/2015', 'texto_completo': 'Ley 40/2015'},  # Misma
        {'ley': 'Ley 1/2000', 'texto_completo': 'LEC'},  # Única de B
    ]

    referencias_por_agente = {
        'Agente A': refs_agente_a,
        'Agente B': refs_agente_b
    }

    # Comparar
    comparador = ComparadorReferencias()
    informe = comparador.generar_informe_detallado(referencias_por_agente)

    print(informe)

    print("\n✅ TEST COMPLETADO")
