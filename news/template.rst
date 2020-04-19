Released on {{versiondata.date}}

{% for section, _ in sections.items() %}
{% set underline = underlines[0] %}{% if section %}{{section}}
{{ underline * section|length }}{% set underline = underlines[1] %}
{% endif %}
{% if sections[section] %}
{% for category, val in definitions.items() if category in sections[section]%}
**{{ definitions[category]['name'] }}**

{% if definitions[category]['showcontent'] %}
{% for text, values in sections[section][category].items() %}
- {{ text }}
  {% if category == 'bugfix' %} ({{ values|sort|join(', ') }}){% endif %}
 
{% endfor %}
{% else %}
- {{ sections[section][category]['']|join(', ') }}
{% endif %}
{% if sections[section][category]|length == 0 %}
No significant changes.
{% endif %}

{% endfor %}
{% else %}
No significant changes.
{% endif %}
{% endfor %}

