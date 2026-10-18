"""Processa uma pasta de comprovantes do começo ao fim."""
from __future__ import annotations

import hashlib
from pathlib import Path

from .alertas import alertas_do_conjunto, alertas_individuais
from .extracao import extrair, ler_texto_pdf
from .modelo import Comprovante, Contexto
from .regras import Regras, carregar

EXTENSOES_PDF = {".pdf"}
EXTENSOES_IMAGEM = {".jpg", ".jpeg", ".png", ".heic", ".webp", ".tif", ".tiff"}


def _hash(caminho: Path) -> str:
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


def processar_arquivo(caminho: Path, contexto: Contexto, regras: Regras) -> Comprovante:
    ext = caminho.suffix.lower()
    formato = "pdf" if ext in EXTENSOES_PDF else "imagem"
    comp = Comprovante(arquivo=caminho.name, formato=formato, hash_arquivo=_hash(caminho))
    if formato == "pdf":
        comp.texto = ler_texto_pdf(caminho)
        if comp.texto.strip():
            extrair(comp, contexto, regras)
        else:
            comp.lido = False  # PDF escaneado, sem texto: será lido com OCR na próxima versão
    else:
        comp.lido = False
    return comp


def processar_pasta(pasta: Path, contexto: Contexto, regras: Regras | None = None) -> list[Comprovante]:
    regras = regras or carregar(contexto.ano_calendario)
    arquivos = sorted(p for p in Path(pasta).iterdir()
                      if p.is_file() and p.suffix.lower() in EXTENSOES_PDF | EXTENSOES_IMAGEM)
    comps = [processar_arquivo(p, contexto, regras) for p in arquivos]
    for c in comps:
        alertas_individuais(c, contexto, regras)
    alertas_do_conjunto(comps)
    return comps


def resumo(comps: list[Comprovante], contexto: Contexto, regras: Regras) -> dict:
    """Totais dedutíveis por categoria e por pessoa, com o limite anual de educação."""
    por_pessoa: dict[str, dict[str, float]] = {}
    for c in comps:
        if c.valor_dedutivel <= 0:
            continue
        pessoa = c.beneficiario or contexto.titular.nome
        por_pessoa.setdefault(pessoa, {}).setdefault(c.categoria, 0.0)
        por_pessoa[pessoa][c.categoria] += c.valor_dedutivel
    educacao_excedente = {}
    for pessoa, cats in por_pessoa.items():
        if cats.get("educacao", 0) > regras.limite_educacao:
            educacao_excedente[pessoa] = cats["educacao"] - regras.limite_educacao
            cats["educacao"] = regras.limite_educacao
    totais: dict[str, float] = {}
    for cats in por_pessoa.values():
        for cat, v in cats.items():
            totais[cat] = totais.get(cat, 0.0) + v
    return {"por_pessoa": por_pessoa, "totais": totais, "educacao_excedente": educacao_excedente,
            "com_alerta": sum(1 for c in comps if c.alertas), "total_arquivos": len(comps)}
