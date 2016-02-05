
# front end common imports
from spinn_front_end_common.interface import interface_functions
from spinn_front_end_common.utilities import report_functions as \
    front_end_common_report_functions
from spinn_front_end_common.utilities import exceptions \
    as front_end_common_exceptions

# pacman imports
from pacman.operations.pacman_algorithm_executor import PACMANAlgorithmExecutor
from pacman import exceptions as pacman_exceptions

# SpinnMan imports
from spinnman.model.core_subsets import CoreSubsets

# general imports
import os
import sys
import logging

logger = logging.getLogger(__name__)


class FrontEndCommonExecuteMapper(object):
    """
    FrontEndCommonExecuteMapper: function that executes the top level pacman
    algorithm executor. Stored to contain safety checks as well
    """

    def __init__(self):
        pass

    def do_mapping(
            self, inputs, algorithms, required_outputs, xml_paths, do_timings,
            algorithms_to_catch_prov_on_crash):
        """
        :param do_timings: bool which states if each algorithm should time
        itself
        :param inputs:
        :param algorithms:
        :param required_outputs:
        :param xml_paths:
        :param algorithms_to_catch_prov_on_crash:
        :return:
        """

        # add xml path to front end common interface functions
        xml_paths.append(
            os.path.join(os.path.dirname(interface_functions.__file__),
                         "front_end_common_interface_functions.xml"))

        # add xml path to front end common report functions
        xml_paths.append(
            os.path.join(os.path.dirname(
                front_end_common_report_functions.__file__),
                "front_end_common_reports.xml"))

        # create executor
        pacman_executor = PACMANAlgorithmExecutor(
            do_timings=do_timings, inputs=inputs, xml_paths=xml_paths,
            algorithms=algorithms, required_outputs=required_outputs)

        # try to execute all mapping and execution processes, if it fails, catch
        # standard exceptions and try to grab provenance data from machine
        # execute mapping process
        try:
            pacman_executor.execute_mapping()
        except pacman_exceptions.PacmanAlgorithmFailedToCompleteException as \
                pacman_exception:

            has_failed_to_start = isinstance(
                pacman_exception.exception,
                front_end_common_exceptions.ExecutableFailedToStartException)
            has_failed_to_end = isinstance(
                pacman_exception.exception,
                front_end_common_exceptions.ExecutableFailedToStopException)

            if ((has_failed_to_start or has_failed_to_end) and
                    pacman_exception.algorithm.algorithm_id in
                    algorithms_to_catch_prov_on_crash):
                self._prov_collection_during_error_state(
                    pacman_exception, pacman_executor, has_failed_to_end)
            else:
                raise pacman_exception.exception
        return pacman_executor

    def _prov_collection_during_error_state(
            self, pacman_exception, pacman_executor, has_failed_to_end):
        """
        function which sets off the extraction of iobuf and provenance data
        from the SpiNNaker machine
        :param pacman_exception: the exception which should contain all the info
        needed to execute prov collection
        :return: Does not return, will exit once collection is done
        """
        # generate inputs
        pacman_inputs = list()
        pacman_inputs.append({
            'type': 'ProvenanceFilePath',
            'value': pacman_executor.get_item("ProvenanceFilePath")})
        pacman_inputs.append({
            'type': 'MemoryTransciever',
            'value': pacman_executor.get_item("MemoryTransciever")})
        pacman_inputs.append({
            'type': 'MemoryExtendedMachine',
            'value': pacman_executor.get_item("MemoryExtendedMachine")})
        pacman_inputs.append({
            'type': 'MemoryRoutingTables',
            'value': pacman_executor.get_item("MemoryRoutingTables")})
        pacman_inputs.append({
            'type': 'MemoryPlacements',
            'value': pacman_executor.get_item("MemoryPlacements")})
        pacman_inputs.append({
            'type': 'RanToken',
            'value': True})
        pacman_inputs.append({
            'type': "FailedCoresSubsets",
            'value': self._convert_to_core_subsets(
                pacman_exception.exception.failed_core_subsets)})

        # make pacman algorithms
        pacman_algorithms = list()
        pacman_algorithms.append("FrontEndCommonIOBufExtractor")
        # only if the system has ran does provenance gathering make sense
        if has_failed_to_end:
            pacman_algorithms.append("FrontEndCommonProvenanceGatherer")
        pacman_algorithms.append("FrontEndCommonMessagePrinter")

        # pacman outputs
        pacman_outputs = list()
        pacman_outputs.append("IOBuffers")
        pacman_outputs.append("ErrorMessages")
        pacman_outputs.append("WarnMessages")

        # pacman xmls
        xml_paths = list()
        xml_paths.append(os.path.join(
            os.path.dirname(interface_functions.__file__),
            "front_end_common_interface_functions.xml"))

        # execute pacman executor
        pacman_executor = PACMANAlgorithmExecutor(
            pacman_algorithms, pacman_inputs, xml_paths, pacman_outputs)
        pacman_executor.execute_mapping()

        # exit the system, as system has failed
        logger.error(
            "Something failed during the run. I have outputted important "
            "messages from the executable code and stored the io_buffers of "
            "said cores in the provenance data. I will now exit.")
        sys.exit(0)

    @staticmethod
    def _convert_to_core_subsets(failed_core_subsets_listing):
        core_subsets = CoreSubsets()
        for (x, y, p) in failed_core_subsets_listing:
            core_subsets.add_processor(x, y, p)
        return core_subsets
