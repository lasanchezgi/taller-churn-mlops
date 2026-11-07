"""API de riesgo de churn (T024, T026, T031, T036, T041, T046, T054, T058, T059, T110; FR-001..013, FR-019, FR-022).

Uso: uv run uvicorn churn.api:app --reload  ·  documentación en /docs
"""
import json
import logging
import time
from contextlib import asynccontextmanager
from typing import Literal

import pandas as pd
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from churn import campana, config, drift, predict
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
    alerta_equidad: str | None = None  # solo mientras el modelo no esté aprobado (FR-026)


class Lote(BaseModel):
    """De 1 a LOTE_MAX clientes (FR-009)."""
    model_config = ConfigDict(extra="forbid")
    clientes: list[Cliente] = Field(min_length=1, max_length=config.LOTE_MAX)


class ResumenRiesgo(BaseModel):
    total_clientes: int
    clientes_riesgo_alto: int
    porcentaje_riesgo_alto: float
    ingresos_mensuales_en_riesgo: float
    ingresos_6_meses_en_riesgo: float
    version_modelo: str
    fecha: str


class RespuestaLote(BaseModel):
    predicciones: list[Prediccion]
    resumen: ResumenRiesgo | None
    mensaje_resumen: str | None
    aviso_uso_responsable: str


class SolicitudContactos(BaseModel):
    """Lote de la campaña (hasta CONTACTOS_LOTE_MAX) con presupuesto y costo por contacto (FR-011, FR-012)."""
    model_config = ConfigDict(extra="forbid")
    clientes: list[Cliente] = Field(min_length=1, max_length=config.CONTACTOS_LOTE_MAX)
    presupuesto: float = Field(default=config.PRESUPUESTO_CAMPANA, ge=config.PRESUPUESTO_MIN,
                               le=config.PRESUPUESTO_MAX, strict=True, allow_inf_nan=False)
    costo_por_contacto: float = Field(default=config.COSTO_CONTACTO, ge=config.COSTO_CONTACTO_MIN,
                                      le=config.COSTO_CONTACTO_MAX, strict=True, allow_inf_nan=False)


class Contacto(BaseModel):
    posicion_en_lote: int
    probabilidad_churn: float
    nivel_riesgo: Literal["alto", "medio", "bajo"]
    recomendacion: str
    ingreso_esperado: float
    id_cliente: str | None = None  # solo si el analista lo envió; nunca va al registro ni a la vista


class ListaContacto(BaseModel):
    presupuesto: float
    costo_por_contacto: float
    max_contactos: int
    clientes_en_riesgo_alto: int
    contactos: list[Contacto]
    costo_total: float
    mensaje: str | None = None
    aviso_uso_responsable: str


class EstadoServicio(BaseModel):
    """Salida de GET /health (FR-013)."""
    estado: Literal["sano", "no_sano"]
    modelo_cargado: bool
    version_modelo: str | None
    aprobado_para_despliegue: bool | None
    alertas: list[str] = Field(default_factory=list)  # razones de no aprobación (FR-028)
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
    if tipo == "too_long":
        return f"máximo {ctx.get('max_length')} clientes por solicitud"
    if tipo == "too_short":
        return f"debe incluir al menos {ctx.get('min_length')} cliente"
    if tipo == "string_pattern_mismatch":
        return "solo letras, números, guion y guion bajo"
    if tipo == "string_type":
        return "tipo incorrecto; se espera texto"
    return "valor no válido"


def _detalle(err: dict) -> dict:
    """Campo y mensaje; en lotes agrega la posición (base 1) del cliente inválido (FR-009)."""
    loc = list(err["loc"][1:])
    d = {}
    if len(loc) >= 2 and loc[0] == "clientes" and isinstance(loc[1], int):
        d["posicion_cliente"] = loc[1] + 1
        loc = loc[2:]
    return {"campo": ".".join(str(p) for p in loc) or "cuerpo", **d, "mensaje": _mensaje(err)}


@app.exception_handler(RequestValidationError)
async def entrada_invalida(request: Request, exc: RequestValidationError):
    request.app.state.metricas.registrar_error()
    detalle = [_detalle(e) for e in exc.errors()]
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


def _alerta(card: dict) -> dict:
    """{"alerta_equidad": texto} si el modelo no está aprobado; vacío si lo está."""
    a = predict.alerta_equidad(card)
    return {"alerta_equidad": a} if a else {}


@app.post("/predict", response_model=Prediccion, response_model_exclude_unset=True)
def predecir(cliente: Cliente) -> Prediccion:
    """Probabilidad de churn en los 60 días siguientes al corte, con nivel y recomendación."""
    inicio = time.perf_counter()
    res = predict.puntuar(app.state.modelo, cliente.model_dump())
    app.state.metricas.registrar_prediccion(
        res["probabilidad_churn"], res["nivel_riesgo"], cliente.cargo_mensual,
        (time.perf_counter() - inicio) * 1000)
    return Prediccion(**res, aviso_uso_responsable=config.AVISO_USO_RESPONSABLE,
                      **_alerta(app.state.modelo["card"]))


@app.post("/predict/lote", response_model=RespuestaLote, response_model_exclude_unset=True)
def predecir_lote(request: Request, lote: Lote) -> dict:
    """Una predicción por cliente, en el mismo orden, más el resumen de riesgo (FR-009, FR-010)."""
    inicio = time.perf_counter()
    clientes = [c.model_dump() for c in lote.clientes]
    preds = predict.puntuar_lote(request.app.state.modelo, clientes)
    ms = (time.perf_counter() - inicio) * 1000 / len(clientes)
    for p, c in zip(preds, clientes):
        request.app.state.metricas.registrar_prediccion(
            p["probabilidad_churn"], p["nivel_riesgo"], c["cargo_mensual"], ms)
    cargos = [c["cargo_mensual"] for c in clientes]
    resumen = campana.resumir_lote(preds, cargos, preds[0]["version_modelo"])
    if resumen:
        campana.guardar_ultimo_lote(resumen)
    return {
        "predicciones": [{**p, "aviso_uso_responsable": config.AVISO_USO_RESPONSABLE,
                          **_alerta(request.app.state.modelo["card"])} for p in preds],
        "resumen": resumen,
        "mensaje_resumen": None if resumen else
        f"Lote demasiado pequeño para resumir (mínimo {config.MIN_LOTE_RESUMEN} clientes)",
        "aviso_uso_responsable": config.AVISO_USO_RESPONSABLE,
    }


@app.post("/campana/contactos", response_model=ListaContacto, response_model_exclude_none=True)
def elegir_contactos(request: Request, solicitud: SolicitudContactos) -> dict:
    """Lista de contacto sobre el lote puntuado: riesgo alto por ingreso esperado (FR-011, FR-012; D5)."""
    clientes = [c.model_dump() for c in solicitud.clientes]
    preds = predict.puntuar_lote(request.app.state.modelo, clientes)
    lista = campana.seleccionar_contactos(
        preds, [c["cargo_mensual"] for c in clientes], [c["id_cliente"] for c in clientes],
        solicitud.presupuesto, solicitud.costo_por_contacto)
    return {**lista, "aviso_uso_responsable": config.AVISO_USO_RESPONSABLE}


def _leer_json(ruta) -> dict | None:
    return json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else None


def _informe_publico(informe: dict | None) -> dict | None:
    """Informe de cambio de datos sin el detalle de la simulación."""
    return None if informe is None else {k: v for k, v in informe.items() if k != "simulacion"}


@app.post("/drift")
def cambio_de_datos(request: Request, lote: Lote) -> dict:
    """Compara el lote con la referencia de entrenamiento y guarda el informe (FR-014)."""
    modelo = request.app.state.modelo
    if modelo is None:
        raise predict.ModeloNoDisponible("modelo no cargado")
    df = pd.DataFrame([c.model_dump() for c in lote.clientes])[config.FEATURES]
    informe = drift.informe(df, modelo["card"]["perfil_referencia"])
    config.DRIFT_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    config.DRIFT_REPORT_PATH.write_text(json.dumps(informe, indent=2, ensure_ascii=False))
    return informe


@app.get("/drift")
def ultimo_cambio_de_datos():
    """Último informe de cambio de datos guardado (FR-014)."""
    informe = _informe_publico(_leer_json(config.DRIFT_REPORT_PATH))
    if informe is None:
        return JSONResponse(status_code=404, content={"error": "Aún no hay un informe de cambio de datos"})
    return informe


@app.get("/health", response_model=EstadoServicio)
def salud(request: Request):
    """Sano solo si el modelo está cargado; sin modelo responde 503 con el mismo esquema."""
    modelo = request.app.state.modelo
    if modelo is None:
        estado = EstadoServicio(estado="no_sano", modelo_cargado=False, version_modelo=None,
                                aprobado_para_despliegue=None, alertas=[], error="Modelo no disponible")
        return JSONResponse(status_code=503, content=estado.model_dump())
    card = modelo["card"]
    return EstadoServicio(estado="sano", modelo_cargado=True, version_modelo=card["version"],
                          aprobado_para_despliegue=card.get("aprobado_para_despliegue"),
                          alertas=predict.razones_no_aprobado(card), error=None)


@app.get("/metrics")
def metricas(request: Request) -> dict:
    """Contadores, latencia, datos del modelo y métricas de negocio; sin identificadores."""
    modelo = request.app.state.modelo
    return {
        **request.app.state.metricas.resumen(modelo["card"] if modelo else None),
        "ultimo_resumen": _leer_json(config.ULTIMO_LOTE_PATH),
        "ultimo_cambio_datos": _informe_publico(_leer_json(config.DRIFT_REPORT_PATH)),
    }


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard() -> str:
    """Vista de solo lectura (FR-019): HTML estático que consulta /health y /metrics."""
    return config.DASHBOARD_PATH.read_text(encoding="utf-8")
