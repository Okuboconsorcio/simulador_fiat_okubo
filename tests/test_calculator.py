from __future__ import annotations

import unittest
from decimal import Decimal

from calculator import MODO_DILUIDO_RATEADO, calcular_diluido_rateado, calcular_simulacao, gerar_tabela_contemplacao


class CalculoDiluidoRateadoTest(unittest.TestCase):
    def test_calcula_pos_contemplacao_diluido_rateado_com_percentual_do_plano(self) -> None:
        resultado = calcular_diluido_rateado(
            credito=Decimal("120000.00"),
            taxa_administracao=Decimal("0.20"),
            fundo_reserva=Decimal("0.03"),
            lance_proprio=Decimal("50000.04"),
            lance_embutido=Decimal("30000.00"),
            seguro_mensal=Decimal("90.04"),
            parcelas_pagas_sem_seguro=[Decimal("1458.72"), Decimal("1349.64")],
            percentual_mensal_pos_contemplacao_sem_seguro=Decimal("0.011247"),
        )

        self.assertEqual(resultado.saldo_contratual_sem_seguro, Decimal("147600.00"))
        self.assertEqual(resultado.total_amortizado, Decimal("82808.40"))
        self.assertEqual(resultado.saldo_remanescente_sem_seguro, Decimal("64791.60"))
        self.assertEqual(resultado.parcela_sem_seguro, Decimal("1349.64"))
        self.assertEqual(resultado.nova_parcela, Decimal("1439.68"))
        self.assertEqual(resultado.quantidade_parcelas_restantes, 48)
        self.assertEqual(resultado.saldo_seguro_futuro, Decimal("4321.92"))
        self.assertEqual(resultado.saldo_total_futuro, Decimal("69113.52"))
        self.assertEqual(resultado.diferenca_residual, Decimal("8.88"))
        self.assertEqual(resultado.ultima_parcela_com_seguro, Decimal("1448.56"))

    def test_tabela_usa_modo_diluido_rateado_sem_dividir_por_parcelas_originais(self) -> None:
        resultado = calcular_simulacao(
            credito=Decimal("120000.00"),
            taxa_admin_percentual=Decimal("0.20"),
            fundo_reserva_percentual=Decimal("0.03"),
            lance_proprio=Decimal("50000.04"),
            lance_embutido_percentual=Decimal("0.25"),
            seguro_percentual=Decimal("0"),
            seguro_mensal=Decimal("90.04"),
            prazo=80,
            plano="MAIS POR MENOS",
            uso_lance=MODO_DILUIDO_RATEADO,
            mes_contemplacao=2,
            parcelas_pagas_sem_seguro=[Decimal("1458.72"), Decimal("1349.64")],
            percentual_mensal_pos_contemplacao_sem_seguro=Decimal("0.011247"),
        )

        primeira_linha = gerar_tabela_contemplacao(resultado)[0]

        self.assertEqual(primeira_linha["Parcelas restantes apos lance"], Decimal("48"))
        self.assertEqual(primeira_linha["Nova parcela"], Decimal("1439.68"))
        self.assertEqual(primeira_linha["Saldo apos lance"], Decimal("69113.52"))


if __name__ == "__main__":
    unittest.main()
