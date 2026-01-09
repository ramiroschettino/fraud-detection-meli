"""
Modelo de Machine Learning para Detección de Fraude
===================================================
Implementa un modelo de detección de anomalías usando Isolation Forest.
Similar a los modelos usados en Mercado Pago para complementar las reglas de negocio.
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import logging
import pickle
import os

# Intentar importar sklearn, si no está disponible usar fallback
try:
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler, LabelEncoder
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logging.warning("scikit-learn no disponible, usando modelo simplificado")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FraudMLModel:
    """
    Modelo de ML para detección de fraude
    Usa Isolation Forest para detectar transacciones anómalas
    """
    
    def __init__(self, model_path: Optional[str] = None):
        self.model = None
        self.scaler = None
        self.label_encoders = {}
        self.feature_columns = [
            'amount',
            'hour',
            'day_of_week',
            'account_age_days',
            'transaction_count',
            'amount_ratio',
            'is_new_device',
            'is_unusual_country',
            'velocity_1min',
            'velocity_1hour'
        ]
        self.is_trained = False
        self.model_path = model_path or "models/fraud_model.pkl"
        
        if SKLEARN_AVAILABLE:
            self._initialize_model()
        
        # Intentar cargar modelo pre-entrenado
        self._load_model()
    
    def _initialize_model(self):
        """Inicializa el modelo Isolation Forest"""
        self.model = IsolationForest(
            n_estimators=100,
            contamination=0.1,  # Esperamos ~10% de fraudes
            random_state=42,
            n_jobs=-1
        )
        self.scaler = StandardScaler()
    
    def extract_features(
        self, 
        transaction: Dict, 
        user_profile: Dict,
        transaction_history: List[Dict]
    ) -> np.ndarray:
        """
        Extrae features de una transacción para el modelo
        
        Este es el "feature engineering" - muy importante para entrevistas!
        """
        now = datetime.now()
        tx_time = transaction.get('created_at', now)
        if isinstance(tx_time, str):
            tx_time = datetime.fromisoformat(tx_time.replace("Z", "+00:00"))
        
        # Features básicas
        amount = transaction.get('amount', 0)
        hour = tx_time.hour
        day_of_week = tx_time.weekday()
        
        # Features del perfil
        account_age_days = user_profile.get('account_age_days', 30)
        transaction_count = user_profile.get('transaction_count', 1)
        avg_amount = user_profile.get('avg_transaction_amount', amount)
        
        # Features derivadas
        amount_ratio = amount / avg_amount if avg_amount > 0 else 1
        
        # Device
        device_id = transaction.get('device_id', '')
        usual_devices = user_profile.get('usual_devices', [])
        is_new_device = 1 if device_id not in usual_devices else 0
        
        # País
        country = transaction.get('country', 'AR')
        usual_countries = user_profile.get('usual_countries', ['AR'])
        is_unusual_country = 1 if country not in usual_countries else 0
        
        # Velocidad
        velocity_1min = self._calculate_velocity(transaction_history, seconds=60)
        velocity_1hour = self._calculate_velocity(transaction_history, seconds=3600)
        
        features = np.array([
            amount,
            hour,
            day_of_week,
            account_age_days,
            transaction_count,
            amount_ratio,
            is_new_device,
            is_unusual_country,
            velocity_1min,
            velocity_1hour
        ]).reshape(1, -1)
        
        return features
    
    def _calculate_velocity(self, history: List[Dict], seconds: int) -> int:
        """Calcula cuántas transacciones hubo en los últimos N segundos"""
        now = datetime.now()
        count = 0
        
        for tx in history:
            tx_time = tx.get('created_at')
            if isinstance(tx_time, str):
                tx_time = datetime.fromisoformat(tx_time.replace("Z", "+00:00"))
            if tx_time and (now - tx_time).total_seconds() < seconds:
                count += 1
        
        return count
    
    def train(self, transactions_df: pd.DataFrame, user_profiles: Dict):
        """
        Entrena el modelo con datos históricos
        
        En producción esto se haría con Spark y datos de millones de transacciones
        """
        if not SKLEARN_AVAILABLE:
            logger.warning("sklearn no disponible, no se puede entrenar")
            return
        
        logger.info("Iniciando entrenamiento del modelo...")
        
        # Extraer features de todas las transacciones
        features_list = []
        
        for _, row in transactions_df.iterrows():
            tx = row.to_dict()
            user_id = tx.get('user_id', 'unknown')
            user_profile = user_profiles.get(user_id, self._default_profile())
            
            # Simplificación: no usamos historial en entrenamiento
            features = self.extract_features(tx, user_profile, [])
            features_list.append(features.flatten())
        
        X = np.array(features_list)
        
        # Escalar features
        X_scaled = self.scaler.fit_transform(X)
        
        # Entrenar modelo
        self.model.fit(X_scaled)
        self.is_trained = True
        
        logger.info(f"Modelo entrenado con {len(X)} transacciones")
        
        # Guardar modelo
        self._save_model()
    
    def predict(
        self, 
        transaction: Dict, 
        user_profile: Dict,
        transaction_history: List[Dict]
    ) -> Tuple[float, bool]:
        """
        Predice si una transacción es fraudulenta
        
        Returns:
            Tuple[float, bool]: (fraud_score, is_anomaly)
        """
        if not SKLEARN_AVAILABLE:
            # Fallback: usar heurística simple
            return self._simple_heuristic(transaction, user_profile)
        
        features = self.extract_features(transaction, user_profile, transaction_history)
        
        if not self.is_trained:
            # Si no hay modelo entrenado, usar heurística
            return self._simple_heuristic(transaction, user_profile)
        
        # Escalar features
        features_scaled = self.scaler.transform(features)
        
        # Predicción (-1 = anomalía, 1 = normal)
        prediction = self.model.predict(features_scaled)[0]
        
        # Score de anomalía (más negativo = más anómalo)
        anomaly_score = self.model.decision_function(features_scaled)[0]
        
        # Convertir a score de fraude (0-1, donde 1 es muy fraudulento)
        # decision_function retorna valores negativos para anomalías
        fraud_score = max(0, min(1, 0.5 - anomaly_score * 0.5))
        
        is_fraud = prediction == -1
        
        logger.info(f"ML Prediction - Score: {fraud_score:.3f}, Is Anomaly: {is_fraud}")
        
        return fraud_score, is_fraud
    
    def _simple_heuristic(self, transaction: Dict, user_profile: Dict) -> Tuple[float, bool]:
        """
        Heurística simple cuando sklearn no está disponible
        """
        score = 0.0
        
        # Factor 1: Monto vs promedio
        amount = transaction.get('amount', 0)
        avg = user_profile.get('avg_transaction_amount', amount)
        if avg > 0:
            ratio = amount / avg
            if ratio > 5:
                score += 0.4
            elif ratio > 3:
                score += 0.2
            elif ratio > 2:
                score += 0.1
        
        # Factor 2: Dispositivo nuevo
        device_id = transaction.get('device_id', '')
        usual_devices = user_profile.get('usual_devices', [])
        if device_id not in usual_devices and len(usual_devices) > 0:
            score += 0.2
        
        # Factor 3: País inusual
        country = transaction.get('country', 'AR')
        usual_countries = user_profile.get('usual_countries', ['AR'])
        if country not in usual_countries:
            score += 0.3
        
        # Factor 4: Horario inusual
        tx_time = transaction.get('created_at', datetime.now())
        if isinstance(tx_time, str):
            tx_time = datetime.fromisoformat(tx_time.replace("Z", "+00:00"))
        hour = tx_time.hour
        if 2 <= hour <= 5:
            score += 0.1
        
        is_fraud = score > 0.5
        
        return score, is_fraud
    
    def _default_profile(self) -> Dict:
        """Perfil por defecto"""
        return {
            'avg_transaction_amount': 10000,
            'transaction_count': 10,
            'usual_countries': ['AR'],
            'usual_devices': [],
            'account_age_days': 30
        }
    
    def _save_model(self):
        """Guarda el modelo entrenado"""
        if not self.is_trained:
            return
        
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'feature_columns': self.feature_columns
        }
        
        with open(self.model_path, 'wb') as f:
            pickle.dump(model_data, f)
        
        logger.info(f"Modelo guardado en {self.model_path}")
    
    def _load_model(self):
        """Carga un modelo pre-entrenado"""
        if not os.path.exists(self.model_path):
            logger.info("No hay modelo pre-entrenado, se usará heurística")
            return
        
        try:
            with open(self.model_path, 'rb') as f:
                model_data = pickle.load(f)
            
            self.model = model_data['model']
            self.scaler = model_data['scaler']
            self.feature_columns = model_data['feature_columns']
            self.is_trained = True
            
            logger.info("Modelo cargado exitosamente")
        except Exception as e:
            logger.error(f"Error cargando modelo: {e}")


class FeatureStore:
    """
    Feature Store simplificado
    En producción usarían algo como Feast o un sistema custom con Redis
    """
    
    def __init__(self):
        self.user_features: Dict[str, Dict] = {}
        self.transaction_history: Dict[str, List[Dict]] = {}
    
    def get_user_features(self, user_id: str) -> Dict:
        """Obtiene features pre-calculadas del usuario"""
        return self.user_features.get(user_id, {
            'avg_transaction_amount': 10000,
            'transaction_count': 0,
            'usual_countries': ['AR'],
            'usual_devices': [],
            'usual_hours': list(range(8, 23)),
            'account_age_days': 30,
            'risk_score': 0.1
        })
    
    def update_user_features(self, user_id: str, transaction: Dict):
        """Actualiza features del usuario después de una transacción"""
        if user_id not in self.user_features:
            self.user_features[user_id] = self.get_user_features(user_id)
        
        profile = self.user_features[user_id]
        
        # Actualizar promedio de monto (moving average)
        old_avg = profile['avg_transaction_amount']
        count = profile['transaction_count']
        new_amount = transaction.get('amount', 0)
        
        new_avg = (old_avg * count + new_amount) / (count + 1)
        profile['avg_transaction_amount'] = new_avg
        profile['transaction_count'] = count + 1
        
        # Actualizar dispositivos
        device_id = transaction.get('device_id')
        if device_id and device_id not in profile['usual_devices']:
            profile['usual_devices'].append(device_id)
            # Mantener solo los últimos 5
            profile['usual_devices'] = profile['usual_devices'][-5:]
        
        # Actualizar países
        country = transaction.get('country')
        if country and country not in profile['usual_countries']:
            profile['usual_countries'].append(country)
    
    def get_transaction_history(self, user_id: str, limit: int = 100) -> List[Dict]:
        """Obtiene historial de transacciones del usuario"""
        return self.transaction_history.get(user_id, [])[-limit:]
    
    def add_transaction_to_history(self, user_id: str, transaction: Dict):
        """Agrega transacción al historial"""
        if user_id not in self.transaction_history:
            self.transaction_history[user_id] = []
        
        self.transaction_history[user_id].append(transaction)
        
        # Mantener solo las últimas 1000
        self.transaction_history[user_id] = self.transaction_history[user_id][-1000:]

    def reset(self):
        """Limpia todo el feature store (usuarios e historial)"""
        self.user_features.clear()
        self.transaction_history.clear()
        logging.info("Feature Store reiniciado")


# Singleton para uso global
feature_store = FeatureStore()
fraud_model = FraudMLModel()


if __name__ == "__main__":
    # Test del modelo
    model = FraudMLModel()
    
    test_tx = {
        'amount': 150000,
        'device_id': 'DEV-NEW',
        'country': 'BR',
        'created_at': datetime.now()
    }
    
    test_profile = {
        'avg_transaction_amount': 15000,
        'transaction_count': 50,
        'usual_countries': ['AR'],
        'usual_devices': ['DEV-001'],
        'account_age_days': 180
    }
    
    score, is_fraud = model.predict(test_tx, test_profile, [])
    
    print(f"\n{'='*50}")
    print("PREDICCIÓN ML")
    print(f"{'='*50}")
    print(f"Score de fraude: {score:.2%}")
    print(f"¿Es fraude?: {'SÍ' if is_fraud else 'NO'}")
