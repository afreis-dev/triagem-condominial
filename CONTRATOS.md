# Contratos das funções

Cada seção define o que uma função recebe e devolve. As duplas só dependem do que está escrito aqui. Se o contrato mudar, este arquivo muda no mesmo pull request.

No Python as funções ficam em `backend/lib/` com nome em snake_case. As chaves dos dicionários (JSON) seguem exatamente o que está escrito aqui.

## salvarOcorrencia(dados)

Python: `backend/lib/salvar_ocorrencia.py` → `salvar_ocorrencia(dados)`. Histórias H01 e H04.

Grava uma ocorrência nova, gera o protocolo e devolve o resultado. Serve ao formulário do condomínio e à mensagem colada pelo síndico.

### Entrada

| Campo | Tipo | Obrigatório no formulário | Obrigatório na mensagem colada | Regra |
|---|---|---|---|---|
| condominioId | número | Sim | Sim | Id do condomínio (`condominios.id`). No formulário vem do link `/c/[identificador]`. Na mensagem colada vem da lista de condomínios |
| origem | texto | Sim | Sim | Formulário: `morador`, `proprietario` ou `funcionario`. Mensagem colada: `whatsapp_sindico` |
| nome | texto | Não | Não | Nome de quem registrou ou mandou a mensagem |
| apartamento | texto | Não para `funcionario`. Para `morador` e `proprietario`, a confirmar com o PO | Não | |
| celular | texto | Sim | Não | Só números, 10 ou 11 dígitos (DDD + número). O servidor remove espaço, parênteses e hífen antes de validar |
| local | texto | Não | Não | Onde fica o problema |
| descricao | texto | Sim | Sim | Até 2.000 caracteres. Na mensagem colada é o texto colado |

### O que a função faz

1. Valida os campos. Se algum falhar, devolve os erros e não grava nada.
2. Grava a ocorrência com status `nova` e gera o protocolo a partir do id.
3. Chama `classificar(descricao)` e guarda o resultado na ocorrência.
4. Chama `registrarDecisao` com o registro de `entrada`.

A ocorrência é gravada antes de classificar. Se a classificação falhar, ela continua gravada e aparece na fila com o motivo `não classificada, revisar`.

### Protocolo

`TS-` mais o id com 6 dígitos, preenchido com zeros à esquerda. Id 1 vira `TS-000001` e id 42 vira `TS-000042`. Acima de 999999 o número só cresce (`TS-1000000`).

### Saída

Sucesso:

```json
{ "ok": true, "ocorrenciaId": 42, "protocolo": "TS-000042" }
```

Erro, com um item por campo inválido e a chave igual ao nome do campo de entrada:

```json
{ "ok": false, "erros": { "descricao": "Descreva a ocorrência" } }
```

### Mensagens de erro

| Campo | Quando | Mensagem |
|---|---|---|
| condominioId | vazio | Escolha o condomínio |
| condominioId | não existe | Condomínio não encontrado |
| origem | fora da lista | Origem inválida |
| apartamento | obrigatório e vazio | Informe o apartamento |
| celular | vazio | Informe o celular |
| celular | não tem 10 ou 11 dígitos | Celular deve ter 10 ou 11 dígitos |
| descricao | vazia | Descreva a ocorrência |
| descricao | mais de 2.000 caracteres | A descrição deve ter no máximo 2000 caracteres |

## classificar(texto)

Python: `backend/lib/classificar.py` → `classificar(texto)`. Histórias H05, H06, H07 e H08.

Recebe o texto da ocorrência e devolve prioridade, categoria, responsável sugerido e o motivo. A trava das palavras de risco é o último passo e vale acima das regras e da IA.

### Saída

```json
{
  "prioridade": "normal",
  "categoria": "manutencao",
  "responsavelSugerido": "zelador",
  "motivo": "manutenção simples de área comum",
  "travada": false,
  "palavraDeRisco": null,
  "fonte": "regras"
}
```

| Campo | Valores permitidos |
|---|---|
| prioridade | `urgente`, `alta`, `normal`, `baixa` |
| categoria | `manutencao`, `seguranca_acesso`, `convivencia`, `pedido_administrativo`, `duvida` |
| responsavelSugerido | `zelador`, `portaria`, `sindico` |
| motivo | Uma frase curta que diz qual palavra ou regra decidiu |
| travada | `true` quando uma palavra de risco acionou a trava, senão `false` |
| palavraDeRisco | A palavra que acionou a trava, ou `null` |
| fonte | `regras` (sprint 1) ou `ia` (sprint 2) |

### Regras

- O texto é padronizado antes da busca: minúsculas, sem acento, sem pontuação. "FUMAÇA no corredor!!!" vira "fumaca no corredor".
- Texto que encaixa em mais de uma regra usa a regra de maior prioridade (a confirmar com o PO).
- Texto sem nenhuma regra devolve prioridade `normal` e motivo `não reconhecida, revisar`. Categoria e responsável nesse caso: a confirmar com o PO. Texto vazio ou só com espaços cai aqui.
- A trava roda depois das regras. Ela procura no texto as 12 palavras de risco, na ordem desta lista, e usa a primeira que aparecer: gás, cheiro de gás, fogo, incêndio, fumaça, preso no elevador, alagamento, desabamento, trinca na estrutura, choque, fio exposto, agressão.
- A palavra precisa aparecer inteira. "gasto" não aciona "gás".
- Se a trava acionar: prioridade `urgente`, `travada` `true`, `palavraDeRisco` com a palavra e motivo `palavra de risco: <palavra>`. Categoria e responsável das ocorrências de risco: a confirmar com o PO.

### Exemplos

Em todos, `fonte` é `regras`.

| Texto | prioridade | categoria | responsavelSugerido | motivo | travada | palavraDeRisco |
|---|---|---|---|---|---|---|
| lâmpada do hall queimada | normal | manutencao | zelador | manutenção simples de área comum | false | null |
| barulho no salão e falta de água no bloco A | alta | manutencao | zelador | falta de água afeta muitos moradores | false | null |
| tem cheiro de gás no bloco B | urgente | manutencao* | zelador* | palavra de risco: gás | true | gás |
| a lâmpada queimou e está com cheiro de gás | urgente | manutencao* | zelador* | palavra de risco: gás | true | gás |
| teste asdf | normal | a confirmar* | a confirmar* | não reconhecida, revisar | false | null |

\* A confirmar com o PO. O texto do motivo das regras vem da lista de palavras-chave do PO, então o das linhas 1 e 2 é ilustrativo.
