{% macro cleanup_old_schemas() %}
  {% set drop_queries = [
    "DROP SCHEMA IF EXISTS EGX_OPERATIONAL_DB.SILVER_silver CASCADE",
    "DROP SCHEMA IF EXISTS EGX_OPERATIONAL_DB.SILVER_gold CASCADE"
  ] %}
  
  {% for query in drop_queries %}
    {% do run_query(query) %}
    {% do log("Executed: " ~ query, info=True) %}
  {% endfor %}
  
  {{ return("Old schemas dropped successfully") }}
{% endmacro %}
