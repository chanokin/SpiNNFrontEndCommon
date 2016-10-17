from spinn_machine.utilities.progress_bar import ProgressBar

from spinnman.messages.sdp.sdp_flag import SDPFlag
from spinnman.messages.sdp.sdp_header import SDPHeader
from spinnman.messages.sdp.sdp_message import SDPMessage
from spinnman.model.cpu_state import CPUState

from spinn_front_end_common.utilities import helpful_functions
from spinn_front_end_common.utilities import constants
from spinn_front_end_common.utilities import exceptions

import struct


class FrontEndCommonChipProvenanceUpdater(object):
    """ Forces all cores to generate provenance data, and then exit
    """

    __slots__ = []

    def __call__(self, txrx, app_id, all_core_subsets):

        # check that the right number of processors are in sync
        processors_completed = txrx.get_core_state_count(
            app_id, CPUState.FINISHED)
        total_processors = len(all_core_subsets)
        left_to_do_cores = total_processors - processors_completed

        progress_bar = ProgressBar(
            left_to_do_cores,
            "Forcing error cores to generate provenance data")

        buggered_cores = helpful_functions.get_cores_in_state(
            all_core_subsets, CPUState.RUN_TIME_EXCEPTION, txrx)
        watched_dogged_cores = helpful_functions.get_cores_in_state(
            all_core_subsets, CPUState.WATCHDOG, txrx)
        disappeared_cores = helpful_functions.get_cores_in_state(
            all_core_subsets, CPUState.IDLE, txrx)

        if (len(buggered_cores) != 0 or len(watched_dogged_cores) != 0 or
                len(disappeared_cores) != 0):
            raise exceptions.ConfigurationException(
                "Some cores have crashed. RTE cores {}, watch-dogged cores {}, "
                "idle cores {}".format(
                    buggered_cores.values(), watched_dogged_cores.values(),
                    disappeared_cores.values()))


        # check that all cores are in the state CPU_STATE_12 which shows that
        # the core has received the message and done provenance updating
        while processors_completed != total_processors:
            unsuccessful_cores = helpful_functions.get_cores_not_in_state(
                all_core_subsets, CPUState.FINISHED, txrx)

            for (x, y, p) in unsuccessful_cores:
                data = struct.pack(
                    "<I", constants.SDP_RUNNING_MESSAGE_CODES.
                    SDP_UPDATE_PROVENCE_REGION_AND_EXIT.value)
                txrx.send_sdp_message(SDPMessage(SDPHeader(
                    flags=SDPFlag.REPLY_NOT_EXPECTED,
                    destination_cpu=p,
                    destination_chip_x=x,
                    destination_port=(
                        constants.SDP_PORTS.RUNNING_COMMAND_SDP_PORT.value),
                    destination_chip_y=y), data=data))

            processors_completed = txrx.get_core_state_count(
                app_id, CPUState.FINISHED)

            left_over_now = total_processors - processors_completed
            to_update = left_to_do_cores - left_over_now
            if to_update != 0:
                progress_bar.update(to_update)
        progress_bar.end()
