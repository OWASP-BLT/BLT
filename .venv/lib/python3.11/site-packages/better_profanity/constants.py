# -*- coding: utf-8 -*-

from io import open
from json import load
from string import ascii_letters, digits

from .utils import get_complete_path_of_file

ALLOWED_CHARACTERS = set(ascii_letters)
ALLOWED_CHARACTERS.update(set(digits))
ALLOWED_CHARACTERS.update({"@", "$", "*", '"', "'"})

# Pre-load the unicode characters
with open(get_complete_path_of_file("alphabetic_unicode.json"), "r") as json_file:
    ALLOWED_CHARACTERS.update(load(json_file))
