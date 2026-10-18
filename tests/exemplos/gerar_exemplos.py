"""Gera comprovantes FICTÍCIOS para testar o Projeto IR.

Todos os nomes, endereços, CPFs e CNPJs são inventados. Os números de CPF e
CNPJ têm dígitos verificadores válidos (exceto onde o erro é proposital),
porque a ferramenta precisa validar esses dígitos. Cada documento traz um
rodapé dizendo que é fictício e não serve como comprovante.

Uso:
    python gerar_exemplos.py            # gera em ./arquivos e ./gabarito.jsonl

Saída:
    arquivos/   PDFs digitais e imagens (fotos simuladas)
    gabarito.jsonl  a resposta esperada para cada arquivo
"""
from __future__ import annotations

import json
import random
import shutil
import subprocess
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from reportlab.lib.pagesizes import A4, A5
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

AQUI = Path(__file__).resolve().parent
SAIDA = AQUI / "arquivos"
GABARITO = AQUI / "gabarito.jsonl"
RODAPE = "DOCUMENTO FICTÍCIO - GERADO PARA TESTES DO PROJETO IR - NÃO TEM VALOR COMO COMPROVANTE"
ANO = 2026
rng = random.Random(2026)


# --------------------------------------------------------------------------
# CPF e CNPJ fictícios com dígitos verificadores calculados
# --------------------------------------------------------------------------
def _dv(numeros: list[int], pesos: list[int]) -> int:
    resto = sum(n * p for n, p in zip(numeros, pesos)) % 11
    return 0 if resto < 2 else 11 - resto


def gerar_cpf() -> str:
    base = [rng.randint(0, 9) for _ in range(9)]
    while len(set(base)) == 1:
        base = [rng.randint(0, 9) for _ in range(9)]
    d1 = _dv(base, list(range(10, 1, -1)))
    d2 = _dv(base + [d1], list(range(11, 1, -1)))
    n = "".join(map(str, base + [d1, d2]))
    return f"{n[:3]}.{n[3:6]}.{n[6:9]}-{n[9:]}"


def gerar_cnpj(valido: bool = True) -> str:
    base = [rng.randint(0, 9) for _ in range(8)] + [0, 0, 0, 1]
    d1 = _dv(base, [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    d2 = _dv(base + [d1], [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    if not valido:
        d2 = (d2 + 3) % 10  # erro proposital no último dígito
    n = "".join(map(str, base + [d1, d2]))
    return f"{n[:2]}.{n[2:5]}.{n[5:8]}/{n[8:12]}-{n[12:]}"


def brl(valor: float) -> str:
    inteiro, centavos = f"{valor:.2f}".split(".")
    inteiro = f"{int(inteiro):,}".replace(",", ".")
    return f"R$ {inteiro},{centavos}"


def data_br(iso: str) -> str:
    a, m, d = iso.split("-")
    return f"{d}/{m}/{a}"


# --------------------------------------------------------------------------
# Pessoas e empresas fictícias
# --------------------------------------------------------------------------
TITULAR = {"nome": "Ana Beatriz Moura Lins", "cpf": gerar_cpf()}
DEPENDENTE = {"nome": "Lucas Moura Lins", "cpf": gerar_cpf()}
NAO_DEPENDENTE = {"nome": "Pedro Henrique Lins", "cpf": gerar_cpf()}

PSICOLOGA = {"nome": "Dra. Helena Duarte Vasconcelos", "cpf": gerar_cpf(), "registro": "CRP 20/01234",
             "endereco": "Rua das Acácias, 120, sala 3 - Cidade Exemplo/AM"}
FISIO = {"nome": "Rafael Toledo Brandão", "cpf": gerar_cpf(), "registro": "CREFITO-12/56789-F",
         "endereco": "Av. Fictícia, 455 - Cidade Exemplo/AM"}
DENTISTA = {"nome": "Clínica Odontológica Sorriso Exemplo Ltda", "cnpj": gerar_cnpj(),
            "endereco": "Rua Modelo, 88 - Cidade Exemplo/AM"}
CLINICA = {"nome": "Centro Médico Vida Exemplo Ltda", "cnpj": gerar_cnpj(),
           "endereco": "Av. dos Testes, 1500 - Cidade Exemplo/AM"}
LAB_INVALIDO = {"nome": "Laboratório Análise Exemplo Ltda", "cnpj": gerar_cnpj(valido=False),
                "endereco": "Rua Imaginária, 77 - Cidade Exemplo/AM"}
ESCOLA = {"nome": "Colégio Saber Exemplo Ltda", "cnpj": gerar_cnpj(),
          "endereco": "Rua do Ensino, 300 - Cidade Exemplo/AM"}
FACULDADE = {"nome": "Faculdade Horizonte Exemplo", "cnpj": gerar_cnpj(),
             "endereco": "Av. Universitária, 2000 - Cidade Exemplo/AM"}
PLANO = {"nome": "Operadora Saúde Exemplo S.A.", "cnpj": gerar_cnpj(),
         "endereco": "Av. Central, 900 - Cidade Exemplo/AM"}
FARMACIA = {"nome": "Drogaria Exemplo Ltda", "cnpj": gerar_cnpj(),
            "endereco": "Rua Comércio, 15 - Cidade Exemplo/AM"}
ACADEMIA = {"nome": "Academia Corpo Exemplo Ltda", "cnpj": gerar_cnpj(),
            "endereco": "Rua do Esporte, 42 - Cidade Exemplo/AM"}
IDIOMAS = {"nome": "Escola de Idiomas Fala Exemplo Ltda", "cnpj": gerar_cnpj(),
           "endereco": "Av. Global, 610 - Cidade Exemplo/AM"}


# --------------------------------------------------------------------------
# Gabarito
# --------------------------------------------------------------------------
@dataclass
class Esperado:
    arquivo: str
    descricao: str
    formato: str                     # "pdf" ou "imagem"
    emitente: str | None
    documento_emitente: str | None   # CPF ou CNPJ como impresso; None se ausente
    documento_valido: bool | None
    data: str | None                 # ISO
    valor: float | None
    beneficiario: str | None
    categoria: str                   # saude | educacao | plano_saude | nao_dedutivel | reembolso
    legibilidade: str = "legivel"    # legivel | duvidoso | ilegivel (rótulo inicial, a calibrar)
    alertas: list[str] = field(default_factory=list)
    observacao: str = ""


# --------------------------------------------------------------------------
# Desenho dos PDFs
# --------------------------------------------------------------------------
def _rodape(c: canvas.Canvas, largura: float) -> None:
    c.setFont("Helvetica", 6.5)
    c.setFillGray(0.35)
    c.drawCentredString(largura / 2, 8 * mm, RODAPE)
    c.setFillGray(0)


def _linhas(c: canvas.Canvas, x: float, y: float, linhas: list[str], tam: float = 10.5, passo: float = 6 * mm) -> float:
    c.setFont("Helvetica", tam)
    for linha in linhas:
        c.drawString(x, y, linha)
        y -= passo
    return y


def recibo_autonomo(caminho: Path, prof: dict, servico: str, paciente: dict, valor: float,
                    data: str, mostrar_cpf: bool = True) -> None:
    """Recibo de profissional autônomo (pessoa física)."""
    w, h = A5[1], A5[0]  # paisagem
    c = canvas.Canvas(str(caminho), pagesize=(w, h))
    c.setFont("Helvetica-Bold", 16)
    c.drawString(18 * mm, h - 20 * mm, "RECIBO")
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(w - 18 * mm, h - 20 * mm, brl(valor))
    texto = [
        f"Recebi de {TITULAR['nome']}, CPF {TITULAR['cpf']},",
        f"a importância de {brl(valor)}, referente a {servico}",
        f"realizada em {data_br(data)}, para o paciente {paciente['nome']},",
        f"CPF {paciente['cpf']}.",
    ]
    y = _linhas(c, 18 * mm, h - 34 * mm, texto)
    y -= 4 * mm
    dados = [prof["nome"]]
    if mostrar_cpf:
        dados.append(f"CPF {prof['cpf']}  -  {prof['registro']}")
    else:
        dados.append(prof["registro"])
    dados.append(prof["endereco"])
    c.line(18 * mm, y + 2 * mm, 100 * mm, y + 2 * mm)
    y -= 3 * mm
    _linhas(c, 18 * mm, y, dados, tam=9.5, passo=5 * mm)
    c.setFont("Helvetica", 9.5)
    c.drawRightString(w - 18 * mm, 22 * mm, f"Cidade Exemplo/AM, {data_br(data)}")
    _rodape(c, w)
    c.save()


def recibo_empresa(caminho: Path, emp: dict, titulo: str, numero: str, itens: list[tuple[str, float]],
                   beneficiario: dict, data: str, extra: list[str] | None = None) -> None:
    """Recibo ou nota de pessoa jurídica (clínica, escola, academia...)."""
    w, h = A4
    c = canvas.Canvas(str(caminho), pagesize=A4)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(20 * mm, h - 22 * mm, emp["nome"])
    _linhas(c, 20 * mm, h - 29 * mm, [f"CNPJ {emp['cnpj']}", emp["endereco"]], tam=9.5, passo=5 * mm)
    c.line(20 * mm, h - 42 * mm, w - 20 * mm, h - 42 * mm)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(20 * mm, h - 52 * mm, titulo)
    c.setFont("Helvetica", 10)
    c.drawRightString(w - 20 * mm, h - 52 * mm, f"Nº {numero}")
    y = _linhas(c, 20 * mm, h - 64 * mm, [
        f"Responsável financeiro: {TITULAR['nome']} - CPF {TITULAR['cpf']}",
        f"Beneficiário: {beneficiario['nome']} - CPF {beneficiario['cpf']}",
        f"Data: {data_br(data)}",
    ])
    y -= 4 * mm
    c.setFont("Helvetica-Bold", 10.5)
    c.drawString(20 * mm, y, "Descrição")
    c.drawRightString(w - 20 * mm, y, "Valor")
    y -= 2 * mm
    c.line(20 * mm, y, w - 20 * mm, y)
    y -= 6 * mm
    c.setFont("Helvetica", 10.5)
    total = 0.0
    for desc, val in itens:
        c.drawString(20 * mm, y, desc)
        c.drawRightString(w - 20 * mm, y, brl(val))
        total += val
        y -= 6 * mm
    c.line(20 * mm, y + 2 * mm, w - 20 * mm, y + 2 * mm)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(20 * mm, y - 4 * mm, "TOTAL PAGO")
    c.drawRightString(w - 20 * mm, y - 4 * mm, brl(total))
    if extra:
        _linhas(c, 20 * mm, y - 18 * mm, extra, tam=9.5, passo=5 * mm)
    _rodape(c, w)
    c.save()


def informe_plano(caminho: Path, pagamentos: list[tuple[dict, float]], reembolsos: list[tuple[str, str, float]]) -> None:
    w, h = A4
    c = canvas.Canvas(str(caminho), pagesize=A4)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(20 * mm, h - 22 * mm, PLANO["nome"])
    _linhas(c, 20 * mm, h - 29 * mm, [f"CNPJ {PLANO['cnpj']}", PLANO["endereco"]], tam=9.5, passo=5 * mm)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(20 * mm, h - 50 * mm, f"INFORME DE PAGAMENTOS PARA O IMPOSTO DE RENDA - ANO-CALENDÁRIO {ANO}")
    y = _linhas(c, 20 * mm, h - 62 * mm, [f"Titular do contrato: {TITULAR['nome']} - CPF {TITULAR['cpf']}"])
    y -= 4 * mm
    c.setFont("Helvetica-Bold", 10.5)
    c.drawString(20 * mm, y, "Beneficiário")
    c.drawString(110 * mm, y, "CPF")
    c.drawRightString(w - 20 * mm, y, "Valor pago no ano")
    y -= 7 * mm
    c.setFont("Helvetica", 10.5)
    for pessoa, val in pagamentos:
        c.drawString(20 * mm, y, pessoa["nome"])
        c.drawString(110 * mm, y, pessoa["cpf"])
        c.drawRightString(w - 20 * mm, y, brl(val))
        y -= 6 * mm
    c.setFont("Helvetica-Bold", 10.5)
    c.drawString(20 * mm, y - 2 * mm, "Total pago no ano")
    c.drawRightString(w - 20 * mm, y - 2 * mm, brl(sum(v for _, v in pagamentos)))
    y -= 16 * mm
    c.drawString(20 * mm, y, "Reembolsos efetuados no ano")
    y -= 7 * mm
    c.setFont("Helvetica", 10.5)
    for prestador, data, val in reembolsos:
        c.drawString(20 * mm, y, f"{data_br(data)} - {prestador}")
        c.drawRightString(w - 20 * mm, y, brl(val))
        y -= 6 * mm
    _rodape(c, w)
    c.save()


def cupom_termico(caminho_png: Path, emp: dict, itens: list[tuple[str, float]], data: str) -> None:
    """Cupom estreito, em fonte mono, como os de papel térmico. Gera PNG direto."""
    fonte = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 22)
    linhas = [emp["nome"].upper(), f"CNPJ {emp['cnpj']}", emp["endereco"], "-" * 34,
              "CUPOM - VENDA AO CONSUMIDOR", f"DATA {data_br(data)} 14:32", "-" * 34]
    total = 0.0
    for desc, val in itens:
        linhas.append(f"{desc[:22]:<22}{brl(val):>12}")
        total += val
    linhas += ["-" * 34, f"{'TOTAL':<22}{brl(total):>12}", f"CPF CONSUMIDOR {TITULAR['cpf']}", "", "DOCUMENTO FICTÍCIO", "PARA TESTES - SEM VALOR"]
    img = Image.new("L", (520, 40 + 30 * len(linhas)), 250)
    d = ImageDraw.Draw(img)
    for i, linha in enumerate(linhas):
        d.text((20, 20 + 30 * i), linha, font=fonte, fill=20)
    img.save(caminho_png)


# --------------------------------------------------------------------------
# Fotos simuladas a partir dos PDFs
# --------------------------------------------------------------------------
def pdf_para_imagem(pdf: Path, dpi: int = 150) -> Image.Image:
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["pdftoppm", "-png", "-r", str(dpi), "-singlefile", str(pdf), f"{tmp}/p"], check=True)
        return Image.open(f"{tmp}/p.png").convert("RGB")


def foto(papel: Image.Image, angulo: float = 0, fundo=(120, 105, 90), sombra: bool = True) -> Image.Image:
    """Coloca o papel sobre uma mesa, levemente girado, com sombra e ruído de câmera."""
    papel = papel.convert("RGB")
    girado = papel.rotate(angulo, expand=True, fillcolor=fundo, resample=Image.BICUBIC)
    margem = 80
    mesa = Image.new("RGB", (girado.width + 2 * margem, girado.height + 2 * margem), fundo)
    mesa.paste(girado, (margem, margem))
    arr = np.asarray(mesa).astype(np.float32)
    if sombra:
        gradiente = np.linspace(1.0, 0.82, arr.shape[1])[None, :, None]
        arr *= gradiente
    arr += np.random.default_rng(7).normal(0, 4, arr.shape)
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def borrada(img: Image.Image) -> Image.Image:
    return img.filter(ImageFilter.GaussianBlur(4.5))


def escura(img: Image.Image) -> Image.Image:
    img = ImageEnhance.Brightness(img).enhance(0.28)
    arr = np.asarray(img).astype(np.float32) + np.random.default_rng(3).normal(0, 9, (img.height, img.width, 3))
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def estourada(img: Image.Image) -> Image.Image:
    img = ImageEnhance.Brightness(img).enhance(1.9)
    return ImageEnhance.Contrast(img).enhance(0.6)


def desbotada(img: Image.Image) -> Image.Image:
    """Papel térmico velho: tinta clara, contraste baixo, manchas."""
    arr = np.asarray(img.convert("L")).astype(np.float32)
    arr = 255 - (255 - arr) * np.linspace(0.10, 0.03, arr.shape[0])[:, None]
    manchas = np.random.default_rng(5).normal(0, 6, arr.shape)
    arr = np.clip(arr + manchas, 0, 255)
    return Image.fromarray(arr.astype(np.uint8)).convert("RGB")


def baixa_resolucao(img: Image.Image) -> Image.Image:
    pequena = img.resize((max(1, img.width // 6), max(1, img.height // 6)), Image.BILINEAR)
    return pequena


def salvar_jpg(img: Image.Image, nome: str) -> str:
    img.convert("RGB").save(SAIDA / nome, "JPEG", quality=82)
    return nome


# --------------------------------------------------------------------------
# Montagem do conjunto
# --------------------------------------------------------------------------
def gerar() -> list[Esperado]:
    if SAIDA.exists():
        shutil.rmtree(SAIDA)
    SAIDA.mkdir(parents=True)
    g: list[Esperado] = []

    # ---- PDFs digitais limpos ----
    recibo_autonomo(SAIDA / "01_psicologa_marco.pdf", PSICOLOGA, "sessão de psicoterapia", TITULAR, 350.0, f"{ANO}-03-12")
    g.append(Esperado("01_psicologa_marco.pdf", "Recibo de psicóloga autônoma", "pdf", PSICOLOGA["nome"], PSICOLOGA["cpf"], True,
                      f"{ANO}-03-12", 350.0, TITULAR["nome"], "saude"))

    recibo_autonomo(SAIDA / "02_fisioterapia_lucas.pdf", FISIO, "sessão de fisioterapia", DEPENDENTE, 180.0, f"{ANO}-05-20")
    g.append(Esperado("02_fisioterapia_lucas.pdf", "Recibo de fisioterapeuta para o dependente", "pdf", FISIO["nome"], FISIO["cpf"], True,
                      f"{ANO}-05-20", 180.0, DEPENDENTE["nome"], "saude"))

    recibo_empresa(SAIDA / "03_dentista_junho.pdf", DENTISTA, "RECIBO DE SERVIÇOS ODONTOLÓGICOS", "000418",
                   [("Restauração em resina - dente 26", 420.0), ("Limpeza e profilaxia", 180.0)], TITULAR, f"{ANO}-06-03")
    g.append(Esperado("03_dentista_junho.pdf", "Recibo de clínica odontológica", "pdf", DENTISTA["nome"], DENTISTA["cnpj"], True,
                      f"{ANO}-06-03", 600.0, TITULAR["nome"], "saude"))

    recibo_empresa(SAIDA / "04_consulta_clinica.pdf", CLINICA, "RECIBO DE CONSULTA MÉDICA", "2026-1187",
                   [("Consulta em dermatologia", 450.0)], TITULAR, f"{ANO}-08-14")
    g.append(Esperado("04_consulta_clinica.pdf", "Consulta médica com reembolso parcial do plano", "pdf", CLINICA["nome"], CLINICA["cnpj"], True,
                      f"{ANO}-08-14", 450.0, TITULAR["nome"], "saude", alertas=["reembolso"],
                      observacao="O informe do plano registra reembolso de R$ 300,00 desta consulta; só R$ 150,00 é dedutível."))

    recibo_empresa(SAIDA / "05_escola_mensalidade_abril.pdf", ESCOLA, "RECIBO DE MENSALIDADE ESCOLAR", "A-0442",
                   [("Mensalidade - Ensino Fundamental - abril", 980.0)], DEPENDENTE, f"{ANO}-04-05")
    g.append(Esperado("05_escola_mensalidade_abril.pdf", "Mensalidade escolar do dependente", "pdf", ESCOLA["nome"], ESCOLA["cnpj"], True,
                      f"{ANO}-04-05", 980.0, DEPENDENTE["nome"], "educacao"))

    recibo_empresa(SAIDA / "06_faculdade_agosto.pdf", FACULDADE, "COMPROVANTE DE PAGAMENTO", "F-88213",
                   [("Mensalidade - Graduação em Administração - agosto", 1250.0)], TITULAR, f"{ANO}-08-10")
    g.append(Esperado("06_faculdade_agosto.pdf", "Mensalidade de graduação da titular", "pdf", FACULDADE["nome"], FACULDADE["cnpj"], True,
                      f"{ANO}-08-10", 1250.0, TITULAR["nome"], "educacao"))

    informe_plano(SAIDA / "07_informe_plano_saude.pdf", [(TITULAR, 7440.0), (DEPENDENTE, 4560.0)],
                  [(CLINICA["nome"], f"{ANO}-08-14", 300.0)])
    g.append(Esperado("07_informe_plano_saude.pdf", "Informe anual do plano de saúde com reembolso", "pdf", PLANO["nome"], PLANO["cnpj"], True,
                      None, 12000.0, TITULAR["nome"], "plano_saude",
                      observacao="Valores por beneficiário: titular R$ 7.440,00 e dependente R$ 4.560,00. Reembolso de R$ 300,00 referente ao arquivo 04."))

    # ---- PDFs com problemas de conteúdo ----
    recibo_autonomo(SAIDA / "08_psicologa_sem_cpf.pdf", PSICOLOGA, "sessão de psicoterapia", TITULAR, 350.0, f"{ANO}-04-09", mostrar_cpf=False)
    g.append(Esperado("08_psicologa_sem_cpf.pdf", "Recibo de autônoma sem o CPF da profissional", "pdf", PSICOLOGA["nome"], None, None,
                      f"{ANO}-04-09", 350.0, TITULAR["nome"], "saude", alertas=["campos_ausentes"]))

    recibo_empresa(SAIDA / "09_laboratorio_cnpj_invalido.pdf", LAB_INVALIDO, "RECIBO DE EXAMES LABORATORIAIS", "L-3301",
                   [("Hemograma completo", 45.0), ("Perfil lipídico", 85.0)], TITULAR, f"{ANO}-02-18")
    g.append(Esperado("09_laboratorio_cnpj_invalido.pdf", "Laboratório com CNPJ de dígito inválido", "pdf", LAB_INVALIDO["nome"], LAB_INVALIDO["cnpj"], False,
                      f"{ANO}-02-18", 130.0, TITULAR["nome"], "saude", alertas=["documento_invalido"]))

    recibo_autonomo(SAIDA / "10_fisioterapia_ano_anterior.pdf", FISIO, "sessão de fisioterapia", TITULAR, 180.0, f"{ANO - 1}-12-15")
    g.append(Esperado("10_fisioterapia_ano_anterior.pdf", "Recibo de dezembro do ano anterior", "pdf", FISIO["nome"], FISIO["cpf"], True,
                      f"{ANO - 1}-12-15", 180.0, TITULAR["nome"], "saude", alertas=["fora_do_ano"]))

    recibo_empresa(SAIDA / "11_academia.pdf", ACADEMIA, "RECIBO DE MENSALIDADE", "M-1290",
                   [("Plano mensal musculação - setembro", 129.9)], TITULAR, f"{ANO}-09-01")
    g.append(Esperado("11_academia.pdf", "Mensalidade de academia", "pdf", ACADEMIA["nome"], ACADEMIA["cnpj"], True,
                      f"{ANO}-09-01", 129.9, TITULAR["nome"], "nao_dedutivel", alertas=["nao_dedutivel"]))

    recibo_empresa(SAIDA / "12_curso_ingles.pdf", IDIOMAS, "RECIBO DE MENSALIDADE", "I-5521",
                   [("Curso de inglês - módulo intermediário - julho", 390.0)], DEPENDENTE, f"{ANO}-07-05")
    g.append(Esperado("12_curso_ingles.pdf", "Curso de idiomas do dependente", "pdf", IDIOMAS["nome"], IDIOMAS["cnpj"], True,
                      f"{ANO}-07-05", 390.0, DEPENDENTE["nome"], "nao_dedutivel", alertas=["nao_dedutivel"]))

    recibo_empresa(SAIDA / "13_consulta_nao_dependente.pdf", CLINICA, "RECIBO DE CONSULTA MÉDICA", "2026-1342",
                   [("Consulta em ortopedia", 400.0)], NAO_DEPENDENTE, f"{ANO}-09-22")
    g.append(Esperado("13_consulta_nao_dependente.pdf", "Consulta de pessoa que não é dependente cadastrado", "pdf", CLINICA["nome"], CLINICA["cnpj"], True,
                      f"{ANO}-09-22", 400.0, NAO_DEPENDENTE["nome"], "saude", alertas=["dependente_nao_cadastrado"]))

    shutil.copy(SAIDA / "03_dentista_junho.pdf", SAIDA / "14_dentista_junho_copia.pdf")
    g.append(Esperado("14_dentista_junho_copia.pdf", "Mesmo arquivo do dentista salvo duas vezes", "pdf", DENTISTA["nome"], DENTISTA["cnpj"], True,
                      f"{ANO}-06-03", 600.0, TITULAR["nome"], "saude", alertas=["duplicado"], observacao="Cópia idêntica do arquivo 03."))

    # ---- Fotos simuladas ----
    p_psico = pdf_para_imagem(SAIDA / "01_psicologa_marco.pdf")
    p_dent = pdf_para_imagem(SAIDA / "03_dentista_junho.pdf")
    p_escola = pdf_para_imagem(SAIDA / "05_escola_mensalidade_abril.pdf")
    p_fisio = pdf_para_imagem(SAIDA / "02_fisioterapia_lucas.pdf")

    recibo_autonomo(SAIDA / "_tmp_psico_julho.pdf", PSICOLOGA, "sessão de psicoterapia", TITULAR, 350.0, f"{ANO}-07-16")
    p_psico_jul = pdf_para_imagem(SAIDA / "_tmp_psico_julho.pdf")
    (SAIDA / "_tmp_psico_julho.pdf").unlink()
    salvar_jpg(foto(p_psico_jul, angulo=2.5), "15_foto_boa_psicologa_julho.jpg")
    g.append(Esperado("15_foto_boa_psicologa_julho.jpg", "Foto boa de recibo, levemente torta", "imagem", PSICOLOGA["nome"], PSICOLOGA["cpf"], True,
                      f"{ANO}-07-16", 350.0, TITULAR["nome"], "saude"))

    salvar_jpg(foto(p_dent, angulo=-1.5), "16_foto_dentista_junho.jpg")
    g.append(Esperado("16_foto_dentista_junho.jpg", "Foto do mesmo recibo do dentista que já existe em PDF", "imagem", DENTISTA["nome"], DENTISTA["cnpj"], True,
                      f"{ANO}-06-03", 600.0, TITULAR["nome"], "saude", alertas=["duplicado"],
                      observacao="Mesma despesa do arquivo 03, em outro formato: o duplicado precisa ser detectado pelo conteúdo, não pelo arquivo."))

    salvar_jpg(borrada(foto(p_escola, angulo=1)), "17_foto_borrada_escola.jpg")
    g.append(Esperado("17_foto_borrada_escola.jpg", "Foto tremida da mensalidade escolar", "imagem", ESCOLA["nome"], ESCOLA["cnpj"], True,
                      f"{ANO}-04-05", 980.0, DEPENDENTE["nome"], "educacao", legibilidade="ilegivel", alertas=["ilegivel", "duplicado"],
                      observacao="Também é a mesma despesa do arquivo 05."))

    salvar_jpg(escura(foto(p_fisio, angulo=-2)), "18_foto_escura_fisioterapia.jpg")
    g.append(Esperado("18_foto_escura_fisioterapia.jpg", "Foto tirada com pouca luz", "imagem", FISIO["nome"], FISIO["cpf"], True,
                      f"{ANO}-05-20", 180.0, DEPENDENTE["nome"], "saude", legibilidade="duvidoso", alertas=["duvidoso", "duplicado"],
                      observacao="Mesma despesa do arquivo 02."))

    salvar_jpg(foto(p_psico, angulo=14), "19_foto_muito_torta_psicologa.jpg")
    g.append(Esperado("19_foto_muito_torta_psicologa.jpg", "Foto bem torta, mas nítida", "imagem", PSICOLOGA["nome"], PSICOLOGA["cpf"], True,
                      f"{ANO}-03-12", 350.0, TITULAR["nome"], "saude", legibilidade="duvidoso", alertas=["duplicado"],
                      observacao="Deve ficar legível depois que a ferramenta endireitar a imagem. Mesma despesa do arquivo 01."))

    salvar_jpg(estourada(foto(p_dent, angulo=0.5, sombra=False)), "20_foto_estourada_dentista.jpg")
    g.append(Esperado("20_foto_estourada_dentista.jpg", "Foto com luz estourada (flash)", "imagem", DENTISTA["nome"], DENTISTA["cnpj"], True,
                      f"{ANO}-06-03", 600.0, TITULAR["nome"], "saude", legibilidade="duvidoso", alertas=["duvidoso", "duplicado"]))

    salvar_jpg(baixa_resolucao(foto(p_fisio, angulo=1)), "21_foto_baixa_resolucao_fisioterapia.jpg")
    g.append(Esperado("21_foto_baixa_resolucao_fisioterapia.jpg", "Imagem pequena demais (miniatura de WhatsApp)", "imagem", FISIO["nome"], FISIO["cpf"], True,
                      f"{ANO}-05-20", 180.0, DEPENDENTE["nome"], "saude", legibilidade="ilegivel", alertas=["ilegivel", "duplicado"]))

    # ---- Cupons de papel térmico ----
    cupom_termico(SAIDA / "_tmp_cupom.png", FARMACIA, [("DIPIRONA 500MG", 12.9), ("PROTETOR SOLAR FPS50", 64.5), ("VITAMINA D 2000UI", 39.9)], f"{ANO}-06-28")
    cupom = Image.open(SAIDA / "_tmp_cupom.png")
    salvar_jpg(foto(cupom, angulo=-3), "22_cupom_farmacia.jpg")
    g.append(Esperado("22_cupom_farmacia.jpg", "Cupom de farmácia em papel térmico, ainda nítido", "imagem", FARMACIA["nome"], FARMACIA["cnpj"], True,
                      f"{ANO}-06-28", 117.3, TITULAR["nome"], "nao_dedutivel", alertas=["nao_dedutivel", "papel_termico"]))

    salvar_jpg(foto(desbotada(cupom), angulo=2), "23_cupom_farmacia_desbotado.jpg")
    (SAIDA / "_tmp_cupom.png").unlink()
    g.append(Esperado("23_cupom_farmacia_desbotado.jpg", "O mesmo cupom com a tinta desbotada", "imagem", FARMACIA["nome"], FARMACIA["cnpj"], True,
                      f"{ANO}-06-28", 117.3, TITULAR["nome"], "nao_dedutivel", legibilidade="ilegivel",
                      alertas=["ilegivel", "papel_termico", "nao_dedutivel", "duplicado"]))
    return g


def main() -> None:
    gabarito = gerar()
    contexto = {"_contexto": True, "ano_calendario": ANO, "titular": TITULAR, "dependentes": [DEPENDENTE],
                "aviso": "Todos os dados são fictícios e gerados por gerar_exemplos.py."}
    with GABARITO.open("w", encoding="utf-8") as f:
        f.write(json.dumps(contexto, ensure_ascii=False) + "\n")
        for e in gabarito:
            f.write(json.dumps(asdict(e), ensure_ascii=False) + "\n")
    print(f"{len(gabarito)} comprovantes em {SAIDA}")
    print(f"Gabarito em {GABARITO}")


if __name__ == "__main__":
    main()
