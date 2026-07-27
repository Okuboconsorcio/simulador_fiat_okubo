from __future__ import annotations

import base64
import html
import re
from datetime import date
from decimal import Decimal
from io import BytesIO
from pathlib import Path

import pandas as pd
from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image as RLImage
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from reportlab.platypus import Table as RLTable
from reportlab.platypus import TableStyle

from logos import LOGOS

COR_MARCA = "#3B369E"


def moeda(valor: Decimal | float | int | str) -> str:
    if isinstance(valor, str):
        return valor

    numero = float(valor)
    texto = f"R$ {numero:,.2f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def percentual(valor: Decimal | float | int) -> str:
    return f"{float(valor) * 100:.2f}%".replace(".", ",")


def formatar_data_resumo(valor: object) -> str:
    if isinstance(valor, date):
        return valor.strftime("%d/%m/%Y")
    return str(valor or "").strip()


def valor_pdf(valor: object) -> str:
    texto = str(valor or "").strip()
    return texto if texto else "-"


def paragrafo_pdf(texto: object, estilo: ParagraphStyle) -> Paragraph:
    conteudo = html.escape(valor_pdf(texto)).replace("\n", "<br/>")
    return Paragraph(conteudo, estilo)


def logo_pdf(nome_arquivo: str, largura_max: float, altura_max: float) -> RLImage:
    _, conteudo = LOGOS[nome_arquivo].split(",", 1)
    imagem = PILImage.open(BytesIO(base64.b64decode(conteudo))).convert("RGBA")
    largura, altura = imagem.size
    escala = min(largura_max / largura, altura_max / altura)

    saida = BytesIO()
    imagem.save(saida, format="PNG")
    saida.seek(0)

    return RLImage(saida, width=largura * escala, height=altura * escala)


def nome_arquivo_pdf(dados_proposta: dict[str, object]) -> str:
    nome_cliente = str(dados_proposta.get("nome_completo") or "cliente").strip()
    nome_limpo = re.sub(r"[^A-Za-z0-9_-]+", "_", nome_cliente).strip("_").lower()
    return f"simulacao_fiat_{nome_limpo or 'cliente'}.pdf"


def fontes_pdf() -> tuple[str, str]:
    opcoes = [
        (
            "OkuboDejaVu",
            "OkuboDejaVuBold",
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ),
        (
            "OkuboArial",
            "OkuboArialBold",
            Path("C:/Windows/Fonts/arial.ttf"),
            Path("C:/Windows/Fonts/arialbd.ttf"),
        ),
    ]

    for fonte_normal, fonte_bold, caminho_normal, caminho_bold in opcoes:
        if caminho_normal.exists():
            if fonte_normal not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont(fonte_normal, str(caminho_normal)))
            if caminho_bold.exists() and fonte_bold not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont(fonte_bold, str(caminho_bold)))
            return fonte_normal, fonte_bold if caminho_bold.exists() else fonte_normal

    return "Helvetica", "Helvetica-Bold"


def dados_pdf_em_linhas(dados_proposta: dict[str, object]) -> list[list[tuple[str, str]]]:
    carro = " - ".join(
        valor
        for valor in [
            str(dados_proposta.get("carro_referencia") or "").strip(),
            str(dados_proposta.get("ano") or "").strip(),
            str(dados_proposta.get("modelo") or "").strip(),
        ]
        if valor
    )

    return [
        [
            ("Data da proposta", formatar_data_resumo(dados_proposta.get("data_proposta"))),
            ("Validade da proposta", formatar_data_resumo(dados_proposta.get("validade_proposta"))),
            ("Vendedor", dados_proposta.get("vendedor") or ""),
        ],
        [
            ("Nome completo", dados_proposta.get("nome_completo") or ""),
            ("CPF", dados_proposta.get("cpf") or ""),
            ("E-mail", dados_proposta.get("email") or ""),
        ],
        [
            ("Data de nascimento", formatar_data_resumo(dados_proposta.get("data_nascimento"))),
            ("Estado/Cidade", f"{dados_proposta.get('estado') or '-'} / {dados_proposta.get('cidade') or '-'}"),
            ("Carro referência", carro),
        ],
    ]


def montar_tabela_campos_pdf(
    linhas: list[list[tuple[str, object]]],
    estilo_valor: ParagraphStyle,
    largura_total: float,
    fonte_normal: str,
    fonte_bold: str,
) -> RLTable:
    dados_tabela: list[list[Paragraph]] = []
    for linha in linhas:
        linha_pdf: list[Paragraph] = []
        for label, valor in linha:
            texto = (
                f'<font name="{fonte_bold}">{html.escape(label)}</font><br/>'
                f'<font name="{fonte_normal}">{html.escape(valor_pdf(valor))}</font>'
            )
            linha_pdf.append(Paragraph(texto, estilo_valor))
        dados_tabela.append(linha_pdf)

    tabela = RLTable(dados_tabela, colWidths=[largura_total / 3] * 3)
    tabela.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F6F7FB")),
                ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#D9DEE7")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return tabela


def gerar_pdf_simulacao(
    dados_proposta: dict[str, object],
    resultado,
    tipo_lance: str,
    tabela_cenario: pd.DataFrame,
) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=10 * mm,
        rightMargin=10 * mm,
        topMargin=7 * mm,
        bottomMargin=7 * mm,
    )

    fonte_normal, fonte_bold = fontes_pdf()
    estilos = getSampleStyleSheet()
    titulo = ParagraphStyle(
        "TituloOkubo",
        parent=estilos["Title"],
        textColor=colors.HexColor(COR_MARCA),
        alignment=TA_CENTER,
        fontName=fonte_bold,
        fontSize=15,
        leading=17,
        spaceAfter=3,
    )
    secao = ParagraphStyle(
        "SecaoOkubo",
        parent=estilos["Heading2"],
        textColor=colors.HexColor(COR_MARCA),
        fontName=fonte_bold,
        fontSize=9,
        leading=10.5,
        spaceBefore=4,
        spaceAfter=3,
    )
    normal = ParagraphStyle(
        "NormalOkubo",
        parent=estilos["BodyText"],
        fontName=fonte_normal,
        fontSize=7.2,
        leading=8.4,
    )
    pequeno = ParagraphStyle(
        "PequenoOkubo",
        parent=normal,
        fontSize=6.7,
        leading=7.7,
        alignment=TA_CENTER,
    )
    pequeno_header = ParagraphStyle(
        "PequenoHeaderOkubo",
        parent=pequeno,
        fontName=fonte_bold,
        textColor=colors.white,
        alignment=TA_CENTER,
    )
    valor = ParagraphStyle(
        "ValorOkubo",
        parent=normal,
        fontSize=8,
        leading=10,
    )

    conteudo = []
    logos = [
        logo_pdf("fiat_logo.webp", 48 * mm, 13 * mm),
        logo_pdf("stellantis_logo.webp", 58 * mm, 13 * mm),
        logo_pdf("mgcon_logo.webp", 56 * mm, 13 * mm),
    ]
    tabela_logos = RLTable([logos], colWidths=[doc.width / 3] * 3, rowHeights=[15 * mm])
    tabela_logos.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#D9DEE7")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
            ]
        )
    )

    conteudo.append(tabela_logos)
    conteudo.append(Spacer(1, 3))
    conteudo.append(Paragraph("Simulação de plano Fiat", titulo))
    conteudo.append(Paragraph("Dados do cliente e proposta", secao))
    conteudo.append(montar_tabela_campos_pdf(dados_pdf_em_linhas(dados_proposta), valor, doc.width, fonte_normal, fonte_bold))

    dados_simulacao = [
        [
            ("Crédito contratado", moeda(resultado.credito)),
            ("Prazo", f"{resultado.prazo} meses"),
            ("Plano", resultado.plano),
        ],
        [
            ("Tipo de Lance", tipo_lance),
            ("Lance recurso próprio", moeda(resultado.lance_proprio)),
            ("Lance embutido", f"{moeda(resultado.lance_embutido)} ({percentual(resultado.lance_embutido_percentual)})"),
        ],
        [
            ("Lance total", f"{moeda(resultado.lance_total)} ({percentual(resultado.lance_total_percentual)})"),
            ("Crédito líquido", moeda(resultado.credito_liquido)),
            ("Parcela até contemplação", moeda(resultado.parcela_ate_contemplacao)),
        ],
        [
            ("Seguro mensal", moeda(resultado.seguro_mensal)),
            ("Parcela normal com seguro", moeda(resultado.parcela_normal)),
            ("Parcela Mais por Menos com seguro", moeda(resultado.parcela_mais_por_menos)),
        ],
        [
            ("Total do plano com seguro", moeda(resultado.total_plano_com_seguro)),
            ("Taxa administrativa", percentual(resultado.taxa_admin_percentual)),
            ("Fundo reserva", percentual(resultado.fundo_reserva_percentual)),
        ],
    ]
    conteudo.append(Paragraph("Dados da simulação e resultado", secao))
    conteudo.append(montar_tabela_campos_pdf(dados_simulacao, valor, doc.width, fonte_normal, fonte_bold))

    conteudo.append(Paragraph("Cenário de contemplação - 5 primeiras linhas", secao))
    tabela_resumida = tabela_cenario.head(5).copy()
    dados_cenario = [[paragrafo_pdf(coluna, pequeno_header) for coluna in tabela_resumida.columns]]
    for _, linha in tabela_resumida.iterrows():
        dados_cenario.append([paragrafo_pdf(linha[coluna], pequeno) for coluna in tabela_resumida.columns])

    tabela_pdf = RLTable(
        dados_cenario,
        colWidths=[35 * mm, 45 * mm, 32 * mm, 45 * mm, 38 * mm, 45 * mm],
        repeatRows=1,
    )
    tabela_pdf.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(COR_MARCA)),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F4FF")]),
                ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#D9DEE7")),
                ("INNERGRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#E5E7EB")),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    conteudo.append(tabela_pdf)
    conteudo.append(Spacer(1, 5))
    conteudo.append(
        Paragraph(
            "Simulador consultivo. Os valores podem variar conforme regra comercial, administradora, assembleia, crédito e vigência do plano.",
            normal,
        )
    )

    doc.build(conteudo)
    buffer.seek(0)
    return buffer.getvalue()
