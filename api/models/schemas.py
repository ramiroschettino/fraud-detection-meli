"""
Pydantic models para la API - Similar a los DTOs en microservicios de MELI
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class TransactionStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVIEW = "review"


class FraudRiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TransactionType(str, Enum):
    PAYMENT = "payment"           # Pago de servicios
    TRANSFER = "transfer"         # Transferencia
    RECHARGE = "recharge"         # Recarga
    CRYPTO = "crypto"             # Crypto
    QR = "qr"                     # Pago QR


class TransactionCreate(BaseModel):
    """Schema para crear una nueva transacción"""
    user_id: str = Field(..., description="ID del usuario")
    amount: float = Field(..., gt=0, description="Monto de la transacción")
    currency: str = Field(default="ARS", description="Moneda")
    transaction_type: TransactionType = Field(..., description="Tipo de transacción")
    merchant_id: Optional[str] = Field(None, description="ID del comercio")
    device_id: str = Field(..., description="ID del dispositivo")
    ip_address: str = Field(..., description="IP del cliente")
    country: str = Field(default="AR", description="País de origen")
    city: Optional[str] = Field(None, description="Ciudad")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "USR-123456",
                "amount": 15000.00,
                "currency": "ARS",
                "transaction_type": "payment",
                "merchant_id": "MCH-789",
                "device_id": "DEV-ABC123",
                "ip_address": "190.220.100.50",
                "country": "AR",
                "city": "Buenos Aires"
            }
        }


class Transaction(TransactionCreate):
    """Schema completo de una transacción"""
    id: str = Field(..., description="ID único de la transacción")
    created_at: datetime = Field(default_factory=datetime.now)
    status: TransactionStatus = Field(default=TransactionStatus.PENDING)
    fraud_score: float = Field(default=0.0, ge=0, le=1)
    risk_level: FraudRiskLevel = Field(default=FraudRiskLevel.LOW)
    fraud_reasons: List[str] = Field(default_factory=list)
    processing_time_ms: Optional[float] = Field(None)


class FraudAlert(BaseModel):
    """Alerta de fraude detectado"""
    id: str
    transaction_id: str
    user_id: str
    alert_type: str
    risk_level: FraudRiskLevel
    score: float
    reasons: List[str]
    created_at: datetime
    is_resolved: bool = False
    resolved_by: Optional[str] = None
    resolution_notes: Optional[str] = None


class FraudAnalysisRequest(BaseModel):
    """Request para analizar una transacción"""
    transaction: TransactionCreate
    include_ml_analysis: bool = True
    include_rules_analysis: bool = True


class FraudAnalysisResponse(BaseModel):
    """Respuesta del análisis de fraude"""
    transaction_id: str
    is_fraud: bool
    fraud_score: float
    risk_level: FraudRiskLevel
    decision: TransactionStatus
    reasons: List[str]
    rules_triggered: List[str]
    ml_score: Optional[float] = None
    processing_time_ms: float
    recommendation: str


class UserProfile(BaseModel):
    """Perfil de usuario para análisis de comportamiento"""
    user_id: str
    avg_transaction_amount: float
    transaction_count: int
    usual_countries: List[str]
    usual_cities: List[str]
    usual_devices: List[str]
    usual_hours: List[int]  # Horas del día más frecuentes
    account_age_days: int
    risk_score: float


class StatsResponse(BaseModel):
    """Estadísticas del sistema"""
    total_transactions: int
    transactions_last_hour: int
    fraud_detected: int
    fraud_rate: float
    avg_processing_time_ms: float
    transactions_by_type: dict
    transactions_by_status: dict
    top_fraud_reasons: List[dict]
