# Projeto IR

Ferramenta gratuita que organiza os comprovantes do Imposto de Renda e alerta o que pode dar problema antes da declaração.

A pessoa coloca recibos e notas numa pasta (PDFs ou fotos). O Projeto IR lê cada comprovante, extrai emitente, CPF ou CNPJ, data, valor e beneficiário, classifica as despesas dedutíveis e aponta problemas: comprovante ilegível, dados obrigatórios ausentes, CPF ou CNPJ inválido, despesa não dedutível, duplicada, fora do ano ou reembolsada pelo plano de saúde. No fim, gera uma planilha de conferência para a declaração.

Tudo roda no computador da pessoa. Nenhum documento é enviado para a internet.

> **Situação:** em desenvolvimento, ainda não pronto para uso. A primeira versão de testes está prevista para o início de 2027.

## Aviso importante

O Projeto IR organiza e alerta, mas não decide. A responsabilidade pela declaração é de quem declara ou do seu contador. Confira sempre as regras oficiais da Receita Federal.

## O que a versão 0.1 faz

- Lê comprovantes em PDF com texto (fotos e PDFs escaneados chegam na versão 0.2).
- Extrai emitente, CPF ou CNPJ, data, valor, beneficiário e categoria.
- Valida os dígitos de CPF e CNPJ.
- Alerta: dados obrigatórios ausentes, documento inválido, despesa fora do ano, não dedutível, duplicada, de quem não é dependente, reembolsada pelo plano de saúde e recibo de profissional de saúde autônomo fora do Receita Saúde.
- Aplica o limite anual de educação por pessoa.
- Mostra uma tela de revisão, onde tudo pode ser corrigido, e exporta a planilha de conferência em Excel.

As regras fiscais ficam em `projeto_ir/regras/<ano>.yaml`, separadas do código, com as fontes oficiais citadas. As de 2026 ainda são um rascunho e precisam de revisão antes da temporada.

## Para desenvolver

Requer Python 3.11 ou superior.

```bash
python -m pip install -e ".[dev]"
python -m projeto_ir                                   # abre a tela no navegador
python -m pytest                                       # roda os testes
python -m projeto_ir.avaliacao tests/exemplos          # relatório de acerto contra o gabarito
```

## Estrutura

- `projeto_ir/` código da ferramenta: leitura (`extracao.py`), documentos (`documentos.py`), regras (`regras.py` e `regras/`), alertas (`alertas.py`), processamento (`processar.py`), planilha (`exportar.py`), tela (`app.py`) e medição de acerto (`avaliacao.py`).
- `tests/exemplos/` 23 comprovantes fictícios com gabarito, usados para testar e calibrar a leitura.
- `tests/exemplos_variados/` 6 comprovantes fictícios em outros formatos, para conferir se a leitura funciona fora do padrão dos exemplos.

## Licença

Copyright (C) 2026 Eric Gabriel Aguiar de Alencar

Este programa é software livre: você pode redistribuí-lo e modificá-lo sob os termos da Licença Pública Geral GNU, versão 3, publicada pela Free Software Foundation. É distribuído na esperança de ser útil, mas **sem nenhuma garantia**, nem mesmo a garantia implícita de comercialização ou de adequação a uma finalidade específica. Veja o arquivo [LICENSE](LICENSE) para os detalhes.
