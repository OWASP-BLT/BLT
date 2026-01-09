# -*- coding: utf-8 -*-

import os.path


def get_complete_path_of_file(filename):
    """Join the path of the current directory with the input filename."""
    root = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(root, filename)


def read_wordlist(filename: str):
    """Return words from a wordlist file."""
    with open(filename, encoding="utf-8") as wordlist_file:
        for row in iter(wordlist_file):
            row = row.strip()
            if row != "":
                yield row


def get_replacement_for_swear_word(censor_char):
    return censor_char * 4


def any_next_words_form_swear_word(cur_word, words_indices, censor_words):
    """
    Return True, and the end index of the word in the text,
    if any word formed in words_indices is in `CENSOR_WORDSET`.
    """
    full_word = cur_word.lower()
    full_word_with_separators = cur_word.lower()

    # Check both words in the pairs
    for index in iter(range(0, len(words_indices), 2)):
        single_word, end_index = words_indices[index]
        word_with_separators, _ = words_indices[index + 1]
        if single_word == "":
            continue

        full_word = "%s%s" % (full_word, single_word.lower())
        full_word_with_separators = "%s%s" % (
            full_word_with_separators,
            word_with_separators.lower(),
        )
        if full_word in censor_words or full_word_with_separators in censor_words:
            return True, end_index
    return False, -1
