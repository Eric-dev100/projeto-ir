"""Estruturas de dados do Projeto IR."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Pessoa:
    nome: str
    cpf: str


@dataclass
class Contexto:
    """Quem declara: o ano, o titular e os dependentes cadastrados."""
    ano_calendario: int
    titular: Pessoa
    dependentes: list[Pessoa] = field(default_factory=list)

    @property
    def pessoas(self) -> list[Pessoa]:
        return [self.titular, *self.dependentes]


@dataclass
class Alerta:
    codigo: str
    mensagem: str
    sugestao: str


@dataclass
class Comprovante:
    arquivo: str
    formato: str                         # pdf | imagem
    texto: str = ""
    emitente: str | None = None
    documento_emitente: str | None = None
    documento_valido: bool | None = None
    data: str | None = None              # AAAA-MM-DD
    valor: float | None = None
    beneficiario: str | None = None
    beneficiario_presumido: bool = False  # sem beneficiário no papel: presume-se o titular
    anual: bool = False                  # informe ou declaração do ano todo
    categoria: str = "indefinida"        # saude | educacao | plano_saude | nao_dedutivel | indefinida
    valor_reembolsado: float = 0.0
    hash_arquivo: str = ""
    lido: bool = True                    # False quando o formato ainda não é lido nesta versão
    alertas: list[Alerta] = field(default_factory=list)

    @property
    def codigos_alerta(self) -> set[str]:
        return {a.codigo for a in self.alertas}

    @property
    def valor_dedutivel(self) -> float:
        """Valor que pode ir para a declaração, antes do limite anual de educação."""
        bloqueios = {"nao_dedutivel", "duplicado", "fora_do_ano", "documento_invalido",
                     "campos_ausentes", "dependente_nao_cadastrado"}
        if not self.lido or self.valor is None or self.codigos_alerta & bloqueios:
            return 0.0
        return max(self.valor - self.valor_reembolsado, 0.0)
