"""Ejecución programada del pipeline (F22, F80).

Lee la frecuencia de `configuracion.pipeline.intervalo_minutos` en cada ciclo, de modo que
se puede cambiar desde Administración sin reiniciar el contenedor. Un fallo no detiene el ciclo.
"""
from __future__ import annotations

import logging
import signal
import time
from datetime import datetime, timedelta

from edualerta import datagen
from edualerta.db import sql
from edualerta.etl import pipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s scheduler: %(message)s")
log = logging.getLogger("scheduler")
_stop = False


def _handle(signum, frame):
    global _stop
    _stop = True


def interval_minutes() -> int:
    with sql.session() as conn:
        sql.init_schema(conn)
        return max(1, int(sql.get_rules(conn)["pipeline"]["intervalo_minutos"]))


def _heartbeat(next_run: datetime) -> None:
    with sql.session() as conn:
        sql.set_rule(conn, "estado.scheduler_proxima_ejecucion", next_run.isoformat(timespec="seconds"), "scheduler")


def main() -> None:
    signal.signal(signal.SIGTERM, _handle)
    signal.signal(signal.SIGINT, _handle)
    # La carga base (data/raw) no está en un volumen compartido: cada contenedor genera la suya. El generador es
    # determinista, así que las huellas coinciden con las de la app y lo ya procesado se omite sin duplicar.
    if datagen.ensure_generated():
        log.info("Carga base sintética generada en este contenedor.")
    last_run = datetime.now()
    announced = None
    log.info("Scheduler iniciado (intervalo %s min).", interval_minutes())
    while not _stop:
        try:
            next_run = last_run + timedelta(minutes=interval_minutes())  # releído en cada ciclo
            if next_run != announced:
                _heartbeat(next_run)
                log.info("Próxima ejecución: %s", next_run.isoformat(timespec="seconds"))
                announced = next_run
            if datetime.now() >= next_run:
                out = pipeline.run(trigger="programado", usuario="scheduler")
                log.info("Ejecución programada: %s (aceptados=%s, rechazados=%s)", out.get("estado"),
                         out.get("aceptados"), out.get("rechazados"))
                last_run = datetime.now()
        except Exception:  # noqa: BLE001 - el ciclo nunca debe morir
            log.exception("Fallo en el ciclo del scheduler")
            last_run = datetime.now()
        time.sleep(10)
    log.info("Scheduler detenido.")


if __name__ == "__main__":
    main()
