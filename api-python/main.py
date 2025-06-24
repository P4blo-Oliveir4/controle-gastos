from fastapi import FastAPI, Depends, Query
from sqlmodel import Field, SQLModel, Session, create_engine, select, Session, delete
from datetime import date
from collections import defaultdict
from sqlalchemy import text
import re
import unidecode
from sqlalchemy import extract

# Modelo de dados com usuario_id
class Gasto(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    usuario_id: str
    categoria: str
    valor: float
    tipo: str  # 'gasto' ou 'ganho'
    pagamento: str  # NOVO CAMPO: 'pix', 'debito', 'credito', 'vr'
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

app = FastAPI()

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

# Categorias de ganhos e gastos
CATEGORIAS_GANHO = [
    "salario", "receita", "pagamento", "ganho", "deposito"
]

CATEGORIAS_GASTO = [
    "gasto", "despesa", "saque", "combustivel", "internet", "carro", "faculdade", "aluguel",
    "condominio", "iptu", "supermercado", "farmacia", "plano de saude", "material escolar",
    "celular", "tv por assinatura", "lazer", "cinema", "restaurante", "passeio", "vestuario",
    "presentes", "seguro", "estacionamento", "transporte publico", "manutencao", "ipva",
    "barbearia", "happy hour", "viagem"
]

def identificar_tipo_categoria(categoria):
    categoria_normalizada = unidecode.unidecode(categoria.strip().lower())
    if categoria_normalizada in ["salario", "receita", "pagamento", "ganho", "deposito"]:
        return "ganho"
    return "gasto"

# Endpoint para processar mensagens e registrar gastos/ganhos com usuario_id
@app.post("/processar")
def processa_mensagem(payload: dict, session: Session = Depends(get_session)):
    texto = payload.get("texto", "")
    usuario_id = payload.get("usuario_id", None)
    if not usuario_id:
        return {"resposta": "Usuário não identificado."}

    match = re.match(
        r"(.+?)\s+(pix|debito|d[eé]bito|credito|cr[eé]dito|vr)\s+([\d,.]+)",
        texto.strip(),
        re.IGNORECASE
    )
    if not match:
        return {"resposta": "Formato inválido. Use: Categoria forma_pagamento valor (ex: Comida credito 100)"}

    categoria, pagamento, valor = match.groups()
    pagamento = pagamento.lower().replace("é", "e")
    if pagamento in ["debito", "pix"]:
        pagamento = "debito"
    elif pagamento in ["credito"]:
        pagamento = "credito"
    elif pagamento == "vr":
        pagamento = "vr"
    else:
        pagamento = "outro"

    valor = float(valor.replace(",", "."))
    tipo = identificar_tipo_categoria(categoria)
    novo = Gasto(
        usuario_id=usuario_id,
        categoria=categoria.strip(),
        valor=valor,
        tipo=tipo,
        pagamento=pagamento
    )
    session.add(novo)
    session.commit()

    # Calcule o saldo apenas da carteira usada
    ganhos = session.exec(
        select(Gasto).where(
            Gasto.tipo == "ganho",
            Gasto.usuario_id == usuario_id,
            Gasto.pagamento == pagamento
        )
    ).all()
    gastos = session.exec(
        select(Gasto).where(
            Gasto.tipo == "gasto",
            Gasto.usuario_id == usuario_id,
            Gasto.pagamento == pagamento
        )
    ).all()
    saldo_carteira = sum(g.valor for g in ganhos) - sum(g.valor for g in gastos)

    return {
        "resposta": f"{tipo.capitalize()} registrado! Saldo {pagamento} atual: R$ {saldo_carteira:.2f}"
    }

# Endpoint de relatório mensal filtrado por usuario_id
@app.get("/relatorio/mensal")
def relatorio_mensal(usuario_id: str, session: Session = Depends(get_session)):
    hoje = date.today()
    mes = hoje.month
    ano = hoje.year
    ganhos = session.exec(
        select(Gasto).where(
            Gasto.tipo == "ganho",
            Gasto.usuario_id == usuario_id,
            extract('month', Gasto.data) == mes,
            extract('year', Gasto.data) == ano
        )
    ).all()
    gastos = session.exec(
        select(Gasto).where(
            Gasto.tipo == "gasto",
            Gasto.usuario_id == usuario_id,
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

# Endpoint de relatório por categoria filtrado por usuario_id
@app.get("/relatorio/categorias")
def relatorio_categorias(usuario_id: str, session: Session = Depends(get_session)):
    gastos = session.exec(select(Gasto).where(Gasto.tipo == "gasto", Gasto.usuario_id == usuario_id)).all()
    por_categoria = defaultdict(float)
    for g in gastos:
        por_categoria[g.categoria] += g.valor
    return por_categoria

@app.delete("/reset_usuario")
def reset_usuario(usuario_id: str = Query(...), session: Session = Depends(get_session)):
    statement = delete(Gasto).where(Gasto.usuario_id == usuario_id)
    session.exec(statement)
    session.commit()
    return {"resposta": "Todos os seus dados foram apagados com sucesso!"}

@app.get("/saldo")
def saldo(usuario_id: str = Query(...), session: Session = Depends(get_session)):
    formas = ["debito", "credito", "vr"]
    saldos = {}
    for carteira in formas:
        ganhos = session.exec(
            select(Gasto).where(
                Gasto.tipo == "ganho",
                Gasto.usuario_id == usuario_id,
                Gasto.pagamento == carteira
            )
        ).all()
        gastos = session.exec(
            select(Gasto).where(
                Gasto.tipo == "gasto",
                Gasto.usuario_id == usuario_id,
                Gasto.pagamento == carteira
            )
        ).all()
        saldo = sum(g.valor for g in ganhos) - sum(g.valor for g in gastos)
        saldos[carteira] = saldo
    return {"saldos": saldos}

@app.post("/carteira/adicionar")
def adicionar_saldo(usuario_id: str, carteira: str, valor: float, session: Session = Depends(get_session)):
    novo = Gasto(
        usuario_id=usuario_id,
        categoria="saldo_inicial",
        valor=valor,
        tipo="ganho",
        pagamento=carteira
    )
    session.add(novo)
    session.commit()
    return {"resposta": f"Saldo adicionado à carteira {carteira}!"}

@app.post("/carteira/remover")
def remover_saldo(usuario_id: str, carteira: str, valor: float, session: Session = Depends(get_session)):
    novo = Gasto(
        usuario_id=usuario_id,
        categoria="ajuste_saldo",
        valor=valor,
        tipo="gasto",
        pagamento=carteira
    )
    session.add(novo)
    session.commit()
    return {"resposta": f"Saldo removido da carteira {carteira}!"}

@app.get("/carteira/saldo")
def saldo_carteira(usuario_id: str, carteira: str, session: Session = Depends(get_session)):
    ganhos = session.exec(
        select(Gasto).where(
            Gasto.tipo == "ganho",
            Gasto.usuario_id == usuario_id,
            Gasto.pagamento == carteira
        )
    ).all()
    gastos = session.exec(
        select(Gasto).where(
            Gasto.tipo == "gasto",
            Gasto.usuario_id == usuario_id,
            Gasto.pagamento == carteira
        )
    ).all()
    saldo = sum(g.valor for g in ganhos) - sum(g.valor for g in gastos)
    return {"saldo": saldo}