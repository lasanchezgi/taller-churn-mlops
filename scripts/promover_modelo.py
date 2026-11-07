"""Asigna el alias «produccion» a la versión «candidato» del registro local (T145; FR-030; D11, D2).

Uso:
    python scripts/promover_modelo.py                              # solo si la ficha dice aprobado
    python scripts/promover_modelo.py --forzar --motivo "texto"    # excepción con motivo obligatorio

El alias solo registra la promoción; la API sigue sirviendo models/churn_model.joblib.
"""
import argparse
from datetime import datetime, timezone

from churn import config, seguimiento


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Promover la versión candidata a producción")
    ap.add_argument("--forzar", action="store_true", help="promover aunque la ficha diga no aprobado")
    ap.add_argument("--motivo", default="", help="obligatorio con --forzar; queda como etiqueta de la versión")
    args = ap.parse_args(argv)
    motivo = args.motivo.strip()
    if args.forzar and not motivo:
        raise SystemExit("--forzar exige --motivo con la razón de la excepción (queda registrada)")

    mlflow = seguimiento.importar_mlflow()
    mlflow.set_tracking_uri(config.MLFLOW_TRACKING_URI)
    client = mlflow.MlflowClient()
    nombre = config.MLFLOW_MODELO_REGISTRADO
    try:
        version = client.get_model_version_by_alias(nombre, config.ALIAS_CANDIDATO)
    except Exception:
        raise SystemExit(f"no hay una versión con alias '{config.ALIAS_CANDIDATO}': entrene con --mlflow") from None

    # La ficha de ESTA versión (no la del disco) es la que manda
    card = mlflow.artifacts.load_dict(f"runs:/{version.run_id}/model_card.json")
    aprobado = bool(card.get("aprobado_para_despliegue"))
    if not aprobado and not args.forzar:
        razones = "; ".join(card.get("razones_no_aprobado", [])) or "sin detalle"
        raise SystemExit(f"la versión {version.version} no está aprobada para despliegue ({razones}). "
                         "No se asignó 'produccion'. Para una excepción use --forzar --motivo")

    for k, v in (("promocion_forzada", str(not aprobado).lower()), ("motivo_forzado", motivo if not aprobado else ""),
                 ("promovido_en", datetime.now(timezone.utc).isoformat(timespec="seconds"))):
        client.set_model_version_tag(nombre, version.version, k, v)
    client.set_registered_model_alias(nombre, config.ALIAS_PRODUCCION, version.version)
    print(f"'{config.ALIAS_PRODUCCION}' -> versión {version.version}"
          f"{' (FORZADO: ' + motivo + ')' if not aprobado else ''}")


if __name__ == "__main__":
    main()
