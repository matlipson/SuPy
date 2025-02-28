import numpy as np
from pathlib import Path
import pandas as pd
from .._load import load_SUEWS_Forcing_met_df_pattern


def parse_suews_datetime(df_raw: pd.DataFrame) -> pd.DataFrame:
    """convert raw SUEWS DataFrame to datetime-aware DataFrame.

    Parameters
    ----------
    df_raw : pd.DataFrame
        raw SUEWS DataFrame

    Returns
    -------
    pd.DataFrame
        datetime-aware DataFrame
    """

    # set timestamp as index
    idx_dt = pd.date_range(
        *df_raw.iloc[[0, -1], :4].astype(int).astype(str).apply(
            lambda ser: ser.str.cat(sep=' '), axis=1).map(
            lambda dt: pd.to_datetime(dt, format='%Y %j %H %M')),
        periods=df_raw.shape[0])

    df_datetime = df_raw.set_index(idx_dt)

    return df_datetime


def read_suews(path_suews_file: str) -> pd.DataFrame:
    """read in SUEWS input/output file as datetime-aware DataFrame.

    Parameters
    ----------
    path_suews_file : str
        a string that can be converted into a valid path to SUEWS file.

    Returns
    -------
    pd.DataFrame
        datetime-aware DataFrame
    """

    path_suews_file = Path(path_suews_file).resolve()
    df_raw = pd.read_csv(
        path_suews_file,
        delim_whitespace=True,
        comment='!',
        error_bad_lines=True
    )
    df_suews = parse_suews_datetime(df_raw)
    return df_suews


def read_forcing(filename_pattern: str) -> pd.DataFrame:
    """read in SUEWS forcing files as DataFrame ready for SuPy simulation.

    Parameters
    ----------
    path_suews_file : str
        a string that represents wildcard pattern can locate SUEWS forcing files, which should follow `SUEWS convention <https://suews-docs.readthedocs.io/en/latest/input_files/met_input.html>`_.

    Returns
    -------
    pd.DataFrame
        datetime-aware DataFrame
    """

    path_suews_file = Path(filename_pattern)
    path_input = path_suews_file.parent
    str_pattern = path_suews_file.name

    df_forcing = load_SUEWS_Forcing_met_df_pattern(path_input, str_pattern)
    df_forcing = df_forcing.replace(-999, np.nan)

    return df_forcing


