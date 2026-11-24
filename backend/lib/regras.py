from typing import NamedTuple


class Regra(NamedTuple):
    """Uma regra do PO: palavras-chave, categoria, prioridade, responsável sugerido e motivo."""

    palavras: tuple
    categoria: str
    prioridade: str
    responsavel: str
    motivo: str


REGRAS = (
    Regra(("falta de água", "sem água", "faltou água"), "manutencao", "alta", "zelador", "falta de água afeta muitos moradores"),
    Regra(("vazamento", "infiltração", "água caindo", "água descendo", "goteira"), "manutencao", "alta", "zelador", "vazamento ativo que pode piorar"),
    Regra(("elevador parado", "elevador quebrado", "elevador travado"), "manutencao", "alta", "zelador", "elevador parado afeta todos os moradores do bloco"),
    Regra(("portão aberto", "portão travado", "portão quebrado", "portão não fecha", "portão travou", "travou aberto", "portao da garagem travou"), "seguranca_acesso", "alta", "portaria", "deixa o acesso ao prédio aberto"),
    Regra(("furto", "roubo", "arrombamento", "invasão"), "seguranca_acesso", "alta", "sindico", "situação de segurança que exige decisão do síndico"),
    Regra(("sem energia", "falta de luz", "disjuntor", "queda de energia"), "manutencao", "alta", "zelador", "falta de energia em área comum afeta muitos moradores"),
    Regra(("entupimento", "entupido", "esgoto", "refluxo"), "manutencao", "alta", "zelador", "entupimento tende a piorar rápido"),
    Regra(("bomba d'água", "caixa d'água", "reservatório"), "manutencao", "alta", "zelador", "afeta o abastecimento do prédio"),
    Regra(("lâmpada", "luz queimada", "lâmpada queimada"), "manutencao", "normal", "zelador", "manutenção simples de área comum"),
    Regra(("interfone", "campainha"), "seguranca_acesso", "normal", "portaria", "afeta a comunicação, mas tem alternativa"),
    Regra(("câmera", "cftv", "monitoramento"), "seguranca_acesso", "normal", "portaria", "equipamento de segurança sem risco imediato"),
    Regra(("fechadura", "chave", "tag", "controle remoto", "crachá"), "seguranca_acesso", "normal", "portaria", "acesso individual, sem risco ao prédio"),
    Regra(("torneira", "descarga", "vaso sanitário", "sifão"), "manutencao", "normal", "zelador", "manutenção simples de área comum"),
    Regra(("pintura", "reboco", "azulejo", "piso solto"), "manutencao", "normal", "zelador", "conservação sem risco imediato"),
    Regra(("jardim", "poda", "grama", "árvore"), "manutencao", "normal", "zelador", "conservação de área externa"),
    Regra(("piscina", "sauna", "academia", "playground"), "manutencao", "normal", "zelador", "área de lazer, sem risco imediato"),
    Regra(("lixo", "lixeira", "coleta"), "manutencao", "normal", "zelador", "limpeza de área comum"),
    Regra(("barulho", "som alto", "festa", "vizinho"), "convivencia", "normal", "sindico", "conflito entre moradores, sem risco imediato"),
    Regra(("cachorro", "gato", "animal", "cocô", "coleira"), "convivencia", "normal", "sindico", "regra de convivência do regimento"),
    Regra(("vaga", "estacionamento", "carro parado", "moto parada"), "convivencia", "normal", "sindico", "uso de área comum entre moradores"),
    Regra(("cigarro", "fumando", "fumaça de cigarro"), "convivencia", "normal", "sindico", "regra de convivência do regimento"),
    Regra(("mudança", "caminhão de mudança", "autorização de mudança"), "pedido_administrativo", "normal", "sindico", "precisa de autorização do síndico"),
    Regra(("obra", "reforma", "furadeira", "martelete"), "pedido_administrativo", "normal", "sindico", "precisa de autorização e tem regra de horário"),
    Regra(("boleto", "segunda via", "taxa", "cota condominial", "multa"), "pedido_administrativo", "baixa", "sindico", "pedido administrativo sem prazo curto"),
    Regra(("reserva", "reservar", "salão de festas", "churrasqueira"), "pedido_administrativo", "baixa", "sindico", "pedido administrativo sem prazo curto"),
    Regra(("declaração", "documento", "ata", "cópia do regimento", "comprovante"), "pedido_administrativo", "baixa", "sindico", "pedido administrativo sem prazo curto"),
    Regra(("sugestão", "sugiro", "proposta", "ideia"), "pedido_administrativo", "baixa", "sindico", "sugestão, sem prazo nem risco"),
    Regra(("dúvida", "pergunta", "como faço", "posso", "qual o horário", "é permitido"), "duvida", "baixa", "sindico", "dúvida sobre regra do condomínio"),
)
