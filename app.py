from __future__ import annotations

import re
from decimal import Decimal

import pandas as pd
import streamlit as st

from calculator import PLANOS, PRAZOS, USOS_LANCE, calcular_simulacao, gerar_tabela_contemplacao


st.set_page_config(
    page_title="Simulador Fiat Okubo",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def moeda(valor: Decimal | float | int | str) -> str:
    if isinstance(valor, str):
        return valor

    numero = float(valor)
    texto = f"R$ {numero:,.2f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def percentual(valor: Decimal | float | int) -> str:
    return f"{float(valor) * 100:.2f}%".replace(".", ",")


def formatar_percentual_input(valor: Decimal | float | int, casas_decimais: int = 2) -> str:
    texto = f"{float(valor):,.{casas_decimais}f}%"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def inteiro(valor: Decimal | float | int | str) -> str:
    if isinstance(valor, str):
        return valor
    return f"{int(valor):,}".replace(",", ".")


def parse_numero_brasileiro(texto: str) -> float:
    valor = re.sub(r"[^0-9,.-]", "", str(texto or "").strip())

    if not valor:
        return 0.0

    if "," in valor:
        valor = valor.replace(".", "").replace(",", ".")
    elif "." in valor:
        partes = valor.split(".")
        if len(partes) > 1 and len(partes[-1]) == 3:
            valor = "".join(partes)

    try:
        return max(0.0, float(valor))
    except ValueError:
        return 0.0


def normalizar_campo_moeda(chave: str) -> None:
    st.session_state[chave] = moeda(parse_numero_brasileiro(st.session_state.get(chave, "")))


def normalizar_campo_percentual(chave: str, casas_decimais: int = 2) -> None:
    st.session_state[chave] = formatar_percentual_input(
        parse_numero_brasileiro(st.session_state.get(chave, "")),
        casas_decimais,
    )


def campo_monetario(rotulo: str, chave: str, valor_inicial: float) -> float:
    if chave not in st.session_state:
        st.session_state[chave] = moeda(valor_inicial)

    texto = st.text_input(rotulo, key=chave, on_change=normalizar_campo_moeda, args=(chave,))
    return parse_numero_brasileiro(texto)


def campo_percentual(rotulo: str, chave: str, valor_inicial: float, casas_decimais: int = 2) -> float:
    if chave not in st.session_state:
        st.session_state[chave] = formatar_percentual_input(valor_inicial, casas_decimais)

    texto = st.text_input(
        rotulo,
        key=chave,
        on_change=normalizar_campo_percentual,
        args=(chave, casas_decimais),
    )
    return parse_numero_brasileiro(texto) / 100


def aplicar_estilo() -> None:
    st.markdown(
        """
        <style>
            :root {
                --bg: #f6f7f9;
                --panel: #ffffff;
                --text: #1f2937;
                --muted: #6b7280;
                --line: #d9dee7;
                --brand: #334155;
                --gold: #b08a3c;
                --green: #0f766e;
            }

            .stApp {
                background: var(--bg);
                color: var(--text);
            }

            [data-testid="stHeader"] {
                background: transparent;
            }

            [data-testid="stSidebar"] {
                display: none;
            }

            .block-container {
                padding-top: 2.2rem;
                padding-bottom: 2rem;
                max-width: 1180px;
            }

            .topbar {
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 16px;
                padding: 18px 0 8px;
                border-bottom: 1px solid var(--line);
                margin-bottom: 22px;
            }

            .brand-title {
                font-size: 1.85rem;
                font-weight: 800;
                color: var(--text);
                letter-spacing: 0;
                margin: 0;
            }

            .brand-subtitle {
                color: var(--muted);
                font-size: 0.95rem;
                margin-top: 4px;
            }

            .tag {
                border: 1px solid #c8b37a;
                background: #fff8e6;
                color: #7a5b16;
                padding: 8px 12px;
                border-radius: 8px;
                font-weight: 700;
                white-space: nowrap;
            }

            .section-title {
                font-size: 1.15rem;
                font-weight: 800;
                color: var(--brand);
                margin: 8px 0 4px;
            }

            div[data-testid="stMetric"] {
                background: var(--panel);
                border: 1px solid var(--line);
                border-top: 4px solid var(--gold);
                border-radius: 8px;
                padding: 16px 16px 14px;
                box-shadow: 0 6px 16px rgba(15, 23, 42, 0.05);
            }

            div[data-testid="stMetricLabel"] p {
                color: var(--muted);
                font-weight: 700;
            }

            div[data-testid="stMetricValue"] {
                color: var(--text);
                font-weight: 800;
            }

            .result-box {
                background: #ffffff;
                border: 1px solid var(--line);
                border-radius: 8px;
                padding: 18px;
                margin-top: 6px;
                box-shadow: 0 8px 22px rgba(15, 23, 42, 0.06);
            }

            .result-box strong {
                color: var(--green);
            }

            .small-note {
                color: var(--muted);
                font-size: 0.86rem;
                line-height: 1.45;
            }

            .stButton > button {
                border-radius: 8px;
                border: 1px solid #9a7a33;
                background: #b08a3c;
                color: white;
                font-weight: 800;
            }

            .stDownloadButton > button {
                border-radius: 8px;
                border: 1px solid var(--brand);
                background: var(--brand);
                color: white;
                font-weight: 800;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def montar_resumo(resultado) -> str:
    return "\n".join(
        [
            "Simulacao Fiat Okubo",
            f"Credito: {moeda(resultado.credito)}",
            f"Prazo: {resultado.prazo} meses",
            f"Plano: {resultado.plano}",
            f"Lance proprio: {moeda(resultado.lance_proprio)}",
            f"Lance embutido: {moeda(resultado.lance_embutido)} ({percentual(resultado.lance_embutido_percentual)})",
            f"Lance total: {moeda(resultado.lance_total)} ({percentual(resultado.lance_total_percentual)})",
            f"Credito liquido: {moeda(resultado.credito_liquido)}",
            f"Parcela ate contemplacao: {moeda(resultado.parcela_ate_contemplacao)}",
            f"Total do plano com seguro: {moeda(resultado.total_plano_com_seguro)}",
        ]
    )


def main() -> None:
    aplicar_estilo()

    st.markdown(
        """
        <div class="topbar">
            <div>
                <h1 class="brand-title">Simulador Fiat Okubo</h1>
                <div class="brand-subtitle">Calcule credito, lance, parcelas e cenarios de contemplacao em tempo real.</div>
            </div>
            <div class="tag">Uso consultivo</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.container():
        st.markdown('<div class="section-title">Dados da simulacao</div>', unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1.1, 1.1, 0.9])

        with col1:
            credito = campo_monetario("Credito a contratar", "credito_input", 100000.0)
            lance_proprio = campo_monetario("Lance recurso proprio", "lance_proprio_input", 25000.0)
            lance_embutido_pct = st.slider(
                "Lance embutido",
                min_value=0,
                max_value=25,
                value=25,
                step=1,
                format="%d%%",
            ) / 100

        with col2:
            prazo = st.selectbox("Prazo", PRAZOS, index=4)
            plano = st.selectbox("Plano", PLANOS, index=1)
            uso_lance = st.selectbox("Uso do lance", USOS_LANCE, index=0)
            mes_contemplacao = st.number_input("Simular contemplacao a partir do mes", min_value=1, max_value=120, value=1, step=1)

        with col3:
            taxa_admin_pct = campo_percentual("Taxa administrativa", "taxa_admin_input", 20.0)
            fundo_reserva_pct = campo_percentual("Fundo reserva", "fundo_reserva_input", 3.0)
            seguro_pct = campo_percentual("Seguro vida ao mes", "seguro_input", 0.075, casas_decimais=3)

    resultado = calcular_simulacao(
        credito=credito,
        lance_proprio=lance_proprio,
        lance_embutido_percentual=lance_embutido_pct,
        taxa_admin_percentual=taxa_admin_pct,
        fundo_reserva_percentual=fundo_reserva_pct,
        seguro_percentual=seguro_pct,
        prazo=prazo,
        plano=plano,
        uso_lance=uso_lance,
        mes_contemplacao=mes_contemplacao,
    )

    st.markdown('<div class="section-title">Resultado</div>', unsafe_allow_html=True)
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Parcela ate contemplacao", moeda(resultado.parcela_ate_contemplacao))
    k2.metric("Lance total", moeda(resultado.lance_total), percentual(resultado.lance_total_percentual))
    k3.metric("Credito liquido", moeda(resultado.credito_liquido))
    k4.metric("Total com seguro", moeda(resultado.total_plano_com_seguro))

    r1, r2 = st.columns([1.1, 0.9])
    with r1:
        st.markdown(
            f"""
            <div class="result-box">
                <strong>Resumo do plano</strong><br><br>
                Lance embutido: <strong>{moeda(resultado.lance_embutido)}</strong><br>
                Seguro mensal: <strong>{moeda(resultado.seguro_mensal)}</strong><br>
                Parcela normal com seguro: <strong>{moeda(resultado.parcela_normal)}</strong><br>
                Parcela Mais por Menos com seguro: <strong>{moeda(resultado.parcela_mais_por_menos)}</strong><br>
                Total do plano sem seguro: <strong>{moeda(resultado.total_plano_sem_seguro)}</strong>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with r2:
        resumo = montar_resumo(resultado)
        st.text_area("Resumo para envio", resumo, height=214)

    st.markdown('<div class="section-title">Cenario de contemplacao</div>', unsafe_allow_html=True)
    tabela = gerar_tabela_contemplacao(resultado)

    if tabela:
        st.caption(
            "A coluna de quitacao e contada desde o inicio do plano. "
            "Exemplo: se contemplar no mes 20 e aparecer quitacao no mes 53, "
            "faltam 33 parcelas apos o lance."
        )
        df = pd.DataFrame(tabela)
        df["Parcelas restantes apos lance"] = df["Parcelas restantes apos lance"].apply(inteiro)
        df["Parcelas abatidas"] = df["Parcelas abatidas"].apply(inteiro)
        df["Mes previsto de quitacao"] = df["Mes previsto de quitacao"].apply(inteiro)
        df["Nova parcela"] = df["Nova parcela"].apply(moeda)
        df["Saldo apos lance"] = df["Saldo apos lance"].apply(moeda)
        st.dataframe(df, use_container_width=True, hide_index=True)

        csv = df.to_csv(index=False, sep=";").encode("utf-8-sig")
        st.download_button(
            "Baixar simulacao em CSV",
            data=csv,
            file_name="simulacao_fiat_okubo.csv",
            mime="text/csv",
        )
    else:
        st.info("Para simular a contemplacao, escolha um mes menor que o prazo total.")

    st.caption(
        "Simulador consultivo. Os valores podem variar conforme regra comercial, administradora, assembleia, credito e vigencia do plano."
    )


if __name__ == "__main__":
    main()
