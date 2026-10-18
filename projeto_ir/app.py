"""Tela de revisão do Projeto IR (Streamlit).

Para abrir:  streamlit run projeto_ir/app.py
"""
from __future__ import annotations

import json
import tempfile
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

from projeto_ir import __version__
from projeto_ir.alertas import alertas_do_conjunto, alertas_individuais, brl
from projeto_ir.documentos import documento_valido
from projeto_ir.exportar import NOMES_CATEGORIA, para_excel
from projeto_ir.modelo import Contexto, Pessoa
from projeto_ir.processar import processar_pasta, resumo
from projeto_ir.regras import anos_disponiveis, carregar

EXEMPLOS = Path(__file__).resolve().parent.parent / "tests" / "exemplos"
CATEGORIAS = {v: k for k, v in NOMES_CATEGORIA.items()}
ROTULOS_ALERTA = {
    "campos_ausentes": "dados ausentes", "documento_invalido": "documento inválido",
    "fora_do_ano": "fora do ano", "nao_dedutivel": "não dedutível", "duplicado": "duplicado",
    "dependente_nao_cadastrado": "não é dependente", "reembolso": "reembolso",
    "receita_saude": "fora do Receita Saúde", "nao_lido": "foto ainda não lida",
}


def _situacao(c) -> str:
    if not c.lido:
        return "Foto: conferir à mão"
    return "Com alerta" if c.alertas else "OK"

st.set_page_config(page_title="Projeto IR", page_icon="🧾", layout="wide")
st.title("Projeto IR")
st.caption(f"Organizador de comprovantes do Imposto de Renda · versão {__version__}")
st.info("A ferramenta organiza e alerta, mas não decide. A responsabilidade pela declaração é de quem declara. "
        "Nenhum arquivo sai do seu computador.")


def _contexto_exemplo() -> dict:
    linha = (EXEMPLOS / "gabarito.jsonl").read_text(encoding="utf-8").splitlines()[0]
    return json.loads(linha)


with st.sidebar:
    st.header("Seus dados")
    usar_exemplos = st.toggle("Usar comprovantes de exemplo", value=True,
                              help="Abre o conjunto de comprovantes fictícios que acompanha o projeto.")
    padrao = _contexto_exemplo() if usar_exemplos else {"titular": {"nome": "", "cpf": ""}, "dependentes": []}
    ano = st.selectbox("Ano-calendário", anos_disponiveis(), index=len(anos_disponiveis()) - 1)
    nome = st.text_input("Nome do titular", padrao["titular"]["nome"])
    cpf = st.text_input("CPF do titular", padrao["titular"]["cpf"])
    deps_txt = st.text_area("Dependentes (um por linha: nome; CPF)",
                            "\n".join(f"{d['nome']}; {d['cpf']}" for d in padrao["dependentes"]))

dependentes = []
for linha in deps_txt.splitlines():
    if ";" in linha:
        n, c = (p.strip() for p in linha.split(";", 1))
        dependentes.append(Pessoa(n, c))
contexto = Contexto(ano, Pessoa(nome.strip(), cpf.strip()), dependentes)
regras = carregar(ano)
if regras.situacao != "revisado":
    st.warning(f"As regras fiscais de {ano} ainda são um rascunho e não foram revisadas para a declaração atual.")

if usar_exemplos:
    pasta = EXEMPLOS / "arquivos"
else:
    enviados = st.file_uploader("Escolha os comprovantes (PDF ou foto)", accept_multiple_files=True,
                                type=["pdf", "jpg", "jpeg", "png"])
    if not enviados:
        st.stop()
    tmp = Path(tempfile.mkdtemp(prefix="projeto_ir_"))
    for arq in enviados:
        (tmp / arq.name).write_bytes(arq.getvalue())
    pasta = tmp

if not nome.strip():
    st.error("Informe o nome do titular para a ferramenta saber de quem são as despesas.")
    st.stop()

comps = processar_pasta(pasta, contexto, regras)
topo = st.container()  # o resumo aparece acima da tabela, mas é calculado depois das correções

st.subheader("Revisão")
st.write("Confira o que foi lido. Você pode corrigir qualquer célula; os alertas são recalculados.")
tabela = pd.DataFrame([{
    "Arquivo": c.arquivo,
    "Emitente": c.emitente or "",
    "CPF/CNPJ": c.documento_emitente or "",
    "Data": date.fromisoformat(c.data) if c.data else None,
    "Valor (R$)": c.valor,
    "Beneficiário": c.beneficiario or "",
    "Categoria": NOMES_CATEGORIA.get(c.categoria, c.categoria),
    "Situação": _situacao(c),
} for c in comps])
editada = st.data_editor(
    tabela, hide_index=True, width="stretch", key="revisao",
    disabled=["Arquivo", "Situação"],
    column_config={
        "Valor (R$)": st.column_config.NumberColumn(format="localized", min_value=0),
        "Data": st.column_config.DateColumn(format="DD/MM/YYYY"),
        "Categoria": st.column_config.SelectboxColumn(options=list(CATEGORIAS)),
    })

# Aplica as correções feitas na tabela e recalcula os alertas.
for c, (_, linha) in zip(comps, editada.iterrows()):
    preenchido = bool(linha["Emitente"] or linha["CPF/CNPJ"] or pd.notna(linha["Valor (R$)"]))
    if not c.lido and not preenchido:
        continue
    c.lido = True  # inclui o caso de a pessoa preencher à mão um comprovante que a ferramenta não leu
    c.emitente = linha["Emitente"] or None
    c.documento_emitente = linha["CPF/CNPJ"] or None
    c.documento_valido = documento_valido(c.documento_emitente) if c.documento_emitente else None
    c.data = linha["Data"].isoformat() if pd.notna(linha["Data"]) else None
    c.valor = None if pd.isna(linha["Valor (R$)"]) else float(linha["Valor (R$)"])
    c.beneficiario = linha["Beneficiário"] or None
    c.categoria = CATEGORIAS.get(linha["Categoria"], "indefinida")
for c in comps:
    c.alertas, c.valor_reembolsado = [], 0.0
    alertas_individuais(c, contexto, regras)
alertas_do_conjunto(comps)

r = resumo(comps, contexto, regras)
with topo:
    col1, col2, col3 = st.columns(3)
    col1.metric("Comprovantes", r["total_arquivos"])
    col2.metric("Com alerta", r["com_alerta"])
    col3.metric("Total dedutível", brl(sum(r["totais"].values())))

st.subheader("Alertas")
com_alerta = [c for c in comps if c.alertas]
if not com_alerta:
    st.success("Nenhum alerta.")
for c in com_alerta:
    rotulos = ", ".join(ROTULOS_ALERTA.get(a.codigo, a.codigo) for a in c.alertas)
    with st.expander(f"{c.arquivo} · {rotulos}"):
        for a in c.alertas:
            st.markdown(f"**{a.mensagem}**  \n{a.sugestao}")

st.subheader("Resumo por pessoa")
linhas_resumo = [{"Pessoa": p, "Categoria": NOMES_CATEGORIA.get(cat, cat), "Valor dedutível": brl(v)}
                 for p, cats in r["por_pessoa"].items() for cat, v in sorted(cats.items())]
st.dataframe(pd.DataFrame(linhas_resumo), hide_index=True, width="stretch")
for p, exc in r["educacao_excedente"].items():
    st.caption(f"{p}: educação passou do limite anual em {brl(exc)}; o excedente não pode ser deduzido.")

with tempfile.TemporaryDirectory() as tmp:
    destino = para_excel(comps, contexto, regras, Path(tmp) / f"projeto-ir-{ano}.xlsx")
    st.download_button("Baixar planilha de conferência", destino.read_bytes(), file_name=destino.name,
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary")
