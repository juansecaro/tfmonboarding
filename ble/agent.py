# ble/agent.py
"""Agente BLE que rechaza pairing automáticamente (NoInputNoOutput)."""

import dbus
import dbus.service
import dbus.mainloop.glib
import logging

logger = logging.getLogger(__name__)

AGENT_PATH = '/com/tfm/agent'


class NoInputNoOutputAgent(dbus.service.Object):
    """Agente D-Bus que rechaza cualquier intento de pairing/bonding."""

    @dbus.service.method('org.bluez.Agent1', in_signature='', out_signature='')
    def Release(self):
        pass

    @dbus.service.method('org.bluez.Agent1', in_signature='os', out_signature='')
    def AuthorizeService(self, device, uuid):
        # Permite el servicio sin pairing
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


def registrar(bus: dbus.SystemBus) -> NoInputNoOutputAgent:
    """
    Registra el agente anti-pairing en BlueZ.

    Args:
        bus: conexión al bus D-Bus del sistema

    Returns:
        Instancia del agente registrado
    """
    agent = NoInputNoOutputAgent(bus, AGENT_PATH)
    manager = dbus.Interface(
        bus.get_object('org.bluez', '/org/bluez'),
        'org.bluez.AgentManager1'
    )
    manager.RegisterAgent(AGENT_PATH, 'NoInputNoOutput')
    manager.RequestDefaultAgent(AGENT_PATH)
    logger.info('Agente anti-pairing registrado ✓')
    return agent
