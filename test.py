import requests
import json

url = 'http://localhost:8001/webhook/'

# Prueba 1: Mensaje completo
data1 = {
    "from": "test_user",
    "content": "Gasté 50 soles en comida hoy 2025-11-07",
    "mimetype": "text",
    "filename": ""
}

# Prueba 2: Mensaje incompleto
data2 = {
    "from": "test_user",
    "content": "Gasté 50 soles en comida",
    "mimetype": "text",
    "filename": ""
}

tests = [data1, data2]

for i, data in enumerate(tests, 1):
    try:
        response = requests.post(url, json=data, timeout=30)
        print(f'Prueba {i}:')
        print('Status:', response.status_code)
        print('Response:', response.json())
        print('---')
    except Exception as e:
        print(f'Prueba {i} Error:', e)