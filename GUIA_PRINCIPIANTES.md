# 🎓 GUÍA PARA PRINCIPIANTES
## Sistema de Detección de Fraude - Explicación Completa

---

## 📌 ¿QUÉ ES ESTE PROYECTO?

Este proyecto simula un **sistema de detección de fraude en tiempo real**, similar al que usa Mercado Pago para proteger millones de transacciones diarias.

Cuando alguien hace un pago, transferencia o compra crypto, el sistema debe decidir en **menos de 100 milisegundos** si la transacción es legítima o fraudulenta.

---

## 🔄 FLUJO COMPLETO DE UNA TRANSACCIÓN

```
USUARIO HACE           EL SISTEMA              SE EVALUAN           SE TOMA UNA
UN PAGO           →    RECIBE LOS DATOS   →    6 REGLAS + ML   →   DECISIÓN
                                                    ↓
                                               SCORE 0-100%
                                                    ↓
                                    ┌─────────────────────────────────┐
                                    │  0-30%  → ✅ APROBAR            │
                                    │  30-60% → ⚠️ REVISAR MANUAL     │
                                    │  60-80% → 🔶 ALTO RIESGO        │
                                    │  80-100%→ 🚨 RECHAZAR           │
                                    └─────────────────────────────────┘
```

---

## 📊 LOS DATOS DE ENTRADA

Cuando simulás una transacción, el sistema recibe estos datos:

| Campo | Descripción | Ejemplo |
|-------|-------------|---------|
| `user_id` | Identificador del usuario | "USR-001" |
| `amount` | Monto en pesos | 15000 |
| `transaction_type` | Tipo de operación | "payment", "transfer", "crypto" |
| `device_id` | ID del dispositivo (celular/PC) | "DEV-001" |
| `ip_address` | Dirección IP del usuario | "190.220.100.50" |
| `country` | País de origen | "AR" (Argentina) |

### 🤔 ¿De dónde vienen estos datos en la vida real?

En Mercado Pago, estos datos se capturan automáticamente:
- **user_id**: Del login del usuario
- **amount**: Del formulario de pago
- **device_id**: Del navegador/app (fingerprinting)
- **ip_address**: De la conexión del usuario
- **country**: Se deriva de la IP

---

## 🔧 LAS 6 REGLAS DE DETECCIÓN

El sistema evalúa cada transacción contra 6 reglas. Cada regla genera un "score" de 0 a 1.

### 1️⃣ HIGH AMOUNT (Monto Alto)
```
SI el monto > 3 veces el promedio del usuario → SOSPECHOSO

Ejemplo:
- Usuario siempre gasta: $10,000 promedio
- Nueva transacción: $50,000
- Ratio: 50,000 / 10,000 = 5x
- Score: 0.7 (70% sospechoso)
```

### 2️⃣ VELOCITY (Velocidad)
```
SI más de 3 transacciones en 1 minuto → SOSPECHOSO

Ejemplo:
- 5 compras en 60 segundos
- Score: 1.0 (100% sospechoso)

¿Por qué? Un humano no puede hacer tantas compras tan rápido.
Puede ser un bot o tarjeta robada.
```

### 3️⃣ GEO LOCATION (Ubicación)
```
SI cambia de país en menos de 1 hora → MUY SOSPECHOSO

Ejemplo:
- 14:00 → Compra desde Argentina
- 14:30 → Compra desde Brasil
- ¡Imposible viajar tan rápido!
- Score: 1.0 (100% sospechoso)
```

### 4️⃣ UNUSUAL TIME (Horario Inusual)
```
SI la hora es inusual para el usuario → SOSPECHOSO

Ejemplo:
- Usuario siempre compra entre 9am-6pm
- Nueva transacción a las 3am
- Score: 0.8 (80% sospechoso)
```

### 5️⃣ NEW DEVICE (Dispositivo Nuevo)
```
SI el dispositivo nunca se usó antes → SOSPECHOSO

Ejemplo:
- Usuario siempre usa: iPhone, PC de casa
- Nueva transacción desde: Android desconocido
- Score: 0.7 (70% sospechoso)
```

### 6️⃣ FIRST TRANSACTION HIGH (Primera Transacción Alta)
```
SI cuenta nueva + monto alto → SOSPECHOSO

Ejemplo:
- Usuario se registró hace 2 días
- Primera transacción: $500,000 a crypto
- Score: 1.0 (100% sospechoso)

¿Por qué? Las cuentas falsas se crean para robar dinero rápido.
```

---

## 🤖 ¿CÓMO FUNCIONA EL ML?

### Estado Actual: HEURÍSTICA (Sin Entrenamiento)

El proyecto usa un modelo llamado **Isolation Forest**, pero actualmente **NO está entrenado** porque no hay datos históricos. En su lugar, usa "heurística" (reglas matemáticas simples).

```python
# Heurística actual (simplificada):
score = 0

if monto > 5x promedio:
    score += 0.4
    
if dispositivo nuevo:
    score += 0.2
    
if país inusual:
    score += 0.3
    
if hora sospechosa (2am-5am):
    score += 0.1
```

### ¿Cómo sería con ML entrenado?

Con datos históricos (miles de transacciones etiquetadas como fraude/no fraude), el modelo aprendería patrones más complejos:

```
CON HEURÍSTICA:                     CON ML ENTRENADO:
- Reglas fijas                      - Detecta patrones ocultos
- Fácil de evadir                   - Se adapta a nuevos fraudes
- Rápido de implementar             - Necesita miles de datos
```

### ¿Cómo entrenar el modelo?

1. Obtener datos históricos de transacciones
2. Etiquetar cuáles fueron fraude y cuáles no
3. Ejecutar el entrenamiento:

```python
from pipeline.ml_model import FraudMLModel
import pandas as pd

model = FraudMLModel()

# Cargar datos históricos
df = pd.read_csv("transacciones_historicas.csv")
perfiles = cargar_perfiles_usuarios()

# Entrenar
model.train(df, perfiles)

# El modelo se guarda automáticamente en models/fraud_model.pkl
```

---

## ⚙️ CÁLCULO DEL SCORE FINAL

```
SCORE FINAL = (Score Reglas × 60%) + (Score ML × 40%)
```

### Ejemplo Práctico:

```
Transacción: $150,000 desde Brasil, dispositivo nuevo, a las 3am

REGLAS:
- High Amount: 0.7 (monto 10x mayor)
- Geo Location: 1.0 (país diferente)  
- New Device: 0.7 (dispositivo nuevo)
- Unusual Time: 0.8 (3am es sospechoso)
- Velocity: 0.0 (primera transacción)
- First Transaction: 0.4 (cuenta nueva)

Score Reglas = promedio ponderado = 0.72 (72%)

ML (Heurística):
Score ML = 0.6 (60%)

SCORE FINAL = (0.72 × 60%) + (0.6 × 40%) = 0.67 = 67%

DECISIÓN: 🔶 ALTO RIESGO → REQUIERE REVISIÓN MANUAL
```

---

## 🚀 CÓMO USAR EL PROYECTO

### Método 1: Menú Interactivo (Recomendado)
```
1. Abrir la carpeta: c:\proyectos\data\fraud-detection-meli
2. Doble clic en: INICIAR.bat
3. Seguir las opciones del menú
```

### Método 2: Línea de Comandos
```bash
# Ir al directorio
cd c:\proyectos\data\fraud-detection-meli

# Activar entorno virtual
.\venv\Scripts\activate

# Iniciar servidor
python -m uvicorn api.main:app --reload --port 8000

# Abrir en navegador: http://localhost:8000
```

---

## 📁 ESTRUCTURA DEL PROYECTO

```
fraud-detection-meli/
│
├── api/                          # 🌐 API REST (FastAPI)
│   ├── main.py                   # Punto de entrada de la API
│   ├── routes/
│   │   ├── transactions.py       # Endpoints de transacciones
│   │   └── fraud.py              # Endpoints de análisis de fraude
│   └── models/
│       └── schemas.py            # Definición de datos (Pydantic)
│
├── pipeline/                     # 🔧 Motor de Detección
│   ├── fraud_detector.py         # Combina reglas + ML
│   ├── rules_engine.py           # Las 6 reglas de detección
│   └── ml_model.py               # Modelo de Machine Learning
│
├── static/                       # 🎨 Frontend
│   ├── css/dashboard.css
│   └── js/dashboard.js
│
├── templates/
│   └── dashboard.html            # Dashboard visual
│
├── scripts/
│   └── generate_transactions.py  # Genera datos de prueba
│
├── data/
│   └── users.json                # Usuarios de ejemplo
│
├── INICIAR.bat                   # 🚀 Menú para Windows
├── requirements.txt              # Dependencias
└── README.md                     # Documentación
```

---

## 🎯 CONCEPTOS CLAVE PARA LA ENTREVISTA

### 1. ¿Por qué combinar Reglas + ML?

| Reglas | Machine Learning |
|--------|------------------|
| ✅ Control inmediato | ✅ Detecta patrones nuevos |
| ✅ Explicables ("rechazado por X") | ✅ Se adapta con el tiempo |
| ❌ Fáciles de evadir | ❌ Caja negra |
| ❌ No detectan patrones nuevos | ❌ Necesita muchos datos |

**Respuesta:** Se usan ambos porque se complementan. Las reglas dan control y explicabilidad, el ML detecta fraudes que no podemos anticipar.

### 2. ¿Cómo manejarías millones de transacciones?

**Respuesta:** 
- **Apache Kafka** para recibir transacciones en tiempo real
- **Apache Spark** para procesar en paralelo
- **Redis** para cache de perfiles de usuario
- **Kubernetes** para escalar automáticamente

### 3. ¿Qué pasa si un cliente legítimo es rechazado?

**Respuesta:**
- Falso positivo (False Positive)
- El sistema tiene estado "REVIEW" para casos dudosos
- Un analista humano revisa manualmente
- Se ajustan los umbrales si hay muchos falsos positivos

---

## 💡 IDEAS PARA MEJORAR

1. **Agregar más datos**: historial de compras, métodos de pago previos
2. **Entrenar el modelo**: con datos reales etiquetados
3. **Agregar notificaciones**: email/SMS cuando hay fraude
4. **Mejor dashboard**: gráficos de tendencias, mapas de ubicación
5. **A/B Testing**: probar diferentes umbrales

---

## 🆘 PROBLEMAS COMUNES

### "No encuentra el módulo pipeline"
```
Solución: Asegurate de estar en el directorio correcto
cd c:\proyectos\data\fraud-detection-meli
```

### "Puerto 8000 en uso"
```
Solución: Cambiá el puerto
python -m uvicorn api.main:app --port 8001
```

### "El modelo no está entrenado"
```
Esto es normal. El sistema usa heurística por defecto.
Para entrenar necesitás datos históricos.
```

---

**¿Preguntas? ¡Éxitos en la entrevista con Mercado Libre!** 🚀
