"""
Generador de Transacciones de Prueba
====================================
Script para generar transacciones simuladas y probar el sistema de detección.
"""
import random
import json
from datetime import datetime, timedelta
from typing import List, Dict
import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Datos de ejemplo
USERS = [
    {"id": "USR-001", "name": "Juan Pérez", "avg_amount": 15000, "age_days": 365, "country": "AR"},
    {"id": "USR-002", "name": "María García", "avg_amount": 25000, "age_days": 180, "country": "AR"},
    {"id": "USR-003", "name": "Carlos López", "avg_amount": 8000, "age_days": 90, "country": "AR"},
    {"id": "USR-004", "name": "Ana Martínez", "avg_amount": 50000, "age_days": 730, "country": "AR"},
    {"id": "USR-005", "name": "Pedro Rodríguez", "avg_amount": 12000, "age_days": 45, "country": "AR"},
]

DEVICES = ["DEV-001", "DEV-002", "DEV-003", "DEV-PHONE-1", "DEV-PHONE-2"]
COUNTRIES = ["AR", "BR", "MX", "CO", "CL", "US", "NG", "RU"]
CITIES = {
    "AR": ["Buenos Aires", "Córdoba", "Rosario"],
    "BR": ["São Paulo", "Rio de Janeiro", "Brasília"],
    "MX": ["Ciudad de México", "Guadalajara"],
    "CO": ["Bogotá", "Medellín"],
    "CL": ["Santiago", "Valparaíso"],
    "US": ["Miami", "New York"],
    "NG": ["Lagos", "Abuja"],
    "RU": ["Moscow", "Saint Petersburg"],
}

TRANSACTION_TYPES = ["payment", "transfer", "recharge", "crypto", "qr"]


def generate_legit_transaction(user: Dict) -> Dict:
    """Genera una transacción legítima"""
    country = user["country"]
    return {
        "user_id": user["id"],
        "amount": random.gauss(user["avg_amount"], user["avg_amount"] * 0.3),
        "currency": "ARS",
        "transaction_type": random.choice(["payment", "transfer", "recharge", "qr"]),
        "device_id": random.choice(DEVICES[:3]),
        "ip_address": f"190.220.{random.randint(1, 255)}.{random.randint(1, 255)}",
        "country": country,
        "city": random.choice(CITIES[country]),
    }


def generate_suspicious_transaction(user: Dict) -> Dict:
    """Genera una transacción sospechosa"""
    return {
        "user_id": user["id"],
        "amount": user["avg_amount"] * random.uniform(3, 6),
        "currency": "ARS",
        "transaction_type": random.choice(["transfer", "crypto"]),
        "device_id": f"DEV-NEW-{random.randint(100, 999)}",
        "ip_address": f"45.67.{random.randint(1, 255)}.{random.randint(1, 255)}",
        "country": random.choice(["BR", "MX", "CO"]),
        "city": "Unknown",
    }


def generate_fraud_transaction() -> Dict:
    """Genera una transacción fraudulenta"""
    return {
        "user_id": f"USR-NEW-{random.randint(1000, 9999)}",
        "amount": random.uniform(200000, 500000),
        "currency": "ARS",
        "transaction_type": "crypto",
        "device_id": f"DEV-UNKNOWN-{random.randint(100, 999)}",
        "ip_address": f"123.45.{random.randint(1, 255)}.{random.randint(1, 255)}",
        "country": random.choice(["NG", "RU"]),
        "city": "Unknown",
    }


def generate_batch(count: int = 100, fraud_rate: float = 0.1) -> List[Dict]:
    """Genera un batch de transacciones"""
    transactions = []
    
    for _ in range(count):
        rand = random.random()
        user = random.choice(USERS)
        
        if rand < (1 - fraud_rate - 0.1):
            tx = generate_legit_transaction(user)
        elif rand < (1 - fraud_rate):
            tx = generate_suspicious_transaction(user)
        else:
            tx = generate_fraud_transaction()
        
        transactions.append(tx)
    
    return transactions


def save_to_file(transactions: List[Dict], filename: str):
    """Guarda transacciones a archivo JSON"""
    with open(filename, 'w') as f:
        json.dump(transactions, f, indent=2, default=str)
    print(f"✅ Guardadas {len(transactions)} transacciones en {filename}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generador de transacciones de prueba")
    parser.add_argument("-n", "--count", type=int, default=100, help="Número de transacciones")
    parser.add_argument("-f", "--fraud-rate", type=float, default=0.1, help="Tasa de fraude (0-1)")
    parser.add_argument("-o", "--output", type=str, default="data/transactions.json", help="Archivo de salida")
    parser.add_argument("--api", action="store_true", help="Enviar a la API en lugar de guardar")
    
    args = parser.parse_args()
    
    print(f"🔧 Generando {args.count} transacciones (fraude: {args.fraud_rate*100:.0f}%)...")
    
    transactions = generate_batch(args.count, args.fraud_rate)
    
    if args.api:
        import httpx
        url = "http://localhost:8000/api/transactions"
        success = 0
        for tx in transactions:
            try:
                r = httpx.post(url, json=tx, timeout=5)
                if r.status_code == 201:
                    success += 1
            except Exception as e:
                print(f"Error: {e}")
        print(f"✅ Enviadas {success}/{len(transactions)} transacciones a la API")
    else:
        os.makedirs(os.path.dirname(args.output), exist_ok=True)
        save_to_file(transactions, args.output)
    
    # Resumen
    print("\n📊 Resumen:")
    print(f"   Total: {len(transactions)}")
