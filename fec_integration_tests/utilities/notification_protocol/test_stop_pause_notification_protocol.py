import unittest

from spinn_utilities.socket_address import SocketAddress

from spinn_front_end_common.utilities.notification_protocol \
    import NotificationProtocol

from spinnman.connections.udp_packet_connections import EIEIOConnection
from spinnman.messages.eieio.command_messages import EIEIOCommandMessage
from spinnman.constants import EIEIO_COMMAND_IDS


class TestStopPauseNotificationProtocol(unittest.TestCase):

    def test_send_stop_pause_notification(self):
        """ Test the sending of the stop/pause message of the notification\
            protocol
        """
        listener = EIEIOConnection()
        socket_addresses = [SocketAddress(
            "127.0.0.1", listener.local_port, None)]
        protocol = NotificationProtocol(socket_addresses, False)
        protocol.send_stop_pause_notification()
        message = listener.receive_eieio_message(timeout=10)
        self.assertIsInstance(message, EIEIOCommandMessage)
        self.assertEqual(
            message.eieio_header.command,
            EIEIO_COMMAND_IDS.STOP_PAUSE_NOTIFICATION.value)


if __name__ == '__main__':
    unittest.main()
