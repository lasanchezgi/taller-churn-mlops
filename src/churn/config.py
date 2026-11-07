"""Configuración central del proyecto (rutas, semillas, umbrales).

Todo valor que afecte resultados vive aquí para garantizar reproducibilidad.
"""
from pathlib import Path

# Rutas base (relativas a la raíz del repositorio)
ROOT = Path(__file__).resolve().parents[2]
DATA_RAW = ROOT / "data" / "raw" / "churn_telco.csv"
DATA_PROCESSED = ROOT / "data" / "processed"
DATA_DRIFT = ROOT / "data" / "drift"
MODELS_DIR = ROOT / "models"
MODEL_PATH = MODELS_DIR / "churn_model.joblib"
MODEL_CARD_PATH = MODELS_DIR / "model_card.json"
REPORTS_DIR = ROOT / "reports"
METRICS_PATH = REPORTS_DIR / "metrics" / "evaluacion.json"
DRIFT_REPORT_PATH = REPORTS_DIR / "metrics" / "drift.json"
MITIGACION_PATH = REPORTS_DIR / "metrics" / "mitigacion_equidad.json"
ULTIMO_LOTE_PATH = REPORTS_DIR / "metrics" / "ultimo_lote.json"
DASHBOARD_PATH = ROOT / "dashboard" / "index.html"
LOGS_DIR = ROOT / "logs"
PREDICTIONS_LOG = LOGS_DIR / "predicciones.jsonl"

# Reproducibilidad
SEED = 42
N_CLIENTES = 5000
TEST_SIZE = 0.25

# Versión del modelo: cambiarla cada vez que cambien datos, features o algoritmo
MODEL_VERSION = "1.0.0"

# Columnas del dataset
TARGET = "churn"
ID_COL = "id_cliente"
NUMERIC_FEATURES = [
    "antiguedad_meses",
    "cargo_mensual",
    "reclamos_ult_3m",
    "uso_datos_gb",
]
CATEGORICAL_FEATURES = ["tipo_plan", "metodo_pago", "renovo_contrato"]
FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES
# Atributo sensible: NO entra al modelo, sólo se usa para auditar sesgo
SENSITIVE_COL = "rango_edad"

# Rangos válidos de las variables numéricas (FR-006): los usan el generador, la calidad de datos y la API
ANTIGUEDAD_RANGO = (1, 120)
CARGO_RANGO = (10.0, 1000.0)
RECLAMOS_RANGO = (0, 6)
USO_DATOS_RANGO = (0.0, 1000.0)
ID_CLIENTE_MAX = 64
ID_CLIENTE_PATRON = r"^[A-Za-z0-9_-]+$"

# Dominios válidos (se reutilizan en la validación de la API)
PLANES = ["prepago", "pospago_basico", "pospago_premium"]
METODOS_PAGO = ["tarjeta_credito", "debito_automatico", "efectivo", "transferencia"]
RENOVACION = ["si", "no"]
RANGOS_EDAD = ["18-25", "26-40", "41-60", "60+"]

# Criterios de éxito acordados en business/ASUM-DM.md
MIN_RECALL = 0.70
MIN_PRECISION = 0.40
MIN_ROC_AUC = 0.75

# Niveles de riesgo (el umbral de decisión se calibra al entrenar)
UMBRAL_DECISION_DEFAULT = 0.50
UMBRAL_RIESGO_ALTO = 0.70

# Parámetros de negocio para la campaña de retención
COSTO_CONTACTO = 8.0          # costo por cliente contactado (USD)
TASA_EXITO_CAMPANA = 0.30     # % de clientes contactados que se retienen
PRESUPUESTO_CAMPANA = 2000.0  # presupuesto mensual (USD)

# Monitoreo de drift (Population Stability Index)
PSI_ALERTA = 0.10
PSI_CRITICO = 0.25

# Equidad (SC-010): brecha máxima de recall entre grupos de edad y tamaño mínimo de grupo
MAX_DIF_RECALL = 0.05
MIN_GRUPO_AUDITORIA = 100

# Respuestas del servicio (FR-002, FR-005)
UMBRAL_RIESGO_MEDIO = 0.50
AVISO_USO_RESPONSABLE = (
    "Apoyo a la decisión: este resultado no es una decisión. "
    "Requiere revisión humana antes de actuar sobre el cliente."
)

# Mínimo de filas para calcular el PSI de un lote (data-model: InformeCambioDatos)
MIN_FILAS_DRIFT = 100

# Tamaños de lote (FR-009, FR-011; D5): puntuar 1.000; contactos sobre la base mensual completa
LOTE_MAX = 1000
CONTACTOS_LOTE_MAX = 5000
MIN_LOTE_RESUMEN = 20  # FR-010: menos clientes no publica resumen

# Límites de presupuesto y costo por contacto (FR-012)
PRESUPUESTO_MIN, PRESUPUESTO_MAX = 0.01, 100_000
COSTO_CONTACTO_MIN, COSTO_CONTACTO_MAX = 0.01, 1000

# Criterios de promoción (constitución I, FR-018; D1) y equidad (SC-010; D3)
TOP_EVALUACION = 0.05        # k = 5 % del conjunto evaluado (equivale a 250 de 5.000)
MIN_PRECISION_TOP = 0.40
MIN_ROI = 3
MIN_RATIO_IMPACTO = 0.80     # regla de los cuatro quintos

# Límite de solicitudes por IP y minuto (FR-020)
LIMITE_SOLICITUDES_POR_MINUTO = 60

# Retención del registro de predicciones en días (FR-023)
RETENCION_REGISTRO_DIAS = 90
