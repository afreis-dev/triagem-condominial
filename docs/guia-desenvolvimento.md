# Guia de desenvolvimento e integração

**Projeto:** Triagem Condominial — Squad 03

Este guia reúne as instruções para configurar o ambiente local e integrar as funcionalidades desenvolvidas pela equipe, preservando o código existente.

## 1. Estrutura proposta do projeto

```text
triagem-condominial/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── fila/
│   │   │   ├── ocorrencia/
│   │   │   └── ui/
│   │   ├── hooks/
│   │   ├── lib/
│   │   ├── routes/
│   │   └── test/
│   ├── public/
│   ├── package.json
│   ├── bun.lock
│   ├── vite.config.ts
│   └── tsconfig.json
│
├── backend/
│   ├── lib/
│   │   ├── classificar.py
│   │   ├── salvar_ocorrencia.py
│   │   └── registrar_decisao.py
│   ├── main.py
│   ├── db.py
│   └── requirements.txt
│
├── database/
│   ├── migrations/
│   │   ├── versions/
│   │   ├── env.py
│   │   └── script.py.mako
│   ├── schema.sql
│   └── seed.sql
│
├── prototype/
│   └── prototipo v.1/
│
├── docs/
│   ├── CONTRATOS.md
│   └── guia-desenvolvimento.md
│
├── .github/
├── .env.example
├── .gitignore
├── alembic.ini
├── docker-compose.yml
└── README.md
```

**Importante:** esta é a estrutura proposta após a integração. Os arquivos ainda estão distribuídos pelas branches da equipe.

### Organização do front-end

Propomos remover a pasta intermediária `frontend/condo-incident-compass/` e manter o projeto React diretamente em `frontend/`.

Essa reorganização foi testada localmente com sucesso:

- Build concluído.
- 22 testes automatizados aprovados.
- Aplicação aberta e executada no navegador.

A mudança deve ser alinhada com a PR #3 antes de ser incorporada à `develop`.

Também propomos manter `CONTRATOS.md` em `docs/` e reunir `schema.sql` e `seed.sql` em `database/`, mediante alinhamento com os respectivos responsáveis.

## 2. Configuração do ambiente local

### Pré-requisitos

- Docker Desktop
- Python 3.12 (versão de referência)
- Bun
- Node.js 20 ou superior, conforme a configuração do front-end

### PostgreSQL

Na raiz do projeto:

```powershell
Copy-Item .env.example .env
docker compose up -d
docker compose ps
```

O serviço PostgreSQL deve aparecer com status `healthy`.


Confira se `POSTGRES_DB` e `DATABASE_URL_DEV` utilizam o mesmo nome de banco.

Exemplo para desenvolvimento local:

```dotenv
APP_ENV=development
POSTGRES_DB=triagem_db_dev
DATABASE_URL_DEV=postgresql://triagem:triagem_dev@localhost:5432/triagem_db_dev
```

Para produção, utilize `APP_ENV=production` e configure `DATABASE_URL_PROD` com a conexão remota.

O backend e o Alembic utilizam a mesma configuração. Os testes com banco usam `TEST_DATABASE_URL`, separadamente.

Os valores acima são ilustrativos. Utilize as credenciais definidas no seu `.env`.

**Nunca envie o arquivo `.env` para o GitHub.**

### Back-end — FastAPI

Na raiz do projeto:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements.txt
```

Para iniciar a aplicação FastAPI, após integrar `backend/main.py`:

```powershell
python -m uvicorn backend.main:app --reload
```

A API estará disponível em:

- `http://127.0.0.1:8000`
- `http://127.0.0.1:8000/docs` — documentação Swagger

**Observação:** a aplicação atual não possui rota `GET /`. Receber `404 Not Found` na raiz é esperado e não significa que a API esteja quebrada.

### Front-end — React + Bun

O front-end utiliza `bun.lock` para registrar as dependências.

Instale o Bun pelo site oficial: https://bun.sh/

Na pasta `frontend/`, após a reorganização proposta:

```powershell
cd frontend
bun install --frozen-lockfile
bun run dev
```

A aplicação deve iniciar em `http://localhost:8080`, conforme a configuração atual.

Para validar:

```powershell
bun run build
bun run test
```

**Importante:**

- Preferir Bun para instalar e executar as dependências do front-end.
- Não misturar `bun.lock` e `package-lock.json` sem alinhamento com a equipe.
- Não executar `npm audit fix --force` para corrigir dependências automaticamente.
- Se houver inconsistência de dependências, verificar a instalação local antes de modificar o `package.json`.

**Validação realizada:** build aprovado e 22 testes passando com Bun, após a reorganização para `frontend/src/`.

## 3. Banco de dados e Alembic

O Alembic será utilizado para versionar alterações na estrutura do PostgreSQL.

As migrations ficam em `database/migrations/`, e a configuração principal em `alembic.ini`.

Com o ambiente virtual Python ativado, na raiz do projeto:

```powershell
# Consultar a versão atual
python -m alembic current

# Consultar o histórico
python -m alembic history
```

Após a criação e aprovação da migration inicial, as migrations pendentes poderão ser aplicadas com:

```powershell
python -m alembic upgrade head
```

**Atenção:** ainda não existe uma migration inicial aprovada. Não utilize `upgrade head` como substituto do `schema.sql` antes desse alinhamento.

### Esquema SQL existente

A branch `feature/db` disponibiliza:

- `sql/schema.sql` — criação das tabelas.
- `sql/seed.sql` — condomínios para testes.

Esses arquivos foram executados com sucesso em um PostgreSQL local vazio.

Para testar a implementação atual em um banco descartável, após conferir o banco de destino:

```powershell
Get-Content -Raw sql/schema.sql |
  docker compose exec -T postgres psql -U triagem -d triagem_db_dev -v ON_ERROR_STOP=1 -1
```

Depois:

```powershell
Get-Content -Raw sql/seed.sql |
  docker compose exec -T postgres psql -U triagem -d triagem_db_dev -v ON_ERROR_STOP=1 -1
```

Esses comandos são destinados exclusivamente ao ambiente local de teste, com o esquema da `feature/db` ainda não migrado para Alembic. Não os execute sobre bancos que já tenham tabelas ou dados importantes.

### Regras para migrations

- Alinhar a migration inicial com o responsável pelo banco.
- Não modificar migrations já aplicadas em ambientes compartilhados.
- Não executar migrations em staging ou produção sem aprovação.
- Não manter definições conflitantes de tabelas no SQL e no Alembic.

## 4. Integração das funcionalidades

### Front-end e FastAPI

O front-end já possui páginas, componentes, rotas e dados simulados.

O back-end possui a rota:

`POST /ocorrencias/colar`

Essa rota foi testada com sucesso, retornando HTTP 200 e persistindo uma ocorrência no PostgreSQL.

**Isso ainda não significa que o front-end esteja integrado à API.**

Antes de substituir dados simulados por requisições reais, confirmar o formato das entradas e saídas, os identificadores e o tratamento de erros.

### Funções de negócio

A equipe desenvolveu:

- `backend/lib/classificar.py`
- `backend/lib/salvar_ocorrencia.py`
- `backend/lib/registrar_decisao.py`

Os imports e retornos básicos dessas funções foram testados com sucesso.

**Entretanto, essas funções ainda são mocks.** Elas não representam necessariamente o funcionamento definitivo.

Também existe uma implementação própria de `classificar()` em `backend/main.py`.

As duas implementações retornam resultados diferentes, apesar de ambas executarem corretamente.

### Incompatibilidades identificadas

| Área | Diferença encontrada |
|---|---|
| Classificação | `backend/main.py` e `backend/lib/classificar.py` possuem lógicas e respostas distintas |
| Identificadores | O esquema SQL usa UUID para ocorrências; `CONTRATOS.md` prevê IDs numéricos |
| Condomínios | O SQL usa IDs textuais; o contrato prevê IDs numéricos |
| Status | O SQL utiliza `Nova`; o contrato prevê `nova` |
| Dependências | A API usa `psycopg2`; a infraestrutura também possui `psycopg` 3 |

**Essas diferenças precisam ser resolvidas com os responsáveis antes da integração definitiva.**

Não substituir uma implementação pela outra sem verificar quem depende de cada contrato.

## 5. Testes de integração realizados

Testes executados localmente na branch experimental `test/integration`:

| Teste | Resultado |
|---|---|
| Build do React com Bun | Aprovado |
| Testes automatizados do React | 22 aprovados |
| Execução do front-end no navegador | Aprovada |
| Inicialização do FastAPI | Aprovada |
| Documentação Swagger | Aprovada |
| Conexão Python → PostgreSQL | Aprovada |
| Criação das tabelas SQL | Aprovada |
| Inserção dos dados de exemplo | Aprovada |
| POST `/ocorrencias/colar` | HTTP 200 |
| Persistência da ocorrência no banco | Confirmada |
| Imports das funções de negócio | Aprovados |
| Execução dos mocks | Aprovada |
| Compatibilidade dos contratos | Pendente |
| Comunicação real React → FastAPI | Ainda não testada |

Esses testes comprovam o funcionamento das partes verificadas, mas não garantem a integração completa de todas as funcionalidades.

## 6. Checklist antes do pull request

- [ ] A implementação respeita a estrutura acordada.
- [ ] As funcionalidades existentes continuam funcionando.
- [ ] Não foram criadas rotas ou regras de negócio duplicadas.
- [ ] Os contratos entre front-end, back-end e banco foram respeitados.
- [ ] Dependências foram registradas corretamente.
- [ ] Arquivos `.env`, `.venv`, caches e arquivos temporários não foram versionados.
- [ ] Os testes pertinentes foram executados.
- [ ] O PR descreve possíveis impactos em outros módulos.
- [ ] O PR foi direcionado à `develop` para revisão.

---

**Regra principal:** preservar o que cada desenvolvedor construiu, validar os contratos e integrar as funcionalidades sem introduzir regressões.