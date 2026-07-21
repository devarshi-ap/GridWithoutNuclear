WITH base AS (
  SELECT
    *
  FROM
    { { ref('fact_grid_demand') } }
)
, hydro_caps AS (
  SELECT
    month
    , hydro_seasonal_max_mw
  FROM
    { { ref('hydro_seasonal_capacity') } }
)
, filled AS (
  SELECT
    b.datetime
    , b.nuclear_mw
    , b.gas_mw
    , b.hydro_mw
    , b.wind_mw
    , b.solar_mw
    , b.biofuel_mw
    , b.total_mw
    , b.ontario_demand_mw
    , b.hoep
    , -- Nuclear gap is everything nuclear produced
      b.nuclear_mw AS nuclear_gap_mw
    , -- Hydro headroom: seasonal max minus what hydro actually produced
      GREATEST(h.hydro_seasonal_max_mw - b.hydro_mw, 0) AS hydro_headroom_mw
    , -- Hydro fills as much of the gap as its headroom allows
      LEAST(
      b.nuclear_mw
      , GREATEST(h.hydro_seasonal_max_mw - b.hydro_mw, 0)
    ) AS hydro_fill_mw
    , -- Gas fills whatever hydro couldn't
      LEAST(
      GREATEST(
        b.nuclear_mw - GREATEST(h.hydro_seasonal_max_mw - b.hydro_mw, 0)
        , 0
      )
      , GREATEST(10500 - b.gas_mw, 0)
    ) AS gas_fill_mw
    , -- Imports cover anything gas couldn't handle
      GREATEST(
      b.nuclear_mw - GREATEST(h.hydro_seasonal_max_mw - b.hydro_mw, 0) - LEAST(
        GREATEST(
          b.nuclear_mw - GREATEST(h.hydro_seasonal_max_mw - b.hydro_mw, 0)
          , 0
        )
        , GREATEST(10500 - b.gas_mw, 0)
      )
      , 0
    ) AS import_fill_mw
  FROM
    base b
    LEFT JOIN hydro_caps h
  ON EXTRACT(
    MONTH
    FROM
      b.datetime
  ) = h.month
)
SELECT
  datetime
  , nuclear_mw
  , gas_mw
  , hydro_mw
  , wind_mw
  , solar_mw
  , biofuel_mw
  , total_mw
  , ontario_demand_mw
  , hoep AS actual_price
  , -- Fill breakdown
    nuclear_gap_mw
  , hydro_headroom_mw
  , hydro_fill_mw
  , gas_fill_mw
  , import_fill_mw
  , -- Counterfactual price (base scenario: gas marginal cost = $95/MWh)
    ROUND(
    (
      hoep + (gas_fill_mw: :numeric / NULLIF(ontario_demand_mw, 0)) * (95 - hoep)
    ): :numeric
    , 4
  ) AS counterfactual_price
  , -- Counterfactual price low scenario ($70/MWh gas)
    ROUND(
    (
      hoep + (gas_fill_mw: :numeric / NULLIF(ontario_demand_mw, 0)) * (70 - hoep)
    ): :numeric
    , 4
  ) AS counterfactual_price_low
  , -- Counterfactual price high scenario ($120/MWh gas)
    ROUND(
    (
      hoep + (gas_fill_mw: :numeric / NULLIF(ontario_demand_mw, 0)) * (120 - hoep)
    ): :numeric
    , 4
  ) AS counterfactual_price_high
  , -- Price delta (base)
    ROUND(
    (
      (gas_fill_mw: :numeric / NULLIF(ontario_demand_mw, 0)) * (95 - hoep)
    ): :numeric
    , 4
  ) AS price_delta
  , -- Cost delta per hour in dollars (base)
    ROUND(
    (
      (gas_fill_mw: :numeric / NULLIF(ontario_demand_mw, 0)) * (95 - hoep) * ontario_demand_mw
    ): :numeric
    , 2
  ) AS cost_delta_dollars
  , -- CO2 avoided in kg
    ROUND((gas_fill_mw * 1000 * 0.490) - (nuclear_mw * 1000 * 0.012)) AS co2_avoided_kg
  , -- CO2 avoided in tonnes (cleaner for dashboards)
    ROUND(
    ((gas_fill_mw * 1000 * 0.490) - (nuclear_mw * 1000 * 0.012)) / 1000.0
    , 2
  ) AS co2_avoided_tonnes
FROM
  filled