"""Testes das peças isoladas: documentos, regras e extração."""
from projeto_ir.documentos import cnpj_valido, cpf_valido, documento_valido
from projeto_ir.extracao import _beneficiario, _data, _sem_rotulo, e_documento_anual
from projeto_ir.modelo import Contexto, Pessoa
from projeto_ir.regras import carregar, normalizar

CTX = Contexto(2026, Pessoa("Ana Teste", "158.813.998-03"), [Pessoa("Lucas Teste", "698.797.309-17")])


def test_cpf():
    assert cpf_valido("158.813.998-03")
    assert cpf_valido("15881399803")
    assert not cpf_valido("158.813.998-04")
    assert not cpf_valido("111.111.111-11")


def test_cnpj():
    assert cnpj_valido("11.222.333/0001-81")
    assert not cnpj_valido("11.222.333/0001-82")
    assert not documento_valido("123")


def test_normalizar():
    assert normalizar("Saúde ÇÃO") == "saude cao"


def test_classificacao():
    r = carregar(2026)
    assert r.classificar("Mensalidade - Curso de Inglês") == "nao_dedutivel"
    assert r.classificar("Consulta em dermatologia") == "saude"
    assert r.classificar("Mensalidade - Ensino Fundamental") == "educacao"
    assert r.classificar("Drogaria Exemplo - cupom") == "nao_dedutivel"
    # Remédios dentro da conta hospitalar são dedutíveis.
    assert r.classificar("CONTA HOSPITALAR - internação. Medicamentos R$ 230,00") == "saude"


def test_datas():
    assert _data("Data: 03/06/2026") == "2026-06-03"
    assert _data("Cidade Exemplo, 15 de setembro de 2026.") == "2026-09-15"
    assert _data("sem data") is None


def test_rotulos_do_nome():
    assert _sem_rotulo("Razão social: Clínica Exemplo Ltda") == "Clínica Exemplo Ltda"
    assert _sem_rotulo("Profissional: Dr. Fulano") == "Dr. Fulano"
    assert _sem_rotulo("Clínica Exemplo Ltda") == "Clínica Exemplo Ltda"


def test_beneficiario():
    assert _beneficiario("Paciente: Lucas Teste - CPF 698.797.309-17", CTX) == ("Lucas Teste", False)
    assert _beneficiario("para o paciente Lucas Teste, CPF 698", CTX) == ("Lucas Teste", False)
    # Sem beneficiário no papel, presume-se o titular (regra da Receita).
    assert _beneficiario("Recibo de consulta", CTX) == ("Ana Teste", True)


def test_documento_anual():
    assert e_documento_anual("DECLARAÇÃO DE QUITAÇÃO ANUAL DE DÉBITOS")
    assert not e_documento_anual("Recibo de consulta")
