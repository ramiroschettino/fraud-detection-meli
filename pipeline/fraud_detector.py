"""
Pipeline Principal de Detección de Fraude
==========================================
Combina el motor de reglas con el modelo ML para tomar decisiones de fraude.
Similar a la arquitectura de decisión usada en Mercado Pago.
"""
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import logging
import json

from .rules_engine import RulesEngine, FraudDecision
from .ml_model import FraudMLModel, feature_store

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class FraudAnalysisResult:
    """Resultado completo del análisis de fraude"""
    transaction_id: str
    is_fraud: bool
    fraud_score: float
    risk_level: str
    decision: str  # approved, rejected, review
    
    # Resultados de reglas
    rules_score: float
    rules_triggered: List[str]
    rules_reasons: List[str]
    
    # Resultados ML
    ml_score: float
    ml_is_anomaly: bool
    
    # Metadata
    processing_time_ms: float
    recommendation: str
    timestamp: datetime
    
    def to_dict(self) -> Dict:
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        return result


class FraudDetector:
    """
    Detector de fraude principal
    Combina reglas + ML para decisión final
    """
    
    def __init__(self):
        self.rules_engine = RulesEngine()
        self.ml_model = FraudMLModel()
        
        # Pesos para combinar scores
        self.RULES_WEIGHT = 0.6
        self.ML_WEIGHT = 0.4
        
        # Umbrales de decisión
        self.APPROVE_THRESHOLD = 0.3
        self.REVIEW_THRESHOLD = 0.6
        self.REJECT_THRESHOLD = 0.8
        
        # Métricas
        self.total_analyzed = 0
        self.fraud_detected = 0
        self.processing_times: List[float] = []
    
    def analyze(
        self, 
        transaction: Dict,
        user_profile: Optional[Dict] = None,
        transaction_history: Optional[List[Dict]] = None,
        use_ml: bool = True,
        use_rules: bool = True
    ) -> FraudAnalysisResult:
        """
        Analiza una transacción para detectar fraude
        
        Args:
            transaction: Datos de la transacción
            user_profile: Perfil del usuario (opcional, se obtiene del feature store)
            transaction_history: Historial de transacciones (opcional)
            use_ml: Si usar el modelo ML
            use_rules: Si usar el motor de reglas
        
        Returns:
            FraudAnalysisResult con la decisión y detalles
        """
        start_time = time.time()
        
        # Obtener datos del feature store si no se proporcionan
        user_id = transaction.get('user_id', 'unknown')
        
        if user_profile is None:
            user_profile = feature_store.get_user_features(user_id)
        
        if transaction_history is None:
            transaction_history = feature_store.get_transaction_history(user_id)
        
        # Agregar timestamp si no existe
        if 'created_at' not in transaction:
            transaction['created_at'] = datetime.now()
        
        # Generar ID si no existe
        tx_id = transaction.get('id', f"TX-{datetime.now().strftime('%Y%m%d%H%M%S%f')}")
        
        # Evaluar con reglas
        rules_score = 0.0
        rules_triggered = []
        rules_reasons = []
        
        if use_rules:
            rules_decision = self.rules_engine.evaluate(
                transaction, user_profile, transaction_history
            )
            rules_score = rules_decision.total_score
            rules_triggered = rules_decision.triggered_rules
            rules_reasons = rules_decision.reasons
        
        # Evaluar con ML
        ml_score = 0.0
        ml_is_anomaly = False
        
        if use_ml:
            ml_score, ml_is_anomaly = self.ml_model.predict(
                transaction, user_profile, transaction_history
            )
        
        # Combinar scores
        if use_rules and use_ml:
            combined_score = (
                rules_score * self.RULES_WEIGHT + 
                ml_score * self.ML_WEIGHT
            )
        elif use_rules:
            combined_score = rules_score
        elif use_ml:
            combined_score = ml_score
        else:
            combined_score = 0.0
        
        # Tomar decisión
        is_fraud, decision, risk_level, recommendation = self._make_decision(
            combined_score, rules_triggered, ml_is_anomaly
        )
        
        # Calcular tiempo de procesamiento
        processing_time_ms = (time.time() - start_time) * 1000
        
        # Actualizar métricas
        self.total_analyzed += 1
        if is_fraud:
            self.fraud_detected += 1
        self.processing_times.append(processing_time_ms)
        
        # Actualizar feature store
        feature_store.add_transaction_to_history(user_id, transaction)
        if not is_fraud:
            feature_store.update_user_features(user_id, transaction)
        
        result = FraudAnalysisResult(
            transaction_id=tx_id,
            is_fraud=is_fraud,
            fraud_score=combined_score,
            risk_level=risk_level,
            decision=decision,
            rules_score=rules_score,
            rules_triggered=rules_triggered,
            rules_reasons=rules_reasons,
            ml_score=ml_score,
            ml_is_anomaly=ml_is_anomaly,
            processing_time_ms=processing_time_ms,
            recommendation=recommendation,
            timestamp=datetime.now()
        )
        
        logger.info(
            f"Transacción {tx_id} analizada: "
            f"score={combined_score:.2%}, decision={decision}, "
            f"time={processing_time_ms:.1f}ms"
        )
        
        return result
    
    def _make_decision(
        self, 
        score: float, 
        rules_triggered: List[str],
        ml_is_anomaly: bool
    ) -> Tuple[bool, str, str, str]:
        """
        Toma la decisión final basada en el score combinado
        
        Returns:
            Tuple[is_fraud, decision, risk_level, recommendation]
        """
        # Reglas de override (ciertas combinaciones siempre rechazan)
        critical_rules = {'geo_location', 'velocity'}
        if len(set(rules_triggered) & critical_rules) >= 2:
            return (
                True, 
                'rejected', 
                'critical',
                'RECHAZAR - Múltiples indicadores críticos'
            )
        
        # Decisión basada en score
        if score >= self.REJECT_THRESHOLD:
            return (
                True, 
                'rejected', 
                'critical',
                'RECHAZAR - Score de fraude muy alto'
            )
        elif score >= self.REVIEW_THRESHOLD:
            return (
                True, 
                'review', 
                'high',
                'REVISAR - Requiere análisis manual del equipo de fraude'
            )
        elif score >= self.APPROVE_THRESHOLD:
            return (
                False, 
                'approved', 
                'medium',
                'APROBAR CON MONITOREO - Transacción sospechosa pero aprobada'
            )
        else:
            return (
                False, 
                'approved', 
                'low',
                'APROBAR - Transacción legítima'
            )
    
    def get_stats(self) -> Dict:
        """Retorna estadísticas del detector"""
        avg_time = sum(self.processing_times) / len(self.processing_times) if self.processing_times else 0
        
        return {
            'total_analyzed': self.total_analyzed,
            'fraud_detected': self.fraud_detected,
            'fraud_rate': self.fraud_detected / self.total_analyzed if self.total_analyzed > 0 else 0,
            'avg_processing_time_ms': avg_time,
            'min_processing_time_ms': min(self.processing_times) if self.processing_times else 0,
            'max_processing_time_ms': max(self.processing_times) if self.processing_times else 0,
        }
    
    def batch_analyze(self, transactions: List[Dict]) -> List[FraudAnalysisResult]:
        """
        Analiza un batch de transacciones
        En producción esto se haría con Spark para millones de transacciones
        """
        results = []
        
        for tx in transactions:
            result = self.analyze(tx)
            results.append(result)
        
        fraud_count = sum(1 for r in results if r.is_fraud)
        logger.info(
            f"Batch analizado: {len(transactions)} transacciones, "
            f"{fraud_count} fraudes detectados ({fraud_count/len(transactions)*100:.1f}%)"
        )
        
        return results


# Instancia global del detector
fraud_detector = FraudDetector()


def analyze_transaction(transaction: Dict) -> FraudAnalysisResult:
    """Función helper para análisis rápido"""
    return fraud_detector.analyze(transaction)


if __name__ == "__main__":
    # Demo del pipeline
    print("="*60)
    print("🛡️  DEMO: Pipeline de Detección de Fraude")
    print("="*60)
    
    # Transacción legítima
    legit_tx = {
        'user_id': 'USR-001',
        'amount': 5000,
        'currency': 'ARS',
        'transaction_type': 'payment',
        'device_id': 'DEV-001',
        'ip_address': '190.220.100.50',
        'country': 'AR',
        'city': 'Buenos Aires'
    }
    
    # Transacción sospechosa
    suspicious_tx = {
        'user_id': 'USR-001',
        'amount': 250000,  # Monto muy alto
        'currency': 'ARS',
        'transaction_type': 'transfer',
        'device_id': 'DEV-NEW-999',  # Dispositivo nuevo
        'ip_address': '45.67.89.100',
        'country': 'BR',  # País diferente
        'city': 'São Paulo'
    }
    
    # Transacción muy fraudulenta
    fraud_tx = {
        'user_id': 'USR-NEW',
        'amount': 500000,
        'currency': 'ARS',
        'transaction_type': 'crypto',
        'device_id': 'DEV-UNKNOWN',
        'ip_address': '123.45.67.89',
        'country': 'NG',  # Nigeria
        'city': 'Lagos'
    }
    
    print("\n📦 Analizando transacciones...\n")
    
    for tx, name in [(legit_tx, "Legítima"), (suspicious_tx, "Sospechosa"), (fraud_tx, "Fraudulenta")]:
        print(f"\n{'─'*50}")
        print(f"Transacción: {name}")
        print(f"{'─'*50}")
        
        result = fraud_detector.analyze(tx)
        
        print(f"ID: {result.transaction_id}")
        print(f"Monto: ${tx['amount']:,.0f}")
        print(f"Score de fraude: {result.fraud_score:.2%}")
        print(f"Nivel de riesgo: {result.risk_level.upper()}")
        print(f"Decisión: {result.decision.upper()}")
        print(f"Tiempo: {result.processing_time_ms:.1f}ms")
        
        if result.rules_triggered:
            print(f"\nReglas activadas:")
            for rule in result.rules_triggered:
                print(f"  ⚠️  {rule}")
        
        print(f"\n💡 {result.recommendation}")
    
    # Estadísticas finales
    stats = fraud_detector.get_stats()
    print("\n" + "="*60)
    print("📊 ESTADÍSTICAS")
    print("="*60)
    print(f"Total analizadas: {stats['total_analyzed']}")
    print(f"Fraudes detectados: {stats['fraud_detected']}")
    print(f"Tasa de fraude: {stats['fraud_rate']:.1%}")
    print(f"Tiempo promedio: {stats['avg_processing_time_ms']:.1f}ms")
