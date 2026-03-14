# ble_server.py
"""Punto de entrada del servicio BLE de onboarding WiFi."""

import logging
from ble.gatt_server import construir_servidor, publicar

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    logger.info('=== TFM BLE Onboarding Service ===')
    try:
        ble_app = construir_servidor()
        publicar(ble_app)
    except KeyboardInterrupt:
        logger.info('Servicio detenido por el usuario')
    except Exception as e:
        logger.exception('Error fatal: %s', e)
        raise


if __name__ == '__main__':
    main()
