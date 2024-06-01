# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import requests

from .base import BaseChannel
from channels.exceptions import HttpError


class YoChannel(BaseChannel):
    url = "https://api.justyo.co/yo/"

    def __init__(self, api_token, username=None, *args, **kwargs):
        self.api_token = api_token
        self.username = username

    def send(self, message, fail_silently=False, options=None):
        payload = {
            "api_token": self.api_token
        }

        if self.username is not None:
            payload["username"] = self.username

        if message is not None:
            # 30 characters max
            payload["text"] = message

        self._set_payload_from_options(payload, options, "yo", [
            "username", "link", "location"])

        try:
            response = requests.post(self.url, data=payload)
            if response.status_code != requests.codes.ok:
                raise HttpError(response.status_code, response.text)
        except:
            if not fail_silently:
                raise
