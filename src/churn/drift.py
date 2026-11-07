"""Cambio de datos (PSI) y simulación de crisis (T051, T055, T108; FR-014, SC-009).

Uso: python -m churn.drift [--escenario base|crisis]
"""
import argparse
import json
from datetime import datetime, timezone

import numpy as np

from churn import config
from churn.dataset import aplicar_crisis
from churn.evaluate import metricas_negocio, metricas_tecnicas
from churn.features import cargar_datos, particionar
from churn.predict import cargar_modelo

EPS = 1e-4  # evita log(0) con intervalos o categorías vacías
NIVELES = ("estable", "alerta", "critico")


def psi(esperado, observado) -> float:
    """PSI = Σ (p_nuevo − p_ref) · ln(p_nuevo / p_ref) sobre proporciones alineadas."""
    e = np.clip(np.asarray(esperado, dtype=float), EPS, None)
    o = np.clip(np.asarray(observado, dtype=float), EPS, None)
    return float(np.sum((o - e) * np.log(o / e)))


def clasificar(valor: float) -> str:
    if valor >= config.PSI_CRITICO:
        return "critico"
    return "alerta" if valor >= config.PSI_ALERTA else "estable"


def _psi_variable(serie, ref: dict) -> float:
    if ref["tipo"] == "numerica":
        cuentas, _ = np.histogram(serie, bins=[-np.inf, *ref["limites"], np.inf])
        return psi(ref["frecuencias"], cuentas / len(serie))
    esperado = ref["frecuencias"]
    nuevo = serie.value_counts(normalize=True).to_dict()
    cats = sorted(set(esperado) | set(nuevo))  # una categoría nueva también cuenta
    return psi([esperado.get(c, 0.0) for c in cats], [nuevo.get(c, 0.0) for c in cats])


def informe(df, perfil_referencia: dict) -> dict:
    """PSI por variable de entrada frente al perfil de referencia del model card."""
    fecha = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if len(df) < config.MIN_FILAS_DRIFT:
        return {"variables": [], "estado_general": "datos_insuficientes",
                "recomendacion": f"el lote tiene menos de {config.MIN_FILAS_DRIFT} filas",
                "fecha": fecha}
    variables = []
    for col in config.FEATURES:
        valor = _psi_variable(df[col], perfil_referencia[col])
        variables.append({"nombre": col, "psi": round(valor, 4), "nivel": clasificar(valor)})
    peor = max((v["nivel"] for v in variables), key=NIVELES.index)
    return {"variables": variables, "estado_general": peor, "fecha": fecha,
            "recomendacion": "evaluar reentrenamiento" if peor == "critico" else "sin acción"}


def _evaluar(modelo: dict, df) -> dict:
    """Métricas técnicas y de negocio del modelo servido sobre un conjunto etiquetado."""
    umbral = modelo["card"]["umbral"]
    proba = modelo["pipeline"].predict_proba(df[config.FEATURES])[:, 1]
    return {"tecnicas": metricas_tecnicas(df[config.TARGET], proba, umbral),
            "negocio": metricas_negocio(proba, df["cargo_mensual"], umbral)}


def simular(escenario: str = "crisis", ruta_salida=None, df=None, modelo=None) -> dict:
    """Compara el escenario con el base y guarda reports/metrics/drift.json (T108, D6).

    Referencia: perfil del split de entrenamiento del CSV (en el model card). Base: split de
    prueba del mismo CSV. Crisis: aplicar_crisis sobre ese split (solo cambian cargos y reclamos;
    las etiquetas no cambian, así que las métricas miden el efecto sobre el modelo, no un nuevo churn).
    """
    modelo = modelo or cargar_modelo()
    df = cargar_datos(config.DATA_RAW) if df is None else df
    _, base = particionar(df)
    otro = aplicar_crisis(base) if escenario == "crisis" else base
    ref = modelo["card"]["perfil_referencia"]
    eb, eo = _evaluar(modelo, base), _evaluar(modelo, otro)

    delta = {
        "recall": eo["tecnicas"]["recall"] - eb["tecnicas"]["recall"],
        "precision": eo["tecnicas"]["precision"] - eb["tecnicas"]["precision"],
        "roc_auc": eo["tecnicas"]["roc_auc"] - eb["tecnicas"]["roc_auc"],
        "clientes_en_riesgo": eo["negocio"]["clientes_en_riesgo"] - eb["negocio"]["clientes_en_riesgo"],
        "ingresos_6_meses_en_riesgo": (eo["negocio"]["ingresos_6_meses_en_riesgo"]
                                       - eb["negocio"]["ingresos_6_meses_en_riesgo"]),
    }
    reporte = informe(otro, ref)
    sim = {"escenario": escenario, "version_modelo": modelo["card"]["version"], "filas": len(otro),
           "base": {"informe": informe(base, ref), **eb}, "delta": delta,
           "alerta_recall": eo["tecnicas"]["recall"] < config.MIN_RECALL}
    if escenario != "base":
        sim[escenario] = eo
    reporte["simulacion"] = sim
    ruta = ruta_salida or config.DRIFT_REPORT_PATH
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(reporte, indent=2, ensure_ascii=False))
    return reporte


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="PSI por variable y simulación de escenario")
    ap.add_argument("--escenario", choices=("base", "crisis"), default="crisis")
    args = ap.parse_args(argv)
    r = simular(args.escenario)
    s = r["simulacion"]
    print(f"escenario {args.escenario} · estado general: {r['estado_general']} · {r['recomendacion']}")
    for v in r["variables"]:
        print(f"  {v['nombre']:<18} PSI {v['psi']:.3f}  {v['nivel']}")
    b, o = s["base"], s.get(args.escenario, s["base"])
    for k in ("recall", "precision", "roc_auc"):
        print(f"  {k:<10} base {b['tecnicas'][k]:.3f} → {args.escenario} {o['tecnicas'][k]:.3f}")
    print(f"  ingresos 6 meses en riesgo: {b['negocio']['ingresos_6_meses_en_riesgo']:.0f} → "
          f"{o['negocio']['ingresos_6_meses_en_riesgo']:.0f} USD")
    print(f"guardado en {config.DRIFT_REPORT_PATH}")


if __name__ == "__main__":
    main()
