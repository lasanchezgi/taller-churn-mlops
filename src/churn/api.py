"""API de riesgo de churn (T024, T026, T046, T058; FR-001..008, FR-013, FR-022).

Uso: uv run uvicorn churn.api:app --reload  ·  documentación en /docs
"""
import logging
import time
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from churn import config, predict
from churn.metricas import Metricas

log = logging.getLogger("churn.api")


class Cliente(BaseModel):
    """Entrada de un cliente; rechaza campos no previstos (incluida la edad)."""
    model_config = ConfigDict(extra="forbid")

    antiguedad_meses: int = Field(ge=1, le=120, strict=True)
    tipo_plan: Literal[*config.PLANES]
    cargo_mensual: float = Field(ge=10, le=1000, strict=True, allow_inf_nan=False)
    reclamos_ult_3m: int = Field(ge=0, le=6, strict=True)
    uso_datos_gb: float = Field(ge=0, le=1000, strict=True, allow_inf_nan=False)
    metodo_pago: Literal[*config.METODOS_PAGO]
    renovo_contrato: Literal[*config.RENOVACION]
    # Solo trazabilidad: no entra al modelo y no se devuelve (FR-011)
    id_cliente: str | None = Field(default=None, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")


class Prediccion(BaseModel):
    probabilidad_churn: float = Field(ge=0, le=1)
    nivel_riesgo: Literal["alto", "medio", "bajo"]
    recomendacion: str
    version_modelo: str
    aviso_uso_responsable: str


class EstadoServicio(BaseModel):
    """Salida de GET /health (FR-013)."""
    estado: Literal["sano", "no_sano"]
    modelo_cargado: bool
    version_modelo: str | None
    aprobado_para_despliegue: bool | None
    error: str | None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Carga el modelo al iniciar; si falla, el servicio arranca pero responde 503."""
    app.state.metricas = Metricas()
    try:
        app.state.modelo = predict.cargar_modelo()
    except predict.ModeloNoDisponible as e:
        log.warning("modelo no disponible: %s", e)
        app.state.modelo = None
    yield


app = FastAPI(title="Riesgo de churn", version=config.MODEL_VERSION, lifespan=lifespan)

# Mensajes en español por tipo de error; nunca repiten el valor recibido (FR-022)
def _mensaje(err: dict) -> str:
    tipo, ctx = err["type"], err.get("ctx", {})
    if tipo == "missing":
        return "campo obligatorio"
    if tipo == "extra_forbidden":
        return "campo no previsto"
    if tipo == "literal_error":
        return f"valor no permitido; use {ctx.get('expected')}"
    if tipo == "greater_than_equal":
        return f"debe ser mayor o igual que {ctx.get('ge')}"
    if tipo == "less_than_equal":
        return f"debe ser menor o igual que {ctx.get('le')}"
    if tipo in ("int_type", "float_type", "int_from_float", "int_parsing", "float_parsing"):
        return "tipo incorrecto; se espera un número" + (" entero" if "int" in tipo else "")
    if tipo == "string_too_long":
        return f"máximo {ctx.get('max_length')} caracteres"
    if tipo == "string_pattern_mismatch":
        return "solo letras, números, guion y guion bajo"
    if tipo == "string_type":
        return "tipo incorrecto; se espera texto"
    return "valor no válido"


@app.exception_handler(RequestValidationError)
async def entrada_invalida(request: Request, exc: RequestValidationError):
    request.app.state.metricas.registrar_error()
    detalle = [
        {"campo": ".".join(str(p) for p in e["loc"][1:]) or "cuerpo", "mensaje": _mensaje(e)}
        for e in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"error": "Entrada inválida", "detalle": detalle})


@app.exception_handler(predict.ModeloNoDisponible)
async def sin_modelo(request: Request, exc: predict.ModeloNoDisponible):
    request.app.state.metricas.registrar_error()
    return JSONResponse(status_code=503, content={"error": "Modelo no disponible"})


@app.exception_handler(Exception)
async def error_interno(request: Request, exc: Exception):
    # El detalle va al log del servidor; el cliente no ve trazas ni rutas (FR-022)
    log.error("error interno", exc_info=exc)
    request.app.state.metricas.registrar_error()
    return JSONResponse(status_code=500, content={"error": "Error interno"})


@app.post("/predict", response_model=Prediccion)
def predecir(cliente: Cliente) -> Prediccion:
    """Probabilidad de churn en los 60 días siguientes al corte, con nivel y recomendación."""
    inicio = time.perf_counter()
    res = predict.puntuar(app.state.modelo, cliente.model_dump())
    app.state.metricas.registrar_prediccion(
        res["probabilidad_churn"], res["nivel_riesgo"], cliente.cargo_mensual,
        (time.perf_counter() - inicio) * 1000)
    return Prediccion(**res, aviso_uso_responsable=config.AVISO_USO_RESPONSABLE)


@app.get("/health", response_model=EstadoServicio)
def salud(request: Request):
    """Sano solo si el modelo está cargado; sin modelo responde 503 con el mismo esquema."""
    modelo = request.app.state.modelo
    if modelo is None:
        estado = EstadoServicio(estado="no_sano", modelo_cargado=False, version_modelo=None,
                                aprobado_para_despliegue=None, error="Modelo no disponible")
        return JSONResponse(status_code=503, content=estado.model_dump())
    card = modelo["card"]
    return EstadoServicio(estado="sano", modelo_cargado=True, version_modelo=card["version"],
                          aprobado_para_despliegue=card.get("aprobado_para_despliegue"), error=None)


@app.get("/metrics")
def metricas(request: Request) -> dict:
    """Contadores, latencia, datos del modelo y métricas de negocio; sin identificadores."""
    modelo = request.app.state.modelo
    return request.app.state.metricas.resumen(modelo["card"] if modelo else None)
