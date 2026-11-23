# Auditoria do banco de dados — Sprint 1

**Projeto:** Triagem do Síndico — Squad 03  
**Tarefa:** [SQU-70 — Auditar esquema SQL e contratos de persistência](https://linear.app/squad03/issue/SQU-70)  
**Data da auditoria:** 20/11/2026  
**Branch de referência:** `develop`  
**Escopo:** H01, H03, H04, H05, H06, H10, H11, H13 e H14

## 1. Objetivo

Identificar o estado atual da estrutura de dados, confrontá-lo com as histórias da Sprint 1 e os contratos já utilizados pelo backend e registrar o que precisa ser preservado, corrigido ou acrescentado antes de criar o modelo definitivo e a migration inicial.

A Sprint 1 deve permitir demonstrar o ciclo **registro → classificação → fila → decisão/ação → conclusão → histórico**, com dados fixos de teste. Esta auditoria **não implementa** tabelas, altera contratos ou substitui funções desenvolvidas por outros integrantes.

## 2. Fontes consultadas e critérios de precedência

### Documentação do produto (PO)

1. `PRD_Triagem_do_Sindico.docx` — objetivos, limites e diretrizes do MVP.
2. `Historias_Triagem_do_Sindico.docx` — regras de negócio e cenários BDD.
3. `Backlog_Triagem_do_Sindico.docx` — entregas priorizadas por sprint.
4. `Dados_fixos_e_regras_Sprint1.xlsx` — **planilha do PO de 17/11/2026**, com os dados fictícios para carga, regras de classificação, palavras de risco e exemplos de testes.

### Implementação da equipe

- [`CONTRATOS.md`](https://github.com/afreis-dev/triagem-condominial/blob/develop/CONTRATOS.md) — entradas, saídas e erros das funções de backend.
- [`backend/lib/tests/schema_teste.sql`](https://github.com/afreis-dev/triagem-condominial/blob/develop/backend/lib/tests/schema_teste.sql) — esquema usado exclusivamente nos testes automatizados.
- `backend/lib/tests/conftest.py` e testes de `salvar_ocorrencia`, `registrar_decisao` e `concluir_ocorrencia`.
- `backend/lib/dominio.py`, `salvar_ocorrencia.py`, `registrar_decisao.py`, `concluir_ocorrencia.py`, `classificar.py` e `conexao.py`.
- `docker-compose.yml`, `alembic.ini` e `database/migrations/env.py`.
- [`docs/guia-desenvolvimento.md`](https://github.com/afreis-dev/triagem-condominial/blob/develop/docs/guia-desenvolvimento.md).
- [`feature/db/sql/schema.sql`](https://github.com/afreis-dev/triagem-condominial/blob/feature/db/sql/schema.sql) e [`feature/db/sql/seed.sql`](https://github.com/afreis-dev/triagem-condominial/blob/feature/db/sql/seed.sql), consultados **apenas como implementação anterior**: esses arquivos não estavam presentes na árvore da `develop` durante a auditoria.

**Critério adotado:** regras de negócio e dados definidos pelo PO orientam os requisitos; `CONTRATOS.md` e o código atual orientam a compatibilidade técnica. Quando existirem diferenças, esta auditoria as aponta — não altera unilateralmente os contratos ou o código dos colegas.

## 3. Decisão de identificadores para a Sprint 1

Foi adotada para esta entrega a manutenção do padrão já utilizado no backend:

- **Chaves primárias numéricas:** `SERIAL` (`INTEGER` com sequência associada).
- **Chaves estrangeiras correspondentes:** `INTEGER`.
- **Condomínios:** `id` numérico interno e `identificador` textual único para o link, como `/c/aurora`.
- **Ocorrências:** protocolo público `TS-000001`, `TS-000002` etc., gerado a partir da sequência numérica de `ocorrencias.id`, como prevê o contrato atual.
- **UUID:** alternativa não adotada nesta sprint; não é requisito para o fluxo do MVP.

A escolha prioriza compatibilidade com `salvar_ocorrencia.py`, `registrar_decisao.py`, `concluir_ocorrencia.py`, fixtures e testes existentes. Não implica que o projeto deva manter o mesmo formato indefinidamente.

## 4. Inventário do estado atual da `develop`

| Componente | Situação encontrada | Observação |
| --- | --- | --- |
| PostgreSQL local | Configurado | Serviço `postgres:16-alpine` no Docker Compose. |
| Conexão Python | Implementada | `backend/lib/conexao.py` utiliza `psycopg2` e `DATABASE_URL`. |
| Alembic | Configurado parcialmente | Existem `alembic.ini` e arquivos-base em `database/migrations/`; `target_metadata = None`. |
| Migration inicial | **Ausente** | Não foi encontrada revisão versionada que crie as tabelas da Sprint 1. |
| SQL de produção | **Ausente na `develop`** | O SQL de `feature/db` é uma implementação anterior, não a fonte oficial integrada. |
| SQL para testes | Presente | `backend/lib/tests/schema_teste.sql` cria tabelas e trigger de histórico. |
| Seed integrado | **Ausente na `develop`** | Há dados em `feature/db/sql/seed.sql` e dados oficiais no XLSX do PO. |
| Registro, decisão e conclusão | Implementações presentes | O backend usa as tabelas e colunas do SQL de testes. |
| Classificação por regras | Ainda simulada no arquivo inspecionado | `backend/lib/classificar.py` retorna classificação padrão e trata `gás` de modo simplificado; outras tarefas cuidam da implementação real. |

### 4.1. Tabelas no esquema de testes

| Tabela | Campos e finalidade atualmente presentes | Pontos a revisar |
| --- | --- | --- |
| `condominios` | `id`, `identificador`, `nome`, `bairro` | Relacionamento com síndico/carteira. |
| `ocorrencias` | `id`, `protocolo`, `condominio_id`, `origem`, `nome`, `apartamento`, `celular`, `local`, `descricao`, `status`, `prioridade`, `categoria`, `responsavel_sugerido`, `motivo`, `travada`, `palavra_de_risco`, `fonte`, `criada_em`, `concluida_em` | Restrições de domínio, índices, vínculo com carteira e ações. |
| `registros_decisao` | `id`, `ocorrencia_id`, `tipo`, `quem_decidiu`, `origem`, `prioridade_sugerida`, `prioridade_final`, `motivo`, `acao`, `responsavel`, `data_agendada`, `nota`, `rebaixou_travada`, `data_hora` | Integridade, critérios por tipo e preservação do histórico. |

O `schema_teste.sql` também cria a função/trigger `recusar_alteracao_registro()` para impedir `UPDATE` e `DELETE` em `registros_decisao`.

**Importante:** a presença desse trigger no esquema de **testes** não prova que ele está instalado em um banco da aplicação. Sua incorporação ao esquema oficial pertence à [SQU-64](https://linear.app/squad03/issue/SQU-64).

### 4.2. O SQL anterior da `feature/db` não é intercambiável

O esquema antigo possui quatro tabelas (`condominios`, `ocorrencias`, `palavras_risco` e `registros_decisao`), mas utiliza:

- `condominios.id TEXT` e `ocorrencias.id UUID`, diferentes dos IDs numéricos dos contratos;
- nomes como `texto_original`, `nome_remetente`, `celular_remetente` e `created_at`, diferentes dos nomes consultados pelas funções Python;
- `status DEFAULT 'Nova'`, diferente de `nova` no contrato;
- uma tabela `registros_decisao` com bem menos campos do que H14 exige;
- `ON DELETE CASCADE` do histórico para a ocorrência, incompatível com a preservação de registros de decisão, caso a ocorrência seja excluída.

O `seed.sql` dessa branch já lista três condomínios e 12 palavras de risco. A base para a carga definitiva, contudo, deve ser a planilha oficial do PO, não a reprodução automática do SQL antigo.

## 5. Requisitos de dados por história da Sprint 1

| História | Necessidade no banco | Evidência/observação |
| --- | --- | --- |
| **H01 — Formulário público** | Condomínio identificado pelo link; ocorrência com origem, nome, apartamento, celular, local, descrição, data de entrada e protocolo. | Celular e descrição obrigatórios; apartamento opcional para funcionário; local opcional. |
| **H03 — Fila única** | Ocorrências associadas aos condomínios da carteira, com prioridade, status, motivo e data. | Ordenar `urgente > alta > normal > baixa`; empate pela **mais antiga**. Na aba concluída, **mais recente conclusão primeiro** (H13). |
| **H04 — Colar mensagem** | Registrar condomínio, texto, origem de WhatsApp e remetente opcional. | Passa pela mesma classificação que H01; descrição até 2.000 caracteres. |
| **H05 — Regras** | Persistir prioridade, categoria, responsável sugerido, motivo e fonte da classificação. | As **28 regras** e a categoria `nao_reconhecida` constam na planilha oficial do PO. |
| **H06 — Risco** | Disponibilizar as **12 palavras de risco** em fonte editável sem redeploy; gravar palavra acionadora e trava. | Palavra de risco impõe prioridade `urgente`; a planilha do PO define também categoria e responsável sugerido. |
| **H10 — Prioridade** | Conservar prioridade sugerida, prioridade final e motivo da alteração. | Rebaixamento de ocorrência travada exige justificativa e registro destacado. |
| **H11 — Ação** | Suportar delegação ao responsável do condomínio, agendamento com data ou responsabilidade do síndico; nota opcional. | Ao confirmar ação, ocorrência passa para `em_andamento`. |
| **H13 — Conclusão** | Status `concluida`, timestamp de conclusão e evento no histórico. | Só pode concluir ocorrência em andamento. |
| **H14 — Histórico** | Gravar cada decisão com data/hora, autor e informações pertinentes; proibir edição e exclusão. | Correção gera novo registro; testar bloqueio de `UPDATE` e `DELETE`. |

O PRD exige que os dados sejam separados por síndico, **mesmo com apenas um síndico de teste**, e que a ocorrência seja persistida antes da classificação; uma falha de classificação não pode fazê-la desaparecer.

## 6. Dados fixos oficiais entregues pelo PO

A planilha `Dados_fixos_e_regras_Sprint1.xlsx`, entregue em **17/11/2026**, contém dados **fictícios para demonstração**:

| Aba | Conteúdo | Uso previsto |
| --- | --- | --- |
| `Condomínios` | **3** condomínios: `aurora`, `vista-verde`, `palmeiras`, com nome e bairro. | Seed de condomínios e slugs. |
| `Síndico` | **1** síndica: Ana Beatriz Moreira, com celular e e-mail fictícios. | Seed da carteira de teste, sem implementação de login. |
| `Responsáveis` | **6** pessoas: zelador e portaria de cada condomínio, com nome e celular fictícios. | Delegação da H11. |
| `Regras de classificação` | **28** regras ordenadas, com palavras-chave, categoria, prioridade, responsável sugerido e motivo. | Implementação da H05 por quem estiver responsável pela classificação. |
| `Palavras de risco` | **12** entradas com categoria, prioridade `urgente`, responsável sugerido e motivo. | Tabela/carga da H06 e integração com a SQU-44. |
| `Frases de teste` | **24** frases com resultados esperados. | Testes de H05/H06; não são automaticamente 24 ocorrências obrigatórias no seed. |

### Regras complementares explicitadas na planilha

- Se houver mais de uma regra compatível, vale a de **maior prioridade**.
- Em empate de prioridade, vale a **primeira regra da planilha**.
- Sem correspondência: prioridade `normal`, categoria `nao_reconhecida`, responsável `sindico`, motivo `não reconhecida, revisar`.
- A trava de risco é aplicada por último e não pode reduzir a prioridade.

**Divergência documental importante:** o `CONTRATOS.md` inspecionado ainda lista apenas cinco categorias e marca o fallback como “a confirmar com o PO”. A planilha de 17/11 acrescenta `nao_reconhecida` e define o fallback. A modelagem deve prever esse valor; o responsável pelo backend precisa alinhar contrato, validação e testes, sem que esta auditoria altere sua implementação unilateralmente.

Também não se deve presumir que os exemplos genéricos de categoria/responsável do contrato substituem os valores específicos da planilha. Por exemplo, a aba `Palavras de risco` sugere `sindico` para os casos urgentes, enquanto exemplos ilustrativos antigos do contrato mostram `zelador` em algumas dessas situações.

## 7. Divergências e ajustes identificados

| ID | Prioridade | Diagnóstico | Encaminhamento |
| --- | --- | --- | --- |
| D01 | **Alta** | Não existe migration inicial integrada à `develop`. | Criar a estrutura oficial com Alembic após aprovar o DER (SQU-72). |
| D02 | **Alta** | Dois esquemas divergentes: SQL antigo da `feature/db` e SQL de testes da `develop`. | Tomar contrato e testes atuais como referência técnica, confrontar com PO e não mesclar schemas cegamente (SQU-71). |
| D03 | **Alta** | Ausência, no esquema de testes, de entidades/vínculos de síndico e responsáveis para o fluxo H03/H11. | Modelar o mínimo necessário para a carteira e delegação, com dados fixos da planilha (SQU-71/73). |
| D04 | **Alta** | `palavras_risco` não existe no esquema de testes e não há seed de produção integrado; SQU-44 está marcada como concluída. | Verificar trabalho já feito, incorporar sem duplicação e manter lista editável no banco (SQU-72/73). |
| D05 | **Alta** | O fallback da classificação e a categoria `nao_reconhecida` estão definidos na planilha, mas não atualizados no contrato da `develop`. | Avisar responsáveis por H05/contrato; incluir o valor permitido no modelo conforme PO. |
| D06 | **Alta** | Gatilho de imutabilidade existe somente no SQL dos testes. | Incorporar ao esquema oficial e validar bloqueio no PostgreSQL (SQU-64/68). |
| D07 | **Alta** | Histórico do SQL antigo tem campos insuficientes e FK com `ON DELETE CASCADE`. | Preservar estrutura completa de H14 e evitar exclusão indireta dos registros. |
| D08 | Média | O esquema de testes não declara `CHECK` para status, prioridade, origem, categoria, ação/tipo de decisão. | Definir restrições compatíveis com o contrato e tolerantes aos campos realmente opcionais (SQU-71/72). |
| D09 | Média | `tests/conftest.py` monta o banco com `schema_teste.sql`, independentemente do Alembic. | Alinhar testes e migration para evitar duas fontes de verdade (SQU-72/74). |
| D10 | Média | Não há índices de consulta da fila/histórico explicitados no SQL de testes. | Projetar apenas os índices que atendem consultas reais da Sprint 1 (SQU-71/72). |
| D11 | Média | O guia de desenvolvimento apresenta uma **estrutura proposta**, incluindo caminhos/arquivos ainda não integrados. | Atualizar documentação só depois de validar o arranjo final (SQU-75). |

## 8. Compatibilidade com o trabalho dos colegas

O código da `develop` já depende das seguintes convenções:

- `salvar_ocorrencia.py` procura `condominios.id`, insere em `ocorrencias` com nomes de colunas do SQL de testes e usa `pg_get_serial_sequence('ocorrencias', 'id')` para gerar o protocolo.
- `registrar_decisao.py` valida o ID numérico da ocorrência, grava em `registros_decisao` e consulta `ocorrencias.travada` para determinar `rebaixou_travada`.
- `concluir_ocorrencia.py` exige `status = 'em_andamento'`, atualiza `concluida_em` e grava evento de `conclusao`.
- Os testes usam schemas temporários com `SERIAL` e verificam retornos numéricos.

**Não alterar essas funções por conta própria na SQU-70.** Se o modelo aprovado exigir colunas ou vínculos novos, incluir de forma compatível com as consultas atuais e comunicar eventuais mudanças de contrato ao responsável pela implementação.

A classificação real, as telas do frontend e a integração da fila pertencem às tarefas dos colegas. A responsabilidade de banco nesta sprint é **fornecer estrutura, integridade e dados de teste** para que esses fluxos funcionem, não duplicar a lógica de aplicação.

## 9. Decisões e pontos a resolver na modelagem (SQU-71)

### Definido para esta entrega

1. IDs internos numéricos com `SERIAL`/`INTEGER`, conforme contratos e funções atuais.
2. Manter slug textual único para o link do condomínio.
3. Manter protocolo público sequencial `TS-000001`.
4. Utilizar exclusivamente dados fictícios na carga inicial.
5. Preservar integralmente o histórico de decisões.
6. Não implementar login, IA, anexos/fotos, filtros avançados ou aprovação em lote como funcionalidades da Sprint 1; campos de tipos já previstos no contrato podem permanecer se não causarem trabalho adicional.

### A especificar no DER

1. Relacionamento entre síndico e condomínios: atender à exigência de separação por carteira sem adicionar autenticação.
2. Representação dos responsáveis: associar os seis registros da planilha a seus condomínios e papéis (`zelador`/`portaria`); o síndico também pode ser responsável por uma ação.
3. Campos/relacionamentos da ação atual e da auditoria: decidir quais dados operacionais ficam em `ocorrencias` e quais pertencem somente ao histórico imutável, respeitando o contrato existente.
4. Restrições e índices mínimos, incluindo a categoria `nao_reconhecida` e prioridades/status previstos.
5. Política de exclusão que não elimine o histórico por cascata.

**Observação:** os pontos acima são decisões de **modelagem**, não permissões para antecipar funcionalidades além do MVP.

## 10. Checklist para encerrar a SQU-70

- [x] Confrontar requisitos H01/H03/H04/H05/H06/H10/H11/H13/H14 com a estrutura disponível.
- [x] Inventariar tabelas e arquivos atuais da `develop`.
- [x] Inspecionar a implementação anterior da `feature/db` sem confundi-la com código integrado.
- [x] Incorporar as informações oficiais de dados fixos e regras do PO.
- [x] Registrar divergências, impactos, encaminhamentos e decisão de identificadores.
- [x] Preservar a autoria/escopo das implementações dos colegas.
- [ ] Revisar este documento no PR e obter aprovação para merge em `develop`.

## 11. Próximas tarefas, em ordem

1. **[SQU-71](https://linear.app/squad03/issue/SQU-71):** produzir modelo lógico normalizado, cardinalidades, DER e dicionário mínimo.
2. **[SQU-72](https://linear.app/squad03/issue/SQU-72):** criar migration inicial e constraints sem conflitar com o SQL de testes.
3. **[SQU-73](https://linear.app/squad03/issue/SQU-73):** criar carga inicial a partir da planilha oficial do PO, respeitando as entregas já realizadas.
4. **[SQU-64](https://linear.app/squad03/issue/SQU-64):** instalar/provar imutabilidade de `registros_decisao` no esquema oficial.
5. **[SQU-74](https://linear.app/squad03/issue/SQU-74) e [SQU-68](https://linear.app/squad03/issue/SQU-68):** validar persistência, relacionamentos, fluxos e cenários BDD.
6. **[SQU-75](https://linear.app/squad03/issue/SQU-75):** atualizar guia de configuração e documentação final.

---

> **Limite desta auditoria:** revisão documental e leitura estática do repositório. Não foram executados testes contra PostgreSQL, aplicadas migrations ou modificados arquivos do backend nesta etapa. As conclusões devem ser revalidadas se a branch `develop` mudar antes da implementação.
