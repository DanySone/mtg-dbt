-- macros/is_legal.sql
{% macro is_legal(column_name) %}
    case
        when {{ column_name }} = 'legal' then true
        else false
    end
{% endmacro %}