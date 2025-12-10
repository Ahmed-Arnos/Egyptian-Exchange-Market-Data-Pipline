{{ config(materialized='view') }}

WITH raw AS (
    SELECT
        raw:"symbol"::string AS symbol,
        raw:"company_name"::string AS company_name,
        raw:"currency"::string AS currency,
        raw:"sector"::string AS sector,
        raw:"industry"::string AS industry,
        raw:"ceo_name"::string AS ceo_name,
        raw:"website"::string AS website,
        raw:"headquarters"::string AS headquarters,
        raw:"founded_date"::string AS founded_date,
        raw:"isin"::string AS isin,
        file_name,
        load_ts
    FROM {{ source('bronze', 'COMPANIES_RAW') }}
)

SELECT * FROM raw