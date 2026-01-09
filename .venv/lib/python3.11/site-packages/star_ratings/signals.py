from __future__ import unicode_literals


def calculate_ratings(sender, instance, **kwargs):
    instance.rating.calculate()
