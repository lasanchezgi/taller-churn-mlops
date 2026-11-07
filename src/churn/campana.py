"""Resumen de riesgo de un lote y selección de contactos (T034, T039, T084; FR-010..012; D5)."""
import json
from datetime import datetime, timezone
from decimal import Decimal

from churn import config


def max_contactos(presupuesto: float, costo: float) -> int:
    """Entero de presupuesto / costo, con decimales exactos (0,3 / 0,1 = 3)."""
    if presupuesto <= 0 or costo <= 0:
        raise ValueError("presupuesto y costo por contacto deben ser mayores que 0")
    return int(Decimal(str(presupuesto)) // Decimal(str(costo)))


def resumir_lote(predicciones: list[dict], cargos: list[float], version: str) -> dict | None:
    """Clientes e ingresos en riesgo alto; None si el lote es menor que MIN_LOTE_RESUMEN."""
    total = len(predicciones)
    if total < config.MIN_LOTE_RESUMEN:
        return None
    ingresos = sum(c for p, c in zip(predicciones, cargos) if p["nivel_riesgo"] == "alto")
    altos = sum(p["nivel_riesgo"] == "alto" for p in predicciones)
    return {
        "total_clientes": total,
        "clientes_riesgo_alto": altos,
        "porcentaje_riesgo_alto": 100 * altos / total,
        "ingresos_mensuales_en_riesgo": float(ingresos),
        "ingresos_6_meses_en_riesgo": float(ingresos) * 6,  # valor del cliente retenido = cargo × 6
        "version_modelo": version,
        "fecha": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def guardar_ultimo_lote(resumen: dict, ruta=None) -> None:
    """Persiste solo agregados (sin identificadores ni datos por cliente) para /metrics y la vista."""
    ruta = ruta or config.ULTIMO_LOTE_PATH
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(resumen, indent=2, ensure_ascii=False))


def seleccionar_contactos(predicciones: list[dict], cargos: list[float], ids: list | None = None,
                          presupuesto: float = config.PRESUPUESTO_CAMPANA,
                          costo: float = config.COSTO_CONTACTO) -> dict:
    """Riesgo alto ordenado por ingreso esperado (prob × cargo); toma min(máximo, en riesgo)."""
    maximo = max_contactos(presupuesto, costo)
    ids = ids or [None] * len(predicciones)
    en_riesgo = [
        (i, p["probabilidad_churn"] * cargos[i]) for i, p in enumerate(predicciones)
        if p["nivel_riesgo"] == "alto"
    ]
    en_riesgo.sort(key=lambda x: -x[1])  # sort estable: empate respeta el orden de entrada
    elegidos = en_riesgo[:maximo]

    contactos = []
    for i, ingreso in elegidos:
        p = predicciones[i]
        c = {"posicion_en_lote": i + 1, "probabilidad_churn": p["probabilidad_churn"],
             "nivel_riesgo": p["nivel_riesgo"], "recomendacion": p["recomendacion"],
             "ingreso_esperado": ingreso}
        if ids[i] is not None:
            c["id_cliente"] = ids[i]
        contactos.append(c)

    res = {"presupuesto": presupuesto, "costo_por_contacto": costo, "max_contactos": maximo,
           "clientes_en_riesgo_alto": len(en_riesgo), "contactos": contactos,
           "costo_total": len(contactos) * costo}
    if maximo == 0:
        res["mensaje"] = "El presupuesto no alcanza para un contacto"
    elif not en_riesgo:
        res["mensaje"] = "El lote no tiene clientes en riesgo alto"
    return res
