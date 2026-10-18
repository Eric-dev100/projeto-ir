"""Regras de alerta. Cada alerta diz o que está errado e o que fazer."""
from __future__ import annotations

import re

from .documentos import somente_digitos
from .extracao import reembolsos_do_informe
from .modelo import Alerta, Comprovante, Contexto
from .regras import Regras, normalizar

MENSAGENS = {
    "campos_ausentes": ("Faltam dados obrigatórios: {campos}.",
                        "Peça a segunda via ao prestador com nome, CPF ou CNPJ, endereço, data e valor."),
    "documento_invalido": ("O {tipo} {doc} tem dígito verificador inválido.",
                           "Confira o número com o prestador. Um documento inválido pode levar à malha fina."),
    "fora_do_ano": ("A data {data} não é do ano-calendário {ano}.",
                    "Guarde este comprovante para a declaração do ano correto."),
    "nao_dedutivel": ("Esta despesa não é dedutível no Imposto de Renda.",
                      "Não lance na declaração. Academia, idiomas, farmácia e material escolar não são dedutíveis."),
    "duplicado": ("Mesma despesa de {original}.",
                  "Mantenha só um dos dois para não lançar o valor em dobro."),
    "dependente_nao_cadastrado": ("O serviço foi para {nome}, que não está cadastrado como dependente.",
                                  "Cadastre a pessoa como dependente, se ela puder ser, ou não lance a despesa."),
    "reembolso": ("O plano de saúde reembolsou {valor} desta despesa.",
                  "Só a parte não reembolsada é dedutível. A ferramenta já descontou o reembolso."),
    "receita_saude": ("Recibo de profissional de saúde autônomo fora do Receita Saúde.",
                      "Desde 2025, esses recibos devem ser emitidos pelo Receita Saúde. Peça ao profissional o recibo eletrônico."),
    "nao_lido": ("Fotos e imagens ainda não são lidas nesta versão.",
                 "A leitura de fotos chega na próxima versão. Por enquanto, confira este comprovante à mão."),
}


def _alerta(codigo: str, **dados) -> Alerta:
    mensagem, sugestao = MENSAGENS[codigo]
    return Alerta(codigo, mensagem.format(**dados), sugestao)


def brl(valor: float) -> str:
    inteiro, centavos = f"{valor:.2f}".split(".")
    return f"R$ {int(inteiro):,}".replace(",", ".") + f",{centavos}"


def alertas_individuais(c: Comprovante, contexto: Contexto, regras: Regras) -> None:
    if not c.lido:
        c.alertas.append(_alerta("nao_lido"))
        return
    ausentes = []
    if not c.emitente:
        ausentes.append("nome do emitente")
    if not c.documento_emitente:
        ausentes.append("CPF ou CNPJ do emitente")
    if c.valor is None:
        ausentes.append("valor")
    if c.data is None and not c.anual:
        ausentes.append("data")
    if ausentes:
        c.alertas.append(_alerta("campos_ausentes", campos=", ".join(ausentes)))
    if c.documento_emitente and c.documento_valido is False:
        tipo = "CNPJ" if len(somente_digitos(c.documento_emitente)) == 14 else "CPF"
        c.alertas.append(_alerta("documento_invalido", tipo=tipo, doc=c.documento_emitente))
    if c.data and int(c.data[:4]) != contexto.ano_calendario:
        dia = "/".join(reversed(c.data.split("-")))
        c.alertas.append(_alerta("fora_do_ano", data=dia, ano=contexto.ano_calendario))
    if c.categoria == "nao_dedutivel":
        c.alertas.append(_alerta("nao_dedutivel"))
    nomes = {normalizar(p.nome) for p in contexto.pessoas}
    if c.beneficiario and normalizar(c.beneficiario) not in nomes:
        c.alertas.append(_alerta("dependente_nao_cadastrado", nome=c.beneficiario))
    if c.categoria == "saude" and _autonomo_de_saude(c, regras) and not _tem_marca_receita_saude(c, regras):
        c.alertas.append(_alerta("receita_saude"))


def _autonomo_de_saude(c: Comprovante, regras: Regras) -> bool:
    eh_pessoa_fisica = c.documento_emitente is None or len(somente_digitos(c.documento_emitente)) == 11
    tem_registro = re.search(r"\b(" + "|".join(regras.registros_saude) + r")\b", c.texto) is not None
    return eh_pessoa_fisica and tem_registro


def _tem_marca_receita_saude(c: Comprovante, regras: Regras) -> bool:
    t = normalizar(c.texto)
    return any(m in t for m in regras.marcas_receita_saude)


def alertas_do_conjunto(comps: list[Comprovante]) -> None:
    """Alertas que dependem de comparar comprovantes entre si."""
    vistos_hash: dict[str, str] = {}
    vistos_conteudo: dict[tuple, str] = {}
    for c in sorted(comps, key=lambda x: x.arquivo):
        original = vistos_hash.get(c.hash_arquivo)
        chave = (somente_digitos(c.documento_emitente or ""), c.data, c.valor) if c.lido else None
        if original is None and chave and chave[0] and c.valor is not None:
            original = vistos_conteudo.get(chave)
        if original:
            c.alertas.append(_alerta("duplicado", original=original))
        else:
            vistos_hash.setdefault(c.hash_arquivo, c.arquivo)
            if chave and chave[0] and c.valor is not None:
                vistos_conteudo.setdefault(chave, c.arquivo)

    reembolsos = [r for c in comps if c.lido and c.categoria == "plano_saude"
                  for r in reembolsos_do_informe(c.texto)]
    for data, prestador, valor in reembolsos:
        for c in comps:
            if (c.lido and c.data == data and c.emitente
                    and normalizar(prestador) == normalizar(c.emitente)
                    and "duplicado" not in c.codigos_alerta):
                c.valor_reembolsado += valor
                c.alertas.append(_alerta("reembolso", valor=brl(valor)))
