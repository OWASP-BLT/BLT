import logging
import shlex
from typing import List

log = logging.getLogger(__name__)


class EasyProcessUnicodeError(Exception):
    pass


def split_command(cmd, posix=None) -> List[str]:
    """
     - cmd is string list -> nothing to do
     - cmd is string -> split it using shlex

    :param cmd: string ('ls -l') or list of strings (['ls','-l'])
    :rtype: string list
    """
    if not isinstance(cmd, str):
        # cmd is string list
        pass
    else:
        if posix is None:
            posix = True
        cmd = shlex.split(cmd, posix=posix)
    return cmd


# def uniencode(s):
#     return s


def unidecode(s):
    s = s.decode("utf-8", "ignore")
    return s
