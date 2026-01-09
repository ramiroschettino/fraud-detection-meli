"""
🛡️ Fraud Detection API - Estilo Mercado Pago
=============================================
API REST para detección de fraude en tiempo real.
"""
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager
import logging
import os

from api.routes.transactions import router as transactions_router
from api.routes.fraud import router as fraud_router

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle del servidor"""
    logger.info("🚀 Iniciando Fraud Detection API...")
    logger.info("📊 Dashboard disponible en http://localhost:8000")
    logger.info("📄 Documentación en http://localhost:8000/docs")
    yield
    logger.info("👋 Cerrando Fraud Detection API...")


# Crear aplicación FastAPI
app = FastAPI(
    title="🛡️ Fraud Detection API",
    description="""
    ## Sistema de Detección de Fraude en Tiempo Real
    
    Similar al sistema usado en **Mercado Pago** para prevención de fraude.
    
    ### Características:
    - 🔍 **Motor de Reglas**: 6 reglas de detección configurables
    - 🤖 **Machine Learning**: Modelo de detección de anomalías
    - ⚡ **Tiempo Real**: Análisis en < 100ms
    - 📊 **Dashboard**: Visualización de métricas
    
    ### Endpoints principales:
    - `POST /api/transactions` - Crear y analizar transacción
    - `POST /api/fraud/analyze` - Analizar sin guardar
    - `GET /api/fraud/alerts` - Ver alertas de fraude
    - `GET /api/fraud/stats` - Estadísticas del sistema
    """,
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers
app.include_router(transactions_router)
app.include_router(fraud_router)

# Configurar archivos estáticos y templates
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
static_dir = os.path.join(BASE_DIR, "static")
templates_dir = os.path.join(BASE_DIR, "templates")

# Crear directorios si no existen
os.makedirs(static_dir, exist_ok=True)
os.makedirs(os.path.join(static_dir, "css"), exist_ok=True)
os.makedirs(os.path.join(static_dir, "js"), exist_ok=True)
os.makedirs(templates_dir, exist_ok=True)

app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=templates_dir)


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Dashboard principal con métricas de fraude"""
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "fraud-detection-api",
        "version": "1.0.0"
    }


@app.get("/api")
async def api_info():
    """Información de la API"""
    return {
        "name": "Fraud Detection API",
        "version": "1.0.0",
        "description": "Sistema de detección de fraude en tiempo real",
        "endpoints": {
            "transactions": "/api/transactions",
            "fraud_analysis": "/api/fraud/analyze",
            "alerts": "/api/fraud/alerts",
            "stats": "/api/fraud/stats",
            "docs": "/docs"
        }
    }
