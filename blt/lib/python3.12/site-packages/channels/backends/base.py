# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from abc import ABCMeta, abstractmethod

from six import add_metaclass

from ..types import SendOptions  # noqa: F401


@add_metaclass(ABCMeta)
class BaseChannel(object):
    @abstractmethod
    def send(self, message, fail_silently=False, options=None):
        # type: (Text, bool, Optional[SendOptions]) -> None
        pass

    @staticmethod
    def _set_payload_from_options(payload, options, option_key, payload_keys):
        """Update payload dictionary with option

        :type payload: dict
        :type options: dict
        :type option_key: str | unicode
        :type payload_keys: list[str | unicode]
        """
        if options is None or option_key not in options:
            return

        options = options[option_key]
        for payload_key in payload_keys:
            if payload_key in options:
                payload[payload_key] = options[payload_key]
