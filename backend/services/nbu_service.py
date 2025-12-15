import requests
from datetime import date as date_type

def get_nbu_rate(currency_code: str, date_val: date_type) -> float:
    """
    Отримує офіційний курс НБУ на дату.
    Повертає 0.0, якщо сталася помилка або курс не знайдено.
    """
    if currency_code == "UAH":
        return 1.0
        
    date_str = date_val.strftime("%Y%m%d") # Формат YYYYMMDD
    api_url = f"https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?valcode={currency_code}&date={date_str}&json"
    
    try:
        response = requests.get(api_url, timeout=5)
        data = response.json()
        if not data:
            return 0.0
        return float(data[0]['rate'])
    except Exception as e:
        print(f"НБУ Error: {e}")
        return 0.0