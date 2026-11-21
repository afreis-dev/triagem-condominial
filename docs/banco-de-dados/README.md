
# Banco de dados — Triagem do Síndico

Documentação técnica do banco de dados da Sprint 1 — Squad 03.

## Tecnologias

- PostgreSQL 16
- Docker Compose
- Python 3.12
- SQLAlchemy
- Alembic
- Taskipy
- Pytest

## 1. Pré-requisitos

- Docker Desktop instalado e em execução.
- Python 3.12.
- Git.

Todos os comandos deste guia devem ser executados na raiz do repositório, com o ambiente virtual Python ativado.

## 2. Configuração inicial

### Windows (PowerShell)

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements-dev.txt
```

Caso ainda não exista um arquivo `.env`:

```powershell
Copy-Item .env.example .env
```

### Linux e macOS

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements-dev.txt
```

Caso ainda não exista um arquivo `.env`:

```bash
cp .env.example .env
```

### Variáveis de ambiente

A configuração padrão para desenvolvimento local é:

```dotenv
POSTGRES_USER=triagem
POSTGRES_PASSWORD=triagem_dev
POSTGRES_DB=triagem_db_dev
POSTGRES_PORT=5432
DATABASE_URL=postgresql://triagem:triagem_dev@localhost:5432/triagem_db_dev
```

Os valores de usuário, senha, porta e banco devem ser consistentes entre o Docker Compose e a DATABASE_URL.

Nunca versione o arquivo `.env`.

## 3. Inicialização do banco

Inicie o PostgreSQL:

```bash
task db-up
```

Verifique se o serviço está saudável:

```bash
docker compose ps
```

Após o PostgreSQL apresentar o status `healthy`, execute:

```bash
task db-migrate
task db-seed
task db-seed-check
```

O banco estará estruturado e populado com os dados de referência da Sprint 1.

Para adicionar ocorrências e históricos de demonstração:

```bash
task db-seed-demo
```

## 4. Comandos disponíveis

Os comandos de desenvolvimento são centralizados no arquivo `pyproject.toml`, utilizando Taskipy.

| Comando | Descrição |
| --- | --- |
| `task --list` | Lista os comandos disponíveis |
| `task db-up` | Inicia o PostgreSQL via Docker |
| `task db-status` | Exibe a migration aplicada |
| `task db-migrate` | Aplica as migrations pendentes |
| `task db-history` | Exibe o histórico de migrations |
| `task db-seed` | Carrega os dados fixos do PO |
| `task db-seed-demo` | Carrega dados fixos e ocorrências demonstrativas |
| `task db-seed-check` | Verifica a carga dos dados de referência |
| `task db-test` | Executa os testes em um banco temporário |

## 5. Modelagem

O banco da Sprint 1 possui seis tabelas.

| Tabela | Responsabilidade |
| --- | --- |
| `sindicos` | Dados dos síndicos |
| `condominios` | Condomínios e vínculo com a carteira |
| `responsaveis` | Contatos responsáveis por condomínio |
| `ocorrencias` | Registro, classificação e estado das ocorrências |
| `registros_decisao` | Histórico imutável das decisões |
| `palavras_risco` | Catálogo de palavras de risco |

### Convenções

- Chaves primárias: `SERIAL`.
- Chaves estrangeiras: `INTEGER`.
- Identificadores textuais dos condomínios separados das chaves primárias.
- Protocolos no formato `TS-000001`, derivados do ID da ocorrência.
- Datas e horários de registro armazenados com `TIMESTAMPTZ`.
- Histórico protegido contra UPDATE e DELETE por gatilho PostgreSQL.

### Documentação complementar

- [Auditoria da Sprint 1](./auditoria-sprint-1.md)
- [Modelagem e dicionário de dados](./modelagem-sprint-1.md)
- [Diagrama Entidade-Relacionamento](./der-sprint-1.md)
- [Contratos do backend](../../CONTRATOS.md)

Os documentos de auditoria e modelagem fazem parte dos PRs #9 e #10 e estarão disponíveis após sua integração.

A coluna `condominios.sindico_id` permite NULL temporariamente. Essa decisão será revisada com o squad conforme a SQU-76.

## 6. Migrations

O Alembic é responsável pelo versionamento da estrutura do banco.

As migrations estão localizadas em:

`database/migrations/versions/`

A revisão inicial da Sprint 1 é `dc53387e1802`.

### Criar uma migration

```bash
python -m alembic revision -m "descricao da alteracao"
```

Preencha as funções `upgrade()` e `downgrade()` do arquivo gerado.

A configuração atual não utiliza metadata de modelos ORM para autogenerate. As migrations são desenvolvidas manualmente.

### Aplicar alterações

```bash
task db-migrate
task db-status
```

### Boas práticas

- Não modificar migrations já aplicadas em ambientes compartilhados.
- Criar uma nova revisão para alterações posteriores.
- Validar as migrations em banco temporário.
- Não executar SQL de criação das tabelas paralelamente ao Alembic.
- Alinhar alterações de contratos com os responsáveis pelas funcionalidades.

## 7. Seeds

Os dados oficiais de referência são armazenados em:

`database/dados_fixos_sprint1.json`

Fonte: planilha Dados_fixos_e_regras_Sprint1.xlsx, fornecida pelo PO em 17/11/2026.

A execução é realizada pelo script:

`scripts/db_seed.py`

### Dados de referência

Em um banco inicialmente vazio:

| Entidade | Quantidade |
| --- | ---: |
| Síndicos | 1 |
| Condomínios | 3 |
| Responsáveis | 6 |
| Palavras de risco | 12 |

### Dados demonstrativos

O comando `task db-seed-demo` acrescenta:

- 5 ocorrências fictícias.
- 12 registros de decisão.

Os dados demonstrativos são opcionais e destinados exclusivamente ao desenvolvimento e às apresentações.

O seed é idempotente para os dados que ele próprio cria. Executá-lo novamente não duplica seus registros.

A carga não deve ser executada em staging ou produção.

## 8. Testes automatizados

Execute:

```bash
task db-test
```

A automação:

1. Inicia ou verifica o PostgreSQL local.
2. Cria um banco temporário com nome exclusivo.
3. Aplica as migrations.
4. Executa os testes com pytest.
5. Executa o downgrade da migration se os testes passarem.
6. Remove o banco temporário.

O banco de desenvolvimento não é utilizado como destino dos testes.

### Cobertura atual

| Grupo | Testes |
| --- | ---: |
| Migration e estrutura | 7 |
| Seed e dados de referência | 6 |
| Integração e persistência | 7 |
| Total | 20 |

Os 20 testes foram aprovados em ambiente local.

A suíte valida:

- Criação das tabelas.
- Integridade referencial.
- Unicidade e restrições de domínio.
- Idempotência do seed.
- Dados de referência.
- Geração de protocolos.
- Persistência das ocorrências.
- Tratamento de falhas na classificação.
- Registro de decisões e conclusão.
- Bloqueio de UPDATE e DELETE no histórico.

A validação integral da interface, do classificador e dos fluxos de negócio depende da integração das respectivas funcionalidades.

Os testes existentes em `backend/lib/tests/` permanecem disponíveis separadamente.

## 9. Solução de problemas

### O comando task não foi encontrado

Confirme que a venv está ativada e instale as dependências:

```bash
python -m pip install -r backend/requirements-dev.txt
```

### PostgreSQL indisponível

Verifique se o Docker Desktop está em execução:

```bash
task db-up
docker compose ps
docker compose logs postgres
```

### Erro de conexão

Confira usuário, senha, porta e nome do banco no `.env`.

O comando `task db-test` exige uma conexão local com `triagem_db_dev`.

### Banco inexistente após alterar o .env

O PostgreSQL inicializa o banco definido em POSTGRES_DB somente quando o volume é criado pela primeira vez.

Alterar essa variável não renomeia nem recria bancos existentes. Caso exista um volume anterior, alinhe a configuração ou solicite ajuda ao responsável pelo banco.

### Tabela já existe ao executar a migration

O banco pode conter tabelas criadas manualmente antes da adoção do Alembic.

Não execute comandos de exclusão nem utilize alembic stamp para ignorar o problema sem conferir a estrutura e os dados existentes.

Preserve os dados importantes e alinhe a regularização do banco com a equipe.

## 10. Segurança

- Não versionar credenciais reais.
- Não executar seeds de demonstração em produção.
- Não executar downgrade em bancos compartilhados sem planejamento.
- Não utilizar `docker compose down -v` sem compreender que o volume e seus dados serão removidos.
- Utilizar `task db-test` para validar migrations e restrições sem apagar o banco de desenvolvimento.
