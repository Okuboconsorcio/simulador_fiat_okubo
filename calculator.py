"""Motor de cálculo do simulador Fiat/Embracon.

Modelo baseado no razão percentual da Embracon, validado contra extratos
reais de consorciados (grupos 009915, 009942, 009943, 009956, 009958) e
contra o Regulamento Fiat (Versão 3 - Resolução 285/23 - C.E. 07/24):

- Toda a contabilidade é feita em percentual do crédito vigente.
- Total do plano = 100% (fundo comum) + FR + TA. Seguro é cobrado à parte,
  todo mês, como percentual fixo do crédito.
- Parcela normal = (100 + FR + TA) / prazo.
- Parcela Mais por Menos = (75% x (100 + FR) + TA) / prazo  (Cláusula 3.4:
  redução de 25% do fundo comum e do fundo de reserva até a contemplação).
- Saldo devedor na contemplação = total - percentuais pagos - lance.
  Validado com exatidão de 4 casas decimais nos extratos com lance
  (saldos de 90,7064% e 55,1177% reproduzidos exatamente).
- Lance com REDUÇÃO DE PRAZO (ordem inversa dos vencimentos): há isenção
  da TA sobre o lance (Cláusula 3.3, §7º/8º). O lance quita parcelas
  vincendas ao percentual ideal de FC+FR: n = lance% / ((100+FR)/prazo).
  Confirmado pelos rótulos "Lance 19 pcls." e "Lance 51 pcls." dos extratos.
- Lance com REDUÇÃO DE PARCELA (amortização linear/diluída, "rateado"):
  sem isenção de TA. Nova parcela = saldo% / meses restantes, respeitado
  o percentual mínimo pós-renegociação (Cláusula 8ª, §único, "b").

Divergências residuais de centavos (< R$ 0,25) em relação aos extratos
decorrem do arredondamento por componente (FC/FR/TA a 4 casas) usado
internamente pela administradora.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_FLOOR, ROUND_HALF_UP
from typing import Sequence

# ---------------------------------------------------------------------------
# Tabelas comerciais
# ---------------------------------------------------------------------------

TABELA_LEVES = "LEVES"
TABELA_PESADOS = "PESADOS"
TABELAS = (TABELA_LEVES, TABELA_PESADOS)


@dataclass(frozen=True)
class ConfiguracaoTabela:
    codigo: str
    nome: str
    descricao: str
    taxa_admin: Decimal                 # fração (0.20 = 20%)
    fundo_reserva: Decimal              # fração
    seguro_mensal_pct: Decimal          # fração do crédito ao mês
    prazos_normais: tuple[int, ...]
    prazos_mais_por_menos: tuple[int, ...]
    piso_fundo_comum_mensal: Decimal    # Cláusula 8ª, §único, b, item 2
    piso_parcela_renegociada: Decimal   # fração/mês, calibrado por extrato
    taxa_cadastro_padrao: Decimal       # fração do crédito, paga do crédito


CONFIGURACOES_TABELAS: dict[str, ConfiguracaoTabela] = {
    TABELA_LEVES: ConfiguracaoTabela(
        codigo=TABELA_LEVES,
        nome="Leves — FTA (Flex TA Antecipada)",
        descricao="Automóveis e motocicletas. TA 20%, FR 3%, seguro 0,075030%/mês.",
        taxa_admin=Decimal("0.20"),
        fundo_reserva=Decimal("0.03"),
        seguro_mensal_pct=Decimal("0.00075030"),
        prazos_normais=(36, 50, 60, 70, 80),
        prazos_mais_por_menos=(36, 50, 60, 70, 80),
        piso_fundo_comum_mensal=Decimal("0.01"),
        piso_parcela_renegociada=Decimal("0.01125"),
        taxa_cadastro_padrao=Decimal("0.01"),
    ),
    TABELA_PESADOS: ConfiguracaoTabela(
        codigo=TABELA_PESADOS,
        nome="Pesados — TSA (Sem Antecipação)",
        descricao="Caminhões, ônibus e veículos pesados. TA 13%, FR 3%, seguro 0,070760%/mês.",
        taxa_admin=Decimal("0.13"),
        fundo_reserva=Decimal("0.03"),
        seguro_mensal_pct=Decimal("0.00070760"),
        prazos_normais=(36, 50, 60, 70, 85, 100),
        prazos_mais_por_menos=(36, 50, 60, 70),
        piso_fundo_comum_mensal=Decimal("0.0075"),
        piso_parcela_renegociada=Decimal("0.0084375"),
        taxa_cadastro_padrao=Decimal("0.01"),
    ),
}

# ---------------------------------------------------------------------------
# Constantes públicas (compatibilidade com app.py)
# ---------------------------------------------------------------------------

PLANOS = ("NORMAL", "MAIS POR MENOS")
PRAZOS = CONFIGURACOES_TABELAS[TABELA_LEVES].prazos_normais

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

FRACAO_MAIS_POR_MENOS = Decimal("0.75")   # Cláusula 3.4
DIFERENCA_MAIS_POR_MENOS = Decimal("0.25")
LIMITE_LANCE_EMBUTIDO = Decimal("0.25")   # lance facilitado, tabelas de venda

CENTAVOS = Decimal("0.01")


def _d(value: float | int | str | Decimal | None) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    return Decimal(str(value))


def quantizar_moeda(value: Decimal) -> Decimal:
    return value.quantize(CENTAVOS, rounding=ROUND_HALF_UP)


def round_half_up(value: Decimal) -> int:
    return int(value.to_integral_value(rounding=ROUND_HALF_UP))


def floor_decimal(value: Decimal) -> int:
    return int(value.to_integral_value(rounding=ROUND_FLOOR))


def normalizar_tabela(valor: str | None) -> str:
    tabela = str(valor or "").strip().upper()
    return tabela if tabela in TABELAS else TABELA_LEVES


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
    if tratamento in TRATAMENTOS_DIFERENCA_MPM:
        return tratamento
    return TRATAMENTO_RENEGOCIAR_NO_SALDO


def prazos_disponiveis(tabela: str, plano: str) -> tuple[int, ...]:
    config = CONFIGURACOES_TABELAS[normalizar_tabela(tabela)]
    if plano == "MAIS POR MENOS":
        return config.prazos_mais_por_menos
    return config.prazos_normais


# ---------------------------------------------------------------------------
# Resultados
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResultadoAmortizacao:
    parcelas_restantes: Decimal
    parcelas_abatidas: Decimal | str
    mes_previsto_quitacao: int
    nova_parcela: Decimal | str
    saldo_total_futuro: Decimal
    saldo_sem_seguro_futuro: Decimal
    descricao: str


@dataclass(frozen=True)
class ResultadoSimulacao:
    # Entradas normalizadas
    tabela: str
    configuracao_tabela: ConfiguracaoTabela
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
    tratamento_diferenca_mais_por_menos: str
    taxa_cadastro_percentual: Decimal
    # Lance
    lance_embutido: Decimal
    lance_total: Decimal
    lance_total_percentual: Decimal
    # Percentuais mensais (frações do crédito)
    percentual_total_plano: Decimal
    parcela_normal_pct: Decimal
    parcela_mais_por_menos_pct: Decimal
    parcela_pre_contemplacao_pct: Decimal
    percentual_ideal_fc_fr: Decimal
    # Valores em reais
    seguro_mensal: Decimal
    parcela_normal_sem_seguro: Decimal
    parcela_mais_por_menos_sem_seguro: Decimal
    parcela_ate_contemplacao_sem_seguro: Decimal
    parcela_normal: Decimal
    parcela_mais_por_menos: Decimal
    parcela_ate_contemplacao: Decimal
    total_plano_sem_seguro: Decimal
    total_plano_com_seguro: Decimal
    # Contemplação / crédito
    taxa_cadastro_valor: Decimal
    credito_liquido: Decimal
    diferenca_mais_por_menos: Decimal
    diferenca_adicionada_saldo: Decimal
    diferenca_deduzida_credito: Decimal
    diferenca_paga_recursos_proprios: Decimal
    outras_antecipacoes: Decimal
    outras_deducoes_credito: Decimal
    calculo_estimado: bool

    # Compatibilidade: campo usado pelo app para limitar a tabela de cenários.
    @property
    def prazo_contratado_cota(self) -> int:
        return self.prazo


# ---------------------------------------------------------------------------
# Simulação
# ---------------------------------------------------------------------------


def calcular_simulacao(
    *,
    credito: float | int | str | Decimal,
    lance_proprio: float | int | str | Decimal,
    lance_embutido_percentual: float | int | str | Decimal,
    prazo: int,
    plano: str,
    uso_lance: str,
    mes_contemplacao: int,
    tabela: str = TABELA_LEVES,
    taxa_admin_percentual: float | int | str | Decimal | None = None,
    fundo_reserva_percentual: float | int | str | Decimal | None = None,
    seguro_percentual: float | int | str | Decimal | None = None,
    seguro_mensal: float | int | str | Decimal | None = None,
    tratamento_diferenca_mais_por_menos: str = TRATAMENTO_RENEGOCIAR_NO_SALDO,
    taxa_cadastro_percentual: float | int | str | Decimal | None = None,
    outras_antecipacoes: float | int | str | Decimal = Decimal("0"),
    outras_deducoes_credito: float | int | str | Decimal = Decimal("0"),
    **_ignorados: object,
) -> ResultadoSimulacao:
    tabela_norm = normalizar_tabela(tabela)
    config = CONFIGURACOES_TABELAS[tabela_norm]

    credito_d = quantizar_moeda(max(_d(credito), Decimal("0")))
    if credito_d <= 0:
        raise ValueError("O crédito precisa ser maior que zero.")

    prazo_i = int(prazo)
    if prazo_i <= 0:
        raise ValueError("O prazo precisa ser maior que zero.")

    plano_norm = plano if plano in PLANOS else "NORMAL"
    uso_norm = normalizar_uso_lance(uso_lance)
    tratamento = normalizar_tratamento_diferenca(tratamento_diferenca_mais_por_menos)
    mes_i = max(1, int(mes_contemplacao))

    taxa_admin = max(_d(taxa_admin_percentual), Decimal("0")) if taxa_admin_percentual is not None else config.taxa_admin
    fundo_reserva = (
        max(_d(fundo_reserva_percentual), Decimal("0"))
        if fundo_reserva_percentual is not None
        else config.fundo_reserva
    )
    seguro_pct = (
        max(_d(seguro_percentual), Decimal("0"))
        if seguro_percentual is not None
        else config.seguro_mensal_pct
    )
    taxa_cadastro = (
        max(_d(taxa_cadastro_percentual), Decimal("0"))
        if taxa_cadastro_percentual is not None
        else config.taxa_cadastro_padrao
    )

    lance_proprio_d = quantizar_moeda(max(_d(lance_proprio), Decimal("0")))
    lance_embutido_pct = min(max(_d(lance_embutido_percentual), Decimal("0")), LIMITE_LANCE_EMBUTIDO)
    lance_embutido = quantizar_moeda(credito_d * lance_embutido_pct)
    lance_total = quantizar_moeda(lance_proprio_d + lance_embutido)
    lance_total_pct = lance_total / credito_d

    outras_antecipacoes_d = quantizar_moeda(max(_d(outras_antecipacoes), Decimal("0")))
    outras_deducoes_d = quantizar_moeda(max(_d(outras_deducoes_credito), Decimal("0")))

    # Percentuais mensais -----------------------------------------------------
    percentual_total = Decimal("1") + fundo_reserva + taxa_admin
    parcela_normal_pct = percentual_total / Decimal(prazo_i)
    parcela_mpm_pct = (FRACAO_MAIS_POR_MENOS * (Decimal("1") + fundo_reserva) + taxa_admin) / Decimal(prazo_i)
    parcela_pre_pct = parcela_mpm_pct if plano_norm == "MAIS POR MENOS" else parcela_normal_pct
    pct_ideal_fc_fr = (Decimal("1") + fundo_reserva) / Decimal(prazo_i)

    seguro_mensal_d = (
        quantizar_moeda(max(_d(seguro_mensal), Decimal("0")))
        if seguro_mensal is not None and _d(seguro_mensal) > 0
        else quantizar_moeda(credito_d * seguro_pct)
    )

    parcela_normal_sem_seguro = quantizar_moeda(credito_d * parcela_normal_pct)
    parcela_mpm_sem_seguro = quantizar_moeda(credito_d * parcela_mpm_pct)
    parcela_pre_sem_seguro = parcela_mpm_sem_seguro if plano_norm == "MAIS POR MENOS" else parcela_normal_sem_seguro

    total_sem_seguro = quantizar_moeda(credito_d * percentual_total)
    total_com_seguro = quantizar_moeda(total_sem_seguro + seguro_mensal_d * Decimal(prazo_i))

    # Diferença do Mais por Menos (Cláusula 3.4, §1º) -------------------------
    # Incisos I, II e IV: a diferença tratada é a "recolhida a menor ANTES da
    # contemplação" (inciso I, "b"), ou seja, proporcional aos meses pagos:
    # meses x 25% do ideal mensal de FC+FR. Validado nos extratos reais: o
    # saldo na contemplação contém exatamente essa diferença proporcional.
    # Inciso III é a exceção: são 25% fixos do crédito ("será disponibilizado
    # 75% do crédito"), que amortizam o saldo devedor.
    if plano_norm == "MAIS POR MENOS":
        diferenca_proporcional_pct = (parcela_normal_pct - parcela_mpm_pct) * Decimal(mes_i)
        diferenca_proporcional = quantizar_moeda(credito_d * diferenca_proporcional_pct)
        if tratamento == TRATAMENTO_DEDUZIR_DO_CREDITO:
            diferenca_mpm = quantizar_moeda(credito_d * DIFERENCA_MAIS_POR_MENOS)
        else:
            diferenca_mpm = diferenca_proporcional
    else:
        diferenca_proporcional = Decimal("0")
        diferenca_mpm = Decimal("0")

    diferenca_saldo = diferenca_mpm if tratamento == TRATAMENTO_RENEGOCIAR_NO_SALDO else Decimal("0")
    diferenca_credito = diferenca_mpm if tratamento == TRATAMENTO_DEDUZIR_DO_CREDITO else Decimal("0")
    diferenca_paga = diferenca_mpm if tratamento == TRATAMENTO_PAGAR_RECURSOS_PROPRIOS else Decimal("0")

    taxa_cadastro_valor = quantizar_moeda(credito_d * taxa_cadastro)
    credito_liquido = max(
        Decimal("0"),
        quantizar_moeda(credito_d - lance_embutido - diferenca_credito - taxa_cadastro_valor - outras_deducoes_d),
    )

    return ResultadoSimulacao(
        tabela=tabela_norm,
        configuracao_tabela=config,
        credito=credito_d,
        lance_proprio=lance_proprio_d,
        lance_embutido_percentual=lance_embutido_pct,
        taxa_admin_percentual=taxa_admin,
        fundo_reserva_percentual=fundo_reserva,
        seguro_percentual=seguro_pct,
        prazo=prazo_i,
        plano=plano_norm,
        uso_lance=uso_norm,
        mes_contemplacao=mes_i,
        tratamento_diferenca_mais_por_menos=tratamento,
        taxa_cadastro_percentual=taxa_cadastro,
        lance_embutido=lance_embutido,
        lance_total=lance_total,
        lance_total_percentual=lance_total_pct,
        percentual_total_plano=percentual_total,
        parcela_normal_pct=parcela_normal_pct,
        parcela_mais_por_menos_pct=parcela_mpm_pct,
        parcela_pre_contemplacao_pct=parcela_pre_pct,
        percentual_ideal_fc_fr=pct_ideal_fc_fr,
        seguro_mensal=seguro_mensal_d,
        parcela_normal_sem_seguro=parcela_normal_sem_seguro,
        parcela_mais_por_menos_sem_seguro=parcela_mpm_sem_seguro,
        parcela_ate_contemplacao_sem_seguro=parcela_pre_sem_seguro,
        parcela_normal=quantizar_moeda(parcela_normal_sem_seguro + seguro_mensal_d),
        parcela_mais_por_menos=quantizar_moeda(parcela_mpm_sem_seguro + seguro_mensal_d),
        parcela_ate_contemplacao=quantizar_moeda(parcela_pre_sem_seguro + seguro_mensal_d),
        total_plano_sem_seguro=total_sem_seguro,
        total_plano_com_seguro=total_com_seguro,
        taxa_cadastro_valor=taxa_cadastro_valor,
        credito_liquido=credito_liquido,
        diferenca_mais_por_menos=diferenca_mpm,
        diferenca_adicionada_saldo=diferenca_saldo,
        diferenca_deduzida_credito=diferenca_credito,
        diferenca_paga_recursos_proprios=diferenca_paga,
        outras_antecipacoes=outras_antecipacoes_d,
        outras_deducoes_credito=outras_deducoes_d,
        calculo_estimado=True,
    )


# ---------------------------------------------------------------------------
# Saldo devedor e amortização do lance
# ---------------------------------------------------------------------------


def saldo_percentual_apos_lance(resultado: ResultadoSimulacao, mes: int) -> Decimal:
    """Saldo (FC + FR + TA) em fração do crédito, na assembleia de contemplação.

    Fórmula validada com exatidão nos extratos reais:
    saldo% = (100% + FR + TA) - meses pagos x parcela% - lance% - abatimentos.

    No Mais por Menos, a diferença recolhida a menor até a contemplação
    (proporcional aos meses pagos) permanece naturalmente no saldo
    ("renegociar no saldo"). Se for paga com recursos próprios ou já
    antecipada, o saldo iguala o de quem pagou o ideal; no "deduzir do
    crédito" (inciso III), 25% do crédito amortizam o saldo.
    """
    pago_pct = resultado.parcela_pre_contemplacao_pct * Decimal(int(mes))
    lance_pct = resultado.lance_total / resultado.credito
    antecipacoes_pct = resultado.outras_antecipacoes / resultado.credito

    abate_diferenca = Decimal("0")
    if resultado.plano == "MAIS POR MENOS":
        diferenca_proporcional_pct = (
            resultado.parcela_normal_pct - resultado.parcela_mais_por_menos_pct
        ) * Decimal(int(mes))
        if resultado.tratamento_diferenca_mais_por_menos in (
            TRATAMENTO_PAGAR_RECURSOS_PROPRIOS,
            TRATAMENTO_DIFERENCA_JA_ANTECIPADA,
        ):
            # Incisos II e IV: quitada a diferença recolhida a menor até a
            # contemplação, o saldo iguala o de quem pagou o percentual ideal.
            abate_diferenca = diferenca_proporcional_pct
        elif resultado.tratamento_diferenca_mais_por_menos == TRATAMENTO_DEDUZIR_DO_CREDITO:
            # Inciso III: 25% do crédito amortizam o saldo devedor.
            abate_diferenca = DIFERENCA_MAIS_POR_MENOS

    saldo = resultado.percentual_total_plano - pago_pct - lance_pct - antecipacoes_pct - abate_diferenca
    return max(Decimal("0"), saldo)


def _resultado_quitado(mes: int, meses_originais: int, descricao: str) -> ResultadoAmortizacao:
    return ResultadoAmortizacao(
        parcelas_restantes=Decimal("0"),
        parcelas_abatidas=Decimal(meses_originais),
        mes_previsto_quitacao=mes,
        nova_parcela="QUITADO",
        saldo_total_futuro=Decimal("0"),
        saldo_sem_seguro_futuro=Decimal("0"),
        descricao=descricao,
    )


def calcular_reduzir_prazo(resultado: ResultadoSimulacao, mes: int) -> ResultadoAmortizacao:
    """Lance quitando parcelas vincendas na ordem inversa dos vencimentos.

    Cláusula 3.3, §7º: com isenção da TA, o lance amortiza ao percentual
    ideal do fundo comum (+ FR proporcional, §10). O número de parcelas
    quitadas equivale a lance% / ((100% + FR)/prazo) — coerente com os
    rótulos "Lance N pcls." dos extratos da administradora.
    A contribuição mensal é mantida; no Mais por Menos, a diferença
    renegociada é diluída nas parcelas vincendas.
    """
    meses_originais = max(0, resultado.prazo - int(mes))
    if meses_originais == 0:
        return _resultado_quitado(mes, 0, "Sem contribuições vincendas.")

    lance_pct = (resultado.lance_total + resultado.outras_antecipacoes) / resultado.credito
    parcelas_abatidas = min(meses_originais, floor_decimal(lance_pct / resultado.percentual_ideal_fc_fr))
    residuo_lance_pct = max(
        Decimal("0"),
        lance_pct - Decimal(parcelas_abatidas) * resultado.percentual_ideal_fc_fr,
    )

    restantes = meses_originais - parcelas_abatidas
    if restantes <= 0:
        return _resultado_quitado(mes, meses_originais, "Lance quita todas as contribuições vincendas.")

    # Parcela pós-contemplação: percentual pleno do plano.
    parcela_pct = resultado.parcela_normal_pct

    # Diferença do Mais por Menos recolhida a menor até a contemplação
    # (proporcional aos meses pagos), renegociada e diluída nas parcelas
    # vincendas (Cláusula 3.4, inciso I). Se paga com recursos próprios ou
    # já antecipada, nada é acrescido.
    abatimento_extra_pct = Decimal("0")
    if resultado.plano == "MAIS POR MENOS":
        diferenca_proporcional_pct = (
            resultado.parcela_normal_pct - resultado.parcela_mais_por_menos_pct
        ) * Decimal(int(mes))
        if resultado.tratamento_diferenca_mais_por_menos == TRATAMENTO_RENEGOCIAR_NO_SALDO:
            parcela_pct = parcela_pct + (diferenca_proporcional_pct / Decimal(restantes))
        elif resultado.tratamento_diferenca_mais_por_menos == TRATAMENTO_DEDUZIR_DO_CREDITO:
            # Inciso III: 25% do crédito amortizam o saldo (sem isenção de TA,
            # pois não é lance) — quitam parcelas adicionais ao percentual pleno.
            abatimento_extra_pct = DIFERENCA_MAIS_POR_MENOS

    if abatimento_extra_pct > 0:
        extras = min(restantes, floor_decimal(abatimento_extra_pct / resultado.parcela_normal_pct))
        restantes -= int(extras)
        parcelas_abatidas = parcelas_abatidas + extras
        if restantes <= 0:
            return _resultado_quitado(mes, meses_originais, "Lance e diferença quitam as contribuições vincendas.")

    nova_parcela_sem_seguro = quantizar_moeda(resultado.credito * parcela_pct)
    # Resíduo do lance abate a primeira contribuição seguinte (Cláusula 8ª, "c");
    # para fins de saldo, desconta-se do total.
    saldo_sem_seguro = max(
        Decimal("0"),
        quantizar_moeda(
            Decimal(restantes) * resultado.credito * parcela_pct - resultado.credito * residuo_lance_pct
        ),
    )
    saldo_com_seguro = quantizar_moeda(saldo_sem_seguro + resultado.seguro_mensal * Decimal(restantes))

    return ResultadoAmortizacao(
        parcelas_restantes=Decimal(restantes),
        parcelas_abatidas=Decimal(parcelas_abatidas),
        mes_previsto_quitacao=mes + restantes,
        nova_parcela=quantizar_moeda(nova_parcela_sem_seguro + resultado.seguro_mensal),
        saldo_total_futuro=saldo_com_seguro,
        saldo_sem_seguro_futuro=saldo_sem_seguro,
        descricao=(
            "Quitação na ordem inversa dos vencimentos, com isenção da taxa de "
            "administração sobre o lance (parcela mantida no percentual pleno)."
        ),
    )


def calcular_reduzir_parcela(resultado: ResultadoSimulacao, mes: int) -> ResultadoAmortizacao:
    """Lance amortizando o saldo devedor de forma linear/diluída ("rateado").

    Sem isenção de TA (Cláusula 3.3, §8º). Nova parcela = saldo% dividido
    pelos meses restantes do plano, respeitado o percentual mínimo mensal
    pós-renegociação (Cláusula 8ª, §único, "b"). Quando o piso é atingido,
    o prazo é reduzido: meses = saldo% / piso.
    Validado contra extratos reais: parcela mantendo prazo (74 meses) e
    parcela com prazo reduzido para 49 meses reproduzidas com erro < R$ 0,25.
    """
    meses_originais = max(0, resultado.prazo - int(mes))
    if meses_originais == 0:
        return _resultado_quitado(mes, 0, "Sem contribuições vincendas.")

    saldo_pct = saldo_percentual_apos_lance(resultado, mes)
    if saldo_pct <= 0:
        return _resultado_quitado(mes, meses_originais, "Lance quita o saldo devedor.")

    piso = resultado.configuracao_tabela.piso_parcela_renegociada
    parcela_pct = saldo_pct / Decimal(meses_originais)

    if parcela_pct < piso:
        restantes = max(1, min(meses_originais, round_half_up(saldo_pct / piso)))
        parcela_pct = saldo_pct / Decimal(restantes)
        descricao = (
            "Amortização linear com percentual mínimo regulamentar aplicado: "
            "o prazo é reduzido e a cota encerra antes do previsto."
        )
    else:
        restantes = meses_originais
        descricao = "Amortização linear/diluída do saldo, mantendo o prazo contratado."

    nova_parcela_sem_seguro = quantizar_moeda(resultado.credito * parcela_pct)
    saldo_sem_seguro = quantizar_moeda(resultado.credito * saldo_pct)
    saldo_com_seguro = quantizar_moeda(saldo_sem_seguro + resultado.seguro_mensal * Decimal(restantes))

    return ResultadoAmortizacao(
        parcelas_restantes=Decimal(restantes),
        parcelas_abatidas=Decimal(meses_originais - restantes) if restantes < meses_originais else "-",
        mes_previsto_quitacao=mes + restantes,
        nova_parcela=quantizar_moeda(nova_parcela_sem_seguro + resultado.seguro_mensal),
        saldo_total_futuro=saldo_com_seguro,
        saldo_sem_seguro_futuro=saldo_sem_seguro,
        descricao=descricao,
    )


def gerar_tabela_contemplacao(resultado: ResultadoSimulacao) -> list[dict[str, Decimal | int | str]]:
    if resultado.mes_contemplacao >= resultado.prazo:
        return []

    linhas: list[dict[str, Decimal | int | str]] = []
    for mes in range(resultado.mes_contemplacao, resultado.prazo):
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
