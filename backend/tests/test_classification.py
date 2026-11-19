from main import classificar

def check(texto, prioridade, categoria, responsavel):
    r = classificar(texto)
    assert r["prioridade"] == prioridade, f"{texto} -> prioridade {r['prioridade']}, esperava {prioridade}"
    assert r["categoria"] == categoria, f"{texto} -> categoria {r['categoria']}, esperava {categoria}"
    assert r["responsavel"] == responsavel, f"{texto} -> responsavel {r['responsavel']}, esperava {responsavel}"

# --- Regras: PRIORIDADE ALTA ---
def test_falta_agua():
    check("Falta de água no prédio todo", "alta", "manutencao", "zelador")

def test_vazamento():
    check("Vazamento no banheiro do hall, água descendo", "alta", "manutencao", "zelador")

def test_elevador_parado():
    check("Elevador parado no térreo", "alta", "manutencao", "zelador")

def test_portao_travado_aceite_h04():
    # Aceite H04: frase exata
    check("o portão da garagem travou aberto", "alta", "seguranca_acesso", "portaria")

def test_furto():
    check("Tiveram um furto na garagem ontem", "alta", "seguranca_acesso", "sindico")

def test_sem_energia():
    check("Estamos sem energia no bloco B", "alta", "manutencao", "zelador")

def test_entupimento():
    check("Esgoto entupido, refluxo no banheiro", "alta", "manutencao", "zelador")

def test_bomba_agua():
    check("Bomba d'água queimou, sem água", "alta", "manutencao", "zelador")

# --- 4 regras: PRIORIDADE NORMAL ---
def test_lampada():
    # Frase do CONTRATOS.md
    check("Lâmpada do hall queimou", "normal", "manutencao", "zelador")

def test_interfone():
    check("Interfone não funciona", "normal", "seguranca_acesso", "portaria")

def test_camera():
    check("Câmera do hall desligada", "normal", "seguranca_acesso", "portaria")

def test_torneira():
    check("Torneira do banheiro pingando", "normal", "manutencao", "zelador")

# --- 4 regras: CONVIVÊNCIA/PEDIDO ---
def test_barulho():
    check("Barulho de festa até 3h da manhã", "normal", "convivencia", "sindico")

def test_cachorro():
    check("Cachorro do vizinho latindo a noite toda", "normal", "convivencia", "sindico")

def test_vaga():
    check("Carro parado na minha vaga", "normal", "convivencia", "sindico")

def test_mudanca():
    check("Quero autorização de mudança para sábado", "normal", "pedido_administrativo", "sindico")

# --- 4 regras: PRIORIDADE BAIXA ---
def test_boleto():
    check("Preciso da segunda via do boleto", "baixa", "pedido_administrativo", "sindico")

def test_reserva():
    check("Quero reservar a churrasqueira", "baixa", "pedido_administrativo", "sindico")

def test_declaracao():
    check("Preciso de uma declaração de residência", "baixa", "pedido_administrativo", "sindico")

def test_duvida():
    # Frase do CONTRATOS.md
    check("Tenho uma dúvida sobre o regimento", "baixa", "duvida", "sindico")

# --- 2 cenários BDD do H05 ---
def test_bdd_h05_prioridade_mais_alta_vence():
    # Se esbarrar em 2 regras, vale a de prioridade mais alta
    check("Barulho no salão e falta de água no prédio", "alta", "manutencao", "zelador")

def test_bdd_h05_trava_risco_nunca_abaixa():
    # BDD H05-2: trava H06, palavra de risco - urgente
    # "lâmpada" é normal, mas "cheiro de gás" é risco = tem que dar urgente
    check("A lâmpada queimou e está com cheiro de gás", "urgente", "manutencao", "sindico")

# --- 4 testes de risco---
def test_risco_gas():
    check("tem cheiro de gás no bloco B", "urgente", "manutencao", "sindico")

def test_risco_fogo():
    check("Tem fumaça saindo do quadro de luz", "urgente", "seguranca_acesso", "sindico")

def test_fumaca_cigarro_nao_e_risco():
    check("fumaça de cigarro no corredor", "normal", "convivencia", "sindico")

def test_nao_reconhecida():
    check("O céu está bonito hoje", "normal", "nao_reconhecida", "sindico")

def test_maiuscula_e_acentos():
    check("LÂMPADA DO CORREDOR QUEIMOU!!!", "normal", "manutencao", "zelador")