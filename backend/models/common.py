from enum import Enum, IntEnum

class CommonType(str, Enum):
    """
    Визначає тип операції.
    Спадкування від str важливе для коректної роботи JSON у FastAPI.
    """
    INCOME = "income"
    EXPENSE = "expense"

class FopGroup(IntEnum):
    GROUP_1 = 1
    GROUP_2 = 2
    GROUP_3 = 3
    GROUP_4 = 4

class TaxSystem(str, Enum):
    SIMPLIFIED = "simplified"
    GENERAL = "general"

class ActivityType(str, Enum):
    SERVICES = "services"
    TRADE = "trade"
    PRODUCTION = "production"
    AGRICULTURE = "agriculture"
    OTHER = "other"

class ReportingPeriod(str, Enum):
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"