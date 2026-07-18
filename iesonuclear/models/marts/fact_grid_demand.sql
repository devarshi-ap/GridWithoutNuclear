SELECT
  g.datetime
  , g.nuclear_mw
  , g.gas_mw
  , g.hydro_mw
  , g.wind_mw
  , g.solar_mw
  , g.biofuel_mw
  , g.total_mw
  , d.ontario_demand_mw
  , p.hoep
FROM
  {{ ref('stg_generation') }} g
  LEFT JOIN {{ ref('stg_demand') }} d
ON g.datetime = d.datetime
LEFT JOIN {{ ref('stg_price') }} p
ON g.datetime = p.datetime