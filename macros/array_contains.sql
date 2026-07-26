-- macros/array_contains.sql
{% macro array_contains(array_expression, value) %}
    {{ value }} in unnest({{ array_expression }})
{% endmacro %}