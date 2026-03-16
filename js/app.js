'use strict';

const SERVICE_UUID = '12345678-1234-5678-1234-56789abcdef0';
const RX_CHAR_UUID = '12345678-1234-5678-1234-56789abcdef1';
const TX_CHAR_UUID = '12345678-1234-5678-1234-56789abcdef2';
const DEVICE_NAME  = 'TFM-Onboarding';
const TIMEOUT_MS   = 30000;

let gattDevice         = null;
let rxCharacteristic   = null;
let redSeleccionada    = null;
let esperandoRespuesta = null;
let countdownInterval  = null;

// ── Utilidades UI ────────────────────────────────────────────────

const $ = id => document.getElementById(id);

const log = (msg, cls = 'log-info') => {
  const div = $('log');
  const line = document.createElement('div');
  line.className = cls;
  line.textContent = `[${new Date().toLocaleTimeString()}] ${msg}`;
  div.appendChild(line);
  div.scrollTop = div.scrollHeight;
};

const mostrarSeccion = id => {
  document.querySelectorAll('.seccion').forEach(s => s.classList.remove('activa'));
  $(id).classList.add('activa');
};

const setEstadoBLE = (texto, cls) => {
  const badge = $('estadoBLE');
  badge.textContent = texto;
  badge.className = `status-badge ${cls}`;
};

const setResultado = (icono, texto) => {
  $('iconoResultado').textContent = icono;
  $('textoResultado').textContent = texto;
};

// Barras de señal WiFi con SVG inline via spans
const signalBars = (signal) => {
  const niveles = [25, 50, 75, 100];
  return niveles.map(n =>
    `<span class="${signal >= n ? 'activa' : ''}" style="height:${n === 25 ? 6 : n === 50 ? 10 : n === 75 ? 14 : 18}px"></span>`
  ).join('');
};

// Cuenta atrás visual durante operaciones largas
const iniciarCountdown = (segundos, elementId) => {
  let restantes = segundos;
  const el = $(elementId);
  if (!el) return;
  el.textContent = `Tiempo restante: ${restantes}s`;
  countdownInterval = setInterval(() => {
    restantes--;
    if (restantes <= 0) {
      clearInterval(countdownInterval);
      if (el) el.textContent = '';
    } else {
      if (el) el.textContent = `Tiempo restante: ${restantes}s`;
    }
  }, 1000);
};

const detenerCountdown = (elementId) => {
  clearInterval(countdownInterval);
  const el = $(elementId);
  if (el) el.textContent = '';
};

// ── BLE ──────────────────────────────────────────────────────────

async function obtenerCaracteristicas(server) {
  const service = await server.getPrimaryService(SERVICE_UUID);
  rxCharacteristic = await service.getCharacteristic(RX_CHAR_UUID);
  const txChar = await service.getCharacteristic(TX_CHAR_UUID);
  await txChar.startNotifications();
  txChar.addEventListener('characteristicvaluechanged', onNotificacion);
  log('BLE conectado ✓', 'log-ok');
}

function onNotificacion(event) {
  const valor = new TextDecoder().decode(event.target.value);
  log(`← ${valor}`, 'log-rx');
  if (esperandoRespuesta) {
    esperandoRespuesta(valor);
    esperandoRespuesta = null;
  }
}

function enviarComando(cmd, timeoutMs = TIMEOUT_MS) {
  return new Promise(async (resolve, reject) => {
    try {
      esperandoRespuesta = resolve;
      const encoded = new TextEncoder().encode(cmd);
      await rxCharacteristic.writeValueWithoutResponse(encoded);
      log(`→ ${cmd}`, 'log-info');
      setTimeout(() => {
        if (esperandoRespuesta) {
          esperandoRespuesta = null;
          reject(new Error('Timeout esperando respuesta'));
        }
      }, timeoutMs);
    } catch (err) {
      esperandoRespuesta = null;
      reject(err);
    }
  });
}

function configurarReconexion() {
  gattDevice.addEventListener('gattserverdisconnected', async () => {
    setEstadoBLE('Reconectando...', 'status-buscando');
    log('Conexión perdida, reconectando...', 'log-info');
    try {
      const server = await gattDevice.gatt.connect();
      await obtenerCaracteristicas(server);
      setEstadoBLE('BLE conectado', 'status-conectado');
    } catch (err) {
      setEstadoBLE('Sin conexión BLE', 'status-desconectado');
      log(`Error reconectando: ${err.message}`, 'log-err');
    }
  });
}

// ── Botón Conectar BLE ───────────────────────────────────────────

$('btnConectar').addEventListener('click', async () => {
  log('Iniciando conexión BLE...', 'log-info');
  if (!navigator.bluetooth) {
    log('Web Bluetooth no disponible en este navegador', 'log-err');
    return;
  }
  try {
    setEstadoBLE('Buscando...', 'status-buscando');
    gattDevice = await navigator.bluetooth.requestDevice({
      filters: [{ name: DEVICE_NAME }],
      optionalServices: [SERVICE_UUID]
    });
    log(`Dispositivo encontrado: ${gattDevice.name}`, 'log-ok');
    const server = await gattDevice.gatt.connect();
    await obtenerCaracteristicas(server);
    configurarReconexion();
    setEstadoBLE('BLE conectado', 'status-conectado');
    mostrarSeccion('secRedes');
  } catch (err) {
    setEstadoBLE('Sin conexión BLE', 'status-desconectado');
    log(`Error: ${err.message}`, 'log-err');
  }
});

// ── Botón Desconectar BLE ────────────────────────────────────────

$('btnDesconectar').addEventListener('click', () => {
  if (gattDevice && gattDevice.gatt.connected) {
    gattDevice.gatt.disconnect();
    log('Desconectado manualmente', 'log-info');
  }
  setEstadoBLE('Sin conexión BLE', 'status-desconectado');
  gattDevice = null;
  rxCharacteristic = null;
  mostrarSeccion('secBLE');
});

// ── Botón Escanear redes ─────────────────────────────────────────

$('btnScan').addEventListener('click', async () => {
  const lista = $('listaRedes');
  lista.innerHTML = '<p style="color:#888;"><span class="spinner"></span>Escaneando...</p>';
  log('Escaneando redes WiFi...', 'log-info');
  iniciarCountdown(15, 'countdownScan');

  try {
    const respuesta = await enviarComando('SCAN', 20000);
    detenerCountdown('countdownScan');

    if (!respuesta.startsWith('NETS:') || respuesta === 'NETS:') {
      lista.innerHTML = '<p style="color:#888;">No se encontraron redes</p>';
      return;
    }

    const redes = respuesta.slice(5).split('|').map(r => {
      const partes = r.split(',');
      return { ssid: partes[0], signal: parseInt(partes[1]), security: partes[2] };
    });

    lista.innerHTML = '';
    redes.forEach(red => {
      const item = document.createElement('div');
      item.className = 'red-item';
      item.innerHTML = `
        <div>
          <div class="red-nombre">${red.ssid}</div>
          <div class="red-meta">${red.security} · ${red.signal}%</div>
        </div>
        <div class="red-signal">${signalBars(red.signal)}</div>
      `;
      item.addEventListener('click', () => seleccionarRed(red, item));
      lista.appendChild(item);
    });

    log(`${redes.length} redes encontradas`, 'log-ok');

  } catch (err) {
    detenerCountdown('countdownScan');
    lista.innerHTML = '<p style="color:#c62828;">Error al escanear</p>';
    log(`Error escaneo: ${err.message}`, 'log-err');
  }
});

// ── Seleccionar red ──────────────────────────────────────────────

function seleccionarRed(red, elemento) {
  document.querySelectorAll('.red-item').forEach(i => i.classList.remove('selected'));
  elemento.classList.add('selected');
  redSeleccionada = red;
  $('labelRedSeleccionada').textContent = `🔒 ${red.ssid}`;
  $('inputPassword').value = '';
  mostrarSeccion('secPassword');
}

// ── Toggle contraseña visible ────────────────────────────────────

$('togglePassword').addEventListener('click', () => {
  const input = $('inputPassword');
  const btn = $('togglePassword');
  if (input.type === 'password') {
    input.type = 'text';
    btn.textContent = '🙈';
  } else {
    input.type = 'password';
    btn.textContent = '👁';
  }
});

// ── Botón Volver ─────────────────────────────────────────────────

$('btnVolver').addEventListener('click', () => mostrarSeccion('secRedes'));

// ── Botón Conectar WiFi ──────────────────────────────────────────

$('btnConectar2').addEventListener('click', async () => {
  const password = $('inputPassword').value;
  if (!password) {
    log('Introduce una contraseña', 'log-err');
    return;
  }

  mostrarSeccion('secResultado');
  setResultado('⏳', `Conectando a "${redSeleccionada.ssid}"...`);
  $('countdownConectar').textContent = '';
  iniciarCountdown(25, 'countdownConectar');

  try {
    const respuesta = await enviarComando(
      `CONNECT:${redSeleccionada.ssid}|${password}`,
      30000
    );
    detenerCountdown('countdownConectar');

    if (respuesta.startsWith('WIFI_OK:')) {
      setResultado('✅', `Conectado a "${redSeleccionada.ssid}" correctamente`);
      log(`WiFi conectado: ${respuesta}`, 'log-ok');
    } else {
      const motivo = respuesta.split(':')[1] || 'desconocido';
      const mensajes = {
        'red_no_encontrada':     'Red no encontrada',
        'contraseña_incorrecta': 'Contraseña incorrecta',
        'timeout':               'Tiempo de espera agotado',
        'formato_invalido':      'Error interno',
        'ssid_vacio':            'Error interno',
      };
      setResultado('❌', mensajes[motivo] || `Error: ${motivo}`);
      log(`Error WiFi: ${respuesta}`, 'log-err');
    }

  } catch (err) {
    detenerCountdown('countdownConectar');
    setResultado('❌', 'Error de comunicación BLE');
    log(`Error: ${err.message}`, 'log-err');
  }
});

// ── Botón Elegir otra red ────────────────────────────────────────

$('btnOtraRed').addEventListener('click', () => mostrarSeccion('secRedes'));
