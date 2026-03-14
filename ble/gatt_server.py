# ble/gatt_server.py
"""
Servidor GATT BLE para onboarding WiFi.

Expone un servicio con dos características:
  - RX: el móvil escribe comandos aquí
  - TX: la RPi envía respuestas aquí (notify)
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import threading
import time
import logging
import dbus
import dbus.mainloop.glib
from gi.repository import GLib
from bluezero import peripheral, adapter

from ble.agent import registrar
from ble.protocol import procesar

logger = logging.getLogger(__name__)

SERVICE_UUID = '12345678-1234-5678-1234-56789abcdef0'
RX_CHAR_UUID = '12345678-1234-5678-1234-56789abcdef1'
TX_CHAR_UUID = '12345678-1234-5678-1234-56789abcdef2'
DEVICE_NAME  = 'TFM-Onboarding'

_tx_characteristic = None


def _enviar_respuesta(respuesta: str) -> None:
    global _tx_characteristic
    if _tx_characteristic is None:
        logger.warning('No hay suscriptor TX activo, respuesta descartada')
        return
    try:
        valor = list(respuesta.encode('utf-8'))
        _tx_characteristic.set_value(valor)
        logger.info('TX enviado: "%s"', respuesta)
    except Exception as e:
        logger.error('Error enviando TX: %s', e)


def _rx_write_callback(value, options) -> None:
    try:
        comando = bytes(value).decode('utf-8')
    except Exception:
        comando = ''.join(chr(b) for b in value)
    logger.info('RX recibido: "%s"', comando)

    def procesar_y_responder():
        respuesta = procesar(comando)
        _enviar_respuesta(respuesta)

    threading.Thread(target=procesar_y_responder, daemon=True).start()


def _tx_notify_callback(notifying, characteristic) -> None:
    global _tx_characteristic
    if notifying:
        _tx_characteristic = characteristic
        logger.info('Móvil suscrito a TX ✓')
    else:
        _tx_characteristic = None
        logger.info('Móvil canceló suscripción TX')


def _tx_read_callback() -> list:
    return list('listo'.encode('utf-8'))


def construir_servidor() -> peripheral.Peripheral:
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    time.sleep(2)

    dongle = adapter.Adapter()
    dongle.pairable = False
    logger.info('Adaptador: %s', dongle.address)

    ble_app = peripheral.Peripheral(
        dongle.address,
        local_name=DEVICE_NAME,
        appearance=0x0000
    )

    ble_app.add_service(srv_id=1, uuid=SERVICE_UUID, primary=True)

    ble_app.add_characteristic(
        srv_id=1, chr_id=1, uuid=RX_CHAR_UUID,
        value=[], notifying=False,
        flags=['write', 'write-without-response'],
        write_callback=_rx_write_callback,
        read_callback=None,
        notify_callback=None
    )

    ble_app.add_characteristic(
        srv_id=1, chr_id=2, uuid=TX_CHAR_UUID,
        value=list('listo'.encode('utf-8')),
        notifying=False,
        flags=['read', 'notify'],
        write_callback=None,
        read_callback=_tx_read_callback,
        notify_callback=_tx_notify_callback
    )

    logger.info('Servidor GATT construido ✓')

    bus = dbus.SystemBus()
    registrar(bus)

    return ble_app


def publicar(ble_app: peripheral.Peripheral) -> None:
    logger.info('Añadiendo objetos al app...')
    for service in ble_app.services:
        ble_app.app.add_managed_object(service)
    for chars in ble_app.characteristics:
        ble_app.app.add_managed_object(chars)
    for desc in ble_app.descriptors:
        ble_app.app.add_managed_object(desc)
    logger.info('Objetos añadidos ✓')

    ble_app._create_advertisement()
    logger.info('Advertisement creado ✓')

    if not ble_app.dongle.powered:
        ble_app.dongle.powered = True

    logger.info('Registrando aplicación GATT...')
    ble_app.srv_mng.register_application(ble_app.app, {})
    logger.info('Aplicación GATT registrada ✓')

    time.sleep(1)

    logger.info('Registrando advertisement...')
    ble_app.ad_manager.register_advertisement(ble_app.advert, {})
    logger.info('Advertisement registrado ✓')

    logger.info('Iniciando bucle de eventos...')
    mainloop = GLib.MainLoop()
    try:
        mainloop.run()
    except KeyboardInterrupt:
        ble_app.ad_manager.unregister_advertisement(ble_app.advert)
        mainloop.quit()
