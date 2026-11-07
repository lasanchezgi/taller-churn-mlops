"""Registro de predicciones en JSONL sin identificadores en claro (T045, T081; FR-015, FR-023, SC-005)."""
import hashlib
import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone

from churn import config

log = logging.getLogger("churn.registro")

SAL_ENV = "CHURN_HASH_SALT"
SAL_DESARROLLO = "sal-solo-desarrollo"  # no usar en producción
LARGO_CODIGO = 16
INTERVALO_PURGA_S = 3600


class Registro:
    """Escribe una línea JSON por predicción; el identificador solo se guarda codificado."""

    def __init__(self, ruta=None, sal: str | None = None):
        self.ruta = ruta or config.PREDICTIONS_LOG
        self.sal = sal or os.environ.get(SAL_ENV)
        if not self.sal:
            log.warning("falta %s: se usa la sal de desarrollo", SAL_ENV)
            self.sal = SAL_DESARROLLO
        self._ultima_purga = time.monotonic()
        self.purgar()

    def codificar(self, id_cliente: str | None) -> str | None:
        """SHA-256 de sal + identificador, 16 caracteres; None si no hay identificador."""
        if id_cliente is None:
            return None
        digest = hashlib.sha256((self.sal + id_cliente).encode("utf-8")).hexdigest()
        return digest[:LARGO_CODIGO]

    def registrar(self, id_cliente: str | None, probabilidad: float, nivel: str,
                  version_modelo: str) -> dict:
        """Agrega la línea al archivo. No recibe ni guarda los datos del cliente (FR-023)."""
        if time.monotonic() - self._ultima_purga >= INTERVALO_PURGA_S:
            self.purgar()
        linea = {
            "fecha": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "id_codificado": self.codificar(id_cliente),
            "probabilidad_churn": probabilidad,
            "nivel_riesgo": nivel,
            "version_modelo": version_modelo,
        }
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        with open(self.ruta, "a", encoding="utf-8") as f:
            f.write(json.dumps(linea, ensure_ascii=False) + "\n")
        return linea

    def purgar(self) -> None:
        """Elimina las líneas más antiguas que `RETENCION_REGISTRO_DIAS`; conserva las ilegibles (FR-023)."""
        self._ultima_purga = time.monotonic()
        if not self.ruta.exists():
            return
        limite = datetime.now(timezone.utc) - timedelta(days=config.RETENCION_REGISTRO_DIAS)
        vigentes = []
        for texto in self.ruta.read_text(encoding="utf-8").splitlines():
            try:
                vencida = datetime.fromisoformat(json.loads(texto)["fecha"]) < limite
            except (ValueError, KeyError, TypeError):
                vencida = False
            if not vencida:
                vigentes.append(texto)
        tmp = self.ruta.with_suffix(".tmp")
        tmp.write_text("".join(t + "\n" for t in vigentes), encoding="utf-8")
        tmp.replace(self.ruta)
