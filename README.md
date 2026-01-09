# 🛡️ Mini Sistema de Detección de Fraude - Estilo Mercado Pago

Este proyecto simula un sistema de detección de fraude en tiempo real, similar a lo que se usa en Mercado Pago para prevención de fraude en transacciones.

## 🎯 ¿Qué aprenderás?

- **Big Data Processing**: Procesamiento de transacciones con PySpark
- **APIs y Microservicios**: API REST con FastAPI
- **Streaming de Datos**: Simulación de procesamiento en tiempo real
- **Machine Learning**: Modelo simple de detección de anomalías
- **Data Engineering**: Pipelines ETL, transformaciones, agregaciones

## 🏗️ Arquitectura

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Generador de  │────▶│   Pipeline de   │────▶│   API REST      │
│   Transacciones │     │   Detección     │     │   (FastAPI)     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │                        │
                               ▼                        ▼
                        ┌─────────────────┐     ┌─────────────────┐
                        │   Modelo ML     │     │   Dashboard     │
                        │   (Anomalías)   │     │   (Web UI)      │
                        └─────────────────┘     └─────────────────┘
```

## 🚀 Stack Tecnológico (Similar a Mercado Libre)

| Tecnología | Uso en este proyecto | Uso en MELI |
|------------|---------------------|-------------|
| Python | Core del proyecto | Principal lenguaje |
| PySpark | Procesamiento batch | Big Data processing |
| FastAPI | API REST | Microservicios |
| Redis | Cache de transacciones | Cache distribuido |
| PostgreSQL | Almacenamiento | Bases relacionales |
| Kafka (simulado) | Streaming | Event streaming |

## 📦 Instalación

```bash
# Crear entorno virtual
python -m venv venv

# Activar entorno (Windows)
.\venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
```

## 🎮 Ejecutar el Proyecto

### 1. Iniciar la API
```bash
python -m uvicorn api.main:app --reload --port 8000
```

### 2. Generar transacciones de prueba
```bash
python scripts/generate_transactions.py
```

### 3. Ejecutar pipeline de detección
```bash
python pipeline/fraud_detector.py
```

### 4. Ver el Dashboard
Abrir en el navegador: http://localhost:8000

## 📊 Endpoints de la API

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/` | Dashboard principal |
| GET | `/api/transactions` | Listar transacciones |
| POST | `/api/transactions` | Crear transacción |
| GET | `/api/transactions/{id}` | Detalle de transacción |
| GET | `/api/fraud/alerts` | Alertas de fraude |
| GET | `/api/stats` | Estadísticas en tiempo real |
| POST | `/api/fraud/analyze` | Analizar transacción |

## 🧠 Reglas de Detección de Fraude

El sistema detecta fraude basándose en:

1. **Monto inusual**: Transacciones > 3x el promedio del usuario
2. **Velocidad**: Múltiples transacciones en < 1 minuto
3. **Ubicación**: Transacciones desde países diferentes en < 1 hora
4. **Horario**: Transacciones en horarios inusuales para el usuario
5. **Dispositivo nuevo**: Primer uso de un dispositivo
6. **ML Score**: Predicción del modelo de anomalías

## 📁 Estructura del Proyecto

```
fraud-detection-meli/
├── api/
│   ├── main.py              # FastAPI app
│   ├── routes/
│   │   ├── transactions.py  # CRUD transacciones
│   │   └── fraud.py         # Endpoints de fraude
│   └── models/
│       └── schemas.py       # Pydantic models
├── pipeline/
│   ├── fraud_detector.py    # Pipeline principal
│   ├── rules_engine.py      # Motor de reglas
│   └── ml_model.py          # Modelo ML
├── data/
│   ├── transactions.json    # Data de prueba
│   └── users.json           # Usuarios de prueba
├── scripts/
│   └── generate_transactions.py
├── static/
│   ├── css/
│   └── js/
├── templates/
│   └── dashboard.html
├── requirements.txt
└── README.md
```

## 🎓 Conceptos Clave para la Entrevista

### 1. ¿Por qué Spark?
- Procesamiento distribuido de millones de transacciones
- Lazy evaluation para optimización
- APIs unificadas (batch + streaming)

### 2. ¿Por qué Kafka?
- Desacoplamiento de servicios
- Garantía de entrega de mensajes
- Procesamiento en tiempo real

### 3. ¿Cómo escala?
- Microservicios independientes
- Particionamiento de datos
- Cache con Redis

### 4. ¿Cómo se detecta fraude en real-time?
- Reglas de negocio + ML
- Feature engineering en tiempo real
- Decisiones en < 100ms

---

**Autor**: Proyecto educativo para preparación de entrevista en Mercado Libre
**Stack**: Python, FastAPI, PySpark, Redis
