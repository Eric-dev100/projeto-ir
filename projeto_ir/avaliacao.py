"""Compara o que a ferramenta leu com o gabarito dos comprovantes de exemplo.

Uso:
    python -m projeto_ir.avaliacao tests/exemplos
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

from .documentos import somente_digitos
from .modelo import Comprovante, Contexto, Pessoa
from .processar import processar_pasta
from .regras import carregar, normalizar

CAMPOS = ["emitente", "documento_emitente", "documento_valido", "data", "valor", "beneficiario", "categoria"]
# Alertas que dependem da análise de imagem, prevista para a versão 0.2.
ALERTAS_DE_IMAGEM = {"ilegivel", "duvidoso", "papel_termico"}


@dataclass
class Resultado:
    lidos: int = 0
    ignorados: list[str] = field(default_factory=list)
    acertos: dict[str, int] = field(default_factory=lambda: {c: 0 for c in CAMPOS})
    erros: list[str] = field(default_factory=list)
    alertas_vp: int = 0   # alerta esperado e emitido
    alertas_fn: int = 0   # alerta esperado e não emitido
    alertas_fp: int = 0   # alerta emitido sem ser esperado

    def taxa(self, campo: str) -> float:
        return self.acertos[campo] / self.lidos if self.lidos else 0.0

    @property
    def precisao_alertas(self) -> float:
        total = self.alertas_vp + self.alertas_fp
        return self.alertas_vp / total if total else 1.0

    @property
    def cobertura_alertas(self) -> float:
        total = self.alertas_vp + self.alertas_fn
        return self.alertas_vp / total if total else 1.0


def carregar_gabarito(pasta: Path) -> tuple[Contexto, dict[str, dict]]:
    linhas = [json.loads(l) for l in (pasta / "gabarito.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    ctx = linhas[0]
    contexto = Contexto(ctx["ano_calendario"], Pessoa(**ctx["titular"]), [Pessoa(**d) for d in ctx["dependentes"]])
    return contexto, {l["arquivo"]: l for l in linhas[1:]}


def _igual(campo: str, lido, esperado) -> bool:
    if campo in ("emitente", "beneficiario"):
        return (lido is None and esperado is None) or (
            lido is not None and esperado is not None and normalizar(lido) == normalizar(esperado))
    if campo == "documento_emitente":
        return somente_digitos(lido or "") == somente_digitos(esperado or "")
    if campo == "valor":
        return (lido is None and esperado is None) or (
            lido is not None and esperado is not None and abs(lido - esperado) < 0.01)
    return lido == esperado


def avaliar(pasta: Path) -> tuple[Resultado, list[Comprovante]]:
    contexto, gabarito = carregar_gabarito(pasta)
    comps = processar_pasta(pasta / "arquivos", contexto, carregar(contexto.ano_calendario))
    r = Resultado()
    for c in comps:
        esperado = gabarito.get(c.arquivo)
        if esperado is None:
            continue
        if not c.lido:
            r.ignorados.append(c.arquivo)
            continue
        r.lidos += 1
        for campo in CAMPOS:
            lido = getattr(c, campo)
            if _igual(campo, lido, esperado[campo]):
                r.acertos[campo] += 1
            else:
                r.erros.append(f"{c.arquivo}: {campo} lido={lido!r} esperado={esperado[campo]!r}")
        esperados = set(esperado["alertas"]) - ALERTAS_DE_IMAGEM
        emitidos = c.codigos_alerta
        r.alertas_vp += len(esperados & emitidos)
        r.alertas_fn += len(esperados - emitidos)
        r.alertas_fp += len(emitidos - esperados)
        for a in sorted(esperados - emitidos):
            r.erros.append(f"{c.arquivo}: alerta '{a}' esperado e não emitido")
        for a in sorted(emitidos - esperados):
            r.erros.append(f"{c.arquivo}: alerta '{a}' emitido sem ser esperado")
    return r, comps


def relatorio(r: Resultado) -> str:
    linhas = [f"Comprovantes lidos: {r.lidos} | aguardando leitura de fotos (versão 0.2): {len(r.ignorados)}", ""]
    linhas.append("Acerto por campo:")
    for campo in CAMPOS:
        linhas.append(f"  {campo:<20} {r.taxa(campo):6.1%}  ({r.acertos[campo]}/{r.lidos})")
    linhas.append("")
    linhas.append(f"Alertas: precisão {r.precisao_alertas:.1%} | cobertura {r.cobertura_alertas:.1%} "
                  f"(acertos {r.alertas_vp}, faltaram {r.alertas_fn}, sobraram {r.alertas_fp})")
    if r.erros:
        linhas += ["", "Divergências:"] + [f"  - {e}" for e in r.erros]
    return "\n".join(linhas)


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    pasta = Path(argv[0]) if argv else Path("tests/exemplos")
    r, _ = avaliar(pasta)
    print(relatorio(r))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
