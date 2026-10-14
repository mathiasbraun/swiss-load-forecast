# Swiss Load Forecasting

Forecasting Swiss electricity consumption 24 hours ahead.

## Goal

Predict the Swiss electricity load for each hour of the following day, using only
information that is available at forecast time.

## Data

- Swiss electricity consumption at 15-minute resolution, published by Swissgrid.
- Historical weather data (temperature) from MeteoSwiss or Open-Meteo.

## Planned approach

1. Baselines: same hour one week earlier, and the average of the same hour over the
   previous weeks.
2. Linear models with calendar, holiday, temperature and lagged load features,
   with Ridge and Lasso regularization.
3. Gradient boosting (LightGBM).
4. A small neural network in PyTorch.

## Evaluation principles

- Strictly chronological splits. Hyperparameters are chosen by rolling-origin
  (walk-forward) validation, and the test period is used once.
- Features only use information available at the time of the forecast.
- Every model is compared against the baselines.
- Error estimates come with uncertainty (bootstrap over days), so that differences
  between models can be judged.
- Errors are analysed by conditions known in advance, such as season, weekday,
  holidays and temperature.

## Status

Work in progress.