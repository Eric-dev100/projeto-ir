# Projeto IR

Ferramenta gratuita que organiza os comprovantes do Imposto de Renda e alerta o que pode dar problema antes da declaração.

A pessoa coloca recibos e notas numa pasta (PDFs ou fotos). O Projeto IR lê cada comprovante, extrai emitente, CPF ou CNPJ, data, valor e beneficiário, classifica as despesas dedutíveis e aponta problemas: comprovante ilegível, dados obrigatórios ausentes, CPF ou CNPJ inválido, despesa não dedutível, duplicada, fora do ano ou reembolsada pelo plano de saúde. No fim, gera uma planilha de conferência para a declaração.

Tudo roda no computador da pessoa. Nenhum documento é enviado para a internet.

> **Situação:** em desenvolvimento, ainda não pronto para uso. A primeira versão de testes está prevista para o início de 2027.

## Aviso importante

O Projeto IR organiza e alerta, mas não decide. A responsabilidade pela declaração é de quem declara ou do seu contador. Confira sempre as regras oficiais da Receita Federal.

## Estrutura

- `tests/exemplos/` comprovantes fictícios com gabarito, usados para testar e calibrar a leitura.

## Licença

Copyright (C) 2026 Eric Gabriel Aguiar de Alencar

Este programa é software livre: você pode redistribuí-lo e modificá-lo sob os termos da Licença Pública Geral GNU, versão 3, publicada pela Free Software Foundation. É distribuído na esperança de ser útil, mas **sem nenhuma garantia**, nem mesmo a garantia implícita de comercialização ou de adequação a uma finalidade específica. Veja o arquivo [LICENSE](LICENSE) para os detalhes.
