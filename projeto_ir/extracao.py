"""Leitura do texto dos comprovantes e extração dos campos.

A extração usa regras simples e explicáveis (expressões regulares e posição das
linhas), sem aprendizado de máquina. Quando um campo não é encontrado, ele fica
vazio, e o alerta de campos ausentes avisa a pessoa.
"""
from __future__ import annotations

import re
from pathlib import Path

import pdfplumber

from .documentos import CNPJ_RE, CPF_RE, documento_valido, somente_digitos
from .modelo import Comprovante, Contexto
from .regras import Regras, normalizar

VALOR_RE = re.compile(r"R\$\s*(\d{1,3}(?:\.\d{3})*,\d{2})")
DATA_RE = re.compile(r"(?<!\d)(\d{2})/(\d{2})/(\d{4})(?!\d)")
LINHAS_IGNORADAS = ("documento ficticio",)
REEMBOLSO_RE = re.compile(r"(\d{2}/\d{2}/\d{4})\s*-\s*(.+?)\s+R\$\s*(\d{1,3}(?:\.\d{3})*,\d{2})")


def ler_texto_pdf(caminho: Path) -> str:
    with pdfplumber.open(caminho) as pdf:
        paginas = [p.extract_text() or "" for p in pdf.pages]
    return "\n".join(paginas)


def para_float(valor_br: str) -> float:
    return float(valor_br.replace(".", "").replace(",", "."))


def para_iso(dia: str, mes: str, ano: str) -> str:
    return f"{ano}-{mes}-{dia}"


def _linhas(texto: str) -> list[str]:
    return [l.strip() for l in texto.splitlines()
            if l.strip() and not any(i in normalizar(l) for i in LINHAS_IGNORADAS)]


MESES = {"janeiro": "01", "fevereiro": "02", "marco": "03", "abril": "04", "maio": "05", "junho": "06",
         "julho": "07", "agosto": "08", "setembro": "09", "outubro": "10", "novembro": "11", "dezembro": "12"}
DATA_EXTENSO_RE = re.compile(r"(\d{1,2}) de (" + "|".join(MESES) + r") de (\d{4})")
MARCAS_ANUAL = ("informe de pagamento", "informe de rendimento", "quitacao anual", "declaracao anual",
                "durante o ano de", "valores pagos no ano", "total pago no ano")
ROTULOS_NOME = re.compile(r"^(razao social|nome empresarial|nome|prestador( de servicos?)?|profissional|"
                          r"emitente|empresa|clinica)\s*:\s*", re.IGNORECASE)


def e_documento_anual(texto: str) -> bool:
    """Informe ou declaração que cobre o ano todo, sem data de um pagamento."""
    t = normalizar(texto)
    return any(m in t for m in MARCAS_ANUAL)


def _sem_rotulo(nome: str) -> str:
    """Tira rótulos como 'Razão social:' do começo do nome."""
    sem_acento = normalizar(nome)
    m = ROTULOS_NOME.match(sem_acento)
    return nome[m.end():].strip() if m else nome.strip()


def _documento_emitente(linhas: list[str], contexto: Contexto) -> str | None:
    """O CNPJ, ou o CPF que não pertence a quem declara."""
    da_familia = {somente_digitos(p.cpf) for p in contexto.pessoas}
    for linha in linhas:
        for m in CNPJ_RE.finditer(linha):
            return m.group(0)
    for linha in linhas:
        for m in CPF_RE.finditer(linha):
            if somente_digitos(m.group(0)) not in da_familia:
                return m.group(0)
    return None


def _emitente(linhas: list[str], doc: str | None, regras: Regras) -> str | None:
    """Nome de quem emitiu: a linha antes do documento ou do registro profissional."""
    registro = re.compile(r"\b(" + "|".join(regras.registros_saude) + r")\b")
    for i, linha in enumerate(linhas):
        tem_doc = doc is not None and doc in linha
        tem_registro = doc is None and registro.search(linha)
        if tem_doc or tem_registro:
            antes = re.split(r"\b(CNPJ|CPF)\b", linha)[0].strip(" -:,")
            if antes and not registro.search(antes) and _sem_rotulo(antes):
                return _sem_rotulo(antes)
            if i > 0:
                return _sem_rotulo(linhas[i - 1])
    return None


def _data(texto: str) -> str | None:
    preferidas = [r"data:?\s*", r"realizad[ao] em\s*", r"emitid[ao] em\s*"]
    t = normalizar(texto)
    for p in preferidas:
        m = re.search(p + DATA_RE.pattern, t)
        if m:
            return para_iso(*m.groups()[-3:])
    m = DATA_RE.search(texto)
    if m:
        return para_iso(*m.groups())
    m = DATA_EXTENSO_RE.search(t)
    if m:
        return para_iso(m.group(1).zfill(2), MESES[m.group(2)], m.group(3))
    return None


def _valor(linhas: list[str]) -> float | None:
    for linha in linhas:
        if re.search(r"\btotal\b", normalizar(linha)):
            m = VALOR_RE.search(linha)
            if m:
                return para_float(m.group(1))
    for linha in linhas:
        if "importancia" in normalizar(linha):
            m = VALOR_RE.search(linha)
            if m:
                return para_float(m.group(1))
    valores = [para_float(v) for v in VALOR_RE.findall("\n".join(linhas))]
    return max(valores) if valores else None


def _beneficiario(texto: str, contexto: Contexto) -> tuple[str | None, bool]:
    """Para quem foi o serviço. Sem indicação, presume-se o titular."""
    fim = r"(?=\s*[-–,(]\s*CPF|\s*$|,)"
    padroes = [r"benefici[aá]rio:?\s+(.+?)" + fim, r"paciente:?\s+(.+?)" + fim,
               r"alun[oa](?:\(a\))?:?\s+(.+?)" + fim]
    for p in padroes:
        m = re.search(p, texto, flags=re.IGNORECASE | re.MULTILINE)
        if m and m.group(1).strip():
            return m.group(1).strip(), False
    return contexto.titular.nome, True


def reembolsos_do_informe(texto: str) -> list[tuple[str, str, float]]:
    """Linhas de reembolso do informe do plano: (data ISO, prestador, valor)."""
    t = texto.split("Reembolsos", 1)
    if len(t) < 2:
        return []
    saida = []
    for m in REEMBOLSO_RE.finditer(t[1]):
        d, mth, a = m.group(1).split("/")
        saida.append((para_iso(d, mth, a), m.group(2).strip(), para_float(m.group(3))))
    return saida


def extrair(comp: Comprovante, contexto: Contexto, regras: Regras) -> Comprovante:
    linhas = _linhas(comp.texto)
    texto = "\n".join(linhas)
    comp.documento_emitente = _documento_emitente(linhas, contexto)
    comp.documento_valido = documento_valido(comp.documento_emitente) if comp.documento_emitente else None
    comp.emitente = _emitente(linhas, comp.documento_emitente, regras)
    comp.valor = _valor(linhas)
    comp.categoria = regras.classificar(texto)
    comp.anual = e_documento_anual(texto)
    comp.data = None if comp.anual else _data(texto)   # documento anual não tem data de um pagamento
    if comp.categoria == "plano_saude":
        comp.beneficiario, comp.beneficiario_presumido = contexto.titular.nome, False
    else:
        comp.beneficiario, comp.beneficiario_presumido = _beneficiario(texto, contexto)
    return comp
