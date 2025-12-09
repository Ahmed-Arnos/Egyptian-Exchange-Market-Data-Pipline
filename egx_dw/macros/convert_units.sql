{% macro convert_units(col) %}
    CASE
        WHEN {{ col }} ILIKE '%B' THEN 
            TRY_TO_NUMBER(REPLACE({{ col }}, 'B', '')) * 1e9
        WHEN {{ col }} ILIKE '%M' THEN 
            TRY_TO_NUMBER(REPLACE({{ col }}, 'M', '')) * 1e6
        WHEN {{ col }} ILIKE '%K' THEN 
            TRY_TO_NUMBER(REPLACE({{ col }}, 'K', '')) * 1e3
        ELSE 
            TRY_TO_NUMBER(REGEXP_REPLACE({{ col }}, '[^0-9\.-]', ''))
    END
{% endmacro %}