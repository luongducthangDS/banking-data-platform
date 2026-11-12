{# Use the custom schema name as-is (staging, core, marts) instead of dbt's <target>_<custom>. #}
{% macro generate_schema_name(custom_schema_name, node) -%}
  {{ custom_schema_name if custom_schema_name else target.schema }}
{%- endmacro %}

{# Grant USAGE only on schemas that exist, so partial runs (--select staging) do not fail. #}
{% macro grant_schema_usage(schemas, role) -%}
DO $$
DECLARE s text;
BEGIN
  FOREACH s IN ARRAY ARRAY[{% for s in schemas %}'{{ s }}'{% if not loop.last %},{% endif %}{% endfor %}] LOOP
    IF EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = s) THEN
      EXECUTE format('GRANT USAGE ON SCHEMA %I TO {{ role }}', s);
    END IF;
  END LOOP;
END $$;
{%- endmacro %}

{# Parse Berka YYMMDD (all dates are 19xx). #}
{% macro yymmdd(col) -%}
  to_date('19' || left({{ col }}, 6), 'YYYYMMDD')
{%- endmacro %}

{# Source strings: '' and ' ' both mean missing. #}
{% macro blank_null(col) -%}
  nullif(trim({{ col }}), '')
{%- endmacro %}
