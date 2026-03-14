import subprocess
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info('Probando nmcli desde contexto systemd...')

# Test red inexistente
r = subprocess.run(
    ['nmcli', '-w', '15', 'device', 'wifi', 'connect', 'REDQUENOEXISTE', 'password', 'test'],
    capture_output=True, text=True, timeout=20
)
logger.info('returncode: %s', r.returncode)
logger.info('stdout: %s', r.stdout.strip())
logger.info('stderr: %s', r.stderr.strip())

# Test contraseña incorrecta
r2 = subprocess.run(
    ['nmcli', '-w', '15', 'device', 'wifi', 'connect', 'TP-Link_4AB7', 'password', 'contraseñafalsa'],
    capture_output=True, text=True, timeout=20
)
logger.info('returncode2: %s', r2.returncode)
logger.info('stdout2: %s', r2.stdout.strip())
logger.info('stderr2: %s', r2.stderr.strip())

import sys
sys.path.insert(0, '/home/redvi/Desktop/TFM/tfmonboarding')
from wifi.connector import conectar, obtener_estado

logger.info('=== Test connector module ===')
ok, msg = obtener_estado()
logger.info('Estado: %s', msg)

ok, msg = conectar('REDQUENOEXISTE', 'test')
logger.info('Red inexistente: ok=%s msg=%s', ok, msg)

ok, msg = conectar('TP-Link_4AB7', 'contraseñafalsa')
logger.info('Contraseña incorrecta: ok=%s msg=%s', ok, msg)
