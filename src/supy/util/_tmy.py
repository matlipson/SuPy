from typing import Tuple
import pandas as pd
import numpy as np
import atmosp

from pathlib import Path

#################################################################
# generate TMY dataframe from supy results
# weight class to determine constants for TMY generation
class _const:
    class ConstError(TypeError):
        pass

    class ConstCaseError(ConstError):
        pass

    def __setattr__(self, name, value):
        if name in self.__dict__:
            raise self.ConstError("can't change const %s" % name)
        if not name.isupper():
            raise self.ConstCaseError(
                'const name "%s" is not all uppercase' % name)
        self.__dict__[name] = value


const = _const()

const.T_MEAN = (2 / 24)
const.T_MAX = (1 / 24)
const.T_MIN = (1 / 24)
const.T_RANGE = 0  # todo
const.RH_MEAN = 2 / 24
const.RH_MAX = 1 / 24
const.RH_MIN = 1 / 24
const.RH_RANGE = 0  # todo
const.WIND_MEAN = 2 / 24
const.WIND_MAX = 2 / 24
const.WIND_MIN = 0
const.WIND_RANGE = 0  # todo
const.WIND_DIRECTION = 0  # todo
const.SOLAR_RADIATION_GLOBAL = 12 / 24
const.SOLAR_RADIATION_DIRECT = 0  # todo


def gen_score_list(length):
    list_score = (np.arange(length) + 0.5) / length
    return list_score


def gen_score_ser(ser_test):
    ser_score = ser_test.sort_values(ascending=True)
    length = ser_score.size
    list_score = (np.arange(length) + 0.5) / length
    ser_score.loc[:] = list_score
    # ser_score.loc[:] = gen_score_list(ser_score.size)
    return ser_score


def gen_FS_DF(df_output):
    """generate DataFrame of scores.

    Parameters
    ----------
    df_WS_data : type
        Description of parameter `df_WS_data`.

    Returns
    -------
    type
        Description of returned object.

    """
    df_day = pd.pivot_table(
        df_output,
        values=['T2', 'U10', 'Kdown', 'RH2'],
        index=['Year', 'Month', 'Day'],
        aggfunc=[min, max, np.mean, ])
    df_day_all_year = pd.pivot_table(
        df_output,
        values=['T2', 'U10', 'Kdown', 'RH2'],
        index=['Month', 'Day'],
        aggfunc=[min, max, np.mean, ])

    array_yr_mon = df_day.index.droplevel(
        'Day').to_frame().drop_duplicates().values

    df_fs = pd.DataFrame(
        {(yr, mon):
         (df_day.loc[(yr, mon)].apply(gen_score_ser) -
          df_day_all_year.loc[mon].apply(gen_score_ser)).abs().mean()
         for yr, mon in array_yr_mon})

    return df_fs


def gen_WS_DF(df_WS_data):
    """generate DataFrame of weighted sums.

    Parameters
    ----------
    df_WS_data : type
        Description of parameter `df_WS_data`.

    Returns
    -------
    type
        Description of returned object.

    """
    df_fs = gen_FS_DF(df_WS_data)

    list_index = [('mean', 'T2'), ('max', 'T2'), ('min', 'T2'),
                  ('mean', 'U10'), ('max', 'U10'), ('min', 'U10'),
                  ('mean', 'RH2'), ('max', 'RH2'), ('min', 'RH2'),
                  ('mean', 'Kdown')]

    list_const = [getattr(const, attr)
                  for attr in ['T_MEAN', 'T_MAX', 'T_MIN',
                               'WIND_MEAN', 'WIND_MAX', 'WIND_MIN',
                               'RH_MEAN', 'RH_MAX', 'RH_MIN',
                               'SOLAR_RADIATION_GLOBAL']]
    list_ws = [df_fs.loc[idx] * cst
               for idx, cst
               in zip(list_index, list_const)]
    df_ws = pd.concat(list_ws, axis=1).sum(axis=1).unstack().dropna()

    return df_ws


# def gen_WS_DF(df_WS_data):
#     """generate DataFrame of weighted sums.

#     Parameters
#     ----------
#     df_WS_data : type
#         Description of parameter `df_WS_data`.

#     Returns
#     -------
#     type
#         Description of returned object.

#     """
#     df_fs = gen_FS_DF(df_WS_data)

#     list_index = [('mean', 'T2'), ('max', 'T2'), ('min', 'T2'),
#                   ('mean', 'U10'), ('max', 'U10'), ('min', 'U10'),
#                   ('mean', 'RH2'), ('max', 'RH2'), ('min', 'RH2'),
#                   ('mean', 'Kdown')]

#     list_const = [getattr(const, attr)
#                   for attr in ['T_MEAN', 'T_MAX', 'T_MIN',
#                                'WIND_MEAN', 'WIND_MAX', 'WIND_MIN',
#                                'RH_MEAN', 'RH_MAX', 'RH_MIN',
#                                'SOLAR_RADIATION_GLOBAL']]
#     list_ws = [df_fs.loc[idx] * cst for idx,
#                cst in zip(list_index, list_const)]
#     df_ws = pd.concat(list_ws, axis=1).sum(axis=1).unstack().dropna()

#     return df_ws


def pick_year(df_ws, df_output, n=5):
    df_day = pd.pivot_table(
        df_output, values='Kdown',
        index=['Year', 'Month', 'Day'],
        aggfunc=[np.mean, ])

    df_day_all_year = pd.pivot_table(
        df_output, values='Kdown',
        index=['Month', 'Day'],
        aggfunc=[np.mean, ])

    array_yr_mon = df_day.index.droplevel(
        'Day').to_frame().drop_duplicates().values

    df_rmsd = pd.DataFrame(
        {(yr, mon):
         np.sqrt(
         np.square(
             df_day.loc[(yr, mon)] - df_day_all_year.loc[mon]).mean())
         for yr, mon in array_yr_mon}).stack().T.dropna()
    df_rmsd.columns = df_rmsd.columns.droplevel([0, 1])

    year_nsmallest = df_ws.apply(lambda ser: ser.nsmallest(n).index)

    year_sel = df_rmsd.apply(
        lambda ser: ser.loc[year_nsmallest[ser.name]]).idxmin()

    return year_sel


# headers of standard EPW files
header_EPW = '''
Year
Month
Day
Hour
Minute
Data Source and Uncertainty Flags
Dry Bulb Temperature
Dew Point Temperature
Relative Humidity
Atmospheric Station Pressure
Extraterrestrial Horizontal Radiation
Extraterrestrial Direct Normal Radiation
Horizontal Infrared Radiation Intensity
Global Horizontal Radiation
Direct Normal Radiation
Diffuse Horizontal Radiation
Global Horizontal Illuminance
Direct Normal Illuminance
Diffuse Horizontal Illuminance
Zenith Luminance
Wind Direction
Wind Speed
Total Sky Cover
Opaque Sky Cover
Visibility
Ceiling Height
Present Weather Observation
Present Weather Codes
Precipitable Water
Aerosol Optical Depth
Snow Depth
Days Since Last Snowfall
Albedo
Liquid Precipitation Depth
Liquid Precipitation Quantity
    '''

# list of variables in EPW
list_var_EPW = header_EPW.split('\n')[1:-1]

# dict: SuPy variables -> EPW standard names
dict_supy_epw = {
    'Kdown': 'Global Horizontal Radiation',
    'T2': 'Dry Bulb Temperature',
    'RH2': 'Relative Humidity',
    'U10': 'Wind Speed',

}
dict_epw_supy = {v: k for k, v in dict_supy_epw.items()}


def gen_TMY(df_output):
    '''generate TMY (typical meteorological year) from SuPy output.

    Parameters
    ----------
    df_output : pandas.DataFrame
        Output from `run_supy`: longterm (e.g., >10 years) simulation results, otherwise not very useful.

    '''

    # calculate weighted score
    ws = gen_WS_DF(df_output)

    # select year
    year_sel = pick_year(ws, df_output, n=5)

    # generate TMY data
    df_TMY = pd.concat(
        # shift(1) here is to conform the convention that
        # timestamps refer to the preceding period
        # [df_output.shift(1).groupby(['Month', 'Year']).get_group(grp)
        # shift(1) is not necessary
        [df_output.groupby(['Month', 'Year']).get_group(grp)
         for grp in year_sel.items()])

    # df_TMY = df_TMY.rename(columns=dict_supy_epw)

    return df_TMY


# function to read in EPW file
def read_epw(path_epw:Path)->pd.DataFrame:
    """Read in `epw` file as a DataFrame

    Parameters
    ----------
    path_epw : Path
        path to `epw` file

    Returns
    -------
    df_tmy: pd.DataFrame
        TMY results of `epw` file
    """
    df_tmy = pd.read_csv(path_epw, skiprows=8, sep=u',', header=None)
    df_tmy.columns = [x.strip() for x in header_EPW.split('\n')[1:-1]]
    df_tmy['DateTime'] = pd.to_datetime(
        pd.to_datetime(
            df_tmy['Year']*10000+df_tmy['Month']*100+df_tmy['Day'],
            format='%Y%m%d')+pd.to_timedelta(df_tmy['Hour'], unit='h'))
    df_tmy = df_tmy.set_index('DateTime')
    return df_tmy


# generate EPW file from `df_TMY`
def gen_epw(df_tmy: pd.DataFrame, path_epw=Path('./uTMY.epw'), ratio_dif_dir=0.15) -> Tuple[pd.DataFrame, str, Path]:
    """Generate an `epw` file of uTMY (urbanised Typical Meteorological Year) using SUEWS simulation results

    Parameters
    ----------
    df_tmy : pd.DataFrame
        SUEWS simulation results.
    path_epw : Path, optional
        Path to store generated epw file, by default Path('./uTMY.epw')
    ratio_dif_dir : float, optional
        Ratio between direct and diffuse solar radiation, by default 0.15

    Returns
    -------
    df_epw, text_meta, path_epw: Tuple[pd.DataFrame, str, Path]
        - df_epw: uTMY result
        - text_meta: meta-info text
        - path_epw: path to generated `epw` file

    """
    df_tmy = df_tmy.copy()
    # df_tmy = pd.concat([df_tmy.iloc[1:], df_tmy.iloc[[0]]])
    # adding necessary variables that can be derive from supy output
    df_tmy['Dew Point Temperature'] = atmosp.calculate(
        "Td",
        T=df_tmy['T2'].values + 273.15,
        qv=(df_tmy['Q2'].values), qv_unit='g/kg',
        RH=df_tmy['RH2'].values,
        rho=1.23)-273.15
    df_tmy['Atmospheric Station Pressure'] = atmosp.calculate(
        "p",
        T=df_tmy['T2'].values + 273.15,
        qv=(df_tmy['Q2'].values), qv_unit='g/kg',
        RH=df_tmy['RH2'].values,
        rho=1.23)-273.15
    # index = df_TMY.index
    # df_TMY = df_TMY.iloc[1:].append(df_TMY.ix[0])
    # df_TMY.index = index
    df_tmy['Year'] = df_tmy.index.year
    df_tmy['Month'] = df_tmy.index.month
    df_tmy['Day'] = df_tmy.index.day
    df_tmy['Hour'] = df_tmy.index.hour
    df_tmy['Minute'] = df_tmy.index.minute

    # convert air pressure to Pa
    # df_tmy['Atmospheric Station Pressure'] *= 1000

    # df_TMY['Kdown'] = df_TMY['Kdown']*2.4
    # processing solar radiation components
    df_tmy.loc[df_tmy['Kdown'] < 0.001, 'Kdown'] = 0
    # direct beam
    frac_dir = (1/(1+ratio_dif_dir))
    df_tmy['Direct Normal Radiation'] = df_tmy['Kdown'] * frac_dir
    # diffuse radiation
    frac_dif = 1-(1/(1+ratio_dif_dir))
    df_tmy['Diffuse Horizontal Radiation'] = df_tmy['Kdown'] * frac_dif

    # conform column names to EPW standard
    df_TMY_x = df_tmy.rename(columns=dict_supy_epw)

    # initialise df_epw for EPW output
    df_epw = pd.DataFrame(columns=list_var_EPW, index=df_tmy.index)

    # dict of default values
    dict_var_dft = {
        'Data Source and Uncertainty Flags': -9992,
        'Extraterrestrial Horizontal Radiation': 9999,
        'Extraterrestrial Direct Normal Radiation': 9999,
        'Horizontal Infrared Radiation Intensity': 9999,
        'Direct Normal Radiation': 9999,
        'Global Horizontal Illuminance': 9999999,
        'Direct Normal Illuminance': 9999999,
        'Diffuse Horizontal Illuminance': 9999999,
        'Zenith Luminance': 9999,
        'Wind Direction': 999,
        'Total Sky Cover': 99,
        'Opaque Sky Cover': 99,
        'Visibility': 9999,
        'Ceiling Height': 99999,
        'Present Weather Observation': 9999,
        'Present Weather Codes': 9999,
        'Precipitable Water': 999,
        'Aerosol Optical Depth': 999,
        'Snow Depth': 999,
        'Days Since Last Snowfall': 99,
        'Albedo': 999,
        'Liquid Precipitation Depth': 999,
        'Liquid Precipitation Quantity': 999,
    }
    for var in list_var_EPW:
        try:
            df_epw[var] = df_TMY_x[var].values
        except:
            # print(f'{var} not existing! This variable will be filled with default value {dict_var_dft[var]}')
            try:
                df_epw[var] = np.ones(len(df_epw))*dict_var_dft[var]
            except:
                df_epw[var] = np.nan
    # fill 'Data Source and Uncertainty Flags'
    df_epw['Data Source and Uncertainty Flags'] = '?9?9?9?9E0?9?9?9*9*9?9*9*9?9*9*9?9?9*9*_*9*9*9*9*9'
    df_epw['Global Horizontal Radiation'] = np.ones(len(df_epw))*9999
    df_epw.index = df_TMY_x.index

    # convert `0h` to `24h` and take care of `day`
    loc_24h = df_epw.index == df_epw.index.normalize()
    ser_24h = df_epw.loc[loc_24h].index-pd.Timedelta('1h')
    df_epw.loc[loc_24h, 'Year'] = ser_24h.year
    df_epw.loc[loc_24h, 'Month'] = ser_24h.month
    df_epw.loc[loc_24h, 'Day'] = ser_24h.day
    df_epw.loc[loc_24h, 'Hour'] = 24

    df_epw = df_epw.sort_values(['Month', 'Day', 'Hour'], axis=0)

    # save pure data to a csv for formatting
    df_epw.to_csv(path_epw, index=None, header=None)
    text_data = path_epw.read_text().split('\n')
    # delete the csv file
    path_epw.unlink()

    text_meta = '''
LOCATION,Chongqing Shapingba,Chongqing,CHN,CSWD,575160,29.58,106.47,8,259.1
DESIGN CONDITIONS,1,Climate Design Data 2009 ASHRAE Handbook,,Heating,1,3.2,4.2,-0.2,3.8,6.5,1.3,4.3,6.2,4.9,7.6,4.3,7.5,1.4,0,Cooling,7,7.4,36.9,25.6,35.5,25.6,34.2,25.4,27.4,32.7,26.9,32.2,26.4,31.6,2.5,110,26.1,22.2,30.2,25.6,21.5,29.8,25.1,20.8,29.3,89.3,32.7,86.9,32.5,84.7,31.7,909,Extremes,5.1,4.3,3.6,35.4,1.1,38.8,1.3,1.6,0.1,40,-0.6,40.9,-1.4,41.8,-2.3,43
TYPICAL/EXTREME PERIODS,6,Summer - Week Nearest Max Temperature For Period,Extreme,7/27,8/ 2,Summer - Week Nearest Average Temperature For Period,Typical,7/ 6,7/12,Winter - Week Nearest Min Temperature For Period,Extreme,12/22,1/ 5,Winter - Week Nearest Average Temperature For Period,Typical,1/13,1/19,Autumn - Week Nearest Average Temperature For Period,Typical,10/13,10/19,Spring - Week Nearest Average Temperature For Period,Typical,4/12,4/18
GROUND TEMPERATURES,3,.5,,,,13.31,10.23,9.39,10.12,14.28,18.95,23.34,26.51,27.44,25.95,22.35,17.82,2,,,,16.09,13.20,11.82,11.77,13.97,17.16,20.59,23.54,25.06,24.77,22.74,19.63,4,,,,17.90,15.65,14.27,13.85,14.66,16.52,18.83,21.09,22.62,22.98,22.11,20.29
HOLIDAYS/DAYLIGHT SAVINGS,No,0,0,0
COMMENTS 1,  generated by SUEWS model
COMMENTS 2, todo
DATA PERIODS,1,1,Data,Sunday, 1/ 1,12/31
    '''
    text_meta = text_meta.split('\n')[1:-1]
    # lines = []
    text_epw = '\n'.join(text_meta+text_data)
    # with open(path_epw, 'r') as f:
    #     for line in f:
    #         lines.append(line)
    #     lines.insert(0, text_meta[1:])
    #     s = ''.join(lines)

    # write out the actual EPW file
    with open(path_epw, 'w') as fp:
        fp.write(text_epw)

    return df_epw, text_meta, path_epw
