import pandas as pd


def load_year(path):
    """Load one Swissgrid yearly file and return end-user load as a series.

    Parameters
    ----------
    path : str
        Path to an EnergieUebersichtCH-YYYY.xlsx file.

    Returns
    -------
    pandas.Series
        Energy consumed by end users in the Swiss control block, in kWh per
        15 minutes, indexed by UTC timestamps marking the end of each interval.
    """
    # row 2 of the sheet contains units (kWh), not data
    df = pd.read_excel(path, sheet_name="Zeitreihen0h15", skiprows=[1], usecols="A:B")
    df.columns = ["timestamps", "load"]
    # explicit format: timestamps are day first (dd.mm.yyyy)
    df["timestamps"] = pd.to_datetime(df["timestamps"], format="%d.%m.%Y %H:%M")

    # the labels around the October DST change differ between years, so instead
    # of localizing every label we build the UTC grid from the first and last
    # timestamps, which are unambiguous (winter time)
    start = df["timestamps"].iloc[0].tz_localize("Europe/Zurich").tz_convert("UTC")
    end = df["timestamps"].iloc[-1].tz_localize("Europe/Zurich").tz_convert("UTC")
    index = pd.date_range(start=start, end=end, freq="15min")

    # guard: the number of rows must match the length of the grid
    if len(index) != len(df):
        raise ValueError(f"{path}: expected {len(index)} rows, found {len(df)}")

    # from 2025 on, Swissgrid labels each interval by its start instead of its
    # end; detect this from the first timestamp (00:00 instead of 00:15) and
    # shift to the end-of-interval convention used throughout the project
    first = df["timestamps"].iloc[0]
    if first.hour == 0 and first.minute == 0:
        index = index + pd.Timedelta(minutes=15)

    return pd.Series(df["load"].to_numpy(), index=index, name="load")