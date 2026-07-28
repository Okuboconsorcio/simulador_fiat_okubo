from __future__ import annotations

import unittest
from decimal import Decimal

from calculator import (
    MODO_REDUZIR_PARCELA,
    MODO_REDUZIR_PRAZO,
    SEGMENTO_AUTOMOVEL_MOTO_MOVEIS,
    TRATAMENTO_DEDUZIR_DO_CREDITO,
    TRATAMENTO_DIFERENCA_JA_ANTECIPADA,
    USOS_LANCE,
    calcular_simulacao,
    gerar_tabela_contemplacao,
)


def simulacao_base(**sobrescritas):
    parametros = {
        "credito": Decimal("120000.00"),
        "taxa_admin_percentual": Decimal("0.20"),
        "fundo_reserva_percentual": Decimal("0.03"),
        "lance_proprio": Decimal("50000.04"),
        "lance_embutido_percentual": Decimal("0.25"),
        "seguro_percentual": Decimal("0"),
        "seguro_mensal": Decimal("90.04"),
        "prazo": 80,
        "plano": "MAIS POR MENOS",
        "uso_lance": MODO_REDUZIR_PRAZO,
        "mes_contemplacao": 2,
        "percentual_mensal_fundo_comum": Decimal("0.008747"),
        "percentual_mensal_fundo_reserva": Decimal("0"),
        "percentual_mensal_taxa_administracao": Decimal("0.002500"),
        "tratamento_diferenca_mais_por_menos": TRATAMENTO_DIFERENCA_JA_ANTECIPADA,
    }
    parametros.update(sobrescritas)
    return calcular_simulacao(**parametros)


class RegrasRegulamentoFiatEmbraconTest(unittest.TestCase):
    def test_opcoes_visiveis_de_uso_do_lance_nao_incluem_diluido_rateado(self) -> None:
        self.assertEqual(USOS_LANCE, (MODO_REDUZIR_PRAZO, MODO_REDUZIR_PARCELA))

    def test_reduzir_prazo_mantem_parcela_regular_e_amortiza_da_ultima_para_primeira(self) -> None:
        resultado = simulacao_base(uso_lance=MODO_REDUZIR_PRAZO)
        primeira_linha = gerar_tabela_contemplacao(resultado)[0]

        self.assertEqual(resultado.parcela_ate_contemplacao_sem_seguro, Decimal("1349.64"))
        self.assertEqual(primeira_linha["Nova parcela"], Decimal("1439.68"))
        self.assertEqual(primeira_linha["Parcelas restantes apos lance"], Decimal("19"))
        self.assertEqual(primeira_linha["Parcelas abatidas"], Decimal("59"))
        self.assertEqual(primeira_linha["Mes previsto de quitacao"], 21)

    def test_reduzir_parcela_respeita_minimo_regulamentar_e_pode_encerrar_antes(self) -> None:
        resultado = simulacao_base(
            uso_lance=MODO_REDUZIR_PARCELA,
            segmento_bem=SEGMENTO_AUTOMOVEL_MOTO_MOVEIS,
        )
        primeira_linha = gerar_tabela_contemplacao(resultado)[0]

        self.assertEqual(primeira_linha["Nova parcela"], Decimal("1290.04"))
        self.assertEqual(primeira_linha["Parcelas restantes apos lance"], Decimal("22"))
        self.assertEqual(primeira_linha["Parcelas abatidas"], Decimal("56"))
        self.assertEqual(primeira_linha["Mes previsto de quitacao"], 24)

    def test_lance_embutido_e_diferenca_do_mais_por_menos_sao_deducoes_separadas(self) -> None:
        resultado = simulacao_base(
            tratamento_diferenca_mais_por_menos=TRATAMENTO_DEDUZIR_DO_CREDITO,
        )

        self.assertEqual(resultado.lance_embutido, Decimal("30000.00"))
        self.assertEqual(resultado.diferenca_deduzida_credito, Decimal("30000.00"))
        self.assertEqual(resultado.credito_liquido, Decimal("60000.00"))


if __name__ == "__main__":
    unittest.main()
