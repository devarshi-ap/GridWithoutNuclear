SELECT
  datetime
  , nuclear_mw
  , gas_mw
  , hydro_mw
  , wind_mw
  , solar_mw
  , biofuel_mw
  , (
    nuclear_mw + gas_mw + hydro_mw + wind_mw + solar_mw + biofuel_mw
  ) AS total_mw
FROM
  raw.generation