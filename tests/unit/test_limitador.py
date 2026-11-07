"""Pruebas de churn.limitador (T069, T077; FR-020)."""
from churn.limitador import Limitador, VENTANA_S


class Reloj:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def test_la_solicitud_siguiente_al_limite_se_rechaza():
    lim = Limitador(60, Reloj())
    assert all(lim.permitir("1.1.1.1")[0] for _ in range(60))
    permitido, espera = lim.permitir("1.1.1.1")
    assert not permitido and 1 <= espera <= 60


def test_otra_ip_no_se_ve_afectada():
    lim = Limitador(2, Reloj())
    lim.permitir("a"), lim.permitir("a")
    assert not lim.permitir("a")[0]
    assert lim.permitir("b")[0]


def test_el_contador_se_reinicia_al_pasar_el_minuto():
    reloj = Reloj()
    lim = Limitador(2, reloj)
    lim.permitir("a"), lim.permitir("a")
    assert not lim.permitir("a")[0]
    reloj.t += VENTANA_S
    assert lim.permitir("a")[0]


def test_ips_inactivas_se_purgan_de_la_memoria():
    reloj = Reloj()
    lim = Limitador(5, reloj)
    for i in range(100):
        lim.permitir(f"ip{i}")
    reloj.t += VENTANA_S + 1
    lim.permitir("nueva")
    assert list(lim._eventos) == ["nueva"]
