# Swiss Load Forecasting

Forecasting Swiss electricity consumption 24 hours ahead.

## Goal

Predict the Swiss electricity load for each **hour** of the following day, using only information that is available at forecast time.

## Data

- Target: total energy consumed by end users in the Swiss control block, at 15-minute
  resolution (kWh), from the yearly "Energy Overview" files published by Swissgrid.
  End-user consumption excludes pumped-storage pumping, power plant own consumption
  and grid losses, which depend on market and plant operation rather than on demand.
- Years 2020–2025. The raw files use Swiss local time; see the data quirks below and the design decisions for how timestamps are handled.
- Public holidays per canton from the Python package `holidays`.
- Temperature: day-ahead forecasts from the Open-Meteo Previous Runs API (model GFS, variable
  `temperature_2m_previous_day1`, i.e. the forecast issued 24 hours earlier) for the eight largest
  Swiss agglomerations, April 2021 to 2025. Archived forecasts are not available before April 2021.

**Forecast archive gap.** For 30 December 2023 00:00 to 19 January 2024 11:00 UTC (492 hours), the archive
contains no day-ahead or two-day-ahead forecasts for any location or model (GFS, ICON, ECMWF). These hours are
*excluded* (see `notebooks/04_temperature.ipynb`).

**Data quirks handled in `src/data.py`.**
- Labels around the October DST change differ between years; the UTC time grid is
  therefore built from the first and last timestamp of each file, with a row-count check.
- From 2025 on, Swissgrid labels intervals by their start instead of their end; this is
  detected and converted to end-of-interval labels.

The data is not included in this repository. See the Swissgrid page "energy data ch" for the source files.

## Approach

1. Data loading and cleaning (2020–2025): unified UTC time grid without gaps, duplicates or daylight saving shifts, consistent interval labels, sanity checks. ✅
2. Baselines: same hour one week earlier, and the mean of the same hour over the previous four weeks. ✅
3. Linear models with calendar, holiday, temperature and lagged load features, with Ridge and Lasso regularization. *In progress: calendar, holiday and lag features done; temperature forecasts loaded and aggregated (`notebooks/04_temperature.ipynb`); model with temperature and regularization to follow.*
4. Gradient boosting (LightGBM).
5. A small neural network in PyTorch.
6. Final evaluation of the selected models on the test year 2025 (used once), with bootstrap uncertainty and error analysis; a script that reproduces all results.

## Evaluation principles

- Strictly chronological split: **training** 2020–2023, **validation** 2024, **test** 2025. A random split would place test hours next to training hours of the same day, so the model would only interpolate and the error would be too optimistic. Hyperparameters will be chosen by rolling-origin (walk-forward) validation, and the test year is used once at the very end.
- Models with temperature are trained from April 2021, when archived forecasts begin. For a fair comparison, the model without temperature is retrained and evaluated on exactly the same hours.
- Features only use information available at the time of the forecast.
- Every model is compared against the baselines.
- Error estimates come with uncertainty (bootstrap over days), so that differences
  between models can be judged.
- Errors are analysed by conditions known in advance, such as season, weekday,
  holidays and temperature.

## Design decisions

### Data

- **UTC time grid.** All computations use UTC, which has no daylight saving gaps or duplicates; local time is used only for plots and for calendar features, since demand follows the wall clock. Trade-off: the grid is built from the first and last timestamp of each file, which assumes the files are complete; this is guarded by a row-count check.
- **End-of-interval labels.** Because the raw files are inconsistent (see data quirks), all timestamps are converted to one convention: each label marks the end of its interval.
- **Hourly resolution.** The quarter-hourly data is aggregated to hourly averages in MW, matching the forecasting goal. Trade-off: variation within the hour is lost, which is acceptable for a day-ahead hourly forecast.

### Evaluation

- **Years in local time.** Each hour is assigned to the Swiss calendar year in which it starts, so that the split follows the years as they are experienced (holidays, seasons).
- **Reference baseline: one week.** The four-week average performs worse (412 vs. 362 MW MAE) because it lags behind seasonal trends; recent information matters more than smoothing out unusual weeks.

### Forecast setting

- **Forecast issued at midnight.** The forecast for day D is made at the end of day D−1, so all load values up to the end of D−1 can be used (same hour on the previous day and one week earlier). Trade-off: operational day-ahead forecasts are often issued around noon of D−1, when only part of the previous day is known.

### Weather

- **Forecasts instead of measurements.** At forecast time (midnight before day D), the actual temperature
  of day D is unknown; only a weather forecast is. Using measured temperatures would leak future information
  and make the validation error too optimistic. Trade-off: training starts in April 2021, when archived
  forecasts begin, so about 15 months of load data are not used by models with temperature.
- **One population-weighted temperature.** Demand follows the temperature where people live, so the
  forecasts of the eight largest agglomerations are averaged with weights proportional to their population
  (Swiss Federal Statistical Office, 2025). The cities are highly correlated (pairwise at least 0.93),
  so eight separate features would be strongly collinear. Each city is represented by a single grid point.
- **Excluding the archive gap.** The 20-day gap cannot be interpolated, filling it with measured temperatures
  would leak, and a climatological average would be an artificial, much weaker feature. Excluding it costs
  48 training hours and 444 validation hours (about 5 % of 2024).

### Linear models

- **Holiday feature as share of cantons.** Most Swiss public holidays are set by the cantons; the share of cantons observing a day (0 to 1) captures that e.g. Easter Monday lowers national demand more than 1 May. Population weighting would be more accurate but needs additional data.
- **Holiday share of the lag days.** Lets the model correct lag values that come from a holiday (the "echo" one week after a holiday seen in the baseline errors).
- **One-hot encoding of hour and weekday.** Each hour and weekday gets its own coefficient instead of a forced linear effect; hour 0 and Monday are reference categories.

## Results

Validation year 2024 (hourly load, 8'784 hours):

| Model | MAE [MW] | MAPE [%] |
|---|---|---|
| Baseline: same hour one week earlier | 362 | 5.84 |
| Baseline: mean of same hour over four weeks | 412 | 6.66 |
| Linear regression (calendar, holidays, load lags) | 274 | 4.55 |

**Baselines.** The one-week baseline is around 5 % on ordinary days; its largest errors occur on public holidays and one week after them. It is the reference that every model must beat (see design decisions and `notebooks/02_baseline.ipynb`).

**Linear regression.** It reduces the error by about 24 % compared with the baseline. The forecast is roughly an even mix of the previous day and the previous week, corrected for holidays (about −900 MW on a holiday in all cantons) and for lags that come from a holiday. The holiday peaks of the baseline are much reduced (e.g. Ascension from 26.5 % to 15.3 % daily MAPE); remaining weak spots are bridge days and ordinary working days after a holiday (see `notebooks/03_linear.ipynb`).

## Limitations

- **Behind-the-meter solar.** Grid data does not include solar power consumed on site; part of the midday dip reflects invisible self-generation rather than lower demand.
- **Single validation year.** All comparisons so far rely on 2024 only; walk-forward validation (planned) will make model selection more robust.
- **Forecast time.** Issuing the forecast at midnight is optimistic compared with operational noon forecasts.
- **Legal holidays only.** Days that are widely work-free without being legal holidays everywhere (e.g. 2 January in Zurich) and bridge days (e.g. the Friday after Ascension) are not captured.
- **Days after holidays.** A single coefficient for "the previous day was a holiday" cannot distinguish quiet days after a holiday (St Stephen's Day) from ordinary working days (the Tuesday after Whit Monday); the latter are underestimated.

## Status

Work in progress.