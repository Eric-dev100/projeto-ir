# Comprovantes de exemplo

Conjunto de 23 comprovantes **fictícios** para testar e calibrar o Projeto IR. Nomes, endereços, CPFs e CNPJs são inventados, e cada documento traz um aviso de que não tem valor como comprovante.

- `gerar_exemplos.py` recria todos os arquivos (`python gerar_exemplos.py`).
- `arquivos/` contém os comprovantes: 14 PDFs digitais e 9 imagens que simulam fotos de celular.
- `gerar_variados.py` cria outros 6 comprovantes, em formatos diferentes, na pasta `../exemplos_variados`.
- `gabarito.jsonl` tem a resposta esperada de cada arquivo: emitente, CPF ou CNPJ, validade do documento, data, valor, beneficiário, categoria, legibilidade e alertas. A primeira linha descreve o contribuinte fictício e o dependente cadastrado.

## O que o conjunto cobre

| Situação | Arquivos |
| --- | --- |
| Comprovantes corretos (saúde, educação, plano de saúde) | 01 a 07, 15 |
| Campos obrigatórios ausentes | 08 |
| CNPJ com dígito inválido | 09 |
| Fora do ano-calendário | 10 |
| Não dedutível (academia, idiomas, farmácia) | 11, 12, 22, 23 |
| Dependente não cadastrado | 13 |
| Reembolso do plano de saúde | 04 com 07 |
| Duplicado: mesmo arquivo e mesma despesa em outro formato | 14, 16 a 21, 23 |
| Foto borrada, escura, torta, estourada, pequena demais | 17 a 21 |
| Papel térmico nítido e desbotado | 22, 23 |
| Recibo de profissional de saúde autônomo fora do Receita Saúde | 01, 02, 08, 10, 15, 18, 19, 21 |

Os níveis de legibilidade do gabarito são rótulos iniciais e serão revistos na calibração com comprovantes reais.
