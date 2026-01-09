"""
API Routes para Detección de Fraude
===================================
Endpoints REST para análisis de fraude y alertas.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime
import uuid

from api.models.schemas import (
    FraudAlert,
    FraudAnalysisRequest,
    FraudAnalysisResponse,
    FraudRiskLevel,
    TransactionStatus,
    StatsResponse
)
from pipeline.fraud_detector import fraud_detector

router = APIRouter(prefix="/api/fraud", tags=["Fraud Detection"])

# Base de datos en memoria para alertas
alerts_db: List[FraudAlert] = []


@router.post("/analyze", response_model=FraudAnalysisResponse)
async def analyze_transaction(request: FraudAnalysisRequest):
    """
    Analiza una transacción para detectar fraude sin guardarla.
    Útil para pre-validación antes de confirmar una transacción.
    """
    tx_data = {
        'user_id': request.transaction.user_id,
        'amount': request.transaction.amount,
        'currency': request.transaction.currency,
        'transaction_type': request.transaction.transaction_type.value,
        'merchant_id': request.transaction.merchant_id,
        'device_id': request.transaction.device_id,
        'ip_address': request.transaction.ip_address,
        'country': request.transaction.country,
        'city': request.transaction.city,
        'created_at': datetime.now()
    }
    
    # Analizar
    result = fraud_detector.analyze(
        tx_data,
        use_ml=request.include_ml_analysis,
        use_rules=request.include_rules_analysis
    )
    
    # Mapear a response
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
    
    # Si es fraude, crear alerta
    if result.is_fraud:
        alert = FraudAlert(
            id=f"ALERT-{uuid.uuid4().hex[:8].upper()}",
            transaction_id=result.transaction_id,
            user_id=request.transaction.user_id,
            alert_type="suspicious_transaction",
            risk_level=risk_map.get(result.risk_level, FraudRiskLevel.MEDIUM),
            score=result.fraud_score,
            reasons=result.rules_reasons,
            created_at=datetime.now(),
            is_resolved=False
        )
        alerts_db.append(alert)
    
    return FraudAnalysisResponse(
        transaction_id=result.transaction_id,
        is_fraud=result.is_fraud,
        fraud_score=result.fraud_score,
        risk_level=risk_map.get(result.risk_level, FraudRiskLevel.LOW),
        decision=status_map.get(result.decision, TransactionStatus.PENDING),
        reasons=result.rules_reasons,
        rules_triggered=result.rules_triggered,
        ml_score=result.ml_score if request.include_ml_analysis else None,
        processing_time_ms=result.processing_time_ms,
        recommendation=result.recommendation
    )


@router.get("/alerts", response_model=List[FraudAlert])
async def list_alerts(
    risk_level: Optional[FraudRiskLevel] = None,
    is_resolved: Optional[bool] = None,
    limit: int = Query(default=50, le=100)
):
    """
    Lista todas las alertas de fraude
    """
    filtered = alerts_db
    
    if risk_level:
        filtered = [a for a in filtered if a.risk_level == risk_level]
    
    if is_resolved is not None:
        filtered = [a for a in filtered if a.is_resolved == is_resolved]
    
    # Ordenar por fecha (más recientes primero)
    filtered.sort(key=lambda x: x.created_at, reverse=True)
    
    return filtered[:limit]


@router.get("/alerts/{alert_id}", response_model=FraudAlert)
async def get_alert(alert_id: str):
    """
    Obtiene una alerta por su ID
    """
    for alert in alerts_db:
        if alert.id == alert_id:
            return alert
    
    raise HTTPException(status_code=404, detail="Alerta no encontrada")


@router.patch("/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: str, 
    resolved_by: str,
    notes: Optional[str] = None
):
    """
    Marca una alerta como resuelta
    """
    for alert in alerts_db:
        if alert.id == alert_id:
            alert.is_resolved = True
            alert.resolved_by = resolved_by
            alert.resolution_notes = notes
            return {"status": "resolved", "alert_id": alert_id}
    
    raise HTTPException(status_code=404, detail="Alerta no encontrada")


@router.post("/reset")
async def reset_system():
    """
    Reinicia el sistema completo (transacciones y estadísticas)
    """
    from api.routes.transactions import clear_transactions
    
    clear_transactions()
    fraud_detector.reset_stats()
    
    # También limpiar alertas locale en este módulo
    global alerts_db
    alerts_db.clear()
    
    return {"status": "success", "message": "Sistema reiniciado correctamente"}


@router.get("/stats", response_model=StatsResponse)
async def get_stats():
    """
    Obtiene estadísticas del sistema de detección
    """
    from api.routes.transactions import get_transactions_db
    
    transactions = get_transactions_db()
    detector_stats = fraud_detector.get_stats()
    
    # Estadísticas por tipo
    by_type = {}
    for tx in transactions:
        tx_type = tx.transaction_type.value
        by_type[tx_type] = by_type.get(tx_type, 0) + 1
    
    # Estadísticas por status
    by_status = {}
    for tx in transactions:
        status = tx.status.value
        by_status[status] = by_status.get(status, 0) + 1
    
    # Top razones de fraude
    reasons_count = {}
    for alert in alerts_db:
        for reason in alert.reasons:
            reasons_count[reason] = reasons_count.get(reason, 0) + 1
    
    top_reasons = [
        {"reason": k, "count": v} 
        for k, v in sorted(reasons_count.items(), key=lambda x: x[1], reverse=True)[:5]
    ]
    
    # Transacciones en la última hora
    one_hour_ago = datetime.now().timestamp() - 3600
    recent_count = sum(
        1 for tx in transactions 
        if tx.created_at.timestamp() > one_hour_ago
    )
    
    return StatsResponse(
        total_transactions=len(transactions),
        transactions_last_hour=recent_count,
        fraud_detected=detector_stats['fraud_detected'],
        fraud_rate=detector_stats['fraud_rate'],
        avg_processing_time_ms=detector_stats['avg_processing_time_ms'],
        transactions_by_type=by_type,
        transactions_by_status=by_status,
        top_fraud_reasons=top_reasons
    )


def get_alerts_db() -> List[FraudAlert]:
    """Helper para acceder a la DB de alertas"""
    return alerts_db
