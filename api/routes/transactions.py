"""
API Routes para Transacciones
=============================
Endpoints REST para gestión de transacciones.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime
import uuid

from api.models.schemas import (
    Transaction, 
    TransactionCreate, 
    TransactionStatus,
    FraudRiskLevel
)

router = APIRouter(prefix="/api/transactions", tags=["Transactions"])

# Base de datos en memoria (en producción sería PostgreSQL/Redis)
transactions_db: List[Transaction] = []


@router.get("", response_model=List[Transaction])
async def list_transactions(
    status: Optional[TransactionStatus] = None,
    risk_level: Optional[FraudRiskLevel] = None,
    user_id: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    offset: int = 0
):
    """
    Lista todas las transacciones con filtros opcionales
    """
    filtered = transactions_db
    
    if status:
        filtered = [tx for tx in filtered if tx.status == status]
    
    if risk_level:
        filtered = [tx for tx in filtered if tx.risk_level == risk_level]
    
    if user_id:
        filtered = [tx for tx in filtered if tx.user_id == user_id]
    
    # Ordenar por fecha (más recientes primero)
    filtered.sort(key=lambda x: x.created_at, reverse=True)
    
    return filtered[offset:offset + limit]


@router.get("/{transaction_id}", response_model=Transaction)
async def get_transaction(transaction_id: str):
    """
    Obtiene una transacción por su ID
    """
    for tx in transactions_db:
        if tx.id == transaction_id:
            return tx
    
    raise HTTPException(status_code=404, detail="Transacción no encontrada")


@router.post("", response_model=Transaction, status_code=201)
async def create_transaction(transaction: TransactionCreate):
    """
    Crea una nueva transacción y la analiza para fraude
    """
    import time
    from pipeline.fraud_detector import fraud_detector
    
    start_time = time.time()
    
    # Crear transacción
    tx_id = f"TX-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"
    
    # Preparar datos para análisis
    tx_data = {
        'id': tx_id,
        'user_id': transaction.user_id,
        'amount': transaction.amount,
        'currency': transaction.currency,
        'transaction_type': transaction.transaction_type.value,
        'merchant_id': transaction.merchant_id,
        'device_id': transaction.device_id,
        'ip_address': transaction.ip_address,
        'country': transaction.country,
        'city': transaction.city,
        'created_at': datetime.now()
    }
    
    # Analizar fraude
    analysis = fraud_detector.analyze(tx_data)
    
    # Mapear decisión a status
    status_map = {
        'approved': TransactionStatus.APPROVED,
        'rejected': TransactionStatus.REJECTED,
        'review': TransactionStatus.REVIEW
    }
    
    risk_map = {
        'low': FraudRiskLevel.LOW,
        'medium': FraudRiskLevel.MEDIUM,
        'high': FraudRiskLevel.HIGH,
        'critical': FraudRiskLevel.CRITICAL
    }
    
    processing_time = (time.time() - start_time) * 1000
    
    # Crear objeto Transaction completo
    new_tx = Transaction(
        id=tx_id,
        user_id=transaction.user_id,
        amount=transaction.amount,
        currency=transaction.currency,
        transaction_type=transaction.transaction_type,
        merchant_id=transaction.merchant_id,
        device_id=transaction.device_id,
        ip_address=transaction.ip_address,
        country=transaction.country,
        city=transaction.city,
        created_at=datetime.now(),
        status=status_map.get(analysis.decision, TransactionStatus.PENDING),
        fraud_score=analysis.fraud_score,
        risk_level=risk_map.get(analysis.risk_level, FraudRiskLevel.LOW),
        fraud_reasons=analysis.rules_reasons,
        processing_time_ms=processing_time
    )
    
    transactions_db.append(new_tx)
    
    return new_tx


@router.delete("/{transaction_id}", status_code=204)
async def delete_transaction(transaction_id: str):
    """
    Elimina una transacción (solo para testing)
    """
    global transactions_db
    
    for i, tx in enumerate(transactions_db):
        if tx.id == transaction_id:
            transactions_db.pop(i)
            return
    
    raise HTTPException(status_code=404, detail="Transacción no encontrada")


def get_transactions_db() -> List[Transaction]:
    """Helper para acceder a la DB desde otros módulos"""
    return transactions_db


def add_transaction(tx: Transaction):
    """Helper para agregar transacciones desde otros módulos"""
    transactions_db.append(tx)
