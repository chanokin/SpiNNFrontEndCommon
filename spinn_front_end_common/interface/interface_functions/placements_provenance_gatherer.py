from spinn_utilities.progress_bar import ProgressBar

# front end common imports
from spinn_front_end_common.utilities.exceptions import ConfigurationException
from spinn_front_end_common.interface.provenance \
    import AbstractProvidesProvenanceDataFromMachine


class PlacementsProvenanceGatherer(object):
    __slots__ = []

    def __call__(
            self, transceiver, placements, has_ran,
            provenance_data_objects=None):
        """
        :param transceiver: the SpiNNMan interface object
        :param placements: The placements of the vertices
        :param has_ran: token that states that the simulation has ran
        """

        if not has_ran:
            raise ConfigurationException(
                "This function has been called before the simulation has ran."
                " This is deemed an error, please rectify and try again")

        if provenance_data_objects is not None:
            prov_items = provenance_data_objects
        else:
            prov_items = list()

        progress = ProgressBar(
            placements.n_placements, "Getting provenance data")

        # retrieve provenance data from any cores that provide data
        for placement in progress.over(placements.placements):
            if isinstance(placement.vertex,
                          AbstractProvidesProvenanceDataFromMachine):
                # get data
                prov_items.extend(
                    placement.vertex.get_provenance_data_from_machine(
                        transceiver, placement))

        return prov_items
