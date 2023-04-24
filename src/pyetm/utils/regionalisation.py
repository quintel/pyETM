"""regionalisation methods"""
import logging
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

def _validate_regionalisation(curves, reg, **kwargs):
    """helper function to validate regionalisation table"""

    # load regionalization
    if isinstance(reg, str):
        reg = pd.read_csv(reg, **kwargs)

    # check is reg specifies keys not in passed curves
    for item in reg.columns[~reg.columns.isin(curves.columns)]:
        raise ValueError(f"'{item}' is not present in the passed curves")

    # check if passed curves specifies keys not specified in reg
    for item in curves.columns[~curves.columns.isin(reg.columns)]:
        raise ValueError(f"'{item}' not present in the regionalization")

    # check if regionalizations add up to 1.000
    sums = round(reg.sum(axis=0), 3)
    for idx, value in sums[sums != 1].items():
        raise ValueError(f'"{idx}" regionalization sums to ' +
                         f'{value: .3f} instead of 1.000')

    return curves, reg

def regionalise_curves(curves, reg, node=None,
                       sector=None, hours=None, **kwargs):
    """Return the residual power of the curves based on a regionalisation table.
    The kwargs are passed to pd.read_csv when the regionalisation argument
    is a passed as a filestring.

    Parameters
    ----------
    curves : DataFrame
        Categorized ETM curves.
    reg : DataFrame or str
        Regionalization table with nodes in index and
        sectors in columns.
    node : key or list of keys, default None
        Specific node in regionalisation for which
        the dot product is evaluated, defaults to all nodes.
    sector : key or list of keys, default None
        Specific sector in regionalisation for which
        the dot product is evaluated, defaults to all sectors.
    hours : key or list of keys, default None
        Specific hours for which the dot product
        is evaluated, defaults to all hours.

    Return
    ------
    curves : DataFrame
        Residual power profiles."""

    # validate regionalisation
    curves, reg = _validate_regionalisation(curves, reg, **kwargs)

    """consider warning for curves that do not sum up to zero,
    as this leads to incorrect regionalisations. Assigning a negative
    sign to demand only happens during categorisation."""

    # handle node subsetting
    if node is not None:

        # warn for subsettign multiple items
        if isinstance(node, list):

            msg = "returning dot product for subset of multiple nodes"
            logger.warning(msg)

        else:
            # ensure list
            node = [node]

        # subset node
        reg = reg.loc[node]

    # handle sector subsetting
    if sector is not None:

        # warn for subsetting multiple items
        if isinstance(sector, list):

            msg = "returning dot product for subset of multiple sectors"
            logger.warning(msg)

        else:
            # ensure list
            sector = [sector]

        # subset sector
        curves, reg = curves[sector], reg[sector]

    # subset hours
    if hours is not None:
        curves = curves.loc[hours]

    return curves.dot(reg.T)

def regionalise_node(curves, reg, node, sector=None, hours=None, **kwargs):
    """Return the sector profiles for a node specified in the regionalisation
    table. The kwargs are passed to pd.read_csv when the regionalisation
    argument is a passed as a filestring.

    Parameters
    ----------
    curves : DataFrame
        Categorized ETM curves.
    reg : DataFrame or str
        Regionalization table with nodes in index and
        sectors in columns.
    node : key or list of keys
        Specific node in regionalisation for which
        the profiles are returned.
    sector : key or list of keys, default None
        Specific sector in regionalisation for which
        the profile is evaluated, defaults to all sectors.
    hours : key or list of keys, default None
        Specific hours for which the profiles
        are evaluated, defaults to all hours.

    Return
    ------
    curves : DataFrame
        Sector profile per specified node."""

    # validate regionalisation
    curves, reg = _validate_regionalisation(curves, reg, **kwargs)

    # subset node(s)
    reg = reg.loc[node]

    # subset hours
    if hours is not None:
        curves = curves.loc[hours]

    # handle single node
    if not isinstance(node, list):

        # handle sector
        if sector is not None:
            return curves[sector].mul(reg[sector])

        return curves.mul(reg)

    # prepare new index
    levels = [reg.index, curves.index]
    index = pd.MultiIndex.from_product(levels, names=None)

    # prepare new dataframe
    columns = curves.columns
    values = np.repeat(curves.values, reg.index.size, axis=0)

    # match index structure of regionalization
    curves = pd.DataFrame(values, index=index, columns=columns)

    return reg.mul(curves, level=0)
