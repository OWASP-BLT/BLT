# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import json

import requests

from .base import BaseChannel
from channels.exceptions import HttpError, ImproperlyConfigured


class HipChatChannel(BaseChannel):
    colors = ("yellow", "green", "red", "purple", "gray", "random")
    message_formats = ("html", "text")

    def __init__(self, api_id, token, base_url="https://api.hipchat.com/v2/",
                 color=None, notify=None, message_format="html", *args,
                 **kwargs):
        self.url = "{0}room/{1}/notification?auth_token={2}".format(
            base_url, api_id, token)
        self.color = color
        self.notify = notify
        self.message_format = message_format

        # Validation
        if self.color is not None:
            if self.color not in self.colors:
                raise ImproperlyConfigured("Invalid color")

        if self.notify is not None:
            if not isinstance(self.notify, bool):
                raise ImproperlyConfigured("Notify must be bool")

        if self.message_format not in self.message_formats:
            raise ImproperlyConfigured("Invalid message_format")

    def send(self, message, fail_silently=False, options=None):
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        payload = {
            "message": message,
            "message_format": self.message_format
        }

        if self.color is not None:
            payload["color"] = self.color
        if self.notify is not None:
            payload["notify"] = self.notify

        self._set_payload_from_options(payload, options, "hipchat", [
            "color", "notify", "message_format"])

        try:
            response = requests.post(self.url,
                                     headers=headers,
                                     data=json.dumps(payload))
            if response.status_code != requests.codes.no_content:
                raise HttpError(response.status_code, response.text)
        except:
            if not fail_silently:
                raise
