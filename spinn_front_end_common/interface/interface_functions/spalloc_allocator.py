import math
import logging
import sys
from threading import Thread

from spalloc import Job
from spalloc.states import JobState
from spinn_front_end_common.abstract_models \
    import AbstractMachineAllocationController

logger = logging.getLogger(__name__)


class _SpallocJobController(Thread, AbstractMachineAllocationController):

    __slots__ = [
        # thread flag to allow it to be killed when the main thread dies
        "daemon",

        # the spalloc job object
        "_job",

        # boolean flag for telling this thread when the system has ended
        "_exited"
    ]

    def __init__(self, job):
        Thread.__init__(self, name="SpallocJobController")
        self.daemon = True
        self._job = job
        self._exited = False

    def extend_allocation(self, new_total_run_time):
        # Does Nothing in this allocator - machines are held until exit
        pass

    def close(self):
        self._exited = True
        self._job.destroy()

    @property
    def power(self):
        return self._job.power

    def set_power(self, power):
        self._job.set_power(power)
        if power:
            self._job.wait_until_ready()

    def where_is_machine(self, chip_x, chip_y):
        return self._job.where_is_machine(chip_y=chip_y, chip_x=chip_x)

    def _wait_for_state_change(self, old_state):
        try:
            if self._job is not None:
                return self._job.wait_for_state_change(old_state)
        except TypeError:
            pass
        return old_state

    def run(self):
        state = self._job.state
        while state != JobState.destroyed and not self._exited:
            state = self._wait_for_state_change(state)

        self._job.close()

        if not self._exited:
            logger.error(
                "The allocated machine has been released before the end of"
                " the script - this script will now exit")
            sys.exit(1)


class SpallocAllocator(object):
    """ Request a machine from a SPALLOC server that will fit the given\
        number of chips
    """

    # Use a worst case calculation
    _N_CHIPS_PER_BOARD = 48.0
    _MACHINE_VERSION = 5

    def __call__(
            self, spalloc_server, spalloc_user, n_chips, spalloc_port=None,
            spalloc_machine=None):
        """

        :param spalloc_server: \
            The server from which the machine should be requested
        :param spalloc_port: The port of the SPALLOC server
        :param spalloc_user: The user to allocate the machine to
        :param n_chips: The number of chips required
        :param spalloc_port: The optional port number to speak to spalloc
        :param spalloc_machine: The optional spalloc machine to use
        """

        # Work out how many boards are needed
        n_boards = float(n_chips) / self._N_CHIPS_PER_BOARD

        # If the number of boards rounded up is less than 10% bigger than the
        # actual number of boards, add another board just in case
        if math.ceil(n_boards) - n_boards < 0.1:
            n_boards += 1
        n_boards = int(math.ceil(n_boards))

        spalloc_kw_args = {
            'hostname': spalloc_server,
            'owner': spalloc_user
        }
        if spalloc_port is not None:
            spalloc_kw_args['port'] = spalloc_port
        if spalloc_machine is not None:
            spalloc_kw_args['machine'] = spalloc_machine

        job, hostname = self._launch_job(n_boards, spalloc_kw_args)
        machine_allocation_controller = _SpallocJobController(job)
        machine_allocation_controller.start()

        return (
            hostname, self._MACHINE_VERSION, None, None, None, None, False,
            False, None, None, None, machine_allocation_controller
        )

    def _launch_job(self, n_boards, spalloc_kw_args):
        job = Job(n_boards, **spalloc_kw_args)
        try:
            job.wait_until_ready()
            # get param from jobs before starting, so that hanging doesn't
            # occur
            return job, job.hostname
        except:
            job.destroy()
            raise
