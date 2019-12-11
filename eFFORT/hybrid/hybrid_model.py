import json
from pathlib import Path

import numpy
import pandas


class Hybrid:
    """Create and apply the Hybrid model approach to inclusive semileptonic b -> u l nu decays.

    The Hybrid model should be created for charged and neutral B mesons separately, because of the different resonances
    contributing in the mX spectrum.

    """

    def __init__(self, hybrid_config: str = None) -> None:
        """Initialize the hybrid weight with the given configuration.

        The default binning is given by
          * BINS_MX: [0.0, 1.4, 1.6, 1.8, 2.0, 2.5, 3.0, 3.5]
          * BINS_EL_B:[0.0, 0.5, 1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 3.0]
          * BINS_Q2: [0.0, 2.5, 5.0, 7.5, 10.0, 12.5, 15.0, 20.0, 25.0]

        which is motivated by theory. This should only be changed with proper theoretical motivation.

        Parameters
        ----------
        hybrid_config: str
            Path to json file defining the binning of the Hybrid model. Has to contain the three attributes:
              * BINS_MX: The binning for the Hybrid model in mX.
              * BINS_ELB: The binning of the Hybrid model in El_B.
              * BINS_Q2: The binning of the Hybrid model in q2.

        """

        if hybrid_config is None:
            this_dir = Path(__file__).parent
            hybrid_config = this_dir / 'hybrid_binning.json'

        with open(hybrid_config) as json_file:
            config = json.load(json_file)

        self.bins_mX = config['BINS_MX']
        self.bins_El_B = config['BINS_ELB']
        self.bins_q2 = config['BINS_Q2']

        self.range_mX = (self.bins_mX[0], self.bins_mX[1])
        self.range_El_B = (self.bins_El_B[0], self.bins_El_B[1])
        self.range_q2 = (self.bins_q2[0], self.bins_q2[1])

    def calculate_weight(self, x: numpy.array, hybrid_weights: numpy.histogramdd) -> float:
        """Calculate the weight in the 3D phase space of the inclusive model.

        Parameters
        ----------
        x : numpy.array
            Phase space location of the inclusive prediction in the form (El_B, q2, mX).
        hybrid_weights: numpy:array
            Hybrid weights generated by :func:`~hybrid.Hybrid.generate_hybrid_weights`.

        Returns
        -------
        hybrid_weight: float
            The hybrid weight w_i at the given phase space point x.

        Examples
        --------
        To apply the generated hybrid weights with :func:`~hybrid.Hybrid.generate_hybrid_weights`, use the following
        syntax, assuming you stored the result of :func:`~hybrid.Hybrid.generate_hybrid_weights` in the variable
        hybrid_weights, and your data is stored in the pandas.DataFrame df:

            >>> # df['hybrid_weight'] = calculate_weight(df[['El_B', 'q2', 'mX']], hybrid_weights)

        """
        # catch bin edges index error by padding the weight table with 0 in both axis
        padded_table = numpy.pad(hybrid_weights, [1, 1], 'constant', constant_values=0)
        digitzed_El = numpy.digitize(x[:, 0], self.bins_El_B)
        digitzed_q2 = numpy.digitize(x[:, 1], self.bins_q2)
        digitzed_mX = numpy.digitize(x[:, 2], self.bins_mX)

        return padded_table[digitzed_El, digitzed_q2, digitzed_mX]

    def generate_hybrid_weights(self, inclusive: pandas.DataFrame, exclusive: pandas.DataFrame) -> numpy.histogramdd:
        """Calculate the Hybrid weights w_i, so that the bin content in the Hybrid model is given by
        H_i = R_i + w_i I_i, where H_i is the bin content of the inclusive prediction in the Hybrid model, R_i is the
        bin content of the resonant contributions, and I_i is the bin content of the total inclusive prediction.

        The required columns in the inclusive and exclusive data frames are:
          * mX: the invariant mass of the hadronic system (the mass of the resonance).
          * El_B: the lepton momentum in the B reference frame.
          * q2: the momentum transfer to the lepton-neutrino system.
          * __weight__: the weight should be adapted in a way that the individual components have the correct relative branching fractions.

        Parameters
        ----------
        inclusive: pandas.DataFrame
            Inclusive MC.
        exclusive: pandas.DataFrame
            Exclusive MC. Can contain any number of resonances.

        Returns
        -------
        hybrid_weights: numpy.histogramdd
            3D histogram containing the weights of the Hybrid model. To be used with
            :func:`~hybrid.Hybrid.calculate_weight`.
        """
        H_exc, _ = numpy.histogramdd(
            exclusive[['El_B', 'q2', 'mX']].values,
            bins=[self.bins_El_B, self.bins_q2, self.bins_mX],
            range=[self.range_El_B, self.range_q2, self.range_mX],
            normed=False,
            weights=exclusive['__weight__']
        )

        H_incl, _ = numpy.histogramdd(
            inclusive[['El_B', 'q2', 'mX']].values,
            bins=[self.bins_El_B, self.bins_q2, self.bins_mX],
            range=[self.range_El_B, self.range_q2, self.range_mX],
            normed=False,
            weights=inclusive['__weight__']
        )

        hybrid_weights = (H_incl - H_exc) / H_incl

        # Replace nan values with 1
        hybrid_weights = numpy.where(
            numpy.isnan(hybrid_weights), numpy.ones(hybrid_weights.shape), hybrid_weights)
        # Replace < 0 values with 0
        hybrid_weights = numpy.where(
            hybrid_weights < 0, numpy.zeros(hybrid_weights.shape), hybrid_weights)

        return hybrid_weights
