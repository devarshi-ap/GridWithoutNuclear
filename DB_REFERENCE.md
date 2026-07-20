# ieso_grid — Database Reference

ieso_grid
├── raw/                          ← untransformed data, exactly as ingested from IESO
│   ├── generation                  hourly MW output per fuel type
│   │   ├── datetime TIMESTAMP      2015-01-01 00:00:00
│   │   ├── nuclear_mw INTEGER      11564
│   │   ├── gas_mw INTEGER          957
│   │   ├── hydro_mw INTEGER        3173
│   │   ├── wind_mw INTEGER         2504
│   │   ├── solar_mw INTEGER        0
│   │   ├── biofuel_mw INTEGER      20
│   │   ├── source_year SMALLINT    2015
│   │   └── loaded_at TIMESTAMP     2026-07-07 15:00:00
│   │
│   ├── demand                      hourly Ontario electricity consumption
│   │   ├── datetime TIMESTAMP      2015-01-01 00:00:00
│   │   ├── ontario_demand_mw INT   14960
│   │   ├── market_demand_mw INT    18358
│   │   ├── source_year SMALLINT    2015
│   │   └── loaded_at TIMESTAMP     2026-07-07 15:00:00
│   │
│   └── price                       hourly HOEP electricity price
│       ├── datetime TIMESTAMP      2015-01-01 00:00:00
│       ├── hoep NUMERIC(10,4)      3.2800
│       ├── source_year SMALLINT    2015
│       └── loaded_at TIMESTAMP     2026-07-07 15:00:00
│
├── staging/                      ← dbt seed files (reference/lookup data)
│   ├── hydro_seasonal_capacity     95th percentile hydro output by month
│   │   ├── month INTEGER           1
│   │   ├── month_name VARCHAR      January
│   │   └── hydro_seasonal_max_mw   5714
│   │
│   └── fuel_co2_factors            CO2 emission intensity per fuel type
│       ├── fuel VARCHAR            NUCLEAR
│       ├── co2_factor_gco2_per_kwh 12
│       ├── is_nuclear BOOLEAN      true
│       ├── is_renewable BOOLEAN    false
│       └── included_in_cf BOOLEAN  false
│
├── staging_staging/              ← dbt staging views (cleaned raw data, no logic)
│   ├── stg_generation              cleaned view of raw.generation + total_mw
│   │   ├── datetime TIMESTAMP      2015-01-01 00:00:00
│   │   ├── nuclear_mw INTEGER      11564
│   │   ├── gas_mw INTEGER          957
│   │   ├── hydro_mw INTEGER        3173
│   │   ├── wind_mw INTEGER         2504
│   │   ├── solar_mw INTEGER        0
│   │   ├── biofuel_mw INTEGER      20
│   │   └── total_mw INTEGER        18218
│   │
│   ├── stg_demand                  cleaned view of raw.demand
│   │   ├── datetime TIMESTAMP      2015-01-01 00:00:00
│   │   ├── ontario_demand_mw INT   14960
│   │   └── market_demand_mw INT    18358
│   │
│   └── stg_price                   cleaned view of raw.price (nulls filtered)
│       ├── datetime TIMESTAMP      2015-01-01 00:00:00
│       └── hoep NUMERIC            3.2800
│
├── staging_marts/                ← dbt mart tables (final analysis-ready tables)
│   ├── fact_grid_demand            one row per hour: generation + demand + price joined
│   │   ├── datetime TIMESTAMP      2015-01-01 00:00:00
│   │   ├── nuclear_mw INTEGER      11564
│   │   ├── gas_mw INTEGER          957
│   │   ├── hydro_mw INTEGER        3173
│   │   ├── wind_mw INTEGER         2504
│   │   ├── solar_mw INTEGER        0
│   │   ├── biofuel_mw INTEGER      20
│   │   ├── total_mw INTEGER        18218
│   │   ├── ontario_demand_mw INT   14960
│   │   └── hoep NUMERIC            3.2800
│   │
│   └── fact_counterfactual         one row per hour: merit order model + all calculations
│       ├── datetime TIMESTAMP      2015-01-01 00:00:00
│       ├── nuclear_mw INTEGER      11564       actual nuclear output
│       ├── gas_mw INTEGER          957         actual gas output
│       ├── hydro_mw INTEGER        3173        actual hydro output
│       ├── total_mw INTEGER        18218       total actual generation
│       ├── ontario_demand_mw INT   14960       actual demand
│       ├── actual_price NUMERIC    3.2800      actual HOEP $/MWh
│       ├── nuclear_gap_mw INT      11564       hole to fill if nuclear = 0
│       ├── hydro_headroom_mw INT   1586        how much more hydro could produce
│       ├── hydro_fill_mw INT       1586        how much hydro fills the gap
│       ├── gas_fill_mw INT         9978        how much gas fills the remainder
│       ├── import_fill_mw INT      0           how much imports cover the rest
│       ├── counterfactual_price    60.8300     price if nuclear was offline $/MWh
│       ├── counterfactual_price_low  48.2100   low scenario ($70/MWh gas)
│       ├── counterfactual_price_high 73.4500   high scenario ($120/MWh gas)
│       ├── price_delta NUMERIC     57.5500     counterfactual - actual $/MWh
│       ├── cost_delta_dollars      861430.00   extra $ consumers would pay that hour
│       ├── co2_avoided_kg          4751240     kg of CO2 nuclear avoided vs gas
│       └── co2_avoided_tonnes      4751.24     same in tonnes (cleaner for dashboards)
│
└── marts/                        ← empty (dbt schema naming artifact, ignore)


QUICK REFERENCE
───────────────
Total rows:         96,432 (one per hour, 2015–2025)
Date range:         2015-01-01 00:00:00 → 2025-12-31 23:00:00
Price coverage:     2015-01-01 → 2025-04-30 (HOEP era only)
Primary table:      staging_marts.fact_counterfactual