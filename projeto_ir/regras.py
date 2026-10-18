"""Carrega as regras fiscais do ano a partir dos arquivos em projeto_ir/regras/."""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from pathlib import Path

import yaml

PASTA_REGRAS = Path(__file__).resolve().parent / "regras"


def normalizar(texto: str) -> str:
    """Minúsculas e sem acentos, para comparar palavras-chave."""
    sem_acento = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in sem_acento if not unicodedata.combining(c)).lower()


@dataclass
class Regras:
    ano_calendario: int
    situacao: str
    limite_educacao: float
    categorias: dict[str, list[str]]
    registros_saude: list[str]
    marcas_receita_saude: list[str]
    campos_obrigatorios: list[str]
    excecoes_nao_dedutivel: dict[str, list[str]]

    def _nao_dedutivel(self, t: str) -> bool:
        for palavra in self.categorias.get("nao_dedutivel", []):
            if palavra in t and not any(e in t for e in self.excecoes_nao_dedutivel.get(palavra, [])):
                return True
        return False

    def classificar(self, texto: str) -> str:
        t = normalizar(texto)
        if self._nao_dedutivel(t):
            return "nao_dedutivel"
        for categoria in ("plano_saude", "saude", "educacao"):
            if any(palavra in t for palavra in self.categorias.get(categoria, [])):
                return categoria
        return "indefinida"


def anos_disponiveis() -> list[int]:
    return sorted(int(p.stem) for p in PASTA_REGRAS.glob("*.yaml"))


def carregar(ano: int) -> Regras:
    caminho = PASTA_REGRAS / f"{ano}.yaml"
    if not caminho.exists():
        raise FileNotFoundError(
            f"Não há regras para o ano-calendário {ano}. Anos disponíveis: {anos_disponiveis()}")
    dados = yaml.safe_load(caminho.read_text(encoding="utf-8"))
    return Regras(
        ano_calendario=dados["ano_calendario"],
        situacao=dados.get("situacao", "desconhecida"),
        limite_educacao=float(dados["educacao"]["limite_anual_por_pessoa"]),
        categorias={k: [normalizar(p) for p in v] for k, v in dados["categorias"].items()},
        registros_saude=dados.get("registros_saude", []),
        marcas_receita_saude=[normalizar(m) for m in dados.get("marcas_receita_saude", [])],
        campos_obrigatorios=dados.get("campos_obrigatorios", []),
        excecoes_nao_dedutivel={normalizar(k): [normalizar(x) for x in xs]
                                for k, xs in (dados.get("excecoes_nao_dedutivel") or {}).items()},
    )
