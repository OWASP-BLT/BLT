import json

import django
from django.contrib import admin
from django.contrib import messages
from django.utils.html import escape
from django.utils.translation import ugettext_lazy as _, pgettext_lazy
from django.utils.safestring import mark_safe

from .models import Feedback


# Display an html table from a dict
# Credit: original author Rogerio Hilbert
def pretty_items(r, d, nametag="<strong>%s: </strong>", itemtag='<li>%s</li>\n',
                 valuetag="%s", blocktag=('<ul>', '</ul>\n')):
    if isinstance(d, dict):
        r.append(blocktag[0])
        for k, v in d.items():
            name = nametag % escape(k)
            if isinstance(v, dict) or isinstance(v, list):
                r.append(itemtag % name)
                pretty_items(r, v, nametag, itemtag, valuetag, blocktag)
            else:
                value = valuetag % escape(v)
                r.append(itemtag % (name + value))
        r.append(blocktag[1])
    elif isinstance(d, list):
        r.append(blocktag[0])
        for i in d:
            if isinstance(i, dict) or isinstance(i, list):
                r.append(itemtag % " - ")
                pretty_items(r, i, nametag, itemtag, valuetag, blocktag)
            else:
                r.append(itemtag % escape(i))
        r.append(blocktag[1])


class FeedbackAdmin(admin.ModelAdmin):
    list_display = ("comment", "url", "screenshot_thumb", "user", "email", "created", "ack")
    list_filter = ("created", "ack", "user", "url")
    search_fields = ("comment", "user__email", "user__name")
    readonly_fields = ("comment", "url", "user", "browser_html", "screenshot_thumb")
    exclude = ('browser', 'screenshot')
    ordering = ("-created",)
    date_hierarchy = 'created'

    actions = ('acknowledge', 'unacknowledge')

    def acknowledge(self, request, queryset):
        queryset.update(ack=True)
        messages.info(request, _("Feedback(s) has been acknowledged."),
                      fail_silently=True)
    acknowledge.short_description = _("Acknowledge selected feedbacks")

    def unacknowledge(self, request, queryset):
        queryset.update(ack=False)
        messages.info(request, _("Feedback(s) has been unacknowledged."),
                      fail_silently=True)
    unacknowledge.short_description = _("Unacknowledge selected feedbacks")

    def screenshot_thumb(self, feedback):
        if feedback.screenshot:
            if django.VERSION[0] < 2:
                return u'<a href="%s" ><img src="%s" width="100"/></a>' % (feedback.get_screenshot_url(), feedback.get_screenshot_url())
            else:
                return mark_safe(u'<a href="%s" ><img src="%s" width="100"/></a>' % (feedback.get_screenshot_url(), feedback.get_screenshot_url()))

    screenshot_thumb.allow_tags = True
    screenshot_thumb.short_description = _("Screenshot")

    def browser_html(self, feedback):
        if feedback.browser:
            r = []
            pretty_items(r, json.loads(feedback.browser))
            if django.VERSION[0] < 2:
                return u''.join(r)
            else:
                return mark_safe(u''.join(r))
    browser_html.allow_tags = True
    browser_html.short_description = pgettext_lazy("Admin model", "Browser Info")


admin.site.register(Feedback, FeedbackAdmin)
