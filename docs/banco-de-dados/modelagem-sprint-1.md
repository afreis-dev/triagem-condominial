# Modelagem do banco de dados — Sprint 1

**Projeto:** Triagem do Síndico — Squad 03  
**Tarefa:** [SQU-71](https://linear.app/squad03/issue/SQU-71)  
**Data:** 20/11/2026  
**Branch de referência:** `develop`  
**Documento relacionado:** [DER da Sprint 1](der-sprint-1.md)

## 1. Objetivo, fontes e limites

Definir um **modelo lógico proposto para implementação na SQU-72** que sustente registro, classificação por regras, fila da carteira, decisões, delegação/agendamento, conclusão e histórico imutável (H01, H03, H04, H05, H06, H10, H11, H13 e H14).

Fontes: PRD, histórias e backlog do PO; planilha `Dados_fixos_e_regras_Sprint1.xlsx` entregue pelo PO em 17/11/2026; `CONTRATOS.md`; `backend/lib/tests/schema_teste.sql`; funções e testes de persistência da `develop`; auditoria [SQU-70](auditoria-sprint-1.md). Em divergências, preservar o requisito do PO e **registrar a necessidade de ajuste dos contratos/código**, sem modificar unilateralmente os módulos dos colegas.

**Fora do escopo:** login, autenticação, cadastros por interface, IA, WhatsApp oficial, anexos, aprovações em lote como funcionalidade da Sprint 1 e modelos financeiros. Este documento **não executa SQL**, não é uma migration e não comprova que as restrições já estejam instaladas no banco.

## 2. Princípios e decisões

1. **IDs internos:** `SERIAL` para novas chaves primárias, `INTEGER` nas FKs; compatíveis com `CONTRATOS.md`, `dominio.inteiro()` e testes da `develop`. UUID e BIGINT IDENTITY não serão usados nesta entrega.
2. **Condomínio:** `id` numérico e `identificador` (slug) textual único. O link `/c/aurora` encontra o condomínio pelo slug e repassa `condominioId` numérico ao backend.
3. **Ocorrência:** preservar nomes de colunas já consultados pelas funções Python; protocolo `TS-` + ID formatado com no mínimo seis dígitos, gerado pelo fluxo atual com a sequência de `ocorrencias.id`.
4. **Uma carteira por síndico neste modelo:** `condominios.sindico_id` atende ao cenário de um síndico de teste com vários condomínios. Não há requisito atual de coadministração simultânea; uma eventual relação N:N exigirá revisão futura.
5. **Contatos por condomínio:** `responsaveis` associa zelador/portaria ao condomínio e armazena nome/celular. Os campos `responsavel_sugerido` e `registros_decisao.responsavel` continuam **papéis textuais** (`zelador`, `portaria`, `sindico`), conforme API; não trocar por FK sem mudança conjunta de contrato.
6. **Histórico:** `registros_decisao` é append-only; impedir UPDATE e DELETE por trigger. Evitar `ON DELETE CASCADE` que eliminaria registros. Correções geram novos eventos.
7. **Classificação falhou:** `ocorrencias.prioridade`, `categoria`, `responsavel_sugerido` e `fonte` podem ficar nulos; `motivo` pode conter `não classificada, revisar`. A ocorrência precisa existir antes da classificação.
8. **Valores de domínio:** usar `TEXT` + `CHECK` onde seguro e não introduzir tipos enum PostgreSQL que dificultem evolução/compatibilidade. Campos de prioridade/resultado da classificação aceitam nulo enquanto a classificação não terminar.

## 3. Entidades e dicionário de dados

Legenda: **PK** chave primária, **FK** chave estrangeira, **UQ** único, **NN** não nulo, **DEF** padrão; `?` indica coluna anulável. Os tamanhos e restrições propostos serão implementados e testados na SQU-72.

### 3.1. `sindicos` — carteira de teste

| Campo | Tipo | Regras | Uso |
| --- | --- | --- | --- |
| `id` | `SERIAL` | PK | Identificador interno. |
| `nome` | `TEXT` | NN | Nome da síndica conforme PO. |
| `celular` | `TEXT` | ? | Celular fictício, armazenado como texto para preservar DDD. |
| `email` | `TEXT` | ? | E-mail fictício; não é credencial de login. |

**Decisão:** não impor unicidade a `nome`; `email` pode ter UQ parcial apenas se necessário para idempotência do seed. Não há autenticação nem tabela de usuários.

### 3.2. `condominios` — propriedade da carteira

| Campo | Tipo | Regras | Uso |
| --- | --- | --- | --- |
| `id` | `SERIAL` | PK | Referenciado pelas funções do backend. |
| `identificador` | `TEXT` | NN, UQ | Slug do link (`aurora`, `vista-verde`, `palmeiras`). |
| `nome` | `TEXT` | NN | Nome exibido. |
| `bairro` | `TEXT` | ? | Bairro fictício da planilha. |
| `sindico_id` | `INTEGER` | NN, FK → `sindicos.id`, `RESTRICT` | Cada condomínio pertence a uma carteira de teste. |

**Compatibilidade:** consultas já existentes por `condominios.id` continuam válidas. A nova FK torna obrigatório inserir a síndica **antes** dos condomínios no seed. As fixtures antigas que criam condomínio sem `sindico_id` precisarão ser alinhadas em conjunto com o responsável pelos testes; esta dependência não é ocultada.

### 3.3. `responsaveis` — contatos fixos para delegação

| Campo | Tipo | Regras | Uso |
| --- | --- | --- | --- |
| `id` | `SERIAL` | PK | ID interno do contato. |
| `condominio_id` | `INTEGER` | NN, FK → `condominios.id`, `RESTRICT` | Contexto do responsável. |
| `papel` | `TEXT` | NN, CHECK (`zelador`, `portaria`) | Papel utilizado pelo contrato de delegação. |
| `nome` | `TEXT` | NN | Nome fictício do contato. |
| `celular` | `TEXT` | ? | Usado na composição futura do aviso via WhatsApp. |

Para o seed oficial, existe **um zelador e uma portaria por condomínio**, portanto recomenda-se `UNIQUE(condominio_id, papel)` **para o cenário de dados fixos da Sprint 1**. Se a equipe decidir permitir múltiplos funcionários com o mesmo papel, remover essa unicidade e definir explicitamente a seleção do destinatário.

O papel `sindico` não gera uma linha duplicada em `responsaveis`; o contato do síndico é obtido pela carteira (`sindicos`).

### 3.4. `ocorrencias` — registro e estado atual

| Campo | Tipo | Regras | Uso |
| --- | --- | --- | --- |
| `id` | `SERIAL` | PK | Identificador sequencial interno. |
| `protocolo` | `TEXT` | NN, UQ | `TS-000001`, vinculado ao ID. |
| `condominio_id` | `INTEGER` | NN, FK → `condominios.id`, `RESTRICT` | Consulta e segregação pela carteira. |
| `origem` | `TEXT` | NN, CHECK | `morador`, `proprietario`, `funcionario`, `whatsapp_sindico`. |
| `nome` | `TEXT` | ? | Remetente, se informado. |
| `apartamento` | `TEXT` | ? | Opcional para funcionário/WhatsApp; regras adicionais de formulário dependem da validação atual. |
| `celular` | `TEXT` | ? | Obrigatório no formulário; opcional no WhatsApp — a aplicação valida por origem. |
| `local` | `TEXT` | ? | Local do problema, se informado. |
| `descricao` | `TEXT` | NN, até 2.000 caracteres | Mensagem original; não alterar para outro campo. |
| `status` | `TEXT` | NN, DEF `nova`, CHECK | `nova`, `em_andamento`, `concluida`. |
| `prioridade` | `TEXT` | ?, CHECK quando não nula | `urgente`, `alta`, `normal`, `baixa`. |
| `categoria` | `TEXT` | ?, CHECK quando não nula | `manutencao`, `seguranca_acesso`, `convivencia`, `pedido_administrativo`, `duvida`, `nao_reconhecida`. |
| `responsavel_sugerido` | `TEXT` | ?, CHECK quando não nulo | `zelador`, `portaria`, `sindico`. |
| `motivo` | `TEXT` | ? | Justificativa da classificação ou da falha. |
| `travada` | `BOOLEAN` | NN, DEF `FALSE` | Indica acionamento da trava de risco. |
| `palavra_de_risco` | `TEXT` | ? | Termo que acionou a trava. Não impor FK ao catálogo: manter evidência histórica mesmo após edição de palavras. |
| `fonte` | `TEXT` | ?, CHECK quando não nula | `regras` ou `ia` (valor já previsto no contrato; IA fora da Sprint 1). |
| `criada_em` | `TIMESTAMPTZ` | NN, DEF `now()` | Entrada para ordenação da fila. |
| `concluida_em` | `TIMESTAMPTZ` | ? | Preenchido quando a ocorrência é concluída. |

**Regras propostas:** `CHECK (char_length(descricao) BETWEEN 1 AND 2000)`; permitir `prioridade IS NULL` em caso de falha; preferir `CHECK (concluida_em IS NULL OR status = 'concluida')` para evitar datas de conclusão em ocorrências abertas. Não exigir `concluida_em` em toda linha com `status='concluida'` antes de conferir todas as funções/fixtures.

**Ponto de integração H10/H11:** o SQL de testes não tem colunas de *prioridade final* ou *responsável atual* em `ocorrencias`. Decisões e ações são gravadas em `registros_decisao`. Para a Sprint 1, não duplicar esses valores sem definir com os responsáveis pela fila como obter o estado atual (último evento válido ou atualização transacional). A consulta da fila deve ordenar por prioridade efetiva: urgente, alta, normal, baixa, e `criada_em ASC` para empate.

### 3.5. `registros_decisao` — eventos imutáveis

| Campo | Tipo | Regras | Uso |
| --- | --- | --- | --- |
| `id` | `SERIAL` | PK | Identificador do evento. |
| `ocorrencia_id` | `INTEGER` | NN, FK → `ocorrencias.id`, `RESTRICT` | Ocorrência que recebeu a decisão. |
| `tipo` | `TEXT` | NN, CHECK | `entrada`, `prioridade_confirmada`, `prioridade_alterada`, `acao`, `conclusao`, `aprovacao_lote`. |
| `quem_decidiu` | `TEXT` | NN, CHECK | `sistema` ou `sindico`. |
| `origem` | `TEXT` | ?, CHECK quando não nula | Origem para evento `entrada`. |
| `prioridade_sugerida` | `TEXT` | ?, CHECK quando não nula | Prioridade anterior/sugerida. |
| `prioridade_final` | `TEXT` | ?, CHECK quando não nula | Prioridade confirmada ou alterada. |
| `motivo` | `TEXT` | ? | Justificativa da alteração. |
| `acao` | `TEXT` | ?, CHECK quando não nula | `delegar`, `agendar`, `eu_mesmo`. |
| `responsavel` | `TEXT` | ?, CHECK quando não nulo | `zelador`, `portaria`, `sindico`. |
| `data_agendada` | `DATE` | ? | Data da ação de agendamento. |
| `nota` | `TEXT` | ? | Observação da ação. |
| `rebaixou_travada` | `BOOLEAN` | NN, DEF `FALSE` | Evidência de rebaixamento de urgência travada. |
| `data_hora` | `TIMESTAMPTZ` | NN, DEF `now()` | Horário do evento. |

**Imutabilidade:** trigger `BEFORE UPDATE OR DELETE` que recusa qualquer alteração (já existe em `schema_teste.sql` e será incorporado à migration pela SQU-64/SQU-72, sem duplicar implementação). A FK não deve usar `CASCADE`. A aplicação não deve realizar exclusão física das ocorrências com histórico; permitir que o registro continue consultável. Regras de obrigatoriedade por `tipo` são aplicadas pelo contrato da função `registrar_decisao.py`; não introduzir `CHECK`s complexos sem comparar com casos de erro e fixtures.

### 3.6. `palavras_risco` — catálogo mutável da H06

| Campo | Tipo | Regras | Uso |
| --- | --- | --- | --- |
| `id` | `SERIAL` | PK | Identificador interno. |
| `palavra` | `TEXT` | NN, UQ | Palavra/expressão de risco definida pelo PO. |
| `categoria` | `TEXT` | NN, CHECK | Categoria da expressão, conforme planilha. |
| `prioridade` | `TEXT` | NN, DEF `urgente`, CHECK (`urgente`) | Trava sempre eleva para urgente. |
| `responsavel_sugerido` | `TEXT` | NN, CHECK | No seed oficial, `sindico`. |
| `motivo` | `TEXT` | NN | Texto conforme PO, ex.: `palavra de risco: cheiro de gás`. |
| `ordem` | `INTEGER` | NN, UQ, CHECK (`ordem > 0`) | Ordem estável para desempate dos termos. |

As **12 expressões da planilha** devem ser carregadas pela SQU-73, coordenadas com a SQU-44 para não repetir trabalho. A tabela é independente das ocorrências: a ocorrência guarda a expressão acionadora como *snapshot*, mesmo que a lista seja editada depois.

**Inconsistência que precisa de teste funcional (H06):** o contrato antigo descreve busca na ordem da lista (inclui `gás` antes de `cheiro de gás`), mas a planilha oficial espera `cheiro de gás` quando a frase contém essa expressão. O banco suporta ambos; a decisão de correspondência (por exemplo, priorizar a expressão específica/mais longa) cabe ao responsável pela classificação H06 e precisa de teste. **Não afirmar que a modelagem resolve essa divergência de algoritmo.**

## 4. Relacionamentos e cardinalidades

| Origem | Destino | Cardinalidade | FK | Exclusão proposta |
| --- | --- | --- | --- | --- |
| `sindicos` | `condominios` | 1:N | `condominios.sindico_id` | `RESTRICT` |
| `condominios` | `responsaveis` | 1:N | `responsaveis.condominio_id` | `RESTRICT` |
| `condominios` | `ocorrencias` | 1:N | `ocorrencias.condominio_id` | `RESTRICT` |
| `ocorrencias` | `registros_decisao` | 1:N | `registros_decisao.ocorrencia_id` | `RESTRICT` |
| `palavras_risco` | `ocorrencias` | Sem FK física | — | Snapshot textual em `palavra_de_risco`. |

No DER, a existência de um condomínio exige síndico e a ocorrência exige condomínio; um síndico, condomínio ou ocorrência pode ter **zero registros filhos** antes das cargas/ações.

## 5. Normalização (até a terceira forma normal)

- **1FN:** colunas atômicas e linhas com PK; lista de responsáveis e de palavras de risco não é armazenada em texto multivalorado na ocorrência.
- **2FN:** todas as tabelas têm PK simples; seus atributos não dependem de parte de uma chave composta.
- **3FN:** dados pessoais e contatos do síndico ficam em `sindicos`, contatos por papel em `responsaveis`, e nome/bairro do condomínio em `condominios` — não são repetidos em cada ocorrência. A ocorrência referencia condomínio por FK; decisões são eventos associados à ocorrência.
- **Snapshots intencionais:** `ocorrencias.palavra_de_risco` e o conteúdo imutável de `registros_decisao` preservam a justificativa histórica mesmo se regras/contatos mudarem. `protocolo` deriva do ID por requisito contratual e é mantido por compatibilidade e exibição.
- **Pragmatismo da Sprint 1:** campos de `categoria`, `prioridade`, `status` e `responsavel` permanecem textuais validados, sem tabelas auxiliares de domínio. Isso não introduz repetição de dados de uma entidade separada, e evita migrações incompatíveis com as funções existentes.

## 6. Índices e consulta

Chaves primárias e UNIQUE criam índices próprios. Além deles, avaliar na migration:

- `ocorrencias(condominio_id, status, criada_em)` para recortes da carteira e status; priorização `urgente > alta > normal > baixa` deve ser feita explicitamente com `CASE`, não com ordem lexicográfica.
- `ocorrencias(condominio_id, concluida_em DESC)` para a aba concluída.
- `registros_decisao(ocorrencia_id, data_hora, id)` para histórico ordenado cronologicamente com desempate por ID.
- `responsaveis(condominio_id, papel)` já coberto por UNIQUE caso aprovado.

Não criar índices de expressão ou filtros complexos antes de verificar as queries implementadas pelo colega responsável pela fila.

## 7. Ordem de carga e dados de referência

1. `sindicos`: **Ana Beatriz Moreira** (dados fictícios do PO).
2. `condominios`: `aurora` (Residencial Aurora / Centro), `vista-verde` (Edifício Vista Verde / Jardim Europa), `palmeiras` (Condomínio Jardim das Palmeiras / Vila Nova), todos associados à carteira de teste.
3. `responsaveis`: **6 contatos** (um zelador e uma portaria por condomínio), da planilha do PO.
4. `palavras_risco`: **12 expressões** com categoria, prioridade e responsável sugerido oficiais.
5. Opcional na seed demonstrativa: ocorrências e histórico consistentes com as 24 frases de teste, sem afirmar que as 24 precisam virar registros permanentes.

As **28 regras de classificação** são um insumo da função H05 mantida pelos colegas; não serão persistidas nesta modelagem sem alinhamento, pois o PO não exige que possam ser editadas sem deploy. A H06, sim, exige lista de risco editável.

O seed precisa ser idempotente, vincular IDs gerados por consultas (não presumir que o condomínio Aurora terá `id = 1`) e não expor dados reais.

## 8. Invariantes e validação esperada na SQU-72/SQU-74

- [ ] Criar as seis tabelas num PostgreSQL vazio via migration Alembic.
- [ ] Garantir compatibilidade de `salvar_ocorrencia`, `registrar_decisao`, `concluir_ocorrencia` com os nomes e tipos de coluna.
- [ ] Validar UNIQUE de `identificador`, `protocolo`, `palavra` e `(condominio_id, papel)` se mantido.
- [ ] Testar FK inválida de condomínio, síndico, responsável e ocorrência.
- [ ] Verificar que uma ocorrência persiste antes da classificação; falha não causa perda do registro.
- [ ] Testar restrições dos domínios e permitir `NULL` na classificação incompleta.
- [ ] Conferir H11: gravar evento de ação e atualização para `em_andamento` pelo fluxo responsável, sem alterar aqui funções de colegas.
- [ ] Testar H13: somente `em_andamento` pode virar `concluida`; timestamp e histórico preenchidos.
- [ ] Testar H14: `UPDATE` e `DELETE` direto em `registros_decisao` rejeitados.
- [ ] Verificar fila com ordenação por prioridade efetiva, empate por antiguidade, e concluídas mais recentes primeiro.
- [ ] Sincronizar fixtures do esquema de teste e migration sem manter duas estruturas conflitantes.

## 9. Pendências de integração (não escondidas pelo DER)

1. **Fixture existente:** `backend/lib/tests/conftest.py` insere condomínio sem síndico; a nova FK `NOT NULL` exige adaptar a fixture ou optar por fase de transição. Esse ajuste pertence à integração SQU-72, coordenada com o autor dos testes.
2. **Fonte da prioridade efetiva:** não existe coluna de prioridade final na ocorrência; revisar com o responsável da fila se consulta o último evento ou atualiza um campo transacional. Evitar armazenar duas fontes divergentes do estado.
3. **Evento de ação e status:** `registrar_decisao.py` grava o histórico, mas não é responsável por atualizar `ocorrencias.status`; garantir que o fluxo H11 faça essa atualização antes do teste de conclusão H13.
4. **Categoria `nao_reconhecida`:** consta no PO de 17/11, não nos valores listados em `CONTRATOS.md`; comunicar ao responsável pelo contrato e pela classificação.
5. **Correspondência da expressão de risco:** `cheiro de gás` deve vencer `gás` nos exemplos oficiais, ponto de algoritmo H06 a alinhar com o colega responsável.
6. **Integridade H14:** implementar trigger uma única vez no esquema oficial; nunca usar `ON DELETE CASCADE` na FK de histórico.
7. **Revisão:** o modelo 1:N de síndico para condomínio e a unicidade de papel por condomínio são escolhas proporcionais ao cenário de dados fixos; caso o squad adote múltiplas carteiras/contatos por papel, estas duas regras precisarão de nova análise.

## 10. Entrega e divisão de responsabilidade

**SQU-71 entrega:** modelagem e DER, sem código executável. **SQU-72 entrega:** migration inicial e ajustes coordenados de compatibilidade. **SQU-73 entrega:** seed com planilha oficial. **SQU-64/SQU-68:** integridade e provas da imutabilidade do histórico. **SQU-74:** testes de persistência e consultas. **SQU-75:** guia final.

A responsabilidade pela classificação H05/H06, endpoints e frontend permanece com os respectivos colegas. Esta modelagem fornece a estrutura necessária sem assumir alterações de lógica que não pertencem às nossas tarefas.
