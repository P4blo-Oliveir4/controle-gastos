from fastapi import FastAPI, Depends
from sqlmodel import Field, SQLModel, Session, create_engine, select
from datetime import date
from collections import defaultdict
import re
import unidecode

# Modelo de dados
class Gasto(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    categoria: str
    valor: float
    tipo: str  # 'gasto' ou 'ganho'
    data: date = Field(default_factory=date.today)

# Configuração do banco de dados
sqlite_file_name = "gastos.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"
engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

# Inicialização do FastAPI
app = FastAPI()

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

# Lista de categorias consideradas como ganhos (entradas)
CATEGORIAS_GANHO = [
    "salario", "receita", "pagamento", "ganho", "deposito"
]

# Lista de categorias consideradas como gastos (saídas)
CATEGORIAS_GASTO = [
    "gasto", "despesa", "saque", "combustivel", "internet", "carro", "faculdade", "aluguel",
    "condominio", "iptu", "supermercado", "farmacia", "plano de saude", "material escolar",
    "celular", "tv por assinatura", "lazer", "cinema", "restaurante", "passeio", "vestuario",
    "presentes", "seguro", "estacionamento", "transporte publico", "manutencao", "ipva",
    "barbearia", "happy hour", "viagem"
]

def identificar_tipo_categoria(categoria):
    categoria_normalizada = unidecode.unidecode(categoria.strip().lower())
    if categoria_normalizada in CATEGORIAS_GANHO:
        return "ganho"
    # "Saque" é uma saída, mas pode ser digitado de várias formas
    if categoria_normalizada in CATEGORIAS_GASTO:
        return "gasto"
    # Por padrão, se não estiver em nenhuma lista, trata como gasto
    return "gasto"

# Endpoint para processar mensagens e registrar gastos/ganhos
@app.post("/processar")
def processa_mensagem(payload: dict, session: Session = Depends(get_session)):
    texto = payload.get("texto", "")
    match = re.match(r"(.+)\s*-\s*([\d,.]+)", texto)
    if not match:
        return {"resposta": "Formato inválido. Use: Categoria - Valor"}
    categoria, valor = match.groups()
    valor = float(valor.replace(",", "."))
    tipo = identificar_tipo_categoria(categoria)
    novo = Gasto(categoria=categoria.strip(), valor=valor, tipo=tipo)
    session.add(novo)
    session.commit()
    ganhos = session.exec(select(Gasto).where(Gasto.tipo == "ganho")).all()
    gastos = session.exec(select(Gasto).where(Gasto.tipo == "gasto")).all()
    saldo = sum(g.valor for g in ganhos) - sum(g.valor for g in gastos)
    return {"resposta": f"{tipo.capitalize()} registrado! Saldo atual: R$ {saldo:.2f}"}

# Endpoint de relatório mensal
from sqlalchemy import extract

@app.get("/relatorio/mensal")
def relatorio_mensal(session: Session = Depends(get_session)):
    hoje = date.today()
    mes = hoje.month
    ano = hoje.year
    ganhos = session.exec(
        select(Gasto).where(
            Gasto.tipo == "ganho",
            extract('month', Gasto.data) == mes,
            extract('year', Gasto.data) == ano
        )
    ).all()
    gastos = session.exec(
        select(Gasto).where(
            Gasto.tipo == "gasto",
            extract('month', Gasto.data) == mes,
            extract('year', Gasto.data) == ano
        )
    ).all()
    saldo = sum(g.valor for g in ganhos) - sum(g.valor for g in gastos)
    return {
        "ganhos": sum(g.valor for g in ganhos),
        "gastos": sum(g.valor for g in gastos),
        "saldo": saldo
    }

# Endpoint de relatório por categoria
@app.get("/relatorio/categorias")
def relatorio_categorias(session: Session = Depends(get_session)):
    gastos = session.exec(select(Gasto).where(Gasto.tipo == "gasto")).all()
    por_categoria = defaultdict(float)
    for g in gastos:
        por_categoria[g.categoria] += g.valor
    return por_categoria