from django.conf import settings

# Sizzle configuration - makes the plugin flexible for different Django projects
SIZZLE_SETTINGS = {
    # Default base template for standalone projects
    'BASE_TEMPLATE': getattr(settings, 'SIZZLE_BASE_TEMPLATE', 'base.html'),
    
    # Parent base template - set this in your main project for integration
    'PARENT_BASE': getattr(settings, 'SIZZLE_PARENT_BASE', None),
    
    # Whether to integrate with the parent project's layout
    'USE_PROJECT_BASE': getattr(settings, 'SIZZLE_USE_PROJECT_BASE', True),
    
    # Show sidenav if available (for BLT integration)
    'SHOW_SIDENAV': getattr(settings, 'SIZZLE_SHOW_SIDENAV', True),
}

def get_base_template():
    """Get the appropriate base template for sizzle templates"""
    if SIZZLE_SETTINGS['PARENT_BASE']:
        return SIZZLE_SETTINGS['PARENT_BASE']
    return SIZZLE_SETTINGS['BASE_TEMPLATE']