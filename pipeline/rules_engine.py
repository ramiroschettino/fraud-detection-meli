"""
Motor de Reglas de Detección de Fraude
======================================
Similar al sistema de reglas de negocio usado en prevención de fraude de Mercado Pago.
Las reglas se evalúan en paralelo y cada una aporta un score al resultado final.
"""
from dataclasses import dataclass
from typing import List, Dict, Any, Callable, Optional
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class RuleResult:
    """Resultado de la evaluación de una regla"""
    rule_name: str
    triggered: bool
    score_contribution: float  # 0.0 - 1.0
    reason: str
    details: Dict[str, Any]


@dataclass
class FraudDecision:
    """Decisión final del motor de reglas"""
    is_fraud: bool
    total_score: float
    risk_level: str
    triggered_rules: List[str]
    reasons: List[str]
    recommendation: str


class FraudRule:
    """Clase base para reglas de fraude"""
    
    def __init__(self, name: str, weight: float = 1.0, threshold: float = 0.5):
        self.name = name
        self.weight = weight
        self.threshold = threshold
    
    def evaluate(self, transaction: Dict, user_profile: Dict, history: List[Dict]) -> RuleResult:
        raise NotImplementedError


class HighAmountRule(FraudRule):
    """
    Regla: Detecta transacciones con montos inusualmente altos
    Si el monto es > 3x el promedio del usuario, es sospechoso
    """
    
    def __init__(self):
        super().__init__("high_amount", weight=0.8, threshold=3.0)
    
    def evaluate(self, transaction: Dict, user_profile: Dict, history: List[Dict]) -> RuleResult:
        amount = transaction.get("amount", 0)
        avg_amount = user_profile.get("avg_transaction_amount", amount)
        
        if avg_amount == 0:
            avg_amount = amount
        
        ratio = amount / avg_amount
        triggered = ratio > self.threshold
        
        # Score basado en qué tan alto es el monto
        if ratio <= 1:
            score = 0.0
        elif ratio <= 2:
            score = 0.2
        elif ratio <= 3:
            score = 0.4
        elif ratio <= 5:
            score = 0.7
        else:
            score = 1.0
        
        return RuleResult(
            rule_name=self.name,
            triggered=triggered,
            score_contribution=score * self.weight,
            reason=f"Monto {ratio:.1f}x mayor al promedio del usuario" if triggered else "",
            details={"amount": amount, "avg_amount": avg_amount, "ratio": ratio}
        )


class VelocityRule(FraudRule):
    """
    Regla: Detecta múltiples transacciones en poco tiempo
    2 transacciones en < 30 seg es sospechoso.
    3 o más es muy sospechoso.
    """
    
    def __init__(self):
        super().__init__("velocity", weight=1.2, threshold=2) # Aumentamos peso
        self.time_window_seconds = 60
    
    def evaluate(self, transaction: Dict, user_profile: Dict, history: List[Dict]) -> RuleResult:
        now = datetime.now()
        recent_count = 1 # Contamos la actual
        
        for tx in history:
            tx_time = tx.get("created_at")
            if isinstance(tx_time, str):
                tx_time = datetime.fromisoformat(tx_time.replace("Z", "+00:00"))
            
            if tx_time and (now - tx_time).total_seconds() < self.time_window_seconds:
                recent_count += 1
        
        triggered = recent_count >= self.threshold
        
        if recent_count < 2:
            score = 0.0
        elif recent_count == 2:
            score = 0.6 # Salta a 60% con solo 2 tx
        else:
            score = 1.0 # 100% con 3 o más
            
        return RuleResult(
            rule_name=self.name,
            triggered=triggered,
            score_contribution=score * self.weight,
            reason=f"Alta frecuencia: {recent_count} transacciones en 1 min" if triggered else "",
            details={"recent_transactions": recent_count}
        )


class GeoLocationRule(FraudRule):
    """
    Regla: Detecta transacciones desde ubicaciones imposibles
    Si cambia de país en menos de 1 hora, es CRÍTICO.
    """
    
    def __init__(self):
        super().__init__("geo_location", weight=2.0, threshold=1) # PESO DOBLE
        self.time_window_hours = 1
    
    def evaluate(self, transaction: Dict, user_profile: Dict, history: List[Dict]) -> RuleResult:
        current_country = transaction.get("country", "AR")
        now = datetime.now()
        
        different_country_recent = False
        last_country = None
        
        for tx in history:
            tx_time = tx.get("created_at")
            if isinstance(tx_time, str):
                tx_time = datetime.fromisoformat(tx_time.replace("Z", "+00:00"))
            
            if tx_time and (now - tx_time).total_seconds() < self.time_window_hours * 3600:
                tx_country = tx.get("country", "AR")
                if tx_country != current_country:
                    different_country_recent = True
                    last_country = tx_country
                    break
        
        usual_countries = user_profile.get("usual_countries", ["AR"])
        is_unusual_country = current_country not in usual_countries
        
        if different_country_recent:
            score = 1.0 # MÁXIMO SCORE
            reason = f"CRITICO: Viaje imposible detectado ({last_country} -> {current_country} en < 1h)"
            triggered = True
        elif is_unusual_country:
            score = 0.6
            reason = f"País inusual: {current_country}"
            triggered = True
        else:
            score = 0.0
            reason = ""
            triggered = False
        
        return RuleResult(
            rule_name=self.name,
            triggered=triggered,
            score_contribution=score * self.weight,
            reason=reason,
            details={"current_country": current_country, "last_country": last_country}
        )


class UnusualTimeRule(FraudRule):
    """
    Regla: Detecta transacciones en horarios inusuales para el usuario
    """
    def __init__(self):
        super().__init__("unusual_time", weight=0.5, threshold=0.5)
    
    def evaluate(self, transaction: Dict, user_profile: Dict, history: List[Dict]) -> RuleResult:
        tx_time = transaction.get("created_at")
        if isinstance(tx_time, str):
            tx_time = datetime.fromisoformat(tx_time.replace("Z", "+00:00"))
        elif tx_time is None:
            tx_time = datetime.now()
        
        current_hour = tx_time.hour
        usual_hours = user_profile.get("usual_hours", list(range(8, 23)))
        is_unusual = current_hour not in usual_hours
        is_very_unusual = 2 <= current_hour <= 5
        
        if is_very_unusual and is_unusual:
            score, triggered, reason = 0.8, True, f"Horario crítico: {current_hour}:00"
        elif is_unusual:
            score, triggered, reason = 0.4, True, f"Horario inusual: {current_hour}:00"
        else:
            score, triggered, reason = 0.0, False, ""
        
        return RuleResult(self.name, triggered, score * self.weight, reason, {"hour": current_hour})


class NewDeviceRule(FraudRule):
    """
    Regla: Detecta transacciones desde dispositivos nuevos
    """
    def __init__(self):
        super().__init__("new_device", weight=1.0, threshold=1)
    
    def evaluate(self, transaction: Dict, user_profile: Dict, history: List[Dict]) -> RuleResult:
        device_id = transaction.get("device_id", "unknown")
        usual_devices = user_profile.get("usual_devices", [])
        is_new = len(usual_devices) > 0 and device_id not in usual_devices
        score = 0.8 if is_new else 0.0
        return RuleResult(self.name, is_new, score * self.weight, "Dispositivo no reconocido" if is_new else "", {"device": device_id})


class FirstTransactionRule(FraudRule):
    """
    Regla: Primera transacción con monto alto
    """
    def __init__(self):
        super().__init__("first_transaction_high", weight=1.0, threshold=50000) # Subimos peso a 1.0
    
    def evaluate(self, transaction: Dict, user_profile: Dict, history: List[Dict]) -> RuleResult:
        amount = transaction.get("amount", 0)
        tx_count = user_profile.get("transaction_count", 0)
        account_age = user_profile.get("account_age_days", 365)
        is_new = tx_count < 3 or account_age < 7
        triggered = is_new and amount > self.threshold
        score = 1.0 if triggered else 0.0
        return RuleResult(self.name, triggered, score * self.weight, f"Cuenta nueva con monto alto (${amount:,.0f})" if triggered else "", {"amount": amount})


class HighRiskCountryRule(FraudRule):
    """
    Regla: Países con alta tasa de fraude (Blacklist dinámica)
    """
    def __init__(self):
        super().__init__("high_risk_country", weight=2.5, threshold=0.5)
        self.blacklist = ["NG", "RU", "KP", "SY"]

    def evaluate(self, transaction: Dict, user_profile: Dict, history: List[Dict]) -> RuleResult:
        country = transaction.get("country", "AR")
        triggered = country in self.blacklist
        score = 1.0 if triggered else 0.0
        return RuleResult(
            rule_name=self.name,
            triggered=triggered,
            score_contribution=score * self.weight,
            reason=f"País de alto riesgo detectado: {country}" if triggered else "",
            details={"country": country}
        )


class HighRiskSectorRule(FraudRule):
    """
    Regla: Sectores de alto riesgo (como Crypto)
    """
    def __init__(self):
        super().__init__("high_risk_sector", weight=1.5, threshold=0.5)

    def evaluate(self, transaction: Dict, user_profile: Dict, history: List[Dict]) -> RuleResult:
        tx_type = transaction.get("transaction_type", "")
        triggered = tx_type == "crypto"
        score = 1.0 if triggered else 0.0
        return RuleResult(
            rule_name=self.name,
            triggered=triggered,
            score_contribution=score * self.weight,
            reason="Transacción en sector de alto riesgo (Crypto)" if triggered else "",
            details={"type": tx_type}
        )


class RulesEngine:
    """
    Motor de reglas principal con lógica de combinación de riesgos
    """
    
    def __init__(self):
        self.rules: List[FraudRule] = [
            HighAmountRule(),
            VelocityRule(),
            GeoLocationRule(),
            UnusualTimeRule(),
            NewDeviceRule(),
            FirstTransactionRule(),
            HighRiskCountryRule(),
            HighRiskSectorRule(),
        ]
        
    def evaluate(
        self, 
        transaction: Dict, 
        user_profile: Optional[Dict] = None,
        transaction_history: Optional[List[Dict]] = None
    ) -> FraudDecision:
        if user_profile is None: user_profile = self._get_default_profile()
        if transaction_history is None: transaction_history = []
        
        results: List[RuleResult] = []
        total_score = 0.0
        max_possible_score = sum(rule.weight for rule in self.rules)
        
        triggered_rules = []
        reasons = []

        for rule in self.rules:
            try:
                result = rule.evaluate(transaction, user_profile, transaction_history)
                results.append(result)
                total_score += result.score_contribution
                
                if result.triggered:
                    logger.info(f"Regla '{rule.name}' activada: {result.reason}")
                    triggered_rules.append(result.rule_name)
                    if result.reason: reasons.append(result.reason)
            except Exception as e:
                logger.error(f"Error evaluando regla {rule.name}: {e}")

        # 🚀 LÓGICA DE BOOST (Correlación de Riesgo)
        # Si es Dispositivo Nuevo + Monto Alto -> El riesgo es critico
        if "new_device" in triggered_rules and "high_amount" in triggered_rules:
            total_score += 1.5 # Boost masivo
            reasons.append("⚠️ PATRÓN CRÍTICO: Dispositivo nuevo con monto elevado")

        # Normalizar score (max 1.0)
        normalized_score = min(1.0, total_score / (max_possible_score * 0.7)) # Hacemos el sistema mas estricto 0.7
        
        if normalized_score >= 0.8:
            risk = "critical"; reject = True; rec = "RECHAZAR - Fraude detectado"
        elif normalized_score >= 0.5:
            risk = "high"; reject = True; rec = "REVISAR - Riesgo alto detectado"
        elif normalized_score >= 0.3:
            risk = "medium"; reject = False; rec = "OBSERVAR - Posible riesgo"
        else:
            risk = "low"; reject = False; rec = "APROBAR - Seguro"

        return FraudDecision(
            is_fraud=reject,
            total_score=normalized_score,
            risk_level=risk,
            triggered_rules=triggered_rules,
            reasons=reasons,
            recommendation=rec
        )
    
    def _get_default_profile(self) -> Dict:
        """Perfil por defecto para usuarios sin historial"""
        return {
            "avg_transaction_amount": 10000,
            "transaction_count": 10,
            "usual_countries": ["AR"],
            "usual_cities": ["Buenos Aires"],
            "usual_devices": [],
            "usual_hours": list(range(8, 23)),
            "account_age_days": 30,
            "risk_score": 0.1
        }


# Ejemplo de uso
if __name__ == "__main__":
    engine = RulesEngine()
    
    # Transacción sospechosa de ejemplo
    test_transaction = {
        "user_id": "USR-123",
        "amount": 500000,  # Monto muy alto
        "currency": "ARS",
        "transaction_type": "transfer",
        "device_id": "DEV-NEW-999",  # Dispositivo nuevo
        "ip_address": "190.220.100.50",
        "country": "BR",  # País diferente
        "created_at": datetime.now()
    }
    
    user_profile = {
        "avg_transaction_amount": 15000,
        "transaction_count": 50,
        "usual_countries": ["AR"],
        "usual_devices": ["DEV-001", "DEV-002"],
        "usual_hours": [9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
        "account_age_days": 180,
        "risk_score": 0.1
    }
    
    decision = engine.evaluate(test_transaction, user_profile)
    
    print("\n" + "="*50)
    print("RESULTADO DEL ANÁLISIS DE FRAUDE")
    print("="*50)
    print(f"Score: {decision.total_score:.2%}")
    print(f"Nivel de riesgo: {decision.risk_level.upper()}")
    print(f"¿Es fraude?: {'SÍ' if decision.is_fraud else 'NO'}")
    print(f"Recomendación: {decision.recommendation}")
    print("\nReglas activadas:")
    for rule in decision.triggered_rules:
        print(f"  - {rule}")
    print("\nRazones:")
    for reason in decision.reasons:
        print(f"  • {reason}")
