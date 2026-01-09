# 🏗️ Arquitectura del Sistema de Detección de Fraude

Este documento explica la arquitectura de software del proyecto, qué hace cada carpeta y cómo interactúan los componentes.

---

## 📁 Estructura del Proyecto

```
fraud-detection-meli/
├── api/                    # 🌐 Capa de API (FastAPI)
│   ├── main.py             # Punto de entrada de la aplicación
│   ├── models/             # Definición de esquemas de datos
│   │   └── schemas.py      # Modelos Pydantic (validación)
│   └── routes/             # Endpoints REST
│       ├── transactions.py # CRUD de transacciones
│       └── fraud.py        # Análisis de fraude y estadísticas
│
├── pipeline/               # 🔧 Motor de Detección de Fraude
│   ├── fraud_detector.py   # Orquestador principal
│   ├── rules_engine.py     # Motor de reglas de negocio
│   └── ml_model.py         # Modelo de Machine Learning
│
├── data/                   # 📊 Datos estáticos
│   └── users.json          # Perfiles de usuarios simulados
│
├── static/                 # 🎨 Archivos estáticos (Frontend)
│   ├── css/dashboard.css   # Estilos del dashboard
│   └── js/dashboard.js     # Lógica del frontend
│
├── templates/              # 📄 Templates HTML
│   └── dashboard.html      # Página principal
│
├── scripts/                # 🛠️ Scripts auxiliares
│   └── generate_transactions.py  # Generador de datos de prueba
│
└── INICIAR.bat             # 🚀 Script de inicio rápido
```

---

## 🏛️ Tipo de Arquitectura

### **Monolito Modular** (NO es microservicios)

Este proyecto usa una arquitectura **monolítica modular**, donde todo corre en un solo proceso pero está organizado en capas bien separadas:

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND                              │
│              (HTML + CSS + JavaScript)                       │
│                   templates/ + static/                       │
└─────────────────────────┬───────────────────────────────────┘
                          │ HTTP
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                      API LAYER                               │
│                  (FastAPI - api/)                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │ /api/       │  │ /api/fraud/ │  │ Dashboard   │          │
│  │ transactions│  │   analyze   │  │   (HTML)    │          │
│  └──────┬──────┘  └──────┬──────┘  └─────────────┘          │
└─────────┼────────────────┼──────────────────────────────────┘
          │                │
          ▼                ▼
┌─────────────────────────────────────────────────────────────┐
│                   PIPELINE LAYER                             │
│              (Detección de Fraude - pipeline/)               │
│  ┌────────────────────────────────────────────────────┐     │
│  │              FraudDetector                         │     │
│  │   (Combina reglas + ML para tomar decisiones)      │     │
│  └───────────┬────────────────────┬───────────────────┘     │
│              │                    │                          │
│  ┌───────────▼─────────┐  ┌───────▼───────────┐             │
│  │   RulesEngine       │  │   FraudMLModel    │             │
│  │ (6 reglas activas)  │  │ (Heurística/ML)   │             │
│  └─────────────────────┘  └───────────────────┘             │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    DATA LAYER                                │
│              (Almacenamiento en memoria)                     │
│  ┌─────────────────┐  ┌─────────────────┐                   │
│  │ transactions_db │  │ users.json      │                   │
│  │ (Lista Python)  │  │ (Perfiles)      │                   │
│  └─────────────────┘  └─────────────────┘                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 📦 Descripción de Cada Capa

### 1️⃣ **Frontend** (`templates/` + `static/`)

| Archivo | Qué hace |
|---------|----------|
| `dashboard.html` | Página principal con el dashboard visual |
| `css/dashboard.css` | Estilos modernos (dark mode, gradientes, animaciones) |
| `js/dashboard.js` | Lógica: llamadas a la API, generación de transacciones, actualización de UI |

**Tecnologías:** HTML5, CSS3 (vanilla), JavaScript (vanilla)

---

### 2️⃣ **API Layer** (`api/`)

El servidor web que expone los endpoints REST.

| Archivo | Qué hace |
|---------|----------|
| `main.py` | Configura FastAPI, monta rutas y archivos estáticos |
| `models/schemas.py` | Define los modelos de datos (Transaction, FraudAlert, etc.) con validación Pydantic |
| `routes/transactions.py` | Endpoints para crear, listar y eliminar transacciones |
| `routes/fraud.py` | Endpoints para análisis de fraude, alertas y estadísticas |

**Endpoints principales:**
```
POST /api/transactions      → Crea transacción y analiza fraude
GET  /api/transactions      → Lista transacciones
GET  /api/fraud/stats       → Estadísticas del sistema
GET  /api/fraud/analyze     → Analiza sin guardar
```

---

### 3️⃣ **Pipeline Layer** (`pipeline/`)

El corazón del sistema: la lógica de detección de fraude.

| Archivo | Qué hace |
|---------|----------|
| `fraud_detector.py` | **Orquestador principal**: combina reglas + ML, toma la decisión final |
| `rules_engine.py` | **Motor de reglas**: 6 reglas de negocio (monto alto, velocidad, geo, etc.) |
| `ml_model.py` | **Modelo ML**: Feature Store + detección de anomalías |

#### Flujo de una transacción:
```
1. Llega transacción → FraudDetector.analyze()
2. Se evalúan las 6 reglas → RulesEngine.evaluate()
3. Se evalúa con ML → FraudMLModel.predict()
4. Se combinan scores (60% reglas + 40% ML)
5. Se toma decisión: approved / rejected / review
6. Se retorna resultado con razones
```

#### Reglas implementadas:
| Regla | Qué detecta | Peso |
|-------|-------------|------|
| `HighAmountRule` | Monto > 3x promedio del usuario | 80% |
| `VelocityRule` | >2 transacciones en <1 minuto | 90% |
| `GeoLocationRule` | Cambio de país en <1 hora | 100% |
| `UnusualTimeRule` | Transacciones en horarios raros | 50% |
| `NewDeviceRule` | Dispositivo nunca visto | 70% |
| `FirstTransactionRule` | Cuenta nueva + monto alto | 60% |

---

### 4️⃣ **Data Layer** (`data/`)

| Archivo | Qué hace |
|---------|----------|
| `users.json` | Perfiles de 5 usuarios simulados con su historial típico |

**Nota:** En producción, esto sería PostgreSQL/Redis/DynamoDB. Acá usamos memoria + JSON para simplicidad.

---

## 🔄 Flujo Completo de una Transacción

```
Usuario presiona "Legítima" en el Dashboard
         │
         ▼
┌────────────────────────┐
│  JavaScript hace POST  │
│  a /api/transactions   │
└──────────┬─────────────┘
           │
           ▼
┌────────────────────────┐
│   FastAPI recibe       │
│   valida con Pydantic  │
└──────────┬─────────────┘
           │
           ▼
┌────────────────────────┐
│  FraudDetector.analyze │
│  ├─ RulesEngine        │
│  │  └─ 6 reglas        │
│  └─ MLModel            │
│     └─ Anomaly score   │
└──────────┬─────────────┘
           │
           ▼
┌────────────────────────┐
│  Combina scores:       │
│  0.6*reglas + 0.4*ML   │
│                        │
│  Si score > 0.8:       │
│    → REJECTED          │
│  Si score > 0.6:       │
│    → REVIEW            │
│  Si score < 0.3:       │
│    → APPROVED          │
└──────────┬─────────────┘
           │
           ▼
┌────────────────────────┐
│  Guarda en memoria     │
│  Retorna JSON response │
└──────────┬─────────────┘
           │
           ▼
┌────────────────────────┐
│  JavaScript actualiza  │
│  la tabla del Dashboard│
└────────────────────────┘
```

---

## 🆚 Diferencia con Microservicios (MELI Real)

| Aspecto | Este Proyecto (Monolito) | MELI Real (Microservicios) |
|---------|-------------------------|---------------------------|
| **Despliegue** | 1 proceso | Muchos servicios independientes |
| **Base de datos** | Memoria/JSON | PostgreSQL, DynamoDB, Redis |
| **Comunicación** | Llamadas directas | Kafka, APIs REST, gRPC |
| **Escalabilidad** | Vertical | Horizontal (Kubernetes) |
| **ML** | Heurística simple | Modelos entrenados (TensorFlow) |
| **Procesamiento** | Sincrónico | Spark, Kafka (streaming) |

---

## 🎯 Para tu entrevista

Si te preguntan sobre arquitectura, podés decir:

> "Este es un **monolito modular** diseñado para demostrar los conceptos. 
> En producción, cada capa sería un **microservicio**: la API en FastAPI/Go, 
> las reglas en un servicio separado, el ML en SageMaker/Vertex AI, 
> y todo conectado con **Kafka** para procesamiento en tiempo real."

---

## 📚 Archivos que podés ignorar

- `__pycache__/` - Cache de Python (se genera automáticamente)
- `venv/` - Entorno virtual (dependencias instaladas)

Estos se limpian automáticamente al ejecutar `INICIAR.bat`.
