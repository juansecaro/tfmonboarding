# ble/protocol.py
"""
Protocolo de comunicación BLE para onboarding WiFi.

Comandos que acepta (escritura en RX):
    SCAN              → escanea redes y devuelve lista
    CONNECT:ssid|pwd  → intenta conectar a la red
    STATUS            → devuelve estado WiFi actual

Respuestas (notificación en TX):
    NETS:ssid1,85,WPA2|ssid2,72,WPA2|...
    WIFI_OK:ssid
    WIFI_ERR:motivo
    CONNECTED:ssid
    DISCONNECTED
    ERR:comando_desconocido
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import logging
from wifi.scanner import escanear_redes, formatear_para_ble
from wifi.connector import conectar, obtener_estado


logger = logging.getLogger(__name__)


def procesar(comando: str) -> str:
    """
    Procesa un comando recibido por BLE y devuelve la respuesta.

    Args:
        comando: string recibido desde el móvil

    Returns:
        string de respuesta para enviar al móvil
    """
    comando = comando.strip()
    logger.info('Comando recibido: "%s"', comando)

    if comando == 'SCAN':
        return _cmd_scan()

    if comando.startswith('CONNECT:'):
        return _cmd_connect(comando[len('CONNECT:'):])

    if comando == 'STATUS':
        return _cmd_status()

    logger.warning('Comando desconocido: "%s"', comando)
    return 'ERR:comando_desconocido'


def _cmd_scan() -> str:
    """Escanea redes WiFi y devuelve respuesta formateada."""
    logger.info('Iniciando escaneo WiFi...')
    redes = escanear_redes()

    if not redes:
        logger.warning('No se encontraron redes')
        return 'NETS:'

    respuesta = 'NETS:' + formatear_para_ble(redes)
    logger.info('Redes encontradas: %d (%d bytes)',
                len(redes), len(respuesta))
    return respuesta


def _cmd_connect(payload: str) -> str:
    """Parsea credenciales y conecta a la red WiFi."""
    partes = payload.split('|', 1)
    if len(partes) != 2:
        logger.warning('Payload CONNECT malformado: "%s"', payload)
        return 'WIFI_ERR:formato_invalido'

    ssid, password = partes[0], partes[1]

    if not ssid:
        return 'WIFI_ERR:ssid_vacio'
    if not password:
        return 'WIFI_ERR:password_vacio'

    logger.info('Intentando conectar a "%s"', ssid)
    ok, msg = conectar(ssid, password)
    return msg


def _cmd_status() -> str:
    """Devuelve el estado actual de la conexión WiFi."""
    _, msg = obtener_estado()
    return msg


# ── Test independiente ───────────────────────────────────────────
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    print('=== Test protocolo ===\n')

    casos = [
        'SCAN',
        'STATUS',
        'CONNECT:REDQUENOEXISTE|test',
        'CONNECT:TP-Link_4AB7|contraseñafalsa',
        'COMANDOBASURA',
        'CONNECT:sinbarra',
    ]

    for cmd in casos:
        print(f'→ {cmd}')
        resp = procesar(cmd)
        print(f'← {resp}\n')
