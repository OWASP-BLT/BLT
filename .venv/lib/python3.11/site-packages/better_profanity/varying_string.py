# -*- coding: utf-8 -*-


class VaryingString:
    """Represents a string with varying character representations."""

    def __init__(self, string, char_map={}):
        """
        Args:
            string (str): String to generate variants of.
            char_mappings (dict): Maps characters to substitute characters.
        """
        self._original = string

        # There is not necessarily a single length for all of this string's variants.
        # Some character substitutions may include more than one character or empty
        # substitutions.
        self._min_len = 0
        self._max_len = 0

        # Create list of all possible character combinations.
        self._char_combos = []
        for char in self._original:
            if char in char_map:
                self._char_combos.append(char_map[char])
                lens = [len(c) for c in char_map[char]]
                self._min_len += min(lens)
                self._max_len += max(lens)
            else:
                self._char_combos.append((char,))
                self._min_len += 1
                self._max_len += 1

    def __str__(self):
        return self._original

    def __eq__(self, other):
        if self is other:
            return True
        elif other.__class__ == VaryingString:
            # We have no use case for this yet.
            raise NotImplementedError
        elif other.__class__ == str:
            len_other = len(other)
            if len_other < self._min_len or len_other > self._max_len:
                return False
            # We use a list of slices instead of a single slices to account for
            # character substitutions that contain multiple characters.
            slices = [other]
            for chars in self._char_combos:
                new_slices = []
                for char in chars:
                    if not char:
                        new_slices.extend(slices)
                    len_char = len(char)
                    for sl in slices:
                        if sl[:len_char] == char:
                            new_slices.append(sl[len_char:])
                if len(new_slices) == 0:
                    return False
                slices = new_slices
            for sl in slices:
                if len(sl) == 0:
                    return True
            return False
        else:
            return False
