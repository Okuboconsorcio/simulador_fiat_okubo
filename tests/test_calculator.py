"""Testes do simulador validados contra documentos reais da Embracon.

Fontes:
- Tabela comercial Leves (FTA) e Pesados (TSA 700 mil);
- Regulamento Fiat (Cláusulas 3.3, 3.4 e 8ª);
- Extratos reais de cotas contempladas (crédito 120.000, plano Mais por
  Menos 25, prazo 80, tabela Leves), usados como caso "Diluído mantendo
  prazo" (contemplação mês 6, lance embutido 25%) e caso "Diluído com piso"
  (contemplação mês 1, lance próprio 50.000,04 + embutido 25%).

A Embracon arredonda cada componente (FC/FR/TA) separadamente, o que gera
ruído de centavos; por isso os valores em reais usam tolerância de R$ 0,25.
"""

from __future__ import annotations

import unittest
from decimal import Decimal

from calculator import (
    CONFIGURACOES_TABELAS,
    TRATAMENTO_DEDUZIR_DO_CREDITO,
    TRATAMENTO_PAGAR_RECURSOS_PROPRIOS,
    TRATAMENTO_RENEGOCIAR_NO_SALDO,
    calcular_reduzir_parcela,
    calcular_reduzir_prazo,
    calcular_simulacao,
    gerar_tabela_contemplacao,
    prazos_disponiveis,
    saldo_percentual_apos_lance,
)

TOLERANCIA_REAIS = Decimal("0.25")


def caso_thiago(**sobrescritas):
    """Crédito 120.000, Leves, MpM 80, contemplação mês 6, embutido 25%."""
    parametros = dict(
        credito=Decimal("120000"),
        lance_proprio=Decimal("0"),
        lance_embutido_percentual=Decimal("0.25"),
        prazo=80,
        plano="MAIS POR MENOS",
        uso_lance="REDUZIR_PARCELA",
        mes_contemplacao=6,
        tabela="LEVES",
        tratamento_diferenca_mais_por_menos=TRATAMENTO_RENEGOCIAR_NO_SALDO,
    )
    parametros.update(sobrescritas)
    return calcular_simulacao(**parametros)


def caso_maykel(**sobrescritas):
    """Crédito 120.000, Leves, MpM 80, contemplação mês 1, lance 66,67%."""
    return caso_thiago(
        lance_proprio=Decimal("50000.04"),
        mes_contemplacao=1,
        **sobrescritas,
    )


class TestParcelasTabelaComercial(unittest.TestCase):
    """Valores de parcela publicados nas tabelas impressas da Embracon."""

    def test_parcela_normal_leves_80_meses(self):
        # Tabela Leves: crédito 180.000 x (100 + 3 + 20)/80 = 1,5375% = 2.767,50
        resultado = caso_thiago(credito=Decimal("180000"), plano="NORMAL")
        self.assertEqual(resultado.parcela_normal_sem_seguro, Decimal("2767.50"))

    def test_parcela_mais_por_menos_leves_80_meses(self):
        # Tabela Leves MpM: 180.000 x (0,75 x 103 + 20)/80 = 1,215625% = 2.188,13
        resultado = caso_thiago(credito=Decimal("180000"))
        self.assertLessEqual(
            abs(resultado.parcela_mais_por_menos_sem_seguro - Decimal("2188.13")),
            Decimal("0.01"),
        )

    def test_seguro_leves_120000(self):
        # Extratos: seguro 90,04 para crédito 120.000 (0,075030%/mês)
        resultado = caso_thiago()
        self.assertEqual(resultado.seguro_mensal, Decimal("90.04"))

    def test_parcela_normal_pesados_100_meses(self):
        # Tabela Pesados TSA: 700.000 x (100 + 3 + 13)/100 = 1,16% = 8.120,00
        resultado = calcular_simulacao(
            credito=Decimal("700000"),
            lance_proprio=Decimal("0"),
            lance_embutido_percentual=Decimal("0"),
            prazo=100,
            plano="NORMAL",
            uso_lance="REDUZIR_PRAZO",
            mes_contemplacao=1,
            tabela="PESADOS",
        )
        self.assertEqual(resultado.parcela_normal_sem_seguro, Decimal("8120.00"))
        # Seguro pesados: 0,070760%/mês
        self.assertEqual(resultado.seguro_mensal, Decimal("495.32"))

    def test_mais_por_menos_paga_75_por_cento_de_fc_e_fr(self):
        # Cláusula 3.4: contribuição reduzida = 75% do FC e do FR + TA integral
        resultado = caso_thiago()
        esperado = (Decimal("0.75") * Decimal("1.03") + Decimal("0.20")) / Decimal(80)
        self.assertEqual(resultado.parcela_mais_por_menos_pct, esperado)


class TestConfiguracoesTabelas(unittest.TestCase):
    def test_padroes_leves(self):
        config = CONFIGURACOES_TABELAS["LEVES"]
        self.assertEqual(config.taxa_admin, Decimal("0.20"))
        self.assertEqual(config.fundo_reserva, Decimal("0.03"))
        self.assertEqual(config.piso_fundo_comum_mensal, Decimal("0.01"))

    def test_padroes_pesados(self):
        config = CONFIGURACOES_TABELAS["PESADOS"]
        self.assertEqual(config.taxa_admin, Decimal("0.13"))
        self.assertEqual(config.piso_fundo_comum_mensal, Decimal("0.0075"))

    def test_prazos_mais_por_menos_pesados_limitados_a_70(self):
        self.assertEqual(prazos_disponiveis("PESADOS", "MAIS POR MENOS"), (36, 50, 60, 70))
        self.assertEqual(prazos_disponiveis("PESADOS", "NORMAL"), (36, 50, 60, 70, 85, 100))
        self.assertEqual(prazos_disponiveis("LEVES", "MAIS POR MENOS"), (36, 50, 60, 70, 80))


class TestSaldoDevedorExtratosReais(unittest.TestCase):
    """Saldo na contemplação: (100 + FR + TA) - mes x parcela% - lance%."""

    def test_saldo_caso_thiago(self):
        # Extrato real: saldo devedor 90,7064% após contemplação no mês 6
        resultado = caso_thiago()
        saldo = saldo_percentual_apos_lance(resultado, 6) * 100
        self.assertLessEqual(abs(saldo - Decimal("90.7064")), Decimal("0.001"))

    def test_saldo_caso_maykel(self):
        # Extrato real: saldo devedor 55,1177% (lance total 66,6667%)
        resultado = caso_maykel()
        saldo = saldo_percentual_apos_lance(resultado, 1) * 100
        self.assertLessEqual(abs(saldo - Decimal("55.1177")), Decimal("0.001"))

    def test_diferenca_mpm_paga_com_recursos_proprios_abate_25_pontos(self):
        base = caso_thiago()
        pago = caso_thiago(
            tratamento_diferenca_mais_por_menos=TRATAMENTO_PAGAR_RECURSOS_PROPRIOS
        )
        diferenca = saldo_percentual_apos_lance(base, 6) - saldo_percentual_apos_lance(pago, 6)
        self.assertEqual(diferenca, Decimal("0.25"))

    def test_diferenca_mpm_deduzida_do_credito(self):
        base = caso_thiago()
        deduzida = caso_thiago(
            tratamento_diferenca_mais_por_menos=TRATAMENTO_DEDUZIR_DO_CREDITO
        )
        # Saldo também cai 25 pontos...
        self.assertEqual(
            saldo_percentual_apos_lance(base, 6) - saldo_percentual_apos_lance(deduzida, 6),
            Decimal("0.25"),
        )
        # ...e o crédito líquido cai 25% do crédito (30.000)
        self.assertEqual(base.credito_liquido - deduzida.credito_liquido, Decimal("30000.00"))


class TestCreditoLiquido(unittest.TestCase):
    def test_credito_liquido_com_embutido_e_taxa_de_cadastro(self):
        # Extratos: taxa de cadastro 1% (1.200) descontada do crédito na contemplação
        resultado = caso_thiago()
        self.assertEqual(resultado.taxa_cadastro_valor, Decimal("1200.00"))
        self.assertEqual(
            resultado.credito_liquido,
            Decimal("120000") - Decimal("30000") - Decimal("1200"),
        )


class TestReduzirParcelaDiluido(unittest.TestCase):
    """Casos reais de renegociação 'diluído/rateado' extraídos dos extratos."""

    def test_caso_thiago_mantem_prazo(self):
        # Extrato: 74 parcelas restantes, nova parcela R$ 1.560,88 (com seguro)
        resultado = caso_thiago()
        amortizacao = calcular_reduzir_parcela(resultado, 6)
        self.assertEqual(amortizacao.parcelas_restantes, Decimal("74"))
        self.assertEqual(amortizacao.mes_previsto_quitacao, 80)
        self.assertLessEqual(
            abs(amortizacao.nova_parcela - Decimal("1560.88")), TOLERANCIA_REAIS
        )

    def test_caso_maykel_piso_reduz_para_49_meses(self):
        # Extrato: piso regulamentar dispara, prazo cai para 49 meses,
        # parcela R$ 1.439,68 (com seguro) e quitação na 50ª assembleia
        resultado = caso_maykel()
        amortizacao = calcular_reduzir_parcela(resultado, 1)
        self.assertEqual(amortizacao.parcelas_restantes, Decimal("49"))
        self.assertEqual(amortizacao.mes_previsto_quitacao, 50)
        self.assertLessEqual(
            abs(amortizacao.nova_parcela - Decimal("1439.68")), TOLERANCIA_REAIS
        )


class TestReduzirPrazoOrdemInversa(unittest.TestCase):
    """Cláusula 3.3 §7º/8º: lance com isenção de TA quita parcelas ao ideal.

    Rótulos reais dos extratos: lance 25% = "Lance 19 pcls.";
    lance 66,67% = "Lance 51 pcls." (percentual ideal FC+FR = 1,2875%/mês).
    """

    def test_lance_25_por_cento_quita_19_parcelas(self):
        resultado = caso_thiago(uso_lance="REDUZIR_PRAZO")
        amortizacao = calcular_reduzir_prazo(resultado, 6)
        self.assertEqual(amortizacao.parcelas_abatidas, Decimal("19"))
        self.assertEqual(amortizacao.parcelas_restantes, Decimal(80 - 6 - 19))

    def test_lance_66_por_cento_quita_51_parcelas(self):
        resultado = caso_maykel(uso_lance="REDUZIR_PRAZO")
        amortizacao = calcular_reduzir_prazo(resultado, 1)
        self.assertEqual(amortizacao.parcelas_abatidas, Decimal("51"))
        self.assertEqual(amortizacao.parcelas_restantes, Decimal(80 - 1 - 51))

    def test_parcela_mantida_no_percentual_pleno_mais_diferenca_diluida(self):
        # Plano normal: parcela pós-contemplação = percentual pleno (1,5375%)
        resultado = caso_thiago(plano="NORMAL", uso_lance="REDUZIR_PRAZO")
        amortizacao = calcular_reduzir_prazo(resultado, 6)
        esperado = Decimal("120000") * Decimal("1.23") / Decimal(80) + resultado.seguro_mensal
        self.assertLessEqual(abs(amortizacao.nova_parcela - esperado), Decimal("0.01"))


class TestTabelaContemplacao(unittest.TestCase):
    def test_estrutura_da_tabela(self):
        resultado = caso_thiago()
        tabela = gerar_tabela_contemplacao(resultado)
        self.assertTrue(tabela)
        chaves = {
            "Mes de contemplacao",
            "Parcelas restantes apos lance",
            "Parcelas abatidas",
            "Mes previsto de quitacao",
            "Nova parcela",
            "Saldo apos lance",
        }
        self.assertTrue(chaves.issubset(tabela[0].keys()))

    def test_tratamento_da_diferenca_altera_saldo_na_tabela(self):
        # Regressão do bug original: as opções da diferença MpM não afetavam o saldo
        renegociar = gerar_tabela_contemplacao(caso_thiago())
        deduzir = gerar_tabela_contemplacao(
            caso_thiago(tratamento_diferenca_mais_por_menos=TRATAMENTO_DEDUZIR_DO_CREDITO)
        )
        self.assertNotEqual(
            renegociar[5]["Saldo apos lance"], deduzir[5]["Saldo apos lance"]
        )


class TestLimites(unittest.TestCase):
    def test_lance_embutido_limitado_a_25_por_cento(self):
        resultado = caso_thiago(lance_embutido_percentual=Decimal("0.40"))
        self.assertEqual(resultado.lance_embutido_percentual, Decimal("0.25"))

    def test_compatibilidade_com_kwargs_antigos(self):
        # O app antigo passava parâmetros extras; devem ser ignorados sem erro
        resultado = caso_thiago(
            prazo_total_grupo=80,
            meses_remanescentes_grupo=74,
            segmento_bem="AUTOMOVEL_MOTOCICLETA_DEMAIS_BENS_MOVEIS",
            saldo_devedor_percentual=Decimal("0"),
        )
        self.assertEqual(resultado.prazo, 80)


if __name__ == "__main__":
    unittest.main()
