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

## registrarDecisao(dados)

Python: `backend/lib/registrar_decisao.py` → `registrar_decisao(dados)`. História H14.

Rascunho feito a partir da H14 e do plano da Sprint 1. Conferir com o `contrato-registrarDecisao.md` antes da aprovação.

Grava um registro no histórico da ocorrência. Toda decisão passa por aqui: entrada, confirmação ou mudança de prioridade, ação, conclusão e aprovação em lote. A aprovação em lote chama a função uma vez por ocorrência.

### Entrada

Campos de todos os tipos:

| Campo | Tipo | Regra |
|---|---|---|
| tipo | texto | `entrada`, `prioridade_confirmada`, `prioridade_alterada`, `acao`, `conclusao` ou `aprovacao_lote` |
| ocorrenciaId | número | Ocorrência que recebeu a decisão |
| quemDecidiu | texto | `sistema` ou `sindico` |

Campos de cada tipo:

| Tipo | Quando | Obrigatórios | Opcionais |
|---|---|---|---|
| entrada | A ocorrência é gravada | origem | prioridadeSugerida. Fica vazia se a classificação falhou |
| prioridade_confirmada | O síndico confirma a prioridade | prioridadeSugerida, prioridadeFinal | |
| prioridade_alterada | O síndico muda a prioridade | prioridadeSugerida, prioridadeFinal, motivo | |
| acao | O síndico escolhe delegar, agendar ou eu mesmo cuido | acao. Mais responsavel se `delegar`, dataAgendada se `agendar` | nota |
| conclusao | O síndico conclui | | |
| aprovacao_lote | O síndico aprova em lote | prioridadeFinal, responsavel | |

Valores:

| Campo | Valores permitidos |
|---|---|
| origem | Os mesmos de `salvarOcorrencia` |
| prioridadeSugerida, prioridadeFinal | `urgente`, `alta`, `normal`, `baixa` |
| acao | `delegar`, `agendar`, `eu_mesmo`. Em `eu_mesmo` o responsável é gravado como `sindico` |
| responsavel | `zelador`, `portaria`, `sindico` |
| dataAgendada | `AAAA-MM-DD` |
| motivo, nota | Texto livre |

Campos que o servidor preenche, e que não devem ser enviados:

| Campo | Valor |
|---|---|
| dataHora | Horário do servidor no momento do registro |
| rebaixouTravada | `true` em `prioridade_alterada` quando a ocorrência é travada (H06) e a prioridade final fica abaixo de `urgente`. Nos outros casos, `false` |

### Saída

Sucesso:

```json
{ "ok": true, "registroId": 7, "dataHora": "2026-11-18T14:10:00+00:00" }
```

`dataHora` é texto ISO 8601 com fuso. Erro, com um item por campo inválido e a chave igual ao nome do campo:

```json
{ "ok": false, "erros": { "motivo": "Informe o motivo da mudança" } }
```

### Mensagens de erro

| Campo | Quando | Mensagem |
|---|---|---|
| tipo | vazio | Informe o tipo de registro |
| tipo | fora da lista | Tipo de registro inválido |
| ocorrenciaId | vazio ou não existe | Ocorrência não encontrada |
| quemDecidiu | vazio ou fora da lista | Informe quem decidiu |
| origem | vazia ou fora da lista, em `entrada` | Origem inválida |
| prioridadeSugerida, prioridadeFinal | vazia ou fora da lista. Em `entrada`, só se fora da lista | Prioridade inválida |
| motivo | vazio em `prioridade_alterada` | Informe o motivo da mudança |
| acao | vazia ou fora da lista | Escolha a ação |
| responsavel | vazio em `delegar` e em `aprovacao_lote` | Escolha o responsável |
| dataAgendada | vazia em `agendar` | Escolha a data do agendamento |

### Registro não muda

Um registro nunca é alterado nem apagado. Correção vira um novo registro. A função só insere, e a tabela `registros_decisao` recusa UPDATE e DELETE por gatilho no banco, então a regra vale também para chamada direta ao banco.

## concluirOcorrencia(ocorrenciaId)

Python: `backend/lib/concluir_ocorrencia.py` → `concluir_ocorrencia(ocorrencia_id)`. História H13.

Conclui uma ocorrência que está em andamento. O botão "Concluir" chama esta função e volta para a fila.

### O que a função faz

1. Confere se a ocorrência existe e se o status é `em_andamento`.
2. Grava o status `concluida` e `concluida_em` com o horário do servidor.
3. Chama `registrarDecisao` com o registro de `conclusao`, com `quemDecidiu` igual a `sindico`.

Os status da ocorrência são `nova`, `em_andamento` e `concluida`.

### Saída

Sucesso:

```json
{ "ok": true, "ocorrenciaId": 42, "concluidaEm": "2026-11-19T14:10:00+00:00" }
```

Erro, com a chave igual ao nome do campo:

```json
{ "ok": false, "erros": { "status": "Só dá para concluir uma ocorrência em andamento" } }
```

### Mensagens de erro

| Campo | Quando | Mensagem |
|---|---|---|
| ocorrenciaId | vazio ou não existe | Ocorrência não encontrada |
| status | não está em `em_andamento` | Só dá para concluir uma ocorrência em andamento |

## listarFila()

Python: `backend/lib/listar_fila.py` → `listar_fila()`. História H03.

Busca no banco as ocorrências de todos os condomínios, com os campos que o cartão da fila mostra. A tela chama esta função ao abrir e ao tocar em "Atualizar". A função só lê, não grava nada, e não recebe campos.

### Saída

```json
{
  "ok": true,
  "ocorrencias": [
    {
      "id": 42,
      "protocolo": "TS-000042",
      "condominioId": 1,
      "condominio": "Residencial Aurora",
      "descricao": "Lâmpada do hall queimada",
      "origem": "morador",
      "status": "nova",
      "prioridade": "normal",
      "categoria": "manutencao",
      "responsavelSugerido": "zelador",
      "motivo": "manutenção simples de área comum",
      "travada": false,
      "criadaEm": "2026-11-19T14:10:00+00:00",
      "concluidaEm": null,
      "acao": null
    }
  ]
}
```

| Campo | Regra |
|---|---|
| id, protocolo, condominioId, origem, status | Os mesmos de `salvarOcorrencia` e `concluirOcorrencia` |
| condominio | Nome do condomínio |
| descricao | Texto completo. O título do cartão é o início dela |
| prioridade, categoria, responsavelSugerido, motivo, travada | O que `classificar` devolveu. Se a classificação falhou, os três primeiros vêm `null` e o motivo é `não classificada, revisar` |
| criadaEm | Texto ISO 8601 em UTC (`+00:00`). O cartão calcula o "há 2 h" a partir dele |
| concluidaEm | Data da conclusão em ISO 8601 UTC, ou `null` se ainda não houver data registrada |
| acao | Última ação que o síndico registrou (`delegar`, `agendar` ou `eu_mesmo`), ou `null`. É a marca de ação do cartão |

### Regras

- Vêm as ocorrências de todos os status (`nova`, `em_andamento` e `concluida`). As abas e as contagens de cada aba saem dessa lista.
- Enquanto não há login, vêm os condomínios de todo o banco.
- Vem por ordem de chegada, da mais antiga para a mais nova (`criadaEm` e depois `id`). A ordenação da fila por prioridade não é feita aqui.
- Sem nenhuma ocorrência, a resposta é `{ "ok": true, "ocorrencias": [] }`.
- Não há mensagens de erro de validação, porque a função não recebe campos.

### Rota

`GET /ocorrencias` (`backend/rotas/fila.py`) devolve a saída acima com status 200. Cada chamada consulta o banco de novo, então é essa rota que a tela chama ao abrir e em "Atualizar". Não recebe parâmetros.

Se o banco não responder, devolve status 503 com `{ "ok": false, "erros": { "banco": "Não foi possível buscar a fila agora. Tente de novo." } }`, sem detalhes do erro.
