# -*- coding: utf-8 -*-

from collections.abc import Iterable

from .constants import ALLOWED_CHARACTERS
from .utils import (
    any_next_words_form_swear_word,
    get_complete_path_of_file,
    get_replacement_for_swear_word,
    read_wordlist,
)
from .varying_string import VaryingString


class Profanity:
    def __init__(self, words=None):
        """
        Args:
            words (Iterable/str): Collection of words or file path for a list of
                words to censor. `None` to use the default word list.

        Raises:
            TypeError: If `words` is not a valid type.
            FileNotFoundError: If `words` is a `str` and is not a valid file path.
        """
        if (
            words is not None
            and not isinstance(words, str)
            and not isinstance(words, Iterable)
        ):
            raise TypeError("words must be of type str, list, or None")
        self.CENSOR_WORDSET = []
        self.CHARS_MAPPING = {
            "a": ("a", "@", "*", "4"),
            "i": ("i", "*", "l", "1"),
            "o": ("o", "*", "0", "@"),
            "u": ("u", "*", "v"),
            "v": ("v", "*", "u"),
            "l": ("l", "1"),
            "e": ("e", "*", "3"),
            "s": ("s", "$", "5"),
            "t": ("t", "7"),
        }
        self.MAX_NUMBER_COMBINATIONS = 1
        self.ALLOWED_CHARACTERS = ALLOWED_CHARACTERS
        self._default_wordlist_filename = get_complete_path_of_file(
            "profanity_wordlist.txt"
        )
        if type(words) == str:
            self.load_censor_words_from_file(words)
        else:
            self.load_censor_words(custom_words=words)

    ## PUBLIC ##

    def censor(self, text, censor_char="*"):
        """Replace the swear words in the text with `censor_char`."""

        if not isinstance(text, str):
            text = str(text)
        if not isinstance(censor_char, str):
            censor_char = str(censor_char)

        if not self.CENSOR_WORDSET:
            self.load_censor_words()
        return self._hide_swear_words(text, censor_char)

    def load_censor_words_from_file(self, filename, **kwargs):
        words = read_wordlist(filename)
        self._populate_words_to_wordset(words, **kwargs)

    def load_censor_words(self, custom_words=None, **kwargs):
        """Generate a set of words that need to be censored."""
        # Replace the words from `profanity_wordlist.txt` with a custom list
        custom_words = custom_words or read_wordlist(self._default_wordlist_filename)
        self._populate_words_to_wordset(custom_words, **kwargs)

    def add_censor_words(self, custom_words):
        if not isinstance(custom_words, (list, tuple, set)):
            raise TypeError(
                "Function 'add_censor_words' only accepts list, tuple or set."
            )
        for w in custom_words:
            self.CENSOR_WORDSET.append(VaryingString(w, char_map=self.CHARS_MAPPING))

    def contains_profanity(self, text):
        """Return True if  the input text has any swear words."""
        return text != self.censor(text)

    ## PRIVATE ##

    def _populate_words_to_wordset(self, words, *, whitelist_words=None):
        if whitelist_words is not None and not isinstance(
            whitelist_words, (list, set, tuple)
        ):
            raise TypeError(
                "The 'whitelist_words' keyword argument only accepts list, tuple or set."
            )

        # Validation
        whitelist_words = whitelist_words or []
        for index, word in enumerate(whitelist_words):
            if not isinstance(word, str):
                raise ValueError(
                    "Each word in 'whitelist_words' must be 'str' type, "
                    "but '{word}' found.".format(word=type(word))
                )
            whitelist_words[index] = word.lower()

        # Populate the words into an internal wordset
        whitelist_words = set(whitelist_words)
        all_censor_words = []
        for word in set(words):
            # All words in CENSOR_WORDSET must be in lowercase
            word = word.lower()

            if word in whitelist_words:
                continue

            num_of_non_allowed_chars = self._count_non_allowed_characters(word)
            if num_of_non_allowed_chars > self.MAX_NUMBER_COMBINATIONS:
                self.MAX_NUMBER_COMBINATIONS = num_of_non_allowed_chars

            all_censor_words.append(VaryingString(word, char_map=self.CHARS_MAPPING))

        # The default wordlist takes ~5MB+ of memory
        self.CENSOR_WORDSET = all_censor_words

    def _count_non_allowed_characters(self, word):
        count = 0
        for char in iter(word):
            if char not in self.ALLOWED_CHARACTERS:
                count += 1
        return count

    def _update_next_words_indices(self, text, words_indices, start_idx):
        """Return a list of next words_indices after the input index."""
        if not words_indices:
            words_indices = self._get_next_words(
                text, start_idx, self.MAX_NUMBER_COMBINATIONS
            )
        else:
            del words_indices[:2]
            if words_indices and words_indices[-1][0] != "":
                words_indices += self._get_next_words(text, words_indices[-1][1], 1)
        return words_indices

    def _hide_swear_words(self, text, censor_char):
        """Replace the swear words with censor characters."""
        censored_text = ""
        cur_word = ""
        skip_index = -1
        next_words_indices = []
        start_idx_of_next_word = self._get_start_index_of_next_word(text, 0)

        # If there are no words in the text, return the raw text without parsing
        if start_idx_of_next_word >= len(text) - 1:
            return text

        # Left strip the text, to avoid inaccurate parsing
        if start_idx_of_next_word > 0:
            censored_text = text[:start_idx_of_next_word]
            text = text[start_idx_of_next_word:]

        # Splitting each word in the text to compare with censored words
        for index, char in iter(enumerate(text)):
            if index < skip_index:
                continue
            if char in ALLOWED_CHARACTERS:
                cur_word += char
                continue

            # Skip continuous non-allowed characters
            if cur_word.strip() == "":
                censored_text += char
                cur_word = ""
                continue

            # Iterate the next words combined with the current one
            # to check if it forms a swear word
            next_words_indices = self._update_next_words_indices(
                text, next_words_indices, index
            )
            contains_swear_word, end_index = any_next_words_form_swear_word(
                cur_word, next_words_indices, self.CENSOR_WORDSET
            )
            if contains_swear_word:
                cur_word = get_replacement_for_swear_word(censor_char)
                skip_index = end_index
                char = ""
                next_words_indices = []

            # If the current a swear word
            if cur_word.lower() in self.CENSOR_WORDSET:
                cur_word = get_replacement_for_swear_word(censor_char)

            censored_text += cur_word + char
            cur_word = ""

        # Final check
        if cur_word != "" and skip_index < len(text) - 1:
            if cur_word.lower() in self.CENSOR_WORDSET:
                cur_word = get_replacement_for_swear_word(censor_char)
            censored_text += cur_word
        return censored_text

    def _get_start_index_of_next_word(self, text, start_idx):
        """Return the index of the first character of the next word in the given text."""
        start_idx_of_next_word = len(text)
        for index in iter(range(start_idx, len(text))):
            if text[index] not in self.ALLOWED_CHARACTERS:
                continue
            start_idx_of_next_word = index
            break

        return start_idx_of_next_word

    def _get_next_word_and_end_index(self, text, start_idx):
        """Return the next word in the given text, and the index of its last character."""
        next_word = ""
        index = start_idx
        for index in iter(range(start_idx, len(text))):
            char = text[index]
            if char in self.ALLOWED_CHARACTERS:
                next_word += char
                continue
            break
        return next_word, index

    def _get_next_words(self, text, start_idx, num_of_next_words=1):
        """
        Return a list of pairs of next words and next words included with separators,
        combined with their end indices.
        For example: Word `hand_job` has next words pairs: `job`, `_job`.
        """

        # Find the starting index of the next word
        start_idx_of_next_word = self._get_start_index_of_next_word(text, start_idx)

        # Return an empty string if there are no other words
        if start_idx_of_next_word >= len(text) - 1:
            return [("", start_idx_of_next_word), ("", start_idx_of_next_word)]

        # Combine the  words into a list
        next_word, end_index = self._get_next_word_and_end_index(
            text, start_idx_of_next_word
        )

        words = [
            (next_word, end_index),
            ("%s%s" % (text[start_idx:start_idx_of_next_word], next_word), end_index),
        ]
        if num_of_next_words > 1:
            words.extend(self._get_next_words(text, end_index, num_of_next_words - 1))

        return words
