from __future__ import annotations

import html
import json
import re
from datetime import date, timedelta
from decimal import Decimal
from textwrap import dedent

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from calculator import PLANOS, PRAZOS, USOS_LANCE, calcular_simulacao, gerar_tabela_contemplacao
from logos import LOGOS

TIPOS_LANCE = ("Sem lance", "Lance livre", "Lance fixo (25%)", "Lance fixo (50%)")
LANCE_FIXO_PERCENTUAIS = {
    "Lance fixo (25%)": 25.0,
    "Lance fixo (50%)": 50.0,
}
LIMITE_LANCE_EMBUTIDO_PERCENTUAL = 25.0
COR_MARCA = "#3B369E"


st.set_page_config(
    page_title="Simulador Fiat Okubo",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def asset_data_uri(nome_arquivo: str) -> str:
    return LOGOS[nome_arquivo]


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


def normalizar_lance_proprio(chave: str) -> None:
    normalizar_campo_moeda(chave)
    st.session_state["ultimo_lance_alterado"] = "proprio"


def marcar_lance_embutido() -> None:
    st.session_state["ultimo_lance_alterado"] = "embutido"


def marcar_tipo_lance() -> None:
    st.session_state["ultimo_lance_alterado"] = "embutido"


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


def formatar_data_resumo(valor: object) -> str:
    if isinstance(valor, date):
        return valor.strftime("%d/%m/%Y")
    return str(valor or "").strip()


def renderizar_formulario_proposta() -> dict[str, object]:
    st.markdown('<div class="section-title">Dados da proposta</div>', unsafe_allow_html=True)

    hoje = date.today()
    col1, col2, col3 = st.columns(3)
    with col1:
        data_proposta = st.date_input("Data da proposta", value=hoje, format="DD/MM/YYYY")
    with col2:
        validade_proposta = st.date_input(
            "Validade da proposta",
            value=hoje + timedelta(days=7),
            format="DD/MM/YYYY",
        )
    with col3:
        vendedor = st.text_input("Vendedor")

    col4, col5, col6 = st.columns(3)
    with col4:
        nome_completo = st.text_input("Nome completo")
    with col5:
        cpf = st.text_input("CPF")
    with col6:
        email = st.text_input("E-mail")

    col7, col8, col9 = st.columns(3)
    with col7:
        data_nascimento = st.date_input("Data de nascimento", value=None, format="DD/MM/YYYY")
    with col8:
        estado = st.text_input("Estado")
    with col9:
        cidade = st.text_input("Cidade")

    col10, col11, col12 = st.columns(3)
    with col10:
        carro_referencia = st.text_input("Carro referencia")
    with col11:
        ano = st.text_input("Ano")
    with col12:
        modelo = st.text_input("Modelo")

    return {
        "data_proposta": data_proposta,
        "validade_proposta": validade_proposta,
        "vendedor": vendedor,
        "nome_completo": nome_completo,
        "cpf": cpf,
        "email": email,
        "data_nascimento": data_nascimento,
        "estado": estado,
        "cidade": cidade,
        "carro_referencia": carro_referencia,
        "ano": ano,
        "modelo": modelo,
    }


def sincronizar_lance_por_tipo(tipo_lance: str, credito: float) -> None:
    if "lance_proprio_input" not in st.session_state:
        st.session_state["lance_proprio_input"] = moeda(25000.0)
    if "lance_embutido_slider" not in st.session_state:
        st.session_state["lance_embutido_slider"] = 25.0

    if st.session_state.get("tipo_lance_anterior") != tipo_lance:
        st.session_state["tipo_lance_anterior"] = tipo_lance
        st.session_state["ultimo_lance_alterado"] = "embutido"

        if tipo_lance == "Sem lance":
            st.session_state["lance_proprio_input"] = moeda(0)
            st.session_state["lance_embutido_slider"] = 0.0
        elif tipo_lance in LANCE_FIXO_PERCENTUAIS:
            limite_total = LANCE_FIXO_PERCENTUAIS[tipo_lance]
            embutido_padrao = min(LIMITE_LANCE_EMBUTIDO_PERCENTUAL, limite_total)
            st.session_state["lance_embutido_slider"] = embutido_padrao
            st.session_state["lance_proprio_input"] = moeda(max(0, credito * ((limite_total - embutido_padrao) / 100)))

    if tipo_lance == "Sem lance":
        st.session_state["lance_proprio_input"] = moeda(0)
        st.session_state["lance_embutido_slider"] = 0.0
        return

    if tipo_lance not in LANCE_FIXO_PERCENTUAIS:
        st.session_state["lance_embutido_slider"] = min(
            max(float(st.session_state.get("lance_embutido_slider", 0.0)), 0.0),
            LIMITE_LANCE_EMBUTIDO_PERCENTUAL,
        )
        return

    limite_total = LANCE_FIXO_PERCENTUAIS[tipo_lance]
    total_lance = credito * (limite_total / 100)
    embutido_maximo = min(LIMITE_LANCE_EMBUTIDO_PERCENTUAL, limite_total)
    proprio_minimo = max(0.0, total_lance - (credito * (embutido_maximo / 100)))
    ultimo = st.session_state.get("ultimo_lance_alterado", "embutido")

    if ultimo == "proprio":
        lance_proprio = parse_numero_brasileiro(st.session_state.get("lance_proprio_input", ""))
        lance_proprio = min(max(lance_proprio, proprio_minimo), total_lance)
        lance_embutido_pct = ((total_lance - lance_proprio) / credito * 100) if credito else 0.0
    else:
        lance_embutido_pct = min(
            max(float(st.session_state.get("lance_embutido_slider", embutido_maximo)), 0.0),
            embutido_maximo,
        )
        lance_proprio = max(0.0, total_lance - (credito * (lance_embutido_pct / 100)))

    st.session_state["lance_embutido_slider"] = round(lance_embutido_pct, 1)
    st.session_state["lance_proprio_input"] = moeda(lance_proprio)


def renderizar_controles_lance(credito: float, tipo_lance: str) -> tuple[float, float]:
    sincronizar_lance_por_tipo(tipo_lance, credito)

    slider_maximo = LIMITE_LANCE_EMBUTIDO_PERCENTUAL
    if tipo_lance in LANCE_FIXO_PERCENTUAIS:
        slider_maximo = min(LIMITE_LANCE_EMBUTIDO_PERCENTUAL, LANCE_FIXO_PERCENTUAIS[tipo_lance])

    desabilitado = tipo_lance == "Sem lance"
    col1, col2 = st.columns(2)
    with col1:
        lance_proprio_texto = st.text_input(
            "Lance recurso proprio",
            key="lance_proprio_input",
            on_change=normalizar_lance_proprio,
            args=("lance_proprio_input",),
            disabled=desabilitado,
        )
    with col2:
        lance_embutido_percentual = st.slider(
            "Lance embutido",
            min_value=0.0,
            max_value=float(slider_maximo),
            step=0.1,
            format="%.1f%%",
            key="lance_embutido_slider",
            on_change=marcar_lance_embutido,
            disabled=desabilitado,
        )

    if desabilitado:
        return 0.0, 0.0

    if tipo_lance in LANCE_FIXO_PERCENTUAIS and st.session_state.get("ultimo_lance_alterado") == "proprio":
        limite_total = LANCE_FIXO_PERCENTUAIS[tipo_lance] / 100
        total_lance = credito * limite_total
        lance_proprio = parse_numero_brasileiro(lance_proprio_texto)
        lance_embutido_percentual = ((total_lance - lance_proprio) / credito * 100) if credito else 0.0
        lance_embutido_percentual = max(0.0, min(lance_embutido_percentual, slider_maximo))

    return parse_numero_brasileiro(st.session_state.get("lance_proprio_input", "")), lance_embutido_percentual / 100


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
                --brand: #3B369E;
                --gold: #3B369E;
                --green: #3B369E;
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

            .logo-strip {
                display: grid;
                grid-template-columns: repeat(3, minmax(0, 1fr));
                gap: 18px;
                margin: 10px 0 18px;
            }

            .logo-card {
                align-items: center;
                background: #ffffff;
                border: 1px solid var(--line);
                border-radius: 8px;
                display: flex;
                height: 108px;
                justify-content: center;
                overflow: hidden;
                padding: 14px 18px;
                box-shadow: 0 6px 18px rgba(15, 23, 42, 0.05);
            }

            .logo-card img {
                display: block;
                max-height: 82px;
                max-width: 100%;
                object-fit: contain;
            }

            .logo-card.logo-dark {
                background: #070707;
            }

            .block-container {
                padding-top: 2.2rem;
                padding-bottom: 2rem;
                padding-left: 2rem;
                padding-right: 2rem;
                max-width: 1480px;
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
                border: 1px solid #cbc9f0;
                background: #f0efff;
                color: var(--brand);
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
                min-height: 112px;
            }

            div[data-testid="stMetricLabel"] p {
                color: var(--muted);
                font-weight: 700;
            }

            div[data-testid="stMetricValue"] {
                color: var(--text);
                font-weight: 800;
                line-height: 1.15;
                white-space: normal;
                overflow-wrap: anywhere;
            }

            div[data-testid="stMetricValue"] > div {
                font-size: clamp(1.35rem, 1.75vw, 2rem);
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
                border: 1px solid var(--brand);
                background: var(--brand);
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

            @media (max-width: 900px) {
                .block-container {
                    padding-left: 1rem;
                    padding-right: 1rem;
                }

                .logo-strip {
                    grid-template-columns: 1fr;
                    gap: 10px;
                }

                .topbar {
                    align-items: flex-start;
                    flex-direction: column;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def renderizar_logos() -> None:
    fiat = asset_data_uri("fiat_logo.webp")
    stellantis = asset_data_uri("stellantis_logo.webp")
    mgcon = asset_data_uri("mgcon_logo.webp")

    st.markdown(
        f"""
        <div class="logo-strip">
            <div class="logo-card"><img src="{fiat}" alt="FIAT Consorcio"></div>
            <div class="logo-card"><img src="{stellantis}" alt="Stellantis"></div>
            <div class="logo-card logo-dark"><img src="{mgcon}" alt="MGCON Consorcios"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def montar_resumo(resultado, dados_proposta: dict[str, object], tipo_lance: str) -> str:
    return "\n".join(
        [
            "Simulacao de plano Fiat",
            "",
            "Dados pessoais",
            "",
            f"Data da proposta: {formatar_data_resumo(dados_proposta.get('data_proposta'))}",
            f"Validade da proposta: {formatar_data_resumo(dados_proposta.get('validade_proposta'))}",
            f"Vendedor: {dados_proposta.get('vendedor') or ''}",
            f"Nome Completo: {dados_proposta.get('nome_completo') or ''}",
            f"CPF: {dados_proposta.get('cpf') or ''}",
            f"E-Mail: {dados_proposta.get('email') or ''}",
            f"Data de Nascimento: {formatar_data_resumo(dados_proposta.get('data_nascimento'))}",
            f"Estado: {dados_proposta.get('estado') or ''}",
            f"Cidade: {dados_proposta.get('cidade') or ''}",
            f"Carro referencia: {dados_proposta.get('carro_referencia') or ''}",
            f"Ano: {dados_proposta.get('ano') or ''}",
            f"Modelo: {dados_proposta.get('modelo') or ''}",
            "",
            "Informacoes do plano",
            "",
            f"Credito contratado: {moeda(resultado.credito)}",
            f"Prazo: {resultado.prazo} meses",
            f"Plano: {resultado.plano}",
            f"Tipo de Lance: {tipo_lance}",
            f"Lance proprio: {moeda(resultado.lance_proprio)}",
            f"Lance embutido: {moeda(resultado.lance_embutido)} ({percentual(resultado.lance_embutido_percentual)})",
            f"Lance total: {moeda(resultado.lance_total)} ({percentual(resultado.lance_total_percentual)})",
            f"Credito liquido: {moeda(resultado.credito_liquido)}",
            f"Parcela ate contemplacao: {moeda(resultado.parcela_ate_contemplacao)}",
            f"Total do plano com seguro: {moeda(resultado.total_plano_com_seguro)}",
            f"Taxa administrativa: {percentual(resultado.taxa_admin_percentual)}",
        ]
    )


def renderizar_resumo_copiavel(texto: str) -> None:
    texto_html = html.escape(texto)
    texto_js = json.dumps(texto)

    components.html(
        f"""
        <style>
            body {{
                margin: 0;
                font-family: Arial, Helvetica, sans-serif;
            }}

            .copy-wrap {{
                background: #ffffff;
                border: 1px solid #d9dee7;
                border-radius: 8px;
                box-sizing: border-box;
                padding: 12px;
            }}

            textarea {{
                border: 1px solid #d9dee7;
                border-radius: 8px;
                box-sizing: border-box;
                color: #1f2937;
                font-family: Arial, Helvetica, sans-serif;
                font-size: 13px;
                height: 292px;
                line-height: 1.45;
                padding: 12px;
                resize: vertical;
                width: 100%;
            }}

            .copy-row {{
                align-items: center;
                display: flex;
                gap: 10px;
                margin-top: 10px;
            }}

            button {{
                background: {COR_MARCA};
                border: 1px solid {COR_MARCA};
                border-radius: 8px;
                color: #ffffff;
                cursor: pointer;
                font-size: 13px;
                font-weight: 800;
                padding: 10px 14px;
            }}

            span {{
                color: {COR_MARCA};
                font-size: 12px;
                font-weight: 700;
            }}
        </style>
        <div class="copy-wrap">
            <textarea id="resumo-envio">{texto_html}</textarea>
            <div class="copy-row">
                <button id="copiar-resumo" type="button">Copiar tudo isso</button>
                <span id="status-copia"></span>
            </div>
        </div>
        <script>
            const textoPadrao = {texto_js};
            const botao = document.getElementById("copiar-resumo");
            const status = document.getElementById("status-copia");
            const area = document.getElementById("resumo-envio");

            async function copiarTexto() {{
                const texto = area.value || textoPadrao;
                try {{
                    await navigator.clipboard.writeText(texto);
                }} catch (erro) {{
                    area.focus();
                    area.select();
                    document.execCommand("copy");
                }}

                status.textContent = "Resumo copiado";
                botao.textContent = "Copiado";
                setTimeout(() => {{
                    status.textContent = "";
                    botao.textContent = "Copiar tudo isso";
                }}, 1800);
            }}

            botao.addEventListener("click", copiarTexto);
        </script>
        """,
        height=382,
    )


def renderizar_tabela_cenario(df: pd.DataFrame) -> None:
    tabela_html = df.to_html(index=False, escape=False, classes="scenario-table")
    css = dedent(
        f"""
        <style>
            .scenario-table-wrap {{
                border: 1px solid #d9dee7;
                border-radius: 8px;
                box-shadow: 0 8px 22px rgba(15, 23, 42, 0.06);
                margin-top: 10px;
                overflow-x: auto;
                overflow-y: hidden;
            }}

            .scenario-table {{
                background: #ffffff;
                border-collapse: collapse;
                margin: 0;
                min-width: 900px;
                width: 100%;
            }}

            .scenario-table thead th {{
                background: {COR_MARCA};
                border-right: 1px solid rgba(255, 255, 255, 0.22);
                color: #ffffff;
                font-size: 0.82rem;
                font-weight: 800;
                padding: 12px 10px;
                text-align: center;
                vertical-align: middle;
                white-space: nowrap;
            }}

            .scenario-table thead th:last-child {{
                border-right: 0;
            }}

            .scenario-table tbody td {{
                border-bottom: 1px solid #e6e8ef;
                border-right: 1px solid #edf0f5;
                color: #1f2937;
                font-size: 0.86rem;
                padding: 11px 10px;
                text-align: center;
                vertical-align: middle;
                white-space: nowrap;
            }}

            .scenario-table tbody td:last-child {{
                border-right: 0;
            }}

            .scenario-table tbody tr:nth-child(even) td {{
                background: #f4f4ff;
            }}

            .scenario-table tbody tr:hover td {{
                background: #ecebff;
            }}

            .scenario-table tbody tr:last-child td {{
                border-bottom: 0;
            }}

            .scenario-table tbody td:first-child {{
                color: {COR_MARCA};
                font-weight: 800;
            }}
        </style>
        """
    ).strip()

    st.markdown(css, unsafe_allow_html=True)
    st.markdown(
        f'<div class="scenario-table-wrap">{tabela_html}</div>',
        unsafe_allow_html=True,
    )


def main() -> None:
    aplicar_estilo()
    renderizar_logos()

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

    dados_proposta = renderizar_formulario_proposta()

    with st.container():
        st.markdown('<div class="section-title">Dados da simulacao</div>', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)

        with col1:
            credito = campo_monetario("Credito a contratar", "credito_input", 100000.0)

        with col2:
            prazo = st.selectbox("Prazo", PRAZOS, index=4)

        with col3:
            plano = st.selectbox("Plano", PLANOS, index=1)

        taxa_col, fundo_col, seguro_col = st.columns(3)
        with taxa_col:
            taxa_admin_pct = campo_percentual("Taxa administrativa", "taxa_admin_input", 20.0)
        with fundo_col:
            fundo_reserva_pct = campo_percentual("Fundo reserva", "fundo_reserva_input", 3.0)
        with seguro_col:
            seguro_pct = campo_percentual("Seguro vida ao mes", "seguro_input", 0.075, casas_decimais=3)

        tipo_lance = st.radio(
            "Tipo de lance ofertado",
            TIPOS_LANCE,
            index=1,
            horizontal=True,
            key="tipo_lance",
            on_change=marcar_tipo_lance,
        )
        lance_proprio, lance_embutido_pct = renderizar_controles_lance(credito, tipo_lance)

        col4, col5 = st.columns([1.0, 1.0])
        with col4:
            uso_lance = st.selectbox("Uso do lance", USOS_LANCE, index=0)
        with col5:
            mes_contemplacao = st.number_input(
                "Simular contemplacao a partir do mes",
                min_value=1,
                max_value=120,
                value=1,
                step=1,
            )

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
        st.markdown("**Resumo para envio**")
        resumo = montar_resumo(resultado, dados_proposta, tipo_lance)
        renderizar_resumo_copiavel(resumo)

    st.markdown('<div class="section-title">Cenario de contemplacao</div>', unsafe_allow_html=True)
    tabela = gerar_tabela_contemplacao(resultado)

    if tabela:
        st.caption(
            "A coluna de quitacao e contada desde o inicio do plano. "
            "Exemplo: se contemplar no mes 20 e aparecer quitacao no mes 53, "
            "faltam 33 parcelas apos o lance."
        )
        df = pd.DataFrame(tabela)
        df["Assembleia"] = df["Mes de contemplacao"].apply(lambda mes: f"{inteiro(mes)}\u00aa Assembleia")
        df = df[
            [
                "Assembleia",
                "Parcelas restantes apos lance",
                "Parcelas abatidas",
                "Mes previsto de quitacao",
                "Nova parcela",
                "Saldo apos lance",
            ]
        ].copy()
        df["Parcelas restantes apos lance"] = df["Parcelas restantes apos lance"].apply(inteiro)
        df["Parcelas abatidas"] = df["Parcelas abatidas"].apply(inteiro)
        df["Mes previsto de quitacao"] = df["Mes previsto de quitacao"].apply(lambda mes: f"{inteiro(mes)}\u00aa Assembleia")
        df["Nova parcela"] = df["Nova parcela"].apply(moeda)
        df["Saldo apos lance"] = df["Saldo apos lance"].apply(moeda)
        df = df.rename(
            columns={
                "Parcelas restantes apos lance": "Parcelas restantes apos lance",
                "Mes previsto de quitacao": "Mes previsto de quitacao",
                "Saldo apos lance": "Saldo apos lance",
            }
        )
        renderizar_tabela_cenario(df)

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
