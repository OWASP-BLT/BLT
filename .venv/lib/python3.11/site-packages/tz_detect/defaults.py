from django.conf import settings

# These countries will be prioritised in the search
# for a matching timezone. Consider putting your
# app's most popular countries first.
# Defaults to top Internet using countries.

TZ_DETECT_COUNTRIES = getattr(settings, "TZ_DETECT_COUNTRIES", ("CN", "US", "IN", "JP", "BR", "RU", "DE", "FR", "GB"))
