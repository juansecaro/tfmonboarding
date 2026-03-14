# wifi/connector.py
"""Conexión a redes WiFi mediante nmcli."""

import subprocess
import logging

logger = logging.getLogger(__name__)

TIMEOUT_CONEXION = 20  # segundos — margen sobre los ~8s reales


def conectar(ssid: str, password: str) -> tuple[bool, str]:
    """
    Intenta conectar a una red WiFi.

    Returns:
        (True,  'WIFI_OK:ssid')                  si conecta
        (False, 'WIFI_ERR:red_no_encontrada')     si el SSID no existe
        (False, 'WIFI_ERR:contraseña_incorrecta') si falla autenticación
        (False, 'WIFI_ERR:timeout')               si supera el tiempo límite
        (False, 'WIFI_ERR:nmcli_no_disponible')   si nmcli no existe
        (False, 'WIFI_ERR:desconocido')           cualquier otro error
    """
    if not ssid:
        return False, 'WIFI_ERR:ssid_vacio'

    try:
        resultado = subprocess.run(
            ['nmcli', '-w', str(TIMEOUT_CONEXION),
             'device', 'wifi', 'connect', ssid,
             'password', password],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_CONEXION + 5
        )
        return _interpretar_resultado(ssid, resultado)

    except subprocess.TimeoutExpired:
        logger.error('Timeout subprocess al conectar a %s', ssid)
        return False, 'WIFI_ERR:timeout'
    except FileNotFoundError:
        logger.error('nmcli no encontrado')
        return False, 'WIFI_ERR:nmcli_no_disponible'


def _interpretar_resultado(ssid: str,
                           r: subprocess.CompletedProcess
                           ) -> tuple[bool, str]:
    """Interpreta returncode y stderr de nmcli."""
    # Éxito
    if r.returncode == 0:
        logger.info('Conectado a "%s"', ssid)
        return True, f'WIFI_OK:{ssid}'

    stderr = r.stderr.strip()

    # returncode 10 → SSID no encontrado
    if r.returncode == 10 or 'No network with SSID' in stderr:
        logger.warning('Red no encontrada: "%s"', ssid)
        return False, 'WIFI_ERR:red_no_encontrada'

    # returncode 4 → fallo de autenticación (contraseña incorrecta)
    if r.returncode == 4 or 'Secrets were required' in stderr:
        logger.warning('Contraseña incorrecta para: "%s"', ssid)
        return False, 'WIFI_ERR:contraseña_incorrecta'

    # Timeout de nmcli
    if 'Timeout' in stderr:
        logger.warning('Timeout conectando a: "%s"', ssid)
        return False, 'WIFI_ERR:timeout'

    logger.error('Error desconocido (rc=%d): %s', r.returncode, stderr)
    return False, 'WIFI_ERR:desconocido'


def obtener_estado() -> tuple[bool, str]:
    """
    Devuelve el estado actual de la conexión WiFi.

    Returns:
        (True,  'CONNECTED:ssid')  si hay conexión activa
        (False, 'DISCONNECTED')    si no hay conexión
    """
    try:
        r = subprocess.run(
            ['nmcli', '-t', '-f', 'TYPE,STATE,CONNECTION', 'device', 'status'],
            capture_output=True, text=True, timeout=5
        )
        for linea in r.stdout.splitlines():
            partes = linea.split(':')
            if len(partes) >= 3 and partes[0] == 'wifi' and partes[1] == 'connected':
                return True, f'CONNECTED:{partes[2]}'
        return False, 'DISCONNECTED'

    except Exception as e:
        logger.error('Error obteniendo estado WiFi: %s', e)
        return False, 'DISCONNECTED'


# ── Test independiente ───────────────────────────────────────────
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    print('=== Estado WiFi actual ===')
    conectado, estado = obtener_estado()
    print(f'  {estado}\n')

    print('=== Test red inexistente ===')
    ok, msg = conectar('REDQUENOEXISTE', 'test')
    print(f'  ok={ok}  msg={msg}\n')

    print('=== Test contraseña incorrecta ===')
    ok, msg = conectar('TP-Link_4AB7', 'contraseñafalsa')
    print(f'  ok={ok}  msg={msg}\n')
