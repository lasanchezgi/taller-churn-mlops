"""Registro de predicciones en JSONL sin identificadores en claro (T045; FR-015, FR-023, SC-005)."""
import hashlib
import json
import logging
import os
from datetime import datetime, timezone

from churn import config

log = logging.getLogger("churn.registro")

SAL_ENV = "CHURN_HASH_SALT"
SAL_DESARROLLO = "sal-solo-desarrollo"  # no usar en producción
LARGO_CODIGO = 16


class Registro:
    """Escribe una línea JSON por predicción; el identificador solo se guarda codificado."""

    def __init__(self, ruta=None, sal: str | None = None):
        self.ruta = ruta or config.PREDICTIONS_LOG
        self.sal = sal or os.environ.get(SAL_ENV)
        if not self.sal:
            log.warning("falta %s: se usa la sal de desarrollo", SAL_ENV)
            self.sal = SAL_DESARROLLO

    def codificar(self, id_cliente: str | None) -> str | None:
        """SHA-256 de sal + identificador, 16 caracteres; None si no hay identificador."""
        if id_cliente is None:
            return None
        digest = hashlib.sha256((self.sal + id_cliente).encode("utf-8")).hexdigest()
        return digest[:LARGO_CODIGO]

    def registrar(self, id_cliente: str | None, probabilidad: float, nivel: str,
                  version_modelo: str, latencia_ms: float) -> dict:
        """Agrega la línea al archivo. No recibe ni guarda los datos del cliente (FR-023)."""
        linea = {
            "fecha": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "id_codificado": self.codificar(id_cliente),
            "probabilidad_churn": probabilidad,
            "nivel_riesgo": nivel,
            "version_modelo": version_modelo,
            "latencia_ms": round(latencia_ms, 3),
        }
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        with open(self.ruta, "a", encoding="utf-8") as f:
            f.write(json.dumps(linea, ensure_ascii=False) + "\n")
        return linea
