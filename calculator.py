from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Sequence


PLANOS = ("NORMAL", "MAIS POR MENOS")
PRAZOS = (36, 50, 60, 70, 80)

MODO_REDUZIR_PARCELA = "REDUZIR_PARCELA"
MODO_REDUZIR_PRAZO = "REDUZIR_PRAZO"
MODO_DILUIDO_RATEADO = "DILUIDO_RATEADO"

USOS_LANCE = (MODO_REDUZIR_PARCELA, MODO_REDUZIR_PRAZO, MODO_DILUIDO_RATEADO)

CENTAVOS = Decimal("0.01")


@dataclass(frozen=True)
class ConfiguracaoPlano:
    percentual_fundo_comum: Decimal
    percentual_mensal_com_taxas: Decimal
    percentual_mensal_seguro: Decimal
    taxa_cobertura_mais_por_menos: Decimal
    forma_utilizacao_lance: str
    regra_arredondamento: str
    tratamento_ultima_parcela: str
    percentual_mensal_pos_contemplacao_sem_seguro: Decimal


CONFIGURACOES_PLANOS = {
    "NORMAL": ConfiguracaoPlano(
        percentual_fundo_comum=Decimal("1"),
        percentual_mensal_com_taxas=Decimal("0"),
        percentual_mensal_seguro=Decimal("0.00075"),
        taxa_cobertura_mais_por_menos=Decimal("1"),
        forma_utilizacao_lance=MODO_REDUZIR_PRAZO,
        regra_arredondamento="ROUND_HALF_UP",
        tratamento_ultima_parcela="AJUSTAR_DIFERENCA_RESIDUAL",
        percentual_mensal_pos_contemplacao_sem_seguro=Decimal("0"),
    ),
    "MAIS POR MENOS": ConfiguracaoPlano(
        percentual_fundo_comum=Decimal("0.75"),
        percentual_mensal_com_taxas=Decimal("0.01215625"),
        percentual_mensal_seguro=Decimal("0.00075"),
        taxa_cobertura_mais_por_menos=Decimal("0.75"),
        forma_utilizacao_lance=MODO_DILUIDO_RATEADO,
        regra_arredondamento="ROUND_HALF_UP",
        tratamento_ultima_parcela="AJUSTAR_DIFERENCA_RESIDUAL",
        percentual_mensal_pos_contemplacao_sem_seguro=Decimal("0.011247"),
    ),
}


def _d(value: float | int | str | Decimal | None) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    return Decimal(str(value))


def quantizar_moeda(value: Decimal) -> Decimal:
    return value.quantize(CENTAVOS, rounding=ROUND_HALF_UP)


def round_half_up(value: Decimal) -> int:
    return int(value.to_integral_value(rounding=ROUND_HALF_UP))


def normalizar_uso_lance(uso_lance: str | None, padrao: str) -> str:
    aliases = {
        "ABATER QUANTIDADE DE PARCELAS": MODO_REDUZIR_PRAZO,
        "REDUZIR VALOR DA PARCELA": MODO_REDUZIR_PARCELA,
        "REDUZIR PRAZO": MODO_REDUZIR_PRAZO,
        "REDUZIR PARCELA": MODO_REDUZIR_PARCELA,
        "DILUIDO/RATEADO": MODO_DILUIDO_RATEADO,
        "DILUÍDO/RATEADO": MODO_DILUIDO_RATEADO,
        "DILUIDO RATEADO": MODO_DILUIDO_RATEADO,
        "DILUÍDO RATEADO": MODO_DILUIDO_RATEADO,
    }
    valor = str(uso_lance or "").strip().upper()
    normalizado = aliases.get(valor, valor)
    return normalizado if normalizado in USOS_LANCE else padrao


@dataclass(frozen=True)
class ResultadoDiluidoRateado:
    saldo_contratual_sem_seguro: Decimal
    total_parcelas_pagas_sem_seguro: Decimal
    total_amortizado: Decimal
    saldo_remanescente_sem_seguro: Decimal
    parcela_sem_seguro: Decimal
    nova_parcela: Decimal
    quantidade_parcelas_restantes: int
    saldo_seguro_futuro: Decimal
    saldo_total_futuro: Decimal
    diferenca_residual: Decimal
    ultima_parcela_sem_seguro: Decimal
    ultima_parcela_com_seguro: Decimal


@dataclass(frozen=True)
class ResultadoSimulacao:
    credito: Decimal
    lance_proprio: Decimal
    lance_embutido_percentual: Decimal
    taxa_admin_percentual: Decimal
    fundo_reserva_percentual: Decimal
    seguro_percentual: Decimal
    prazo: int
    plano: str
    uso_lance: str
    mes_contemplacao: int
    configuracao_plano: ConfiguracaoPlano
    lance_embutido: Decimal
    lance_total: Decimal
    lance_total_percentual: Decimal
    credito_liquido: Decimal
    outras_antecipacoes: Decimal
    seguro_mensal: Decimal
    total_plano_sem_seguro: Decimal
    total_plano_com_seguro: Decimal
    parcela_normal_sem_seguro: Decimal
    parcela_mais_por_menos_sem_seguro: Decimal
    parcela_ate_contemplacao_sem_seguro: Decimal
    parcela_normal: Decimal
    parcela_mais_por_menos: Decimal
    parcela_ate_contemplacao: Decimal
    percentual_mensal_pos_contemplacao_sem_seguro: Decimal
    parcelas_pagas_sem_seguro: tuple[Decimal, ...]


def calcular_diluido_rateado(
    *,
    credito: Decimal,
    taxa_administracao: Decimal,
    fundo_reserva: Decimal,
    lance_proprio: Decimal,
    lance_embutido: Decimal,
    seguro_mensal: Decimal,
    parcelas_pagas_sem_seguro: Sequence[Decimal],
    percentual_mensal_pos_contemplacao_sem_seguro: Decimal,
    outras_antecipacoes: Decimal = Decimal("0"),
) -> ResultadoDiluidoRateado:
    saldo_contratual_sem_seguro = quantizar_moeda(
        credito * (Decimal("1") + taxa_administracao + fundo_reserva)
    )
    total_parcelas_pagas_sem_seguro = quantizar_moeda(sum(parcelas_pagas_sem_seguro, Decimal("0")))
    total_amortizado = quantizar_moeda(
        lance_proprio + lance_embutido + total_parcelas_pagas_sem_seguro + outras_antecipacoes
    )
    saldo_remanescente_sem_seguro = max(
        Decimal("0"),
        quantizar_moeda(saldo_contratual_sem_seguro - total_amortizado),
    )
    parcela_sem_seguro = quantizar_moeda(credito * percentual_mensal_pos_contemplacao_sem_seguro)

    if saldo_remanescente_sem_seguro == 0 or parcela_sem_seguro == 0:
        quantidade_parcelas_restantes = 0
    else:
        quantidade_parcelas_restantes = max(
            1,
            round_half_up(saldo_remanescente_sem_seguro / parcela_sem_seguro),
        )

    nova_parcela = quantizar_moeda(parcela_sem_seguro + seguro_mensal) if quantidade_parcelas_restantes else Decimal("0")
    saldo_seguro_futuro = quantizar_moeda(Decimal(quantidade_parcelas_restantes) * seguro_mensal)
    saldo_total_futuro = quantizar_moeda(saldo_remanescente_sem_seguro + saldo_seguro_futuro)
    diferenca_residual = (
        quantizar_moeda(
            saldo_remanescente_sem_seguro - (Decimal(quantidade_parcelas_restantes) * parcela_sem_seguro)
        )
        if quantidade_parcelas_restantes
        else Decimal("0")
    )
    ultima_parcela_sem_seguro = (
        quantizar_moeda(parcela_sem_seguro + diferenca_residual)
        if quantidade_parcelas_restantes
        else Decimal("0")
    )
    ultima_parcela_com_seguro = (
        quantizar_moeda(ultima_parcela_sem_seguro + seguro_mensal)
        if quantidade_parcelas_restantes
        else Decimal("0")
    )

    return ResultadoDiluidoRateado(
        saldo_contratual_sem_seguro=saldo_contratual_sem_seguro,
        total_parcelas_pagas_sem_seguro=total_parcelas_pagas_sem_seguro,
        total_amortizado=total_amortizado,
        saldo_remanescente_sem_seguro=saldo_remanescente_sem_seguro,
        parcela_sem_seguro=parcela_sem_seguro,
        nova_parcela=nova_parcela,
        quantidade_parcelas_restantes=quantidade_parcelas_restantes,
        saldo_seguro_futuro=saldo_seguro_futuro,
        saldo_total_futuro=saldo_total_futuro,
        diferenca_residual=diferenca_residual,
        ultima_parcela_sem_seguro=ultima_parcela_sem_seguro,
        ultima_parcela_com_seguro=ultima_parcela_com_seguro,
    )


def calcular_simulacao(
    *,
    credito: float | int | str | Decimal,
    lance_proprio: float | int | str | Decimal,
    lance_embutido_percentual: float | int | str | Decimal,
    taxa_admin_percentual: float | int | str | Decimal,
    fundo_reserva_percentual: float | int | str | Decimal,
    seguro_percentual: float | int | str | Decimal,
    prazo: int,
    plano: str,
    uso_lance: str,
    mes_contemplacao: int,
    percentual_mensal_pos_contemplacao_sem_seguro: float | int | str | Decimal | None = None,
    outras_antecipacoes: float | int | str | Decimal = Decimal("0"),
    seguro_mensal: float | int | str | Decimal | None = None,
    parcelas_pagas_sem_seguro: Sequence[float | int | str | Decimal] | None = None,
) -> ResultadoSimulacao:
    credito_d = quantizar_moeda(max(_d(credito), Decimal("0")))
    lance_proprio_d = quantizar_moeda(max(_d(lance_proprio), Decimal("0")))
    lance_embutido_pct_d = min(max(_d(lance_embutido_percentual), Decimal("0")), Decimal("0.25"))
    taxa_admin_pct_d = max(_d(taxa_admin_percentual), Decimal("0"))
    fundo_reserva_pct_d = max(_d(fundo_reserva_percentual), Decimal("0"))
    seguro_pct_d = max(_d(seguro_percentual), Decimal("0"))
    outras_antecipacoes_d = quantizar_moeda(max(_d(outras_antecipacoes), Decimal("0")))
    prazo_i = int(prazo)
    mes_i = max(1, int(mes_contemplacao))
    plano_normalizado = plano if plano in PLANOS else "NORMAL"
    configuracao = CONFIGURACOES_PLANOS[plano_normalizado]
    uso_lance_normalizado = normalizar_uso_lance(uso_lance, configuracao.forma_utilizacao_lance)

    if prazo_i <= 0:
        raise ValueError("O prazo precisa ser maior que zero.")

    percentual_pos_d = (
        max(_d(percentual_mensal_pos_contemplacao_sem_seguro), Decimal("0"))
        if percentual_mensal_pos_contemplacao_sem_seguro is not None
        else configuracao.percentual_mensal_pos_contemplacao_sem_seguro
    )
    lance_embutido = quantizar_moeda(credito_d * lance_embutido_pct_d)
    lance_total = quantizar_moeda(lance_proprio_d + lance_embutido)
    lance_total_percentual = lance_total / credito_d if credito_d else Decimal("0")
    credito_liquido = max(Decimal("0"), quantizar_moeda(credito_d - lance_embutido))
    seguro_mensal_d = (
        quantizar_moeda(max(_d(seguro_mensal), Decimal("0")))
        if seguro_mensal is not None
        else quantizar_moeda(credito_d * seguro_pct_d)
    )
    seguro_pct_calculado = seguro_mensal_d / credito_d if credito_d and seguro_mensal is not None else seguro_pct_d
    total_plano_sem_seguro = quantizar_moeda(credito_d * (Decimal("1") + taxa_admin_pct_d + fundo_reserva_pct_d))
    total_plano_com_seguro = quantizar_moeda(total_plano_sem_seguro + (seguro_mensal_d * Decimal(prazo_i)))
    parcela_normal_sem_seguro = quantizar_moeda(total_plano_sem_seguro / Decimal(prazo_i))
    parcela_normal = quantizar_moeda(parcela_normal_sem_seguro + seguro_mensal_d)

    if configuracao.percentual_mensal_com_taxas:
        parcela_mais_por_menos_sem_seguro = quantizar_moeda(credito_d * configuracao.percentual_mensal_com_taxas)
    else:
        parcela_mais_por_menos_sem_seguro = quantizar_moeda(
            credito_d
            * (
                (configuracao.taxa_cobertura_mais_por_menos * (Decimal("1") + fundo_reserva_pct_d))
                + taxa_admin_pct_d
            )
            / Decimal(prazo_i)
        )
    parcela_mais_por_menos = quantizar_moeda(parcela_mais_por_menos_sem_seguro + seguro_mensal_d)
    parcela_ate_contemplacao_sem_seguro = (
        parcela_mais_por_menos_sem_seguro if plano_normalizado == "MAIS POR MENOS" else parcela_normal_sem_seguro
    )
    parcela_ate_contemplacao = quantizar_moeda(parcela_ate_contemplacao_sem_seguro + seguro_mensal_d)
    parcelas_pagas = tuple(quantizar_moeda(_d(valor)) for valor in (parcelas_pagas_sem_seguro or ()))

    return ResultadoSimulacao(
        credito=credito_d,
        lance_proprio=lance_proprio_d,
        lance_embutido_percentual=lance_embutido_pct_d,
        taxa_admin_percentual=taxa_admin_pct_d,
        fundo_reserva_percentual=fundo_reserva_pct_d,
        seguro_percentual=seguro_pct_calculado,
        prazo=prazo_i,
        plano=plano_normalizado,
        uso_lance=uso_lance_normalizado,
        mes_contemplacao=mes_i,
        configuracao_plano=configuracao,
        lance_embutido=lance_embutido,
        lance_total=lance_total,
        lance_total_percentual=lance_total_percentual,
        credito_liquido=credito_liquido,
        outras_antecipacoes=outras_antecipacoes_d,
        seguro_mensal=seguro_mensal_d,
        total_plano_sem_seguro=total_plano_sem_seguro,
        total_plano_com_seguro=total_plano_com_seguro,
        parcela_normal_sem_seguro=parcela_normal_sem_seguro,
        parcela_mais_por_menos_sem_seguro=parcela_mais_por_menos_sem_seguro,
        parcela_ate_contemplacao_sem_seguro=parcela_ate_contemplacao_sem_seguro,
        parcela_normal=parcela_normal,
        parcela_mais_por_menos=parcela_mais_por_menos,
        parcela_ate_contemplacao=parcela_ate_contemplacao,
        percentual_mensal_pos_contemplacao_sem_seguro=percentual_pos_d,
        parcelas_pagas_sem_seguro=parcelas_pagas,
    )


def parcelas_pagas_sem_seguro_para_mes(resultado: ResultadoSimulacao, mes: int) -> tuple[Decimal, ...]:
    if resultado.parcelas_pagas_sem_seguro and len(resultado.parcelas_pagas_sem_seguro) >= mes:
        return resultado.parcelas_pagas_sem_seguro[:mes]
    return tuple(resultado.parcela_ate_contemplacao_sem_seguro for _ in range(mes))


def saldo_remanescente_sem_seguro(resultado: ResultadoSimulacao, mes: int) -> Decimal:
    total_pago_sem_seguro = quantizar_moeda(sum(parcelas_pagas_sem_seguro_para_mes(resultado, mes), Decimal("0")))
    return max(
        Decimal("0"),
        quantizar_moeda(
            resultado.total_plano_sem_seguro
            - total_pago_sem_seguro
            - resultado.lance_total
            - resultado.outras_antecipacoes
        ),
    )


def linha_diluido_rateado(resultado: ResultadoSimulacao, mes: int) -> tuple[Decimal, Decimal | str, int, Decimal, Decimal]:
    calculo = calcular_diluido_rateado(
        credito=resultado.credito,
        taxa_administracao=resultado.taxa_admin_percentual,
        fundo_reserva=resultado.fundo_reserva_percentual,
        lance_proprio=resultado.lance_proprio,
        lance_embutido=resultado.lance_embutido,
        seguro_mensal=resultado.seguro_mensal,
        parcelas_pagas_sem_seguro=parcelas_pagas_sem_seguro_para_mes(resultado, mes),
        percentual_mensal_pos_contemplacao_sem_seguro=resultado.percentual_mensal_pos_contemplacao_sem_seguro,
        outras_antecipacoes=resultado.outras_antecipacoes,
    )
    parcelas_restantes = Decimal(calculo.quantidade_parcelas_restantes)
    parcelas_abatidas = Decimal(resultado.prazo - mes) - parcelas_restantes
    mes_quitacao = mes + calculo.quantidade_parcelas_restantes
    return (
        parcelas_restantes,
        parcelas_abatidas,
        mes_quitacao,
        calculo.nova_parcela,
        calculo.saldo_total_futuro,
    )


def linha_reduzir_prazo(resultado: ResultadoSimulacao, mes: int) -> tuple[Decimal, Decimal | str, int, Decimal | str, Decimal]:
    saldo_sem_seguro = saldo_remanescente_sem_seguro(resultado, mes)

    if saldo_sem_seguro == 0:
        return Decimal("0"), Decimal(resultado.prazo - mes), mes, "QUITADO", Decimal("0")

    parcelas_restantes = Decimal(max(1, round_half_up(saldo_sem_seguro / resultado.parcela_normal_sem_seguro)))
    parcelas_abatidas = Decimal(resultado.prazo - mes) - parcelas_restantes
    mes_quitacao = mes + int(parcelas_restantes)
    saldo_total_futuro = quantizar_moeda(saldo_sem_seguro + (parcelas_restantes * resultado.seguro_mensal))
    return parcelas_restantes, parcelas_abatidas, mes_quitacao, resultado.parcela_normal, saldo_total_futuro


def linha_reduzir_parcela(resultado: ResultadoSimulacao, mes: int) -> tuple[Decimal, Decimal | str, int, Decimal | str, Decimal]:
    saldo_sem_seguro = saldo_remanescente_sem_seguro(resultado, mes)

    if saldo_sem_seguro == 0:
        return Decimal("0"), Decimal(resultado.prazo - mes), mes, "QUITADO", Decimal("0")

    parcelas_restantes = Decimal(max(1, resultado.prazo - mes))
    nova_parcela_sem_seguro = quantizar_moeda(saldo_sem_seguro / parcelas_restantes)
    nova_parcela = quantizar_moeda(nova_parcela_sem_seguro + resultado.seguro_mensal)
    saldo_total_futuro = quantizar_moeda(saldo_sem_seguro + (parcelas_restantes * resultado.seguro_mensal))
    return parcelas_restantes, "-", resultado.prazo, nova_parcela, saldo_total_futuro


def gerar_tabela_contemplacao(resultado: ResultadoSimulacao) -> list[dict[str, Decimal | int | str]]:
    if resultado.mes_contemplacao >= resultado.prazo:
        return []

    linhas: list[dict[str, Decimal | int | str]] = []

    for mes in range(resultado.mes_contemplacao, resultado.prazo):
        if resultado.uso_lance == MODO_DILUIDO_RATEADO:
            parcelas_restantes, parcelas_abatidas, mes_previsto_quitacao, nova_parcela, saldo = linha_diluido_rateado(
                resultado, mes
            )
        elif resultado.uso_lance == MODO_REDUZIR_PRAZO:
            parcelas_restantes, parcelas_abatidas, mes_previsto_quitacao, nova_parcela, saldo = linha_reduzir_prazo(
                resultado, mes
            )
        else:
            parcelas_restantes, parcelas_abatidas, mes_previsto_quitacao, nova_parcela, saldo = linha_reduzir_parcela(
                resultado, mes
            )

        linhas.append(
            {
                "Mes de contemplacao": mes,
                "Parcelas restantes apos lance": parcelas_restantes,
                "Parcelas abatidas": parcelas_abatidas,
                "Mes previsto de quitacao": mes_previsto_quitacao,
                "Nova parcela": nova_parcela,
                "Saldo apos lance": saldo,
            }
        )

    return linhas
