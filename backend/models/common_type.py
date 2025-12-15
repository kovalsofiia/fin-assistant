from enum import Enum

class CommonType(str, Enum):
    """
    Визначає тип операції.
    Спадкування від str важливе для коректної роботи JSON у FastAPI.
    """
    INCOME = "income"
    EXPENSE = "expense"