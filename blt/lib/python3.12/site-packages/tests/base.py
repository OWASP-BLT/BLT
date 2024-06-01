from django.apps import apps
from django.conf import settings


class BaseFooTest:
    """
        We need to use a different Foo class if the model rating model is switched out (as it needs UUID).

    """
    def setUp(self):
        foo_app, foo_model_name = settings.FOO_MODEL.split('.')
        self.foo_model = apps.get_model(app_label=foo_app, model_name=foo_model_name)

        bar_app, bar_model_name = settings.BAR_MODEL.split('.')
        self.bar_model = apps.get_model(app_label=bar_app, model_name=bar_model_name)
