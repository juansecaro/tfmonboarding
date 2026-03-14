# wifi/scanner.py
"""Escaneo de redes WiFi mediante nmcli."""

import subprocess
import logging

logger = logging.getLogger(__name__)

MAX_REDES = 10
SEÑAL_MINIMA = 20  # dBm relativo (0-100), descartar redes muy débiles


def escanear_redes() -> list[dict]:
    """
    Escanea redes WiFi disponibles usando nmcli.

    Returns:
        Lista de dicts ordenada por señal descendente:
        [{'ssid': str, 'signal': int, 'security': str}, ...]
    """
    try:
        resultado = subprocess.run(
            ['nmcli', '-t', '-f', 'SSID,SIGNAL,SECURITY',
             'device', 'wifi', 'list'],
            capture_output=True,
            text=True,
            timeout=15
        )

        if resultado.returncode != 0:
            logger.error('nmcli error: %s', resultado.stderr)
            return []

        return _parsear_salida(resultado.stdout)

    except subprocess.TimeoutExpired:
        logger.error('nmcli timeout al escanear')
        return []
    except FileNotFoundError:
        logger.error('nmcli no encontrado')
        return []


def _parsear_salida(salida: str) -> list[dict]:
    """Parsea la salida de nmcli y devuelve lista de redes filtrada."""
    redes = {}  # ssid -> dict, para deduplicar quedándonos con la mejor señal

    for linea in salida.strip().splitlines():
        partes = linea.split(':')
        if len(partes) < 3:
            continue

        ssid = partes[0].strip()
        if not ssid:
            continue  # ignorar redes sin nombre

        try:
            signal = int(partes[1])
        except ValueError:
            continue

        # partes[2:] porque security puede contener espacios o ':'
        security = ':'.join(partes[2:]).strip() or 'OPEN'

        if signal < SEÑAL_MINIMA:
            continue

        # Deduplicar: quedarse con la entrada de mayor señal
        if ssid not in redes or signal > redes[ssid]['signal']:
            redes[ssid] = {
                'ssid': ssid,
                'signal': signal,
                'security': security
            }

    # Ordenar por señal descendente y limitar
    ordenadas = sorted(redes.values(),
                       key=lambda r: r['signal'],
                       reverse=True)
    return ordenadas[:MAX_REDES]


def formatear_para_ble(redes: list[dict]) -> str:
    """
    Serializa la lista de redes en formato compacto para enviar por BLE.

    Formato: "SSID1,85,WPA2|SSID2,75,WPA2|..."
    Garantiza que el resultado cabe en un MTU de 512 bytes.
    """
    partes = []
    total = 0

    for red in redes:
        entrada = f"{red['ssid']},{red['signal']},{red['security']}"
        # +1 por el separador '|'
        if total + len(entrada) + 1 > 510:
            logger.warning('Lista truncada por límite MTU')
            break
        partes.append(entrada)
        total += len(entrada) + 1

    return '|'.join(partes)


# ── Test independiente ───────────────────────────────────────────
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    print('Escaneando redes WiFi...\n')

    redes = escanear_redes()

    if not redes:
        print('No se encontraron redes.')
    else:
        print(f'{"SSID":<30} {"Señal":>6}  {"Seguridad"}')
        print('-' * 55)
        for r in redes:
            print(f"{r['ssid']:<30} {r['signal']:>6}  {r['security']}")

        print(f'\nFormato BLE ({len(formatear_para_ble(redes))} bytes):')
        print(formatear_para_ble(redes))
