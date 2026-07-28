from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP
from typing import Sequence


PLANOS = ("NORMAL", "MAIS POR MENOS")
PRAZOS = (36, 50, 60, 70, 80)

MODO_REDUZIR_PRAZO = "REDUZIR_PRAZO"
MODO_REDUZIR_PARCELA = "REDUZIR_PARCELA"
USOS_LANCE = (MODO_REDUZIR_PRAZO, MODO_REDUZIR_PARCELA)

TRATAMENTO_RENEGOCIAR_NO_SALDO = "RENEGOCIAR_NO_SALDO"
TRATAMENTO_PAGAR_RECURSOS_PROPRIOS = "PAGAR_RECURSOS_PROPRIOS"
TRATAMENTO_DEDUZIR_DO_CREDITO = "DEDUZIR_DO_CREDITO"
TRATAMENTO_DIFERENCA_JA_ANTECIPADA = "DIFERENCA_JA_ANTECIPADA"
TRATAMENTOS_DIFERENCA_MPM = (
    TRATAMENTO_RENEGOCIAR_NO_SALDO,
    TRATAMENTO_PAGAR_RECURSOS_PROPRIOS,
    TRATAMENTO_DEDUZIR_DO_CREDITO,
    TRATAMENTO_DIFERENCA_JA_ANTECIPADA,
)

SEGMENTO_AUTOMOVEL_MOTO_MOVEIS = "AUTOMOVEL_MOTOCICLETA_DEMAIS_BENS_MOVEIS"
SEGMENTO_PESADOS = "CAMINHOES_ONIBUS_VEICULOS_PESADOS"
SEGMENTOS_BEM = (SEGMENTO_AUTOMOVEL_MOTO_MOVEIS, SEGMENTO_PESADOS)
PERCENTUAL_MINIMO_SEGMENTO = {
    SEGMENTO_AUTOMOVEL_MOTO_MOVEIS: Decimal("0.01"),
    SEGMENTO_PESADOS: Decimal("0.0075"),
}

CENTAVOS = Decimal("0.01")


@dataclass(frozen=True)
class ConfiguracaoPlano:
    prazo_total_grupo: int
    prazo_contratado_cota: int
    assembleia_contemplacao: int
    meses_remanescentes_grupo: int
    percentual_mensal_fundo_comum: Decimal
    percentual_mensal_fundo_reserva: Decimal
    percentual_mensal_taxa_administracao: Decimal
    taxa_administracao_antecipada_percentual: Decimal
    percentual_mensal_seguro: Decimal
    valor_mensal_seguro: Decimal | None
    credito_vigente: Decimal
    saldo_devedor_percentual: Decimal
    segmento_bem: str
    forma_utilizacao_lance: str
    tratamento_diferenca_mais_por_menos: str
    criterios_ata_assembleia_inaugural: str
    criterios_tabela_vendas: str
    taxa_cobertura_mais_por_menos: Decimal
    regra_arredondamento: str
    tratamento_ultima_parcela: str
    descricao_amortizacao_linear: str


CONFIGURACOES_PLANOS = {
    "NORMAL": {
        "percentual_mensal_fundo_comum": Decimal("0.010000"),
        "percentual_mensal_fundo_reserva": Decimal("0.000000"),
        "percentual_mensal_taxa_administracao": Decimal("0.002500"),
        "percentual_mensal_seguro": Decimal("0.000750"),
        "taxa_cobertura_mais_por_menos": Decimal("1"),
    },
    "MAIS POR MENOS": {
        "percentual_mensal_fundo_comum": Decimal("0.008747"),
        "percentual_mensal_fundo_reserva": Decimal("0.000000"),
        "percentual_mensal_taxa_administracao": Decimal("0.002500"),
        "percentual_mensal_seguro": Decimal("0.000750"),
        "taxa_cobertura_mais_por_menos": Decimal("0.75"),
    },
}


def _d(value: float | int | str | Decimal | None) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    return Decimal(str(value))


def quantizar_moeda(value: Decimal) -> Decimal:
    return value.quantize(CENTAVOS, rounding=ROUND_HALF_UP)


def round_half_up(value: Decimal) -> int:
    return int(value.to_integral_value(rounding=ROUND_HALF_UP))


def ceil_decimal(value: Decimal) -> int:
    return int(value.to_integral_value(rounding=ROUND_CEILING))


def normalizar_uso_lance(uso_lance: str | None, padrao: str = MODO_REDUZIR_PRAZO) -> str:
    aliases = {
        "ABATER QUANTIDADE DE PARCELAS": MODO_REDUZIR_PRAZO,
        "REDUZIR VALOR DA PARCELA": MODO_REDUZIR_PARCELA,
        "REDUZIR PRAZO": MODO_REDUZIR_PRAZO,
        "REDUZIR PARCELA": MODO_REDUZIR_PARCELA,
    }
    valor = str(uso_lance or "").strip().upper()
    normalizado = aliases.get(valor, valor)
    return normalizado if normalizado in USOS_LANCE else padrao


def normalizar_tratamento_diferenca(valor: str | None) -> str:
    tratamento = str(valor or "").strip().upper()
    return tratamento if tratamento in TRATAMENTOS_DIFERENCA_MPM else TRATAMENTO_DIFERENCA_JA_ANTECIPADA


def normalizar_segmento(valor: str | None) -> str:
    segmento = str(valor or "").strip().upper()
    return segmento if segmento in SEGMENTOS_BEM else SEGMENTO_AUTOMOVEL_MOTO_MOVEIS


@dataclass(frozen=True)
class ResultadoAmortizacao:
    parcelas_restantes: Decimal
    parcelas_abatidas: Decimal | str
    mes_previsto_quitacao: int
    nova_parcela: Decimal | str
    saldo_total_futuro: Decimal
    saldo_sem_seguro_futuro: Decimal
    ultima_parcela_sem_seguro: Decimal
    ultima_parcela_com_seguro: Decimal
    descricao: str


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
    outras_deducoes_credito: Decimal
    seguro_mensal: Decimal
    total_plano_sem_seguro: Decimal
    total_plano_com_seguro: Decimal
    parcela_normal_sem_seguro: Decimal
    parcela_mais_por_menos_sem_seguro: Decimal
    parcela_ate_contemplacao_sem_seguro: Decimal
    parcela_normal: Decimal
    parcela_mais_por_menos: Decimal
    parcela_ate_contemplacao: Decimal
    percentual_mensal_total: Decimal
    taxa_administracao_antecipada_valor: Decimal
    diferenca_mais_por_menos: Decimal
    diferenca_adicionada_saldo: Decimal
    diferenca_deduzida_credito: Decimal
    diferenca_paga_recursos_proprios: Decimal
    calculo_estimado: bool


def montar_configuracao_plano(
    *,
    plano: str,
    credito_vigente: Decimal,
    prazo_total_grupo: int,
    prazo_contratado_cota: int,
    assembleia_contemplacao: int,
    meses_remanescentes_grupo: int | None,
    percentual_mensal_fundo_comum: Decimal | None,
    percentual_mensal_fundo_reserva: Decimal | None,
    percentual_mensal_taxa_administracao: Decimal | None,
    taxa_administracao_antecipada_percentual: Decimal,
    percentual_mensal_seguro: Decimal,
    valor_mensal_seguro: Decimal | None,
    saldo_devedor_percentual: Decimal,
    segmento_bem: str,
    forma_utilizacao_lance: str,
    tratamento_diferenca_mais_por_menos: str,
    criterios_ata_assembleia_inaugural: str,
    criterios_tabela_vendas: str,
) -> ConfiguracaoPlano:
    defaults = CONFIGURACOES_PLANOS[plano]
    meses_remanescentes = (
        max(0, int(meses_remanescentes_grupo))
        if meses_remanescentes_grupo is not None
        else max(0, int(prazo_total_grupo) - int(assembleia_contemplacao))
    )

    return ConfiguracaoPlano(
        prazo_total_grupo=int(prazo_total_grupo),
        prazo_contratado_cota=int(prazo_contratado_cota),
        assembleia_contemplacao=int(assembleia_contemplacao),
        meses_remanescentes_grupo=meses_remanescentes,
        percentual_mensal_fundo_comum=(
            percentual_mensal_fundo_comum
            if percentual_mensal_fundo_comum is not None
            else defaults["percentual_mensal_fundo_comum"]
        ),
        percentual_mensal_fundo_reserva=(
            percentual_mensal_fundo_reserva
            if percentual_mensal_fundo_reserva is not None
            else defaults["percentual_mensal_fundo_reserva"]
        ),
        percentual_mensal_taxa_administracao=(
            percentual_mensal_taxa_administracao
            if percentual_mensal_taxa_administracao is not None
            else defaults["percentual_mensal_taxa_administracao"]
        ),
        taxa_administracao_antecipada_percentual=taxa_administracao_antecipada_percentual,
        percentual_mensal_seguro=percentual_mensal_seguro or defaults["percentual_mensal_seguro"],
        valor_mensal_seguro=valor_mensal_seguro,
        credito_vigente=credito_vigente,
        saldo_devedor_percentual=max(saldo_devedor_percentual, Decimal("0")),
        segmento_bem=normalizar_segmento(segmento_bem),
        forma_utilizacao_lance=normalizar_uso_lance(forma_utilizacao_lance),
        tratamento_diferenca_mais_por_menos=normalizar_tratamento_diferenca(tratamento_diferenca_mais_por_menos),
        criterios_ata_assembleia_inaugural=criterios_ata_assembleia_inaugural,
        criterios_tabela_vendas=criterios_tabela_vendas,
        taxa_cobertura_mais_por_menos=defaults["taxa_cobertura_mais_por_menos"],
        regra_arredondamento="ROUND_HALF_UP",
        tratamento_ultima_parcela="AJUSTAR_DIFERENCA_RESIDUAL",
        descricao_amortizacao_linear="Amortização linear/rateada interna usada somente em REDUZIR_PARCELA.",
    )


def calcular_diferencas_mais_por_menos(
    plano: str,
    credito: Decimal,
    configuracao: ConfiguracaoPlano,
) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    if plano != "MAIS POR MENOS":
        return Decimal("0"), Decimal("0"), Decimal("0"), Decimal("0")

    diferenca = quantizar_moeda(credito * (Decimal("1") - configuracao.taxa_cobertura_mais_por_menos))

    if configuracao.tratamento_diferenca_mais_por_menos == TRATAMENTO_RENEGOCIAR_NO_SALDO:
        return diferenca, diferenca, Decimal("0"), Decimal("0")
    if configuracao.tratamento_diferenca_mais_por_menos == TRATAMENTO_DEDUZIR_DO_CREDITO:
        return diferenca, Decimal("0"), diferenca, Decimal("0")
    if configuracao.tratamento_diferenca_mais_por_menos == TRATAMENTO_PAGAR_RECURSOS_PROPRIOS:
        return diferenca, Decimal("0"), Decimal("0"), diferenca
    return diferenca, Decimal("0"), Decimal("0"), Decimal("0")


def meses_restantes_no_prazo(resultado: ResultadoSimulacao, mes: int) -> int:
    return max(0, resultado.configuracao_plano.prazo_contratado_cota - int(mes))


def saldo_total_apos_lance(resultado: ResultadoSimulacao, mes: int) -> Decimal:
    parcelas_pagas = quantizar_moeda(resultado.parcela_ate_contemplacao * Decimal(int(mes)))
    amortizacoes = quantizar_moeda(resultado.lance_total + resultado.outras_antecipacoes)
    return max(
        Decimal("0"),
        quantizar_moeda(resultado.total_plano_com_seguro - parcelas_pagas - amortizacoes),
    )


def amortizar_ordem_inversa(cronograma: Sequence[Decimal], valor_lance: Decimal) -> list[Decimal]:
    restante = [quantizar_moeda(valor) for valor in cronograma]
    saldo_lance = quantizar_moeda(valor_lance)

    for indice in range(len(restante) - 1, -1, -1):
        if saldo_lance <= 0:
            break

        if saldo_lance >= restante[indice]:
            saldo_lance = quantizar_moeda(saldo_lance - restante[indice])
            restante[indice] = Decimal("0")
        else:
            restante[indice] = quantizar_moeda(restante[indice] - saldo_lance)
            saldo_lance = Decimal("0")

    return restante


def calcular_reduzir_prazo(resultado: ResultadoSimulacao, mes: int) -> ResultadoAmortizacao:
    meses_originais = meses_restantes_no_prazo(resultado, mes)
    saldo_total = saldo_total_apos_lance(resultado, mes)
    if meses_originais == 0 or saldo_total <= 0:
        return ResultadoAmortizacao(
            parcelas_restantes=Decimal("0"),
            parcelas_abatidas=Decimal(meses_originais),
            mes_previsto_quitacao=mes,
            nova_parcela="QUITADO",
            saldo_total_futuro=Decimal("0"),
            saldo_sem_seguro_futuro=Decimal("0"),
            ultima_parcela_sem_seguro=Decimal("0"),
            ultima_parcela_com_seguro=Decimal("0"),
            descricao="Sem contribuições vincendas.",
        )

    quantidade_restante = min(meses_originais, ceil_decimal(saldo_total / resultado.parcela_normal))
    parcelas_abatidas = max(0, meses_originais - quantidade_restante)
    saldo_sem_seguro = max(Decimal("0"), quantizar_moeda(saldo_total - (Decimal(quantidade_restante) * resultado.seguro_mensal)))
    ultima_com_seguro = quantizar_moeda(
        saldo_total - (Decimal(max(0, quantidade_restante - 1)) * resultado.parcela_normal)
    )
    ultima_sem_seguro = max(Decimal("0"), quantizar_moeda(ultima_com_seguro - resultado.seguro_mensal))

    return ResultadoAmortizacao(
        parcelas_restantes=Decimal(quantidade_restante),
        parcelas_abatidas=Decimal(parcelas_abatidas),
        mes_previsto_quitacao=mes + quantidade_restante,
        nova_parcela=resultado.parcela_normal
        if quantidade_restante
        else "QUITADO",
        saldo_total_futuro=saldo_total,
        saldo_sem_seguro_futuro=saldo_sem_seguro,
        ultima_parcela_sem_seguro=ultima_sem_seguro,
        ultima_parcela_com_seguro=ultima_com_seguro,
        descricao="Lance aplicado da última contribuição vincenda para a primeira.",
    )


def calcular_reduzir_parcela(resultado: ResultadoSimulacao, mes: int) -> ResultadoAmortizacao:
    meses_originais = meses_restantes_no_prazo(resultado, mes)
    saldo_total = saldo_total_apos_lance(resultado, mes)
    if meses_originais == 0 or saldo_total <= 0:
        return ResultadoAmortizacao(
            parcelas_restantes=Decimal("0"),
            parcelas_abatidas=Decimal(meses_originais),
            mes_previsto_quitacao=mes,
            nova_parcela="QUITADO",
            saldo_total_futuro=Decimal("0"),
            saldo_sem_seguro_futuro=Decimal("0"),
            ultima_parcela_sem_seguro=Decimal("0"),
            ultima_parcela_com_seguro=Decimal("0"),
            descricao="Sem saldo vincendo.",
        )

    percentual_minimo = PERCENTUAL_MINIMO_SEGMENTO[resultado.configuracao_plano.segmento_bem]
    parcela_minima = quantizar_moeda((resultado.credito * percentual_minimo) + resultado.seguro_mensal)
    parcela_linear = quantizar_moeda(saldo_total / Decimal(meses_originais))

    if parcela_linear < parcela_minima:
        nova_parcela = parcela_minima
        quantidade_restante = min(meses_originais, max(1, ceil_decimal(saldo_total / nova_parcela)))
        descricao = "Parcela mínima regulamentar aplicada; a cota pode encerrar antes do prazo original."
    else:
        nova_parcela = parcela_linear
        quantidade_restante = meses_originais
        descricao = "Amortização percentual/linear mantendo o prazo contratado."

    ultima_com_seguro = quantizar_moeda(
        saldo_total - (Decimal(max(0, quantidade_restante - 1)) * nova_parcela)
    )
    ultima_sem_seguro = max(Decimal("0"), quantizar_moeda(ultima_com_seguro - resultado.seguro_mensal))
    saldo_sem_seguro = max(Decimal("0"), quantizar_moeda(saldo_total - (Decimal(quantidade_restante) * resultado.seguro_mensal)))
    parcelas_abatidas = Decimal(meses_originais - quantidade_restante) if quantidade_restante < meses_originais else "-"

    return ResultadoAmortizacao(
        parcelas_restantes=Decimal(quantidade_restante),
        parcelas_abatidas=parcelas_abatidas,
        mes_previsto_quitacao=mes + quantidade_restante,
        nova_parcela=nova_parcela,
        saldo_total_futuro=saldo_total,
        saldo_sem_seguro_futuro=saldo_sem_seguro,
        ultima_parcela_sem_seguro=ultima_sem_seguro,
        ultima_parcela_com_seguro=ultima_com_seguro,
        descricao=descricao,
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
    prazo_total_grupo: int | None = None,
    prazo_contratado_cota: int | None = None,
    meses_remanescentes_grupo: int | None = None,
    percentual_mensal_fundo_comum: float | int | str | Decimal | None = None,
    percentual_mensal_fundo_reserva: float | int | str | Decimal | None = None,
    percentual_mensal_taxa_administracao: float | int | str | Decimal | None = None,
    taxa_administracao_antecipada_percentual: float | int | str | Decimal = Decimal("0"),
    credito_vigente: float | int | str | Decimal | None = None,
    saldo_devedor_percentual: float | int | str | Decimal = Decimal("0"),
    segmento_bem: str = SEGMENTO_AUTOMOVEL_MOTO_MOVEIS,
    tratamento_diferenca_mais_por_menos: str = TRATAMENTO_DIFERENCA_JA_ANTECIPADA,
    outras_antecipacoes: float | int | str | Decimal = Decimal("0"),
    outras_deducoes_credito: float | int | str | Decimal = Decimal("0"),
    seguro_mensal: float | int | str | Decimal | None = None,
    criterios_ata_assembleia_inaugural: str = "",
    criterios_tabela_vendas: str = "",
    parcelas_pagas_sem_seguro: Sequence[float | int | str | Decimal] | None = None,
) -> ResultadoSimulacao:
    credito_base_d = quantizar_moeda(max(_d(credito), Decimal("0")))
    credito_vigente_d = quantizar_moeda(max(_d(credito_vigente), Decimal("0"))) if credito_vigente is not None else credito_base_d
    lance_proprio_d = quantizar_moeda(max(_d(lance_proprio), Decimal("0")))
    lance_embutido_pct_d = min(max(_d(lance_embutido_percentual), Decimal("0")), Decimal("0.25"))
    taxa_admin_pct_d = max(_d(taxa_admin_percentual), Decimal("0"))
    fundo_reserva_pct_d = max(_d(fundo_reserva_percentual), Decimal("0"))
    seguro_pct_d = max(_d(seguro_percentual), Decimal("0"))
    outras_antecipacoes_d = quantizar_moeda(max(_d(outras_antecipacoes), Decimal("0")))
    outras_deducoes_credito_d = quantizar_moeda(max(_d(outras_deducoes_credito), Decimal("0")))
    prazo_i = int(prazo)
    mes_i = max(1, int(mes_contemplacao))
    plano_normalizado = plano if plano in PLANOS else "NORMAL"

    if prazo_i <= 0:
        raise ValueError("O prazo precisa ser maior que zero.")

    defaults = CONFIGURACOES_PLANOS[plano_normalizado]
    percentual_fundo_comum_d = (
        max(_d(percentual_mensal_fundo_comum), Decimal("0"))
        if percentual_mensal_fundo_comum is not None
        else defaults["percentual_mensal_fundo_comum"]
    )
    percentual_fundo_reserva_d = (
        max(_d(percentual_mensal_fundo_reserva), Decimal("0"))
        if percentual_mensal_fundo_reserva is not None
        else defaults["percentual_mensal_fundo_reserva"]
    )
    percentual_taxa_admin_mensal_d = (
        max(_d(percentual_mensal_taxa_administracao), Decimal("0"))
        if percentual_mensal_taxa_administracao is not None
        else defaults["percentual_mensal_taxa_administracao"]
    )
    seguro_mensal_d = (
        quantizar_moeda(max(_d(seguro_mensal), Decimal("0")))
        if seguro_mensal is not None and _d(seguro_mensal) > 0
        else quantizar_moeda(credito_vigente_d * seguro_pct_d)
    )
    seguro_pct_calculado = seguro_mensal_d / credito_vigente_d if credito_vigente_d else Decimal("0")

    configuracao = montar_configuracao_plano(
        plano=plano_normalizado,
        credito_vigente=credito_vigente_d,
        prazo_total_grupo=prazo_total_grupo or prazo_i,
        prazo_contratado_cota=prazo_contratado_cota or prazo_i,
        assembleia_contemplacao=mes_i,
        meses_remanescentes_grupo=meses_remanescentes_grupo,
        percentual_mensal_fundo_comum=percentual_fundo_comum_d,
        percentual_mensal_fundo_reserva=percentual_fundo_reserva_d,
        percentual_mensal_taxa_administracao=percentual_taxa_admin_mensal_d,
        taxa_administracao_antecipada_percentual=max(_d(taxa_administracao_antecipada_percentual), Decimal("0")),
        percentual_mensal_seguro=seguro_pct_calculado,
        valor_mensal_seguro=seguro_mensal_d,
        saldo_devedor_percentual=max(_d(saldo_devedor_percentual), Decimal("0")),
        segmento_bem=segmento_bem,
        forma_utilizacao_lance=uso_lance,
        tratamento_diferenca_mais_por_menos=tratamento_diferenca_mais_por_menos,
        criterios_ata_assembleia_inaugural=criterios_ata_assembleia_inaugural,
        criterios_tabela_vendas=criterios_tabela_vendas,
    )

    lance_embutido = quantizar_moeda(credito_vigente_d * lance_embutido_pct_d)
    lance_total = quantizar_moeda(lance_proprio_d + lance_embutido)
    lance_total_percentual = lance_total / credito_vigente_d if credito_vigente_d else Decimal("0")
    diferenca_mpm, diferenca_saldo, diferenca_credito, diferenca_paga = calcular_diferencas_mais_por_menos(
        plano_normalizado,
        credito_vigente_d,
        configuracao,
    )
    credito_liquido = max(
        Decimal("0"),
        quantizar_moeda(credito_vigente_d - lance_embutido - diferenca_credito - outras_deducoes_credito_d),
    )
    percentual_mensal_total = (
        configuracao.percentual_mensal_fundo_comum
        + configuracao.percentual_mensal_fundo_reserva
        + configuracao.percentual_mensal_taxa_administracao
    )
    taxa_admin_antecipada_valor = quantizar_moeda(
        credito_vigente_d * configuracao.taxa_administracao_antecipada_percentual
    )
    total_plano_sem_seguro = quantizar_moeda(credito_vigente_d * (Decimal("1") + taxa_admin_pct_d + fundo_reserva_pct_d))
    total_plano_com_seguro = quantizar_moeda(total_plano_sem_seguro + (seguro_mensal_d * Decimal(prazo_i)))
    parcela_normal_sem_seguro = quantizar_moeda(total_plano_sem_seguro / Decimal(prazo_i))
    parcela_mais_por_menos_sem_seguro = quantizar_moeda(
        credito_vigente_d
        * ((configuracao.taxa_cobertura_mais_por_menos * (Decimal("1") + fundo_reserva_pct_d)) + taxa_admin_pct_d)
        / Decimal(prazo_i)
    )
    parcela_ate_contemplacao_sem_seguro = (
        parcela_mais_por_menos_sem_seguro if plano_normalizado == "MAIS POR MENOS" else parcela_normal_sem_seguro
    )
    parcela_normal = quantizar_moeda(parcela_normal_sem_seguro + seguro_mensal_d)
    parcela_mais_por_menos = quantizar_moeda(parcela_mais_por_menos_sem_seguro + seguro_mensal_d)
    parcela_ate_contemplacao = quantizar_moeda(parcela_ate_contemplacao_sem_seguro + seguro_mensal_d)

    calculo_estimado = not (
        criterios_ata_assembleia_inaugural.strip() and criterios_tabela_vendas.strip() and configuracao.saldo_devedor_percentual > 0
    )

    return ResultadoSimulacao(
        credito=credito_vigente_d,
        lance_proprio=lance_proprio_d,
        lance_embutido_percentual=lance_embutido_pct_d,
        taxa_admin_percentual=taxa_admin_pct_d,
        fundo_reserva_percentual=fundo_reserva_pct_d,
        seguro_percentual=seguro_pct_calculado,
        prazo=prazo_i,
        plano=plano_normalizado,
        uso_lance=configuracao.forma_utilizacao_lance,
        mes_contemplacao=mes_i,
        configuracao_plano=configuracao,
        lance_embutido=lance_embutido,
        lance_total=lance_total,
        lance_total_percentual=lance_total_percentual,
        credito_liquido=credito_liquido,
        outras_antecipacoes=outras_antecipacoes_d,
        outras_deducoes_credito=outras_deducoes_credito_d,
        seguro_mensal=seguro_mensal_d,
        total_plano_sem_seguro=total_plano_sem_seguro,
        total_plano_com_seguro=total_plano_com_seguro,
        parcela_normal_sem_seguro=parcela_normal_sem_seguro,
        parcela_mais_por_menos_sem_seguro=parcela_mais_por_menos_sem_seguro,
        parcela_ate_contemplacao_sem_seguro=parcela_ate_contemplacao_sem_seguro,
        parcela_normal=parcela_normal,
        parcela_mais_por_menos=parcela_mais_por_menos,
        parcela_ate_contemplacao=parcela_ate_contemplacao,
        percentual_mensal_total=percentual_mensal_total,
        taxa_administracao_antecipada_valor=taxa_admin_antecipada_valor,
        diferenca_mais_por_menos=diferenca_mpm,
        diferenca_adicionada_saldo=diferenca_saldo,
        diferenca_deduzida_credito=diferenca_credito,
        diferenca_paga_recursos_proprios=diferenca_paga,
        calculo_estimado=calculo_estimado,
    )


def gerar_tabela_contemplacao(resultado: ResultadoSimulacao) -> list[dict[str, Decimal | int | str]]:
    if resultado.mes_contemplacao >= resultado.configuracao_plano.prazo_contratado_cota:
        return []

    linhas: list[dict[str, Decimal | int | str]] = []

    for mes in range(resultado.mes_contemplacao, resultado.configuracao_plano.prazo_contratado_cota):
        if resultado.uso_lance == MODO_REDUZIR_PRAZO:
            amortizacao = calcular_reduzir_prazo(resultado, mes)
        else:
            amortizacao = calcular_reduzir_parcela(resultado, mes)

        linhas.append(
            {
                "Mes de contemplacao": mes,
                "Parcelas restantes apos lance": amortizacao.parcelas_restantes,
                "Parcelas abatidas": amortizacao.parcelas_abatidas,
                "Mes previsto de quitacao": amortizacao.mes_previsto_quitacao,
                "Nova parcela": amortizacao.nova_parcela,
                "Saldo apos lance": amortizacao.saldo_total_futuro,
            }
        )

    return linhas
