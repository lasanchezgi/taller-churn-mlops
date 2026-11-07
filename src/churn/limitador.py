"""Límite de solicitudes por IP en memoria, sin dependencias (T077; FR-020)."""
import math
import time
from collections import deque

VENTANA_S = 60.0


class Limitador:
    """Ventana deslizante de un minuto por origen; el reloj es inyectable para las pruebas."""

    def __init__(self, limite: int, reloj=time.monotonic):
        self.limite = limite
        self.reloj = reloj
        self._eventos: dict[str, deque] = {}
        self._ultima_purga = reloj()

    def permitir(self, ip: str) -> tuple[bool, int]:
        """(True, 0) si la solicitud pasa; (False, segundos_de_espera) si supera el límite."""
        ahora = self.reloj()
        if ahora - self._ultima_purga >= VENTANA_S:
            self._purgar(ahora)
        cola = self._eventos.setdefault(ip, deque())
        while cola and cola[0] <= ahora - VENTANA_S:
            cola.popleft()
        if len(cola) >= self.limite:
            return False, max(1, math.ceil(cola[0] + VENTANA_S - ahora))
        cola.append(ahora)
        return True, 0

    def _purgar(self, ahora: float) -> None:
        """Descarta orígenes inactivos una vez por ventana para que la memoria no crezca sin tope."""
        self._ultima_purga = ahora
        for ip in list(self._eventos):
            cola = self._eventos[ip]
            while cola and cola[0] <= ahora - VENTANA_S:
                cola.popleft()
            if not cola:
                del self._eventos[ip]
