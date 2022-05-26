import pandas as pd

from sarracen import SarracenDataFrame


def test_special_columns():
    # The 'x', 'y', 'rho', 'm', and 'h' keywords should be detected.
    # A 'z' column should not be detected.
    df = pd.DataFrame({'P': [1, 1],
                       'h': [1, 1],
                       'rho': [1, 1],
                       'x': [5, 6],
                       'y': [5, 4],
                       'm': [1, 1]})
    sdf = SarracenDataFrame(df)

    assert sdf.xcol == 'x'
    assert sdf.ycol == 'y'
    assert sdf.zcol is None
    assert sdf.rhocol == 'rho'
    assert sdf.mcol == 'm'
    assert sdf.hcol == 'h'

    # The 'rx', 'ry', 'rz', 'density', and 'mass' keywords should be detected.
    # An 'h' column should not be detected.
    df = pd.DataFrame({'ry': [-1, 1],
                       'density': [1, 1],
                       'rx': [3, 4],
                       'P': [1, 1],
                       'rz': [4, 3],
                       'mass': [1, 1]})
    sdf = SarracenDataFrame(df)

    assert sdf.xcol == 'rx'
    assert sdf.ycol == 'ry'
    assert sdf.zcol == 'rz'
    assert sdf.rhocol == 'density'
    assert sdf.mcol == 'mass'
    assert sdf.hcol is None

    # No keywords, so fall back to the first two columns for x and y.
    # Even though 'k' exists, this will be assumed to be 2D data.
    # The 'h' column will be detected, but no density or mass column will be detected.
    df = pd.DataFrame({'i': [3.4, 2.1],
                       'j': [4.9, 1.6],
                       'k': [2.3, 2.0],
                       'h': [1, 1],
                       'P': [1, 1]})
    sdf = SarracenDataFrame(df)

    assert sdf.xcol == 'i'
    assert sdf.ycol == 'j'
    assert sdf.zcol is None
    assert sdf.rhocol is None
    assert sdf.mcol is None
    assert sdf.hcol == 'h'


def test_dimensions():
    # This should be detected as 3-dimensional data.
    df = pd.DataFrame({'P': [1, 1],
                       'z': [4, 3],
                       'h': [1, 1],
                       'rho': [1, 1],
                       'x': [5, 6],
                       'y': [5, 4],
                       'm': [1, 1]})
    sdf = SarracenDataFrame(df)

    assert sdf.get_dim() == 3

    # This should be detected as 2-dimensional data.
    df = pd.DataFrame({'P': [1, 1],
                       'h': [1, 1],
                       'y': [5, 4],
                       'rho': [1, 1],
                       'm': [1, 1],
                       'x': [5, 6]})
    sdf = SarracenDataFrame(df)

    assert sdf.get_dim() == 2

    # This should assumed to be 2-dimensional data.
    df = pd.DataFrame({'P': [1, 1],
                       'h': [1, 1],
                       'rho': [1, 1],
                       'm': [1, 1]})
    sdf = SarracenDataFrame(df)

    assert sdf.get_dim() == 2


def test_column_changing():
    df = pd.DataFrame({'P': [1],
                       'z': [2],
                       'h': [3],
                       'rho': [4],
                       'x': [5],
                       'y': [6],
                       'm': [7],
                       'd': [8],
                       'smooth': [9],
                       'ma': [10]})
    sdf = SarracenDataFrame(df)

    assert sdf.xcol == 'x'
    assert sdf.ycol == 'y'
    assert sdf.zcol == 'z'
    assert sdf.rhocol == 'rho'
    assert sdf.mcol == 'm'
    assert sdf.hcol == 'h'

    sdf.xcol = 'z'  # column 'z' exists, assignment will be accepted
    sdf.ycol = 'a'  # column 'a' doesn't exist, assignment will be rejected
    sdf.zcol = 'x'  # accept
    sdf.rhocol = 'e'  # reject
    sdf.mcol = 'ma'  # accept
    sdf.hcol = 'smooth_length'  # reject

    assert sdf.xcol == 'z'
    assert sdf.ycol == 'y'
    assert sdf.zcol == 'x'
    assert sdf.rhocol == 'rho'
    assert sdf.mcol == 'ma'
    assert sdf.hcol == 'h'

    sdf.xcol = 'v'  # reject
    sdf.ycol = 'P'  # accept
    sdf.zcol = 'k'  # reject
    sdf.rhocol = 'd'  # accept
    sdf.mcol = 'mass'  # reject
    sdf.hcol = 'smooth'  # accept

    assert sdf.xcol == 'z'
    assert sdf.ycol == 'P'
    assert sdf.zcol == 'x'
    assert sdf.rhocol == 'd'
    assert sdf.mcol == 'ma'
    assert sdf.hcol == 'smooth'
