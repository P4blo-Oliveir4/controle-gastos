from sqlmodel import Field, SQLModel
from datetime import date

class Gasto(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    categoria: str
    valor: float
    tipo: str  # 'gasto' ou 'ganho'
    data: date = Field(default_factory=date.today)