---
applyTo: "website/templates/**/*.html"
---

# Django Template Requirements for OWASP BLT

When creating or editing Django templates for OWASP BLT, follow these guidelines to ensure consistency and maintainability:

## Template Structure

1. **Use Template Inheritance** - Extend base templates to avoid duplication
   ```django
   {% extends "base.html" %}
   
   {% block content %}
     <!-- Your content here -->
   {% endblock %}
   ```

2. **Block Organization** - Common blocks in base templates:
   - `{% block title %}` - Page title
   - `{% block extra_head %}` - Additional CSS/meta tags
   - `{% block content %}` - Main content
   - `{% block extra_js %}` - Additional JavaScript

## Styling Guidelines

1. **Use Tailwind CSS ONLY** - Never add `<style>` tags or inline styles
   - ❌ BAD: `<div style="color: red;">`
   - ❌ BAD: `<style> .class { color: red; } </style>`
   - ✅ GOOD: `<div class="text-red-500">`

2. **Brand Color** - Use `#e74c3c` for BLT red (check Tailwind config)
   ```html
   <button class="bg-red-600 hover:bg-red-700">Click Me</button>
   ```

3. **Responsive Design** - Use Tailwind responsive classes
   ```html
   <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
   ```

## JavaScript Guidelines

1. **NO Inline JavaScript** - Keep JavaScript in separate `.js` files
   - ❌ BAD: `<button onclick="doSomething()">`
   - ✅ GOOD: Load JS file with `{% static %}` and use event listeners

2. **Load Static Files Correctly**
   ```django
   {% load static %}
   <script src="{% static 'js/myfile.js' %}"></script>
   ```

## Django Template Language Best Practices

1. **Load Template Tags** - Load at the top of the template
   ```django
   {% load static %}
   {% load custom_tags %}
   ```

2. **URL Resolution** - Always use `{% url %}` tag
   - ❌ BAD: `<a href="/issues/">`
   - ✅ GOOD: `<a href="{% url 'issue_list' %}">`

3. **Static Files** - Use `{% static %}` tag
   ```django
   <img src="{% static 'images/logo.png' %}" alt="Logo">
   ```

4. **CSRF Protection** - Include in all forms
   ```django
   <form method="post">
     {% csrf_token %}
     <!-- Form fields -->
   </form>
   ```

5. **Template Variables** - Use safe filters appropriately
   ```django
   {{ user.username }}  <!-- Auto-escaped -->
   {{ content|safe }}   <!-- Only if content is trusted HTML -->
   ```

## Form Rendering

1. **Use Django Form Helpers**
   ```django
   <form method="post">
     {% csrf_token %}
     {{ form.as_p }}  <!-- or form.as_table, form.as_ul -->
     <button type="submit">Submit</button>
   </form>
   ```

2. **Manual Form Rendering** - For custom styling
   ```django
   <form method="post">
     {% csrf_token %}
     {% for field in form %}
       <div class="mb-4">
         {{ field.label_tag }}
         {{ field }}
         {% if field.errors %}
           <p class="text-red-500">{{ field.errors }}</p>
         {% endif %}
       </div>
     {% endfor %}
   </form>
   ```

## Conditional Rendering

1. **Use if/else Appropriately**
   ```django
   {% if user.is_authenticated %}
     <p>Welcome, {{ user.username }}!</p>
   {% else %}
     <a href="{% url 'login' %}">Login</a>
   {% endif %}
   ```

2. **Empty Checks**
   ```django
   {% if items %}
     {% for item in items %}
       <li>{{ item.name }}</li>
     {% endfor %}
   {% else %}
     <p>No items found.</p>
   {% endif %}
   ```

## Loops and Iteration

1. **Use forloop Variables**
   ```django
   {% for item in items %}
     <div class="{% if forloop.first %}mt-0{% else %}mt-4{% endif %}">
       {{ item.name }}
     </div>
   {% endfor %}
   ```

2. **Loop Counter**
   ```django
   {% for item in items %}
     <p>Item {{ forloop.counter }}: {{ item.name }}</p>
   {% endfor %}
   ```

## Comments

1. **Template Comments** - Use Django comments
   ```django
   {# This is a template comment #}
   
   {% comment %}
   This is a multi-line
   template comment
   {% endcomment %}
   ```

## Filters and Template Tags

1. **Common Filters**
   ```django
   {{ text|truncatewords:20 }}
   {{ date|date:"Y-m-d" }}
   {{ text|title }}
   {{ text|default:"N/A" }}
   ```

2. **Custom Template Tags** - Load from `templatetags/`
   ```django
   {% load custom_tags %}
   {% custom_tag argument %}
   ```

## Accessibility

1. **Use Semantic HTML**
   ```html
   <nav>...</nav>
   <main>...</main>
   <article>...</article>
   <section>...</section>
   ```

2. **Alt Text for Images**
   ```html
   <img src="{% static 'images/logo.png' %}" alt="OWASP BLT Logo">
   ```

3. **Form Labels**
   ```html
   <label for="id_username">Username:</label>
   <input type="text" id="id_username" name="username">
   ```

## Security Considerations

1. **Auto-escaping** - Django auto-escapes by default
   - Trust Django's auto-escaping for user input
   - Only use `|safe` for trusted HTML content

2. **CSRF Protection** - Always include `{% csrf_token %}` in forms

3. **User Input Validation** - Never trust user input in templates

## Template Formatting

1. **Use djLint** - Templates are automatically formatted by pre-commit
2. **Indentation** - Use 2 spaces for HTML, consistent with djLint
3. **Line Length** - Keep lines under 120 characters when possible

## Common Patterns

### Modal
```django
<div class="fixed inset-0 bg-gray-600 bg-opacity-50 hidden" id="modal">
  <div class="bg-white rounded-lg p-6 max-w-md mx-auto mt-20">
    <h2 class="text-xl font-bold mb-4">Modal Title</h2>
    <p>Modal content</p>
    <button class="mt-4 bg-red-600 text-white px-4 py-2 rounded">Close</button>
  </div>
</div>
```

### Cards
```django
<div class="bg-white shadow rounded-lg p-6">
  <h3 class="text-lg font-semibold mb-2">{{ card.title }}</h3>
  <p class="text-gray-600">{{ card.description }}</p>
</div>
```

### Lists with Pagination
```django
<ul class="space-y-4">
  {% for item in items %}
    <li class="border-b pb-2">{{ item.name }}</li>
  {% endfor %}
</ul>

{% if is_paginated %}
  <div class="flex justify-center mt-4 space-x-2">
    {% if page_obj.has_previous %}
      <a href="?page={{ page_obj.previous_page_number }}" class="px-3 py-1 bg-gray-200 rounded">Previous</a>
    {% endif %}
    {% if page_obj.has_next %}
      <a href="?page={{ page_obj.next_page_number }}" class="px-3 py-1 bg-gray-200 rounded">Next</a>
    {% endif %}
  </div>
{% endif %}
```

## Best Practices Summary

✅ **DO**:
- Use Tailwind CSS utility classes
- Keep JavaScript in separate files
- Use template inheritance
- Use `{% url %}` for links
- Use `{% static %}` for static files
- Include `{% csrf_token %}` in forms
- Use semantic HTML
- Add alt text to images
- Follow djLint formatting

❌ **DON'T**:
- Add `<style>` tags
- Add inline styles
- Add inline JavaScript (`onclick`, etc.)
- Hardcode URLs
- Forget CSRF tokens
- Use `|safe` on user input
- Skip accessibility attributes
- Commit code that fails djLint checks
