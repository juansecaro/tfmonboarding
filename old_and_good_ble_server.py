# ble_server.py
import logging
import threading
import time
import dbus
import dbus.service
import dbus.mainloop.glib
from bluezero import peripheral, adapter

logging.basicConfig(level=logging.INFO)

SERVICE_UUID = '12345678-1234-5678-1234-56789abcdef0'
RX_CHAR_UUID = '12345678-1234-5678-1234-56789abcdef1'
TX_CHAR_UUID = '12345678-1234-5678-1234-56789abcdef2'

tx_characteristic = None

AGENT_PATH = '/com/tfm/agent'

class NoInputNoOutputAgent(dbus.service.Object):

    @dbus.service.method('org.bluez.Agent1', in_signature='', out_signature='')
    def Release(self):
        pass

    @dbus.service.method('org.bluez.Agent1', in_signature='os', out_signature='')
    def AuthorizeService(self, device, uuid):
        pass

    @dbus.service.method('org.bluez.Agent1', in_signature='o', out_signature='')
    def RequestAuthorization(self, device):
        raise dbus.DBusException('org.bluez.Error.Rejected')

    @dbus.service.method('org.bluez.Agent1', in_signature='o', out_signature='u')
    def RequestPasskey(self, device):
        raise dbus.DBusException('org.bluez.Error.Rejected')

    @dbus.service.method('org.bluez.Agent1', in_signature='ouq', out_signature='')
    def DisplayPasskey(self, device, passkey, entered):
        pass

    @dbus.service.method('org.bluez.Agent1', in_signature='os', out_signature='')
    def DisplayPinCode(self, device, pincode):
        pass

    @dbus.service.method('org.bluez.Agent1', in_signature='ou', out_signature='')
    def RequestConfirmation(self, device, passkey):
        raise dbus.DBusException('org.bluez.Error.Rejected')

    @dbus.service.method('org.bluez.Agent1', in_signature='o', out_signature='s')
    def RequestPinCode(self, device):
        raise dbus.DBusException('org.bluez.Error.Rejected')

    @dbus.service.method('org.bluez.Agent1', in_signature='', out_signature='')
    def Cancel(self):
        pass

def registrar_agente():
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()
    agent = NoInputNoOutputAgent(bus, AGENT_PATH)
    manager = dbus.Interface(
        bus.get_object('org.bluez', '/org/bluez'),
        'org.bluez.AgentManager1'
    )
    manager.RegisterAgent(AGENT_PATH, 'NoInputNoOutput')
    manager.RequestDefaultAgent(AGENT_PATH)
    print('[RPi] Agente anti-pairing registrado ✓')

def enviar_respuesta(mensaje):
    respuesta = f'RPi recibió: {mensaje}'
    valor = list(respuesta.encode('utf-8'))  # ← en lugar de [ord(c) for c in respuesta]  #valor = [ord(c) for c in respuesta]
    for _ in range(30):
        if tx_characteristic is not None:
            tx_characteristic.set_value(valor)  # ← cambio clave
            print(f'[RPi] → Notificación enviada: "{respuesta}"')
            return
        time.sleep(0.1)
    print('[RPi] ✗ Timeout: no hubo suscripción activa para notificar')

def rx_write_callback(value, options):
    mensaje = bytes(value).decode('utf-8')  # ← en lugar de ''.join(chr(b) for b in value)
    print(f'\n[RPi] ← Recibido desde móvil: "{mensaje}"')
    threading.Thread(target=enviar_respuesta, args=(mensaje,), daemon=True).start() 

def tx_notify_callback(notifying, characteristic):
    global tx_characteristic
    if notifying:
        tx_characteristic = characteristic
        print('[RPi] Móvil suscrito a notificaciones TX ✓')
    else:
        tx_characteristic = None
        print('[RPi] Móvil canceló suscripción TX')

def tx_read_callback():
    return [ord(c) for c in 'esperando...']

registrar_agente()

dongle = adapter.Adapter()
dongle.pairable = False  # ← evita que BlueZ acepte bonding
print('[RPi] Modo no-pairable activado ✓')

ble_app = peripheral.Peripheral(
    dongle.address,
    local_name='HolaMundo-BLE',
    appearance=0x0000
)

ble_app.add_service(srv_id=1, uuid=SERVICE_UUID, primary=True)

ble_app.add_characteristic(
    srv_id=1, chr_id=1, uuid=RX_CHAR_UUID,
    value=[], notifying=False,
    flags=['write', 'write-without-response'],
    write_callback=rx_write_callback,
    read_callback=None, notify_callback=None
)

ble_app.add_characteristic(
    srv_id=1, chr_id=2, uuid=TX_CHAR_UUID,
    value=[ord(c) for c in 'esperando...'],
    notifying=False,
    flags=['read', 'notify'],
    write_callback=None,
    read_callback=tx_read_callback,
    notify_callback=tx_notify_callback
)

print('[RPi] Servidor BLE iniciado')
print(f'      Nombre:   HolaMundo-BLE')
print(f'      Servicio: {SERVICE_UUID}')
print(f'      Esperando conexión...\n')

ble_app.publish()
