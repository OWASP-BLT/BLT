from django.conf import settings
from django.core.mail import send_mail as django_send_mail
from django.utils.translation import ugettext_lazy as _
try:
    from django.core.urlresolvers import reverse
except ImportError:
    from django.urls import reverse


def send_mail(request, feedback, fail_silently=True):
    message = _("Your site %(host)s received feedback from %(user)s.\n"
                "The comments were:\n"
                "%(note)s.\n\n"
                "See the full feedback content here: %(url)s")\
              % {'host': request.get_host(), 'user': str(request.user), 'note': feedback.comment,
                 'url': request.build_absolute_uri(
                     reverse('admin:tellme_feedback_change', args=(feedback.id,)))}
    django_send_mail(
        _('[%(host)s] Received feedback') % {'host': request.get_host()},
        message,
        settings.SERVER_EMAIL,
        [settings.TELLME_FEEDBACK_EMAIL],
        fail_silently=fail_silently)
