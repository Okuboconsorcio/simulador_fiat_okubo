from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP


PLANOS = ("NORMAL", "MAIS POR MENOS")
USOS_LANCE = ("ABATER QUANTIDADE DE PARCELAS", "REDUZIR VALOR DA PARCELA")
PRAZOS = (36, 50, 60, 70, 80)


def _d(value: float | int | Decimal) -> Decimal:
    return Decimal(str(value or 0))


def round_half_up(value: Decimal) -> int:
    return int(value.to_integral_value(rounding=ROUND_HALF_UP))


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
    lance_embutido: Decimal
    lance_total: Decimal
    lance_total_percentual: Decimal
    credito_liquido: Decimal
    seguro_mensal: Decimal
    total_plano_sem_seguro: Decimal
    total_plano_com_seguro: Decimal
    parcela_normal: Decimal
    parcela_mais_por_menos: Decimal
    parcela_ate_contemplacao: Decimal


def calcular_simulacao(
    *,
    credito: float,
    lance_proprio: float,
    lance_embutido_percentual: float,
    taxa_admin_percentual: float,
    fundo_reserva_percentual: float,
    seguro_percentual: float,
    prazo: int,
    plano: str,
    uso_lance: str,
    mes_contemplacao: int,
) -> ResultadoSimulacao:
    credito_d = _d(credito)
    lance_proprio_d = _d(lance_proprio)
    lance_embutido_pct_d = min(max(_d(lance_embutido_percentual), Decimal("0")), Decimal("0.25"))
    taxa_admin_pct_d = max(_d(taxa_admin_percentual), Decimal("0"))
    fundo_reserva_pct_d = max(_d(fundo_reserva_percentual), Decimal("0"))
    seguro_pct_d = max(_d(seguro_percentual), Decimal("0"))
    prazo_i = int(prazo)
    mes_i = max(1, int(mes_contemplacao))
    plano_normalizado = plano if plano in PLANOS else "NORMAL"
    uso_lance_normalizado = uso_lance if uso_lance in USOS_LANCE else USOS_LANCE[0]

    if prazo_i <= 0:
        raise ValueError("O prazo precisa ser maior que zero.")

    lance_embutido = credito_d * lance_embutido_pct_d
    lance_total = lance_proprio_d + lance_embutido
    lance_total_percentual = lance_total / credito_d if credito_d else Decimal("0")
    credito_liquido = max(Decimal("0"), credito_d - lance_embutido)
    seguro_mensal = credito_d * seguro_pct_d
    total_plano_sem_seguro = credito_d * (Decimal("1") + taxa_admin_pct_d + fundo_reserva_pct_d)
    total_plano_com_seguro = total_plano_sem_seguro + (seguro_mensal * prazo_i)
    parcela_normal = (total_plano_sem_seguro / prazo_i) + seguro_mensal
    parcela_mais_por_menos = (
        credito_d * ((Decimal("0.75") * (Decimal("1") + fundo_reserva_pct_d)) + taxa_admin_pct_d) / prazo_i
    ) + seguro_mensal
    parcela_ate_contemplacao = parcela_mais_por_menos if plano_normalizado == "MAIS POR MENOS" else parcela_normal

    return ResultadoSimulacao(
        credito=credito_d,
        lance_proprio=lance_proprio_d,
        lance_embutido_percentual=lance_embutido_pct_d,
        taxa_admin_percentual=taxa_admin_pct_d,
        fundo_reserva_percentual=fundo_reserva_pct_d,
        seguro_percentual=seguro_pct_d,
        prazo=prazo_i,
        plano=plano_normalizado,
        uso_lance=uso_lance_normalizado,
        mes_contemplacao=mes_i,
        lance_embutido=lance_embutido,
        lance_total=lance_total,
        lance_total_percentual=lance_total_percentual,
        credito_liquido=credito_liquido,
        seguro_mensal=seguro_mensal,
        total_plano_sem_seguro=total_plano_sem_seguro,
        total_plano_com_seguro=total_plano_com_seguro,
        parcela_normal=parcela_normal,
        parcela_mais_por_menos=parcela_mais_por_menos,
        parcela_ate_contemplacao=parcela_ate_contemplacao,
    )


def gerar_tabela_contemplacao(resultado: ResultadoSimulacao) -> list[dict[str, Decimal | int | str]]:
    if resultado.mes_contemplacao >= resultado.prazo:
        return []

    linhas: list[dict[str, Decimal | int | str]] = []

    for mes in range(resultado.mes_contemplacao, resultado.prazo):
        saldo = max(
            Decimal("0"),
            resultado.total_plano_com_seguro - (resultado.parcela_ate_contemplacao * mes) - resultado.lance_total,
        )

        if saldo == 0:
            parcelas_restantes_apos_lance = Decimal("0")
            parcelas_abatidas: Decimal | str = (
                Decimal(resultado.prazo - mes)
                if resultado.uso_lance == "ABATER QUANTIDADE DE PARCELAS"
                else Decimal(resultado.prazo - mes)
            )
            mes_previsto_quitacao = mes
            nova_parcela: Decimal | str = "QUITADO"
        elif resultado.uso_lance == "ABATER QUANTIDADE DE PARCELAS":
            parcelas_restantes_apos_lance = Decimal(round_half_up(saldo / resultado.parcela_normal))
            parcelas_abatidas = Decimal(resultado.prazo - mes) - parcelas_restantes_apos_lance
            mes_previsto_quitacao = mes + int(parcelas_restantes_apos_lance)
            nova_parcela = resultado.parcela_normal
        else:
            parcelas_restantes_apos_lance = Decimal(resultado.prazo - mes)
            parcelas_abatidas = "-"
            mes_previsto_quitacao = resultado.prazo
            parcelas_restantes = max(1, resultado.prazo - mes)
            nova_parcela = saldo / Decimal(parcelas_restantes)

        linhas.append(
            {
                "Mes de contemplacao": mes,
                "Parcelas restantes apos lance": parcelas_restantes_apos_lance,
                "Parcelas abatidas": parcelas_abatidas,
                "Mes previsto de quitacao": mes_previsto_quitacao,
                "Nova parcela": nova_parcela,
                "Saldo apos lance": saldo,
            }
        )

    return linhas
