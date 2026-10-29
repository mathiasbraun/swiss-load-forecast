# Swiss Load Forecasting

Forecasting Swiss electricity consumption 24 hours ahead.

## Goal

Predict the Swiss electricity load for each **hour** of the following day, using only information that is available at forecast time.

## Data

- Target: total energy consumed by end users in the Swiss control block, at 15-minute
  resolution (kWh), from the yearly "Energy Overview" files published by Swissgrid.
  End-user consumption excludes pumped-storage pumping, power plant own consumption
  and grid losses, which depend on market and plant operation rather than on demand.
- Timestamps mark the **start or end** of each 15-minute interval; streamlined in data cleaning.
- Weather data (temperature) from MeteoSwiss or Open-Meteo.

**Data quirks handled in `src/data.py`.**
- Labels around the October DST change differ between years; the UTC time grid is
  therefore built from the first and last timestamp of each file, with a row-count check.
- From 2025 on, Swissgrid labels intervals by their start instead of their end; this is
  detected and converted to end-of-interval labels.

The data is not included in this repository. See the Swissgrid page "energy data ch" for the source files.

## Approach

1. Data loading and cleaning (2020–2025): unified UTC time grid without gaps, duplicates or daylight saving shifts, consistent interval labels, sanity checks. ✅
2. Baselines: same hour one week earlier, and the mean of the same hour over the previous four weeks. ✅
3. Linear models with calendar, holiday, temperature and lagged load features, with Ridge and Lasso regularization.
4. Gradient boosting (LightGBM).
5. A small neural network in PyTorch.

## Evaluation principles

- Strictly chronological split: **training** 2020–2023, **validation** 2024, **test** 2025. A random split would place test hours next to training hours of the same day, so the model would only interpolate and the error would be too optimistic. Hyperparameters will be chosen by rolling-origin (walk-forward) validation, and the test year is used once at the very end.
- Features only use information available at the time of the forecast.
- Every model is compared against the baselines.
- Error estimates come with uncertainty (bootstrap over days), so that differences
  between models can be judged.
- Errors are analysed by conditions known in advance, such as season, weekday,
  holidays and temperature.

## Results

Validation year 2024 (hourly load, 8'784 hours):

| Model | MAE [MW] | MAPE [%] |
|---|---|---|
| Baseline: same hour one week earlier | 362 | 5.84 |
| Baseline: mean of same hour over four weeks | 412 | 6.66 |

The one-week baseline is around 5 % on ordinary days; its largest errors occur on public holidays and one week after them. The four-week baseline damps such single unusual weeks but performs worse overall, since it lags behind seasonal trends. The one-week baseline (more recent data) therefore remains the reference that every model must beat (see `notebooks/02_baseline.ipynb`).

## Status

Work in progress.