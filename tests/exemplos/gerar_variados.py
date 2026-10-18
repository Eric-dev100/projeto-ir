"""Gera comprovantes FICTÍCIOS em formatos diferentes dos de gerar_exemplos.py.

Servem para medir se a leitura funciona em layouts que ela nunca viu: textos
com outras palavras, CNPJ sem pontuação, data por extenso, valores sem espaço
depois do R$, declaração anual e conta de hospital.

Uso:
    python gerar_variados.py   # gera em ../exemplos_variados
"""
from __future__ import annotations

import json
import shutil
from dataclasses import asdict
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

import gerar_exemplos as ge

DESTINO = ge.AQUI.parent / "exemplos_variados"
SAIDA = DESTINO / "arquivos"
ANO = ge.ANO
T, D = ge.TITULAR, ge.DEPENDENTE


def documento(caminho: Path, linhas: list[tuple[str, float, str]]) -> None:
    """linhas: (texto, tamanho da fonte, 'b' para negrito ou '')."""
    w, h = A4
    c = canvas.Canvas(str(caminho), pagesize=A4)
    y = h - 22 * mm
    for texto, tam, estilo in linhas:
        c.setFont("Helvetica-Bold" if estilo == "b" else "Helvetica", tam)
        c.drawString(20 * mm, y, texto)
        y -= tam * 0.55 * mm + 3 * mm
    c.setFont("Helvetica", 6.5)
    c.setFillGray(0.35)
    c.drawCentredString(w / 2, 8 * mm, ge.RODAPE)
    c.save()


def gerar() -> list[ge.Esperado]:
    if DESTINO.exists():
        shutil.rmtree(DESTINO)
    SAIDA.mkdir(parents=True)
    g: list[ge.Esperado] = []

    cardio = {"nome": "Instituto do Coração Exemplo Ltda", "cnpj": ge.gerar_cnpj()}
    cnpj_sem_pontos = ge.somente = "".join(ch for ch in cardio["cnpj"] if ch.isdigit())
    documento(SAIDA / "v01_nota_fiscal_servico.pdf", [
        ("NOTA FISCAL DE SERVIÇOS ELETRÔNICA - NFS-e", 13, "b"),
        ("Número da nota: 00004521        Data de emissão: 02/09/2026", 10, ""),
        ("PRESTADOR DE SERVIÇOS", 10, "b"),
        (f"Razão social: {cardio['nome']}", 10, ""),
        (f"CNPJ: {cnpj_sem_pontos}", 10, ""),
        ("Endereço: Rua do Ritmo, 12 - Cidade Exemplo/AM", 10, ""),
        ("TOMADOR DE SERVIÇOS", 10, "b"),
        (f"Nome: {T['nome']}    CPF: {T['cpf']}", 10, ""),
        ("DISCRIMINAÇÃO DOS SERVIÇOS", 10, "b"),
        ("Consulta em cardiologia com eletrocardiograma", 10, ""),
        ("VALOR TOTAL DA NOTA = R$ 520,00", 11, "b"),
    ])
    g.append(ge.Esperado("v01_nota_fiscal_servico.pdf", "NFS-e com CNPJ sem pontuação", "pdf", cardio["nome"],
                         cardio["cnpj"], True, f"{ANO}-09-02", 520.0, T["nome"], "saude"))

    medico = {"nome": "Dr. Caio Ferraz Mendonça", "cpf": ge.gerar_cpf()}
    documento(SAIDA / "v02_recibo_receita_saude.pdf", [
        ("Receita Saúde - Recibo de Prestação de Serviço de Saúde", 12, "b"),
        ("Recibo emitido eletronicamente", 9, ""),
        (f"Profissional: {medico['nome']}", 10, ""),
        (f"CPF do profissional: {medico['cpf']}    Registro: CRM-AM 98765", 10, ""),
        (f"Pagador: {T['nome']} - CPF {T['cpf']}", 10, ""),
        (f"Paciente: {D['nome']} - CPF {D['cpf']}", 10, ""),
        ("Serviço: consulta pediátrica", 10, ""),
        ("Data do pagamento: 10/10/2026", 10, ""),
        ("Valor: R$ 300,00", 11, "b"),
    ])
    g.append(ge.Esperado("v02_recibo_receita_saude.pdf", "Recibo eletrônico do Receita Saúde (não deve alertar)", "pdf",
                         medico["nome"], medico["cpf"], True, f"{ANO}-10-10", 300.0, D["nome"], "saude"))

    documento(SAIDA / "v03_declaracao_anual_escola.pdf", [
        (ge.ESCOLA["nome"], 13, "b"),
        (f"CNPJ {ge.ESCOLA['cnpj']}", 10, ""),
        ("DECLARAÇÃO DE QUITAÇÃO ANUAL DE DÉBITOS", 12, "b"),
        (f"Declaramos para fins de Imposto de Renda que {T['nome']}, CPF {T['cpf']},", 10, ""),
        (f"responsável pelo aluno {D['nome']}, CPF {D['cpf']}, matriculado no", 10, ""),
        (f"Ensino Fundamental, pagou durante o ano de {ANO} o valor total de R$ 11.760,00", 10, ""),
        ("referente às mensalidades de janeiro a dezembro.", 10, ""),
    ])
    g.append(ge.Esperado("v03_declaracao_anual_escola.pdf", "Declaração anual da escola (sem data única)", "pdf",
                         ge.ESCOLA["nome"], ge.ESCOLA["cnpj"], True, None, 11760.0, D["nome"], "educacao",
                         observacao="Documento anual: não tem data de um pagamento. O valor passa do limite anual de educação."))

    lab = {"nome": "Laboratório Diagnóstico Exemplo Ltda", "cnpj": ge.gerar_cnpj()}
    documento(SAIDA / "v04_laboratorio_data_extenso.pdf", [
        (lab["nome"], 13, "b"),
        (f"CNPJ {lab['cnpj']}", 10, ""),
        ("Comprovante de pagamento de exames", 12, "b"),
        (f"Cliente: {T['nome']} (CPF {T['cpf']})", 10, ""),
        ("Exames: glicemia, TSH, vitamina B12", 10, ""),
        ("Valor pago: R$350,00", 10, ""),
        ("Cidade Exemplo, 15 de setembro de 2026.", 10, ""),
    ])
    g.append(ge.Esperado("v04_laboratorio_data_extenso.pdf", "Data por extenso e valor sem espaço", "pdf",
                         lab["nome"], lab["cnpj"], True, f"{ANO}-09-15", 350.0, T["nome"], "saude"))

    dentista_pf = {"nome": "Marina Couto Albuquerque", "cpf": ge.gerar_cpf()}
    documento(SAIDA / "v05_dentista_autonoma.pdf", [
        ("RECIBO DE PAGAMENTO", 13, "b"),
        (f"Paciente: {D['nome']}", 10, ""),
        (f"Responsável: {T['nome']} - CPF {T['cpf']}", 10, ""),
        ("Tratamento: manutenção de aparelho ortodôntico", 10, ""),
        ("Valor recebido: R$ 800,00", 10, ""),
        ("Data: 21/07/2026", 10, ""),
        (dentista_pf["nome"], 10, ""),
        (f"Cirurgiã-dentista - CRO-AM 4321 - CPF {dentista_pf['cpf']}", 10, ""),
    ])
    g.append(ge.Esperado("v05_dentista_autonoma.pdf", "Dentista autônoma, recibo em papel", "pdf", dentista_pf["nome"],
                         dentista_pf["cpf"], True, f"{ANO}-07-21", 800.0, D["nome"], "saude",
                         alertas=["receita_saude"]))

    hosp = {"nome": "Hospital Esperança Exemplo S.A.", "cnpj": ge.gerar_cnpj()}
    documento(SAIDA / "v06_conta_hospitalar.pdf", [
        (hosp["nome"], 13, "b"),
        (f"CNPJ {hosp['cnpj']}", 10, ""),
        ("CONTA HOSPITALAR - INTERNAÇÃO", 12, "b"),
        (f"Paciente: {T['nome']} - CPF {T['cpf']}", 10, ""),
        ("Período: 03/11/2026 a 05/11/2026", 10, ""),
        ("Diárias de internação ............ R$ 2.400,00", 10, ""),
        ("Medicamentos ..................... R$ 230,00", 10, ""),
        ("Honorários médicos ............... R$ 850,00", 10, ""),
        ("TOTAL DA CONTA ................... R$ 3.480,00", 11, "b"),
    ])
    g.append(ge.Esperado("v06_conta_hospitalar.pdf", "Conta hospitalar com remédios incluídos", "pdf", hosp["nome"],
                         hosp["cnpj"], True, f"{ANO}-11-03", 3480.0, T["nome"], "saude",
                         observacao="Remédios dentro da conta hospitalar são dedutíveis."))
    return g


def main() -> None:
    g = gerar()
    contexto = {"_contexto": True, "ano_calendario": ANO, "titular": T, "dependentes": [D],
                "aviso": "Todos os dados são fictícios e gerados por gerar_variados.py."}
    with (DESTINO / "gabarito.jsonl").open("w", encoding="utf-8") as f:
        f.write(json.dumps(contexto, ensure_ascii=False) + "\n")
        for e in g:
            f.write(json.dumps(asdict(e), ensure_ascii=False) + "\n")
    print(f"{len(g)} comprovantes em {SAIDA}")


if __name__ == "__main__":
    main()
