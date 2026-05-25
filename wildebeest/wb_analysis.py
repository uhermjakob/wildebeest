#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Written by Ulf Hermjakob, USC/ISI
This script analyzes a given text for a wide range of anomalies.
When using STDIN and/or STDOUT, it might be necessary, particularly for older versions of Python, to do
'export PYTHONIOENCODING=UTF-8' before calling this Python script to ensure UTF-8 encoding.
"""
# -*- encoding: utf-8 -*-

import argparse
import io
import json
import time
import datetime
from collections import defaultdict
import logging as log
import os
from pathlib import Path
import re
import regex
import sys
from tqdm.auto import tqdm
from typing import IO, Optional, TextIO, Tuple, Union, List
import unicodedata as ud
import unicodeblock.blocks
if __name__ == "__main__":
    import wb_pprint_html as wb_pp
from wildebeest.utilities import ScriptDirection
from wildebeest.wb_normalize import Wildebeest
from wildebeest import __version__, last_mod_date
from gr_versification import BackVersification


log.basicConfig(level=log.INFO)


def guard_html(s: str) -> str:
    s = re.sub('&', '&amp;', s)
    s = re.sub('<', '&lt;', s)
    s = re.sub('>', '&gt;', s)
    s = re.sub('"', '&quot;', s)
    return s


def slot_value_in_double_colon_del_list(line: str, slot: str, default: Optional = None) -> str:
    """For a given slot, e.g. 'cost', get its value from a line such as '::s1 of course ::s2 ::cost 0.3' -> 0.3
    The value can be an empty string, as for ::s2 in the example above."""
    m = regex.match(fr'(?:.*\s)?::{slot}(|\s+\S.*?)(?:\s+::\S.*|\s*)$', line)
    return m.group(1).strip() if m else default


def control_character_name(char: str) -> str | None:
    # Dictionary with the names of the most common control characters.
    control_character_dict = {
        '\x00': 'NULL', '\x01': 'START OF HEADING', '\x02': 'START OF TEXT', '\x03': 'END OF TEXT',
        '\x07': 'BELL', '\x08': 'BACKSPACE', '\x09': 'TAB', '\x0A': 'NEW LINE',
        '\x0D': 'CARRIAGE RETURN', 'x1B': 'ESCAPE', '\x7F': 'DELETE'}
    if char in control_character_dict:
        return f'control character {control_character_dict[char]}'
    elif char <= '\x1F':            # Unicode block C0
        return "control character"
    elif '\x80' <= char <= '\x9F':  # Unicode block C1
        return "control character"
    else:
        return None


def print_char_unicode_name(char: str) -> str:
    c_name = ud.name(char, None) or control_character_name(char) or ''
    invisible_char = regex.match(r'(\pZ|\pC)', char)
    hex_code = f"U+{ord(char):04X}"
    return f"{c_name} ({hex_code})" if invisible_char else f"{char} ({c_name}, {hex_code})"


def print_str_unicode_names(s: str, delimiter: str = ', ') -> str:
    return delimiter.join(map(print_char_unicode_name, s))


class WildebeestAnalysis:
    """
    Object stores raw and aggregate information of a Wildebeest test checking analysis.
    Final results are stored in self.analysis
    """
    def __init__(self, args, verbose: Optional[bool] = False):
        self.wildebeest = Wildebeest()
        self.lang_code = args.lc
        self.verbose = verbose
        self.filename = None
        self.character_count = defaultdict(int)
        self.token_count = defaultdict(int)
        self.token_examples = defaultdict(list)  # values are lists of lists(token, line number)
        # noinspection SpellCheckingInspection
        self.pattern_characters_of_interest = ("-‐‑−‒–—―=\u00AD+~*_.,:꞉;!¡¿?/⁄§'‚‘’ʼˊˋˈˀˆˉ`«»‹›„“”\"()\\[\\]<>⌞⌟"
                                               "、。．،٫٬，；？（）।॥።፣፤፥፦፧՜՝՞։؛؟۔@#&%$€£¥₪¢¤₨₹µ‌¦|‍")
        self.pattern_characters_of_interest += 'ـ'  # Arabic tatweel
        self.pattern_characters_of_interest_re = regex.compile(rf'[{self.pattern_characters_of_interest}]')
        self.pattern_count = defaultdict(int)
        self.pattern_examples = defaultdict(list)
        self.pattern_lines = defaultdict(set)
        self.max_pattern_lines = args.max_pattern_lines
        self.max_bad_pattern_lines = args.max_bad_pattern_lines
        self.max_n_token_examples = args.max_examples
        self.max_n_viz_examples = 5 if args.max_examples_viz is None else args.max_examples_viz
        self.max_n_cases = args.max_cases
        self.script_count_letter = defaultdict(int)
        self.script_count_number = defaultdict(int)
        self.script_count_other = defaultdict(int)
        self.script_examples_letter = defaultdict(str)
        self.script_examples_number = defaultdict(str)
        self.script_examples_other = defaultdict(str)
        self.mixed_script_count_letter = defaultdict(int)
        self.mixed_script_instances_letter = defaultdict(list)
        self.script_lines = defaultdict(set)
        self.max_script_lines = args.max_script_lines
        self.non_canonical_lines = defaultdict(set)
        self.max_non_canonical_lines = args.max_non_canonical_lines
        self.char_conflict_lines = defaultdict(set)
        self.max_char_conflict_lines = args.max_char_conflict_lines
        self.notable_token_lines = defaultdict(set)
        self.max_notable_token_lines = args.max_notable_token_lines
        self.open_quot_refresh_class_prev_unexpected_sub_result_values = []  # used in stderr duplicate reduction
        self.analysis = {'n_lines': 0,
                         'n_empty_lines': 0,
                         'n_characters': 0,
                         'letter-script': defaultdict(dict),
                         'number-script': defaultdict(dict),
                         'other-script': defaultdict(dict),
                         'non-canonical': defaultdict(dict),
                         'rival-char-sets': defaultdict(list),
                         'notable-token': defaultdict(dict),
                         'notable-token-meta': defaultdict(dict),
                         'pattern': defaultdict(dict),
                         'block': defaultdict(dict)}
        self.pattern_class_counts = defaultdict(lambda: [0, 0, 0])
        # Key: (pattern_character_of_interest, pattern)
        # Value: List of counts for '-'/''/'+'
        self.script_direction = ScriptDirection(lang_code=self.lang_code or args.input)
        self.log_message_counts = defaultdict(int)
        self.abbreviations = defaultdict(set)         # key: lang_code, e.g. "fas"
        self.active_abbreviations = defaultdict(set)  # key: lang_code, e.g. "fas"
        self.in_word_punct_patterns = set()

        # The following blocks will be printed out in order as specified below:
        for block in ['LOW_SURROGATES', 'REPLACEMENT', 'C0_CONTROL', 'C1_CONTROL', 'ZERO_WIDTH', 'DIRECTIONAL',
                      'VARIATION_SELECTORS', 'VARIATION_SELECTORS_SUPPLEMENT',
                      'ASCII_PUNCTUATION', 'GENERAL_PUNCTUATION', 'ARABIC_PUNCTUATION', 'ETHIOPIC_PUNCTUATION',
                      'CHINESE_PUNCTUATION', 'DEVANAGARI_PUNCTUATION', 'ARMENIAN_PUNCTUATION',
                      'CURRENCY_SYMBOLS', 'SPACE',
                      'ASCII_DIGIT', 'FULLWIDTH_DIGIT', 'VULGAR_FRACTION', 'ROMAN_NUMERAL',
                      'ARABIC_INDIC_DIGIT', 'EXTENDED_ARABIC_INDIC_DIGIT',
                      'NUMBER_FORMS', 'SUPERSCRIPT_DIGIT', 'SUBSCRIPT_DIGIT', 'SUPERSCRIPTS_AND_SUBSCRIPTS',
                      'COMBINING_DIACRITICAL_MARKS',
                      'BASIC_LATIN', 'LATIN_EXTENDED_LETTER', 'LATIN_EXTENDED_A', 'LATIN_EXTENDED_B',
                      'LATIN_EXTENDED_C', 'LATIN_EXTENDED_D', 'LATIN_ALPHABETIC_PRESENTATION_FORMS',
                      'LATIN', 'IPA_EXTENSIONS', 'LETTERLIKE_SYMBOLS', 'FULLWIDTH_LATIN',
                      'CYRILLIC',
                      'ARMENIAN', 'ARMENIAN_ALPHABETIC_PRESENTATION_FORMS',
                      'GREEK', 'GREEK_EXTENDED',
                      'ARABIC', 'ARABIC_PRESENTATION_FORMS_A', 'ARABIC_PRESENTATION_FORMS_B',
                      'HEBREW', 'HEBREW_ALPHABETIC_PRESENTATION_FORMS', 'HEBREW_PRESENTATION_FORMS']:
            self.analysis['block'][block] = {}

        self.char_to_name_dict = {
            '\0': 'NULL',
            '': 'START OF HEADING',
            '': 'START OF TEXT',
            '': 'END OF TEXT',
            '': 'END OF TRANSMISSION',
            '': 'ENQUIRY',
            '': 'ACKNOWLEDGE',
            '': 'BELL',
            '': 'BACKSPACE',
            '\t': 'TAB',
            '\n': 'LINE FEED',
            '': 'LINE TABULATION',
            '': 'FORM FEED',
            '\r': 'CARRIAGE RETURN',
            '': 'SHIFT OUT',
            '': 'SHIFT IN',
            '': 'DATA LINK ESCAPE',
            '': 'DEVICE CONTROL ONE',
            '': 'DEVICE CONTROL TWO',
            '': 'DEVICE CONTROL THREE',
            '': 'DEVICE CONTROL FOUR',
            '': 'NEGATIVE ACKNOWLEDGE',
            '': 'SYNCHRONOUS IDLE',
            '': 'END OF TRANSMISSION BLOCK',
            '': 'CANCEL',
            '': 'END OF MEDIUM',
            '': 'SUBSTITUTE',
            '': 'ESCAPE',
            '': 'INFORMATION SEPARATOR FOUR',
            '': 'INFORMATION SEPARATOR THREE',
            '': 'INFORMATION SEPARATOR TWO',
            '':  'INFORMATION SEPARATOR ONE',
            '': 'DELETE',
            '':   'PADDING CHARACTER (W1252: Euro Sign)',
            '': 'HIGH OCTET PRESET',
            '': 'BREAK PERMITTED HERE (W1252: Single Low-9 Quotation Mark)',
            '': 'NO BREAK HERE (W1252: Latin Small Letter F With Hook)',
            '': 'INDEX (W1252: Double Low-9 Quotation Mark)',
            '': 'NEXT LINE (W1252: Horizontal Ellipsis)',
            '': 'START OF SELECTED AREA (W1252: Dagger)',
            '': 'END OF SELECTED AREA (W1252: Double Dagger)',
            '': 'CHARACTER TABULATION SET (W1252: Modifier Letter Circumflex Accent)',
            '': 'CHARACTER TABULATION WITH JUSTIFICATION (W1252: Per Mille Sign)',
            '': 'LINE TABULATION SET (W1252: Latin Capital Letter S With Caron)',
            '': 'PARTIAL LINE FORWARD (W1252: Single Left-Pointing Angle Quotation Mark)',
            '': 'PARTIAL LINE BACKWARD (W1252: Latin Capital Ligature OE)',
            '': 'REVERSE LINE FEED',
            '': 'SINGLE SHIFT TWO (W1252: Latin Capital Letter Z With Caron)',
            '': 'SINGLE SHIFT THREE',
            '': 'DEVICE CONTROL STRING',
            '': 'PRIVATE USE ONE (W1252: Left Single Quotation Mark)',
            '': 'PRIVATE USE TWO (W1252: Right Single Quotation Mark)',
            '': 'SET TRANSMIT STATE (W1252: Left Double Quotation Mark)',
            '': 'CANCEL CHARACTER (W1252: Right Double Quotation Mark)',
            '': 'MESSAGE WAITING (W1252: Bullet)',
            '': 'START OF GUARDED AREA (W1252: En Dash)',
            '': 'END OF GUARDED AREA (W1252: Em Dash)',
            '': 'START OF STRING (W1252: Small Tilde)',
            '': 'SINGLE GRAPHIC CHARACTER INTRODUCER (W1252: Trade Mark Sign)',
            '': 'SINGLE CHARACTER INTRODUCER (W1252: Latin Small Letter S With Caron)',
            '': 'CONTROL SEQUENCE INTRODUCER (W1252: Single Right-Pointing Angle Quotation Mark)',
            '': 'STRING TERMINATOR (W1252: Latin Small Ligature OE)',
            '': 'OPERATING SYSTEM COMMAND',
            '': 'PRIVACY MESSAGE (W1252: Latin Small Letter Z With Caron)',
            '': 'APPLICATION PROGRAM COMMAND (W1252: Latin Capital Letter Y With Diaeresis)',
            '﻿': 'ZERO WIDTH NO-BREAK SPACE (BYTE ORDER MARK)'
        }
        self.char_to_block_dict = defaultdict(str)
        self.unicode_block_to_script_dict = defaultdict(str)
        self.char_to_script_dict = defaultdict(str)
        self.populate_char_to_block_dict()
        self.token_to_pattern_dict = defaultdict(list)
        self.ref_id_dict = None
        self.corpus = None
        self.corpus_w_rtf_delimiter_adjustments = None
        self.lrm = '‎'  # left-to-right directional mark
        # structure of dictionaries for unmatched, nesting_l, nesting_r:
        #   key: char (paired_delimiter)
        #   value: list[(line_number, char_pos)]
        # structure of dictionaries for open_lefts, refresher_lefts:
        #   key: char (paired_delimiter)
        #   value: list[(line_number, char_pos, n_chars_in_line)]   # helps gauge approximate pos. in translation
        # structure of dictionary for open_first_lefts:
        #   key: char (paired_delimiter)
        #   value: (line_number, char_pos) | None
        # structure of dictionary for cross_snt_spans:
        #   key: char (paired_delimiter)
        #   value: list[((open_line_number, open_char_pos, open_line_len),
        #                (close_line_number, close_char_pos, close_line_len))]
        self.punct_analysis = {'stack': [],       # list of characters
                               'stack_plus': [],  # list of (character, (line_number, char_pos, line_len), snt_id)
                               'open_lefts': defaultdict(list),
                               'matching_punct': '()[]{}«»‹›（）［］【】「」『』《》〈〉⌞⌟',
                               'matching_punct_supplement_low_quote': '„”‚’',    # German, Danish
                               'matching_punct_supplement_low_quote2': '„“‚‘',   # Ukrainian, Belarusian
                               'matching_punct_supplement_low_quote3': '„“‘’',   # Russian
                               'matching_punct_supplement_default': '“”‘’',
                               'refreshable_punct': '“‘«‹',             # Refreshable across sentences
                               'unmatched': {},
                               'open-quote-legitimate-refresher': {},
                               'open-quote-legitimate-span': {},
                               'open-quote-refresher': {},
                               'nesting_l': {},
                               'nesting_r': {},
                               'open_first_lefts': {},    # Start of long quote
                               'last_close_right': {},
                               'refresher_lefts': defaultdict(list),   # Refresher open quote (often at start of para)
                               'last_legit_open_refresher_line_number': {},
                               'last_illegit_open_refresher_line_number': {},
                               'line_lengths': {},
                               'cross_snt_spans': defaultdict(list),
                               'triple_nesting': defaultdict(list),
                               'ref_translations': []}
        if self.lang_code in ('dan', 'deu'):
            self.punct_analysis['matching_punct'] += self.punct_analysis['matching_punct_supplement_low_quote']
        elif self.lang_code in ('ukr', 'bel'):
            self.punct_analysis['matching_punct'] += self.punct_analysis['matching_punct_supplement_low_quote2']
        elif self.lang_code in ('rus',):
            self.punct_analysis['matching_punct'] += self.punct_analysis['matching_punct_supplement_low_quote3']
        else:
            self.punct_analysis['matching_punct'] += self.punct_analysis['matching_punct_supplement_default']
        i, punct_list = 0, self.punct_analysis['matching_punct']
        while i < len(punct_list):
            punct_l, punct_r = punct_list[i], punct_list[i+1]
            self.punct_analysis[('lr', punct_l)] = punct_r
            self.punct_analysis[('rl', punct_r)] = punct_l
            self.punct_analysis['unmatched'][punct_l] = []
            self.punct_analysis['unmatched'][punct_r] = []
            self.punct_analysis['open-quote-legitimate-refresher'][punct_l] = []
            self.punct_analysis['open-quote-legitimate-refresher'][punct_r] = []
            self.punct_analysis['open-quote-legitimate-span'][punct_l] = []
            self.punct_analysis['open-quote-legitimate-span'][punct_r] = []
            self.punct_analysis['open-quote-refresher'][punct_l] = []
            self.punct_analysis['open-quote-refresher'][punct_r] = []
            self.punct_analysis['nesting_l'][punct_l] = []
            self.punct_analysis['nesting_r'][punct_r] = []
            i += 2
        for punct_l in self.punct_analysis['refreshable_punct']:
            self.punct_analysis['open_first_lefts'][punct_l] = None
        self.load_tok_resource()

    def load_tok_resource(self):
        wb_src_dir = Path(os.path.dirname(os.path.abspath(__file__)))
        tok_data_dir = wb_src_dir / "data-tok"
        for lang_code in (self.lang_code,):
            filename = tok_data_dir / f"tok-resource-{lang_code}.txt"
            if os.path.isfile(filename):
                with open(filename) as f:
                    for line in f:
                        if abbreviation := slot_value_in_double_colon_del_list(line, 'abbrev'):
                            self.abbreviations[lang_code].add(abbreviation)
                n_abbreviations = len(self.abbreviations[lang_code])
                sys.stderr.write(f"load_tok_resource {self.lang_code} {filename} {n_abbreviations} entries\n")

    def remove_empty_dicts(self):
        """Remove any empty dictionaries, which might have been created as empty to proscribe output order."""
        for key1 in ('block', 'notable-token'):
            blocks = self.analysis[key1].keys()
            blocks_with_dicts_to_be_deleted = []
            for block in blocks:
                block_dict = self.analysis[key1].get(block)
                if isinstance(block_dict, dict) and len(block_dict) == 0:
                    blocks_with_dicts_to_be_deleted.append(block)
            for block in blocks_with_dicts_to_be_deleted:
                del self.analysis[key1][block]

    def set_new_char_to_block_dict_entry(self, c: Union[str, int], block_name: str):
        """Set block_name for given character. Do not overwrite any previous value."""
        char = chr(c) if isinstance(c, int) else c
        if not self.char_to_block_dict.get(char):
            self.char_to_block_dict[char] = block_name

    def populate_char_to_block_dict(self):
        """Set block_name for characters (that differ from unicodedata block names)."""
        for char in '⁰¹²³⁴⁵⁶⁷⁸⁹':
            self.set_new_char_to_block_dict_entry(char, 'SUPERSCRIPT_DIGIT')
        for char in '₀₁₂₃₄₅₆₇₈₉':
            self.set_new_char_to_block_dict_entry(char, 'SUBSCRIPT_DIGIT')
        for char in 'ªº':
            self.set_new_char_to_block_dict_entry(char, 'SUPERSCRIPTS_AND_SUBSCRIPTS')
        for char in '               ፡':
            self.set_new_char_to_block_dict_entry(char, 'SPACE')
        for char in '­​‌‍﻿':
            self.set_new_char_to_block_dict_entry(char, 'ZERO_WIDTH')
        for char in '‏‎':
            self.set_new_char_to_block_dict_entry(char, 'DIRECTIONAL')
        for char in '$¢£¤¥':
            self.set_new_char_to_block_dict_entry(char, 'CURRENCY_SYMBOLS')
        # noinspection SpellCheckingInspection
        for char in "ʌɓɗɖɛəɡɠɨᵻɟᴋɫɲⁿɔɵᵽɹʃʉʋʊʒɣɩʔ":
            self.set_new_char_to_block_dict_entry(char, 'LATIN')
        self.set_new_char_to_block_dict_entry('ᵸ', 'CYRILLIC')
        # noinspection SpellCheckingInspection
        for char in "ᵉⁱᵏᵘ":
            self.set_new_char_to_block_dict_entry(char, 'LATIN_SUPERSCRIPT_LETTER')
        self.set_new_char_to_block_dict_entry('々', 'CJK')
        self.set_new_char_to_block_dict_entry('�', 'REPLACEMENT')
        for code_point in range(0x1D62, 0x1D66):
            self.set_new_char_to_block_dict_entry(code_point, 'LATIN_SUBSCRIPT_LETTER')
        for code_point in range(0x1C90, 0x1CC0):
            self.set_new_char_to_block_dict_entry(code_point, 'GEORGIAN')
        for code_point in range(0x2D00, 0x2D30):
            self.set_new_char_to_block_dict_entry(code_point, 'GEORGIAN')
        for code_point in range(0xFB00, 0xFB10):
            self.set_new_char_to_block_dict_entry(code_point, 'LATIN_ALPHABETIC_PRESENTATION_FORMS')
        for code_point in range(0xFB10, 0xFB20):
            self.set_new_char_to_block_dict_entry(code_point, 'ARMENIAN_ALPHABETIC_PRESENTATION_FORMS')
        for code_point in range(0xFB20, 0xFB4F):
            self.set_new_char_to_block_dict_entry(code_point, 'HEBREW_ALPHABETIC_PRESENTATION_FORMS')
        for code_point in range(0x00, 0x20):
            self.set_new_char_to_block_dict_entry(code_point, 'C0_CONTROL')
        self.set_new_char_to_block_dict_entry(0x7F, 'C0_CONTROL')
        for code_point in range(0x80, 0xA0):
            self.set_new_char_to_block_dict_entry(code_point, 'C1_CONTROL')
        for code_point in range(0x21, 0x07F):
            if regex.match(r'(?:\pP|\pS)', chr(code_point)):
                self.set_new_char_to_block_dict_entry(code_point, 'ASCII_PUNCTUATION')
        for code_point in range(0x30, 0x03A):
            self.set_new_char_to_block_dict_entry(code_point, 'ASCII_DIGIT')
        for code_point in range(0x0660, 0x066A):
            self.set_new_char_to_block_dict_entry(code_point, 'ARABIC_INDIC_DIGIT')
        for code_point in range(0x06F0, 0x06FA):
            self.set_new_char_to_block_dict_entry(code_point, 'EXTENDED_ARABIC_INDIC_DIGIT')
        for code_point in range(0xBC, 0xBF):
            self.set_new_char_to_block_dict_entry(code_point, 'VULGAR_FRACTION')
        for code_point in range(0x2150, 0x2160):
            self.set_new_char_to_block_dict_entry(code_point, 'VULGAR_FRACTION')
        self.set_new_char_to_block_dict_entry('↉', 'VULGAR_FRACTION')
        for code_point in range(0x2160, 0x2180):
            self.set_new_char_to_block_dict_entry(code_point, 'ROMAN_NUMERAL')
        self.set_new_char_to_block_dict_entry('ↄ', 'ARCHAIC_CLAUDIAN_LETTER')
        for code_point in range(0x2180, 0x2189):
            self.set_new_char_to_block_dict_entry(code_point, 'ARCHAIC_ROMAN_NUMERAL')
        for code_point in range(0x218A, 0x218C):
            self.set_new_char_to_block_dict_entry(code_point, 'TURNED_DIGIT')
        for code_point in range(0xA1, 0x0100):
            if regex.match(r'(?:\pP|\pS)', chr(code_point)):
                self.set_new_char_to_block_dict_entry(code_point, 'GENERAL_PUNCTUATION')
        for code_point in range(0x16F00, 0x16FA0):
            self.set_new_char_to_block_dict_entry(code_point, 'MIAO')
        for char in '،؍؛؞؟٪٭٫٬۔':
            self.set_new_char_to_block_dict_entry(char, 'ARABIC_PUNCTUATION')
        for char in '።፣፤፥፦፧':
            self.set_new_char_to_block_dict_entry(char, 'ETHIOPIC_PUNCTUATION')
        for char in '。．、·，！？；：（）［］【】「」『』《》〈〉':
            self.set_new_char_to_block_dict_entry(char, 'CHINESE_PUNCTUATION')
        for char in '।॥':
            self.set_new_char_to_block_dict_entry(char, 'DEVANAGARI_PUNCTUATION')
        for char in '՜՝՞։՛':
            self.set_new_char_to_block_dict_entry(char, 'ARMENIAN_PUNCTUATION')
        self.set_new_char_to_block_dict_entry(0xB5, 'LETTERLIKE_SYMBOLS')  # micro sign

    def pattern_to_regex(self, pattern: str):
        pattern = regex.sub(r'[]', '', pattern)
        active_abbreviations_regex = None
        if 'Abbreviation.' in pattern:
            reg_active_abbreviations = map(regex.escape, self.active_abbreviations[self.lang_code])
            active_abbreviations_regex = f"(?:{'|'.join(reg_active_abbreviations)})"
            pattern = regex.sub(r'Abbreviation\\?.', '', pattern)
        s = regex.escape(pattern)
        s = regex.sub('Xml', r'&(?:[aA][mM][pP];)*(?:#[xX][0-9A-Fa-f]{1,6}|#\\d{1,7}|[A-Za-z]{1,6});', s)
        s = regex.sub('WordWLM', r'[\\u064E-\\u0650]\\pL\\pM*(?:[\\u200C\\u200D]?\\pL\\pM*)*', s)
        if self.lang_code in ('enb', 'tuy'):
            s = regex.sub('Word', r"(?::|\\*|\\*:|/|\\*/)?\\pL+(?:'\\pL+)*'?", s)
        else:
            s = regex.sub('Word', r'\\pL\\pM*(?:[\\u200C\\u200D]?\\pL\\pM*)*', s)
        s = regex.sub('NumberWP', r'(?<!\\pN)\\pN{1,3}(?:\\.\\pN{3})+(?!\\.?\\pN)', s)
        s = regex.sub('NumberWC', r'(?<!\\pN)\\pN{1,3}(?:,\\pN{3})+(?!,?\\pN)', s)
        s = regex.sub('Number', r'\\pN+', s)
        s = regex.sub('Modifiers', r'\\pM{2,}', s)
        s = regex.sub('Modifier', r'\\pM', s)
        if active_abbreviations_regex:
            s = s.replace('', active_abbreviations_regex)
        return s

    def token_to_patterns(self, token: str) -> List[str]:
        # check for cached result
        if result := self.token_to_pattern_dict[token]:
            return result
        pattern = token
        pattern = regex.sub(r'[]', '', pattern)
        if self.lang_code:
            if m := regex.match(r'(.*?)((?:(?:\pL\pM*)+\.){2,})(.*)$', pattern):
                pre, abbreviation, post = m.group(1, 2, 3)
                if abbreviation in self.abbreviations[self.lang_code]:
                    self.active_abbreviations[self.lang_code].add(abbreviation)
                    pattern = pre + '' + post
        pattern = regex.sub('\u0640', '', pattern)  # tatweel
        pattern = regex.sub(r'&(?:[aA][mM][pP];)*(?:#[xX][0-9A-Fa-f]{1,6}|#\d{1,7}|[A-Za-z]{1,6});',
                            r'&;', pattern, regex.IGNORECASE)  # problem with IGNORECASE
        pattern = regex.sub(r'(?:%(?:25)*[0-9A-Fa-f]{2}){2,}',
                            r'%', pattern, regex.IGNORECASE)  # problem with IGNORECASE
        pattern = regex.sub(r'(?<!\pL\pM*|\pM)[\u064E-\u0650]\pL\pM*(?:[\u200C\u200D]?\pL\pM*)*', '', pattern)
        if self.lang_code in ('enb', 'tuy'):
            pattern = regex.sub(r"(?::|\*|\*:|/|\*/)?\pL+(?:'\pL+)*'?", 'Word', pattern)
        else:
            pattern = regex.sub(r"\pL\pM*(?:[\u00AD\u200C\u200Dʼ']?\pL\pM*)*", 'Word', pattern)
        pattern = regex.sub(r'\pM{2,}', 'Modifiers', pattern)
        pattern = regex.sub(r'\pM', 'Modifier', pattern)
        pattern = regex.sub(r'(?<!\pN)\pN{1,3}(\.\pN{3})+(?!\.?\pN)', 'NumberWP', pattern)
        pattern = regex.sub(r'(?<!\pN)\pN{1,3}(,\pN{3})+(?!,?\pN)', 'NumberWC', pattern)
        pattern = regex.sub(r'\pN+', 'Number', pattern)
        pattern = regex.sub(r'', 'Abbreviation.', pattern)
        pattern = regex.sub(r'', 'WordWLM', pattern)
        pattern = regex.sub(r'', 'Xml', pattern)
        pattern = regex.sub(r'', '\u0640', pattern)
        # if "\u00AD" in token:
        #     sys.stderr.write(f"  SH:{token} P:{pattern}\n")
        pattern1 = pattern
        pattern2 = regex.sub(r'(?:Word)+\u0640+(?:Word)+', 'Word', pattern)
        result = [pattern1]
        if pattern2 != pattern1:
            result.append(pattern2)
        for in_word_punct in "ʼ'\u00AD":
            # MODIFIER LETTER APOSTROPHE e.g. as in "donʼt"
            # regular apostrophe
            # soft hyphen
            if in_word_punct in token:
                if (in_word_punct == "'") and not regex.match(r"[^']*\pL\pM*(?:'\pL\pM*)+[^']*$", token):
                    continue
                if (in_word_punct == "\u00AD") and not regex.match(r"[^\u00AD]*\pL\pM*(?:\u00AD\pL\pM*)+[^\u00AD]*$", token):
                    continue
                pattern3 = regex.sub(r'[]', '', token)
                pattern3 = pattern3.replace(in_word_punct, '')
                pattern3 = regex.sub(r'\pL\pM*(?:[\u200C\u200D]?\pL\pM*)*', 'Word', pattern3)
                pattern3 = pattern3.replace('', in_word_punct)
                pattern3 = regex.sub(r'[.,;:!?})]+’[ ”»⌟]*$', '', pattern3)
                pattern3 = pattern3.lstrip("‘“«⌞([{ ")
                pattern3 = pattern3.rstrip(".,;:?!)]}”»⌟ ")
                result.append(pattern3)
                self.in_word_punct_patterns.add(pattern3)
        # Cache result, but avoid clogging run-time memory space
        if len(self.token_to_pattern_dict) < 1000000:
            self.token_to_pattern_dict[token] = result
        return result

    def snt_id(self, line_number: int, default: str = None) -> str:
        default_snt_id = default if default else str(line_number)
        return self.ref_id_dict.get(line_number, default_snt_id) if self.ref_id_dict else default_snt_id

    def punct_analysis_in_line(self, line: str, line_number: int):
        refreshable_punctuations = self.punct_analysis['refreshable_punct']
        punct_stack = self.punct_analysis['stack']
        last_non_space_char_position = len(line.rstrip()) - 1
        verbose = False  # (25420 <= line_number <= 25427)  # or (1730 < line_number < 1760)
        for char_pos, char in enumerate(line):
            # found left delimiter
            # Example for triple: https://www.biblegateway.com/passage/?search=Matthew+22%3A43-45&version=NIV
            # Example for "quad": https://www.biblegateway.com/passage/?search=ISA+7%3A3-9&version=ESV
            full_pos = (line_number, char_pos)
            full_pos2 = (line_number, char_pos, last_non_space_char_position)  # len helps gauge position in translation
            if right_char := self.punct_analysis.get(('lr', char), None):
                triple_nesting = ((len(punct_stack) >= 2)
                                   and (punct_stack[-2] == char)
                                   and (punct_stack[-1] in refreshable_punctuations)
                                   and (punct_stack[-2] in refreshable_punctuations)
                                   and (punct_stack[-1] != punct_stack[-2]))
                # if verbose and triple_nesting: print("PRELIM", line_number, char_pos, punct_stack)
                quad_nesting1 = (triple_nesting and line[char_pos+1:].lstrip().startswith(punct_stack[-1]))
                quad_nesting2 = ((len(punct_stack) >= 2)
                                 and (punct_stack[-1] == char)
                                 and (punct_stack[-1] in refreshable_punctuations)
                                 and (punct_stack[-2] in refreshable_punctuations)
                                 and (punct_stack[-1] != punct_stack[-2])
                                 and line[:char_pos].rstrip().endswith(punct_stack[-2]))
                if quad_nesting1 or quad_nesting2:
                    triple_nesting = False
                # if verbose and triple_nesting: print("TRIPLE", line_number, char_pos, punct_stack)
                # if verbose and quad_nesting1: print("QUAD1", line_number, char_pos, punct_stack)
                # if verbose and quad_nesting2: print("QUAD2", line_number, char_pos, punct_stack)
                # if triple_nesting and verbose:
                #     print("TRIPLE", char, full_pos2, self.snt_id(line_number), punct_stack)
                if ((char in self.punct_analysis['refreshable_punct'])
                        and self.punct_analysis['open_lefts'][char]
                        and (not triple_nesting)):
                    refresher_category = (self.open_quotation_refresher_classification(char, full_pos, line)
                                          or 'unmatched')
                    if refresher_category == 'unmatched':
                        open_first_pos = self.punct_analysis['open_first_lefts'][char]
                        if (open_first_pos and (open_first_pos[0] < line_number)
                                and (open_first_pos not in self.punct_analysis[refresher_category][char])):
                            self.punct_analysis[refresher_category][char].append(open_first_pos)
                    self.punct_analysis[refresher_category][char].append(full_pos2)
                    if verbose:
                        print('REFRESHER', line_number, char_pos, char, self.snt_id(line_number), refresher_category)
                else:
                    if verbose and triple_nesting:
                        print("TRIPLE2", char, full_pos2, self.snt_id(line_number), self.punct_analysis['stack_plus'])
                    if not self.punct_analysis['nesting_r'][right_char]:
                        self.punct_analysis['nesting_l'][char].append(full_pos)
                    self.punct_analysis['nesting_r'][right_char] = []
                    punct_stack.append(char)
                    self.punct_analysis['stack_plus'].append((char, full_pos2, self.snt_id(full_pos[0])))
                    self.punct_analysis['open_lefts'][char].append(full_pos)
                if char in self.punct_analysis['refreshable_punct']:
                    if self.punct_analysis['open_first_lefts'][char]:
                        self.punct_analysis['refresher_lefts'][char].append(full_pos2)
                    else:
                        self.punct_analysis['open_first_lefts'][char] = full_pos2
                self.punct_analysis['line_lengths'][line_number] = last_non_space_char_position
                self.punct_analysis['last_close_right'][right_char] = None
            # found right delimiter
            elif left_char := self.punct_analysis.get(('rl', char), None):
                self.punct_analysis['nesting_r'][char].append(full_pos)
                if verbose:
                    print('CLOSE', line_number, left_char, char, self.snt_id(line_number),
                          self.punct_analysis['stack_plus'], self.punct_analysis['open_lefts'][left_char])
                triple_nesting = ((len(punct_stack) >= 3)
                                  and (punct_stack[-1] == punct_stack[-3])
                                  and (punct_stack[-1] in refreshable_punctuations)
                                  and (punct_stack[-2] in refreshable_punctuations)
                                  and (punct_stack[-1] != punct_stack[-2]))
                popped_pos = None
                if punct_stack and (punct_stack[-1] == left_char):
                    popped_pos = self.punct_analysis['stack_plus'][-1][1]
                    del punct_stack[-1]
                    del self.punct_analysis['stack_plus'][-1]
                    if self.punct_analysis['open_lefts'][left_char]:
                        del self.punct_analysis['open_lefts'][left_char][-1]
                else:
                    last_close_right_pos = self.punct_analysis['last_close_right'].get(char)
                    if (last_close_right_pos and (last_close_right_pos[0] < line_number)
                            and (last_close_right_pos not in self.punct_analysis['unmatched'][char])):
                        self.punct_analysis['unmatched'][char].append(last_close_right_pos)
                        if verbose: print("FLAG", char, 'unmatched', last_close_right_pos)
                    self.punct_analysis['unmatched'][char].append(full_pos)
                    if verbose: print("FLAG", char, 'unmatched', full_pos)
                if triple_nesting and popped_pos:
                    span_info = self.span_info_with_ids(popped_pos, full_pos2)
                    self.punct_analysis['triple_nesting'][left_char].append(span_info)
                    if verbose:
                        print("**TRIPLE-SPAN", left_char, char, "TRIPLE" if triple_nesting else "", span_info)
                if popped_pos and not triple_nesting and self.punct_analysis['open_lefts'][left_char]:
                    # todo: possibly elaborate
                    log_message = f"-----CLEAN?? {left_char}, {char}, {self.punct_analysis['open_lefts'][left_char]}"
                    if log_message not in self.log_message_counts:
                        sys.stderr.write(log_message + "\n")
                    self.log_message_counts[log_message] += 1
                if ((left_char in self.punct_analysis['open_first_lefts'])
                        and (not (triple_nesting and popped_pos))
                        and (open_pos := self.punct_analysis['open_first_lefts'][left_char])):
                    if open_pos[0] < line_number:
                        span_info = self.span_info_with_ids(open_pos, full_pos2)
                        self.punct_analysis['cross_snt_spans'][left_char].append(span_info)
                        if verbose:
                            print("**CROSS", left_char, char, "TRIPLE" if triple_nesting else "",span_info)
                    self.punct_analysis['open_first_lefts'][left_char] = None
                if (left_char in self.punct_analysis['refreshable_punct']) and not triple_nesting:
                    self.punct_analysis['open_lefts'][left_char] = []
                self.punct_analysis['last_close_right'][char] = full_pos2
                self.punct_analysis['last_legit_open_refresher_line_number'][left_char] = None
                self.punct_analysis['last_illegit_open_refresher_line_number'][left_char] = None
                if verbose:
                    print('CLOSE2', line_number, left_char, char, self.snt_id(line_number),
                          self.punct_analysis['stack_plus'], self.punct_analysis['open_lefts'][left_char])
        if self.ref_id_dict:
            snt_id = self.snt_id(line_number)
            next_snt_id = self.snt_id(line_number+1, 'None')
            snt_id_tokens1 = snt_id.split()
            snt_id_tokens2 = next_snt_id.split()
            if (len(snt_id_tokens1) >= 2) and (len(snt_id_tokens2) >= 2) and (snt_id_tokens1[0] != snt_id_tokens2[0]):
                # if punct_stack: print('CLEAN at EOC?', snt_id, next_snt_id, self.punct_analysis['stack_plus'])
                while punct_stack:
                    popped_pos = self.punct_analysis['stack_plus'][-1][1]
                    popped_char = self.punct_analysis['stack_plus'][-1][0]
                    # print('  CLEAN at EOC unmatched', self.punct_analysis['stack_plus'][-1])
                    self.punct_analysis['unmatched'][popped_char].append(popped_pos)
                    del punct_stack[-1]
                    del self.punct_analysis['stack_plus'][-1]
                    if self.punct_analysis['open_lefts'][popped_char]:
                        del self.punct_analysis['open_lefts'][popped_char][-1]

    def span_info_with_ids(self, pos1: tuple, pos2: tuple) -> tuple:
        snt_id1 = self.snt_id(pos1[0])
        snt_id2 = self.snt_id(pos2[0])
        snt_id_span = self.combine_vref_start_end(snt_id1, snt_id2) if snt_id1 and snt_id2 else None
        return (pos1, pos2, snt_id_span) if snt_id_span else (pos1, pos2)

    @staticmethod
    def combine_vref_start_end(snt_id1: str, snt_id2: str) -> str:
        if snt_id1 == snt_id2:
            return snt_id1
        # Bible format
        m1 = regex.search(r'([A-Z1-3][A-Z][A-Z])\s+(\d+):(\d+)$', snt_id1)
        m2 = regex.search(r'([A-Z1-3][A-Z][A-Z])\s+(\d+):(\d+)$', snt_id2)
        if m1 and m2:
            if m1.group(1) == m2.group(1):
                if m1.group(2) == m2.group(2):
                    return f'{m1.group(1)} {m1.group(2)}:{m1.group(3)}-{m2.group(3)}'
                else:
                    return f'{m1.group(1)} {m1.group(2)}:{m1.group(3)}-{m2.group(2)}:{m2.group(3)}'
        return f"{snt_id1}-{snt_id2}"

    def punct_analysis_at_end(self):
        # to be called after last line to mark any open punctuation as unmatched
        if self.punct_analysis['stack_plus']:
            print("FINAL-PUNCT-STACK", self.punct_analysis['stack_plus'], len(self.punct_analysis['stack_plus']))
        ref_translation_names = [x.get('translation') for x in self.punct_analysis['ref_translations']
                                 if x.get('translation')]
        ref_translation_name_clause = ", ".join(ref_translation_names) if ref_translation_names else ''
        for punct_analysis_key, analysis_report_title, ass_class, ass_descr \
                in [('unmatched',
                     'Paired delimiters:    unmatched',
                     '-', f"Note regarding open quotation marks (e.g. {self.punct_analysis['refreshable_punct']})"
                          f"&xxxnbsp;&#xA;\n"
                          f" — Crossing delimiter pairs are flagged (e.g. “…[…”…]) &#xA;\n"
                          f"&xnbsp;whereas nested delimiter pairs are ok (e.g. “…[…]…”).\n"
                          f" — Suspicious repeated unclosed open quotation marks (e.g. «…«…») are flagged "
                          f"in both places.\n"
                          f" — ‘Suspicious’ means that they are not supported by any reference translation: "
                          f"{ref_translation_name_clause}\n"
                          f"Similarly, repeated close quotation marks (e.g. »…») are flagged in both places."),
                    ('open-quote-refresher',
                     'Paired delimiters:   refreshing open quotation mark (maybe ok)',
                     'o',
                     f'Refreshing open quotation mark does NOT fall inside a long quotation '
                     f'in a reference translation: {ref_translation_name_clause}\n'),
                    ('open-quote-legitimate-refresher',
                     'Paired delimiters: refreshing open quotation mark matched in reference (most likely ok)',
                     '+',
                     f'Refreshing open quotation mark has corresponding refreshing open quotation mark in '
                     f'a reference translation: {ref_translation_name_clause}'),
                    ('open-quote-legitimate-span',
                     'Paired delimiters:  refreshing open quotation mark inside reference quotation span (probably ok)',
                     '+',
                     f'Refreshing open quotation mark falls inside a long quotation '
                     f'in a reference translation: {ref_translation_name_clause}\n(Probably ok.)')]:
            for char in self.punct_analysis['matching_punct']:
                if example_pos_list := self.punct_analysis[punct_analysis_key][char]:
                    code_point = ord(char)
                    unicode_id = 'U+%04X' % code_point
                    unicode_name = self.unicode_name(char)
                    self.analysis['notable-token-meta'][analysis_report_title]['ass-class'] = ass_class
                    self.analysis['notable-token-meta'][analysis_report_title]['ass-descr'] = ass_descr
                    self.analysis['notable-token'][analysis_report_title][char] \
                        = {'token': char,
                           'id': unicode_id,
                           'name': unicode_name,
                           'count': len(example_pos_list),
                           'ex': list(map(lambda x: [char, x[0], x[1]], example_pos_list))}

    def refreshing_quote_candidate(self, char: str, open_line_number: int, open_char_pos: int, line: str) -> bool:
        """checks whether character (e.g. '“') is open quote at position 0 (or nearby) and has match on stack"""
        if self.punct_analysis.get(('lr', char)) \
                and self.punct_analysis['stack_plus'] \
                and (char == self.punct_analysis['stack_plus'][-1][0]):
            if open_char_pos == 0:
                return True
            else:
                char2 = line[0:open_char_pos].rstrip()  # Example: char==‘  char2==“
                if self.punct_analysis.get(('lr', char2)) \
                        and (len(self.punct_analysis['stack_plus']) >= 2) \
                        and (char2 == self.punct_analysis['stack_plus'][-2][0]):
                    return True
        else:
            last_illegit_orln = self.punct_analysis['last_illegit_open_refresher_line_number'][char]
            if last_illegit_orln and (open_line_number-last_illegit_orln <= 10):
                return True
        return False
        
    def open_quotation_refresher_classification(self, char: str, open_pos, line: str) -> str | None:
        result = None
        result_priority = 0
        result_value_order = (None, 'unmatched', 'open-quote-legitimate-span', 'open-quote-legitimate-refresher')
        ref_translations: list[dict] = self.punct_analysis['ref_translations']
        if ref_translations:
            for ref_translation in ref_translations:
                sub_result = self.open_quotation_refresher_classification_rec(char, open_pos, ref_translation)
                try:
                    sub_priority = result_value_order.index(sub_result)
                    if sub_priority > result_priority:
                        result = sub_result
                        result_priority = sub_priority
                except ValueError:
                    if not (sub_result in self.open_quot_refresh_class_prev_unexpected_sub_result_values):
                        sys.stderr.write(f'Warning from open_quotation_refresher_classification: '
                                         f'unexpected sub-result {sub_result}\n')
                        self.open_quot_refresh_class_prev_unexpected_sub_result_values.append(sub_result)
        if result in (None, 'unmatched'):
            open_line_number, open_char_pos = open_pos
            if self.refreshing_quote_candidate(char, open_line_number, open_char_pos, line):
                top_of_stack = self.punct_analysis['stack_plus'][-1]
                tos_full_pos = top_of_stack[1]
                tos_line_number = tos_full_pos[0]
                last_legit_orln = self.punct_analysis['last_legit_open_refresher_line_number'][char]
                last_illegit_orln = self.punct_analysis['last_illegit_open_refresher_line_number'][char]
                if (((open_line_number-tos_line_number <= 20)
                            or ((last_legit_orln is not None)
                                and (open_line_number-last_legit_orln <= 15)))
                        or ((last_illegit_orln is not None) and (open_line_number-last_illegit_orln <= 10))):
                    if tos_full_pos not in self.punct_analysis['open-quote-refresher'][char]:
                        self.punct_analysis['open-quote-refresher'][char].append(tos_full_pos)
                    self.punct_analysis['last_legit_open_refresher_line_number'][char] = open_line_number
                    return 'open-quote-refresher'
            if open_char_pos == 0:
                self.punct_analysis['last_illegit_open_refresher_line_number'][char] = open_line_number

        return result

    def open_quotation_refresher_classification_rec(self, char: str, open_pos: list[int, int], ref_translation: dict)\
            -> str | None:
        refresher_dict: dict | None = ref_translation.get('refresher-dict', None)
        cross_snt_span_dict: dict | None = ref_translation.get('cross-snt-span-dict', None)
        char_count: dict | None = ref_translation.get('char_count', None)
        ref_line_length_dict: dict | None = ref_translation.get('line-length', None)
        line_length_dict = self.punct_analysis['line_lengths']
        map_char = {'«': '“', '‹': '‘'}
        char2 = char
        if char_count and (char_count[char] == 0) and (char_count[map_char.get(char)]):
            char2 = map_char.get(char)
        open_line_number, open_char_pos = open_pos
        last_line_pos = line_length_dict.get(open_line_number)
        ref_last_line_pos = ref_line_length_dict.get(open_line_number)
        if refresher_dict:
            for refresher_elem in refresher_dict.get((char2, open_line_number), []):
                if self.similar_relative_line_position(open_char_pos, last_line_pos,
                                                       refresher_elem[0], ref_last_line_pos):
                    return 'open-quote-legitimate-refresher'
                # if 23300 <= open_line_number <= 26000:
                #     print('REFRESHER2', char, char2, open_pos, refresher_elem, last_line_pos, ref_last_line_pos)
        if cross_snt_span_dict:
            for cross_snt_span in cross_snt_span_dict.get((char2, open_line_number), []):
                cross_snt_start, cross_snt_end, *optional_args = cross_snt_span
                cross_snt_start_line_number, cross_snt_start_char_pos, cross_snt_start_len = cross_snt_start
                cross_snt_end_line_number, cross_snt_end_char_pos, cross_snt_end_len = cross_snt_end
                if cross_snt_start_line_number <= open_line_number <= cross_snt_end_line_number:
                    # if 26700 <= open_line_number <= 26800:
                    #     print('REFRESHER3', char, char2, open_pos, cross_snt_span, last_line_pos, ref_last_line_pos)
                    if ((open_line_number == cross_snt_start_line_number)
                            and (self.relative_line_pos_diff(open_char_pos, last_line_pos,
                                                             cross_snt_start_char_pos, cross_snt_start_len) <= 0.1)):
                        continue
                    elif ((open_line_number == cross_snt_end_line_number)
                            and (self.relative_line_pos_diff(open_char_pos, last_line_pos,
                                                             cross_snt_end_char_pos, cross_snt_end_len) >= -0.1)):
                        continue
                    else:
                        return 'open-quote-legitimate-span'
        return 'unmatched'

    @staticmethod
    def relative_line_pos_diff(a_pos, a_last_pos, b_pos, b_last_pos) -> float:
        if a_last_pos or b_last_pos:
            a_rel_pos = a_pos/(a_last_pos or b_last_pos)
            b_rel_pos = b_pos/(b_last_pos or a_last_pos)
            return a_rel_pos - b_rel_pos
        return 0

    def similar_relative_line_position(self, a_pos, a_last_pos, b_pos, b_last_pos, max_rel_diff: float = 0.25) -> bool:
        return abs(self.relative_line_pos_diff(a_pos, a_last_pos, b_pos, b_last_pos)) <= max_rel_diff

    @staticmethod
    def rearrange_selected_tokens(tokens: list[str]) -> list[str]:
        """Make single tokens out of “ ‘ and of ’ ”"""
        # tokens = regex.findall(r'((?:[“‘][ \u202F][“‘])?\S+(?![ \u202F][’”])(?:[’”](?:[ \u202F][’”])*)?)', line)
        i = 1
        while i < len(tokens):
            if ((tokens[i-1].endswith('“') and tokens[i].startswith('‘'))
                    or (tokens[i-1].endswith('‘') and tokens[i].startswith('“'))
                    or (tokens[i-1].endswith('’') and tokens[i] == '”')
                    or (tokens[i-1].endswith('”') and tokens[i] == '’')):
                tokens = tokens[:i-1] + [' '.join(tokens[i-1:i+1])] + tokens[i+1:]
            else:
                i += 1
        return tokens

    def collect_counts_and_examples_in_line(self, line: str, line_number: int):
        max_token_examples = max(self.max_n_token_examples, self.max_n_viz_examples)
        self.analysis['n_characters'] += len(line)
        line = line.strip()
        if line == '<range>':
            return
        # line_id = str(line_number)
        char_position = 0
        for char in line:
            self.character_count[char] += 1
            char_position += 1
            if len(self.token_examples[char]) < max_token_examples:
                # if char.isalpha():
                if regex.search(r'(?:\pL|\pM|�)', char):
                    token_examples = regex.findall(rf'((?:\pL\pM*|�)*\pM*{char}\pM*(?:\pL\pM*|�)*)', line)
                elif char.isnumeric():
                    token_examples = regex.findall(rf'(\pN*{char}\pN*)', line)
                else:
                    token_examples = [char]
                for token_example in token_examples:
                    token_tuple = [token_example, line_number]
                    if len(self.token_examples[char]) < max_token_examples \
                            and (token_tuple not in self.token_examples[char]):
                        self.token_examples[char].append(token_tuple)
            # uc_block = None
            if not (uc_script := self.char_to_script_dict[char]):
                uc_block = self.unicode_block(char)
                uc_script = self.unicode_script(uc_block)
            if len(self.script_lines[uc_script]) < self.max_script_lines:
                self.script_lines[uc_script].add(line_number)
        words = regex.findall(r'((?:\pL\pM*){2,})', line, re.IGNORECASE)
        complex_chars = regex.findall(r'(\pL\pM+)', line, re.IGNORECASE)
        xml_esc_dec_tokens = regex.findall(r'(&#\d{1,7};)', line, regex.IGNORECASE)
        xml_esc_hex_tokens = regex.findall(r'(&#X[0-9A-F]{1,6};)', line, regex.IGNORECASE)
        xml_esc_abc_tokens = regex.findall(r'(&(?:[a-z]{1,6});)', line, regex.IGNORECASE)
        xml_esc_nst_tokens = regex.findall(r'&(?:amp;)+(?:#X[0-9A-F]{1,6}|#\d{1,7}|[a-z]{1,6});',
                                           line, regex.IGNORECASE)
        for token in words + complex_chars + xml_esc_dec_tokens + xml_esc_hex_tokens \
                     + xml_esc_abc_tokens + xml_esc_nst_tokens:
            self.token_count[token] += 1
            token_tuple = [token, line_number]
            if (len(self.token_examples[token]) < max_token_examples) \
                    and (token_tuple not in self.token_examples[token]):
                self.token_examples[token].append(token_tuple)
        # tokens = regex.findall(r'((?:[“‘][ \u202F][“‘])?\S+(?![ \u202F][’”])(?:[’”](?:[ \u202F][’”])*)?)', line)
        tokens = regex.findall(r'(\S+)', line)
        tokens = self.rearrange_selected_tokens(tokens)
        # if line_number in (59, 507, 3848, 3848, 509): print("TOK", line_number, tokens, line)
        for token in tokens:
            if self.pattern_characters_of_interest_re.search(token) \
                    or regex.search(r'(?<!\pL\pM*)\pM', token):
                token_tuple = [token, line_number]
                for pattern in self.token_to_patterns(token):
                    self.pattern_count[pattern] += 1
                    if len(self.pattern_examples[pattern]) < max_token_examples \
                            and (token_tuple not in self.pattern_examples[pattern]):
                        self.pattern_examples[pattern].append(token_tuple)
                    if len(self.pattern_lines[pattern]) < self.max_bad_pattern_lines:
                        self.pattern_lines[pattern].add(line_number)

    def collect_counts_and_examples_in_file(self, input_file: IO, total_bytes=None, progress_bar=True) -> None:
        """Collect counts and examples for characters, tokens, and patterns occurring in file."""
        line_number = 0
        n_empty_lines = 0
        st = time.time()
        prefix = 'Checking'
        with (tqdm(input_file, total=total_bytes, disable=not progress_bar, unit='b', unit_scale=True,
                  dynamic_ncols=True, desc=prefix) as data_bar):
            try:
                for line in data_bar:
                    line_w_rtf_delimiter_adjustments = None
                    line_number += 1
                    if not re.match('\S', line):
                        n_empty_lines += 1
                    if progress_bar:
                        line_speed = int(line_number / (time.time() - st))
                        data_bar.set_postfix_str(f'{line_speed}L/s', refresh=False)
                        data_bar.set_description_str(f'{prefix} {line_number}', refresh=False)
                        data_bar.update(len(line.encode()))  # bytes
                    self.collect_counts_and_examples_in_line(line, line_number)
                    ref_id = self.snt_id(line_number)
                    self.corpus[ref_id] = line
                    line_rtl = ScriptDirection.string_is_right_to_left(line)
                    if line_rtl:
                        if not self.corpus_w_rtf_delimiter_adjustments.get(ref_id):
                            if self.script_direction.text_contains_switchable_chars(line):
                                line_w_rtf_delimiter_adjustments \
                                    = self.script_direction.switch_delimiters_for_rtl_scripts(line)
                                self.corpus_w_rtf_delimiter_adjustments[ref_id] = line_w_rtf_delimiter_adjustments
                    self.punct_analysis_in_line(line_w_rtf_delimiter_adjustments or line, line_number)
            # Exception for safety only. Should not occur.
            except UnicodeError as error:
                sys.stderr.write(f"*** Unicode error: {error}\n")
                sys.stderr.write(f"***    Input aborted. The input is not in valid UTF-8 encoding.\n")
                if input_file is sys.stdin:
                    sys.stderr.write(f"***    For a more encoding-robust input, consider using -i <input-filename> "
                                     f"instead of reading from STDIN.\n")
            self.punct_analysis_at_end()
        self.analysis['n_lines'] = line_number
        self.analysis['n_empty_lines'] = n_empty_lines
        for char in self.character_count.keys():
            self.script_direction.add_stats(char, self.character_count[char])
        if self.script_direction.is_right_to_left():
            sys.stderr.write(self.script_direction.report(details=True))

    @staticmethod
    def unicode_category(char) -> str:
        """Safe version of character to Unicode category. Example: 'a' -> 'Ll' (lowercase letter)"""
        try:
            unicode_cat = ud.category(char)
        except ValueError:
            unicode_cat = '_UNDEFINED_'
        return unicode_cat

    def unicode_name(self, char) -> str:
        """Safe version of character to Unicode name,
        which also includes locally defined names, e.g. for control characters.
        Example: 'a' -> 'LATIN SMALL LETTER A'"""
        if unicode_name := self.char_to_name_dict.get(char):
            return unicode_name
        try:
            unicode_name = ud.name(char)
        except ValueError:
            unicode_name = '_UNDEFINED_'
        return unicode_name

    def unicode_block(self, char) -> str:
        """Safe version of character to Unicode block, which also includes locally defined blocks.
        Example: 'a' -> 'BASIC_LATIN'"""
        if block_name := self.char_to_block_dict[char]:
            return block_name
        try:
            block_name = unicodeblock.blocks.of(char) or 'OTHER'
            if block_name == 'OTHER':
                code_point = ord(char)
                if 0x2B820 <= code_point <= 0x2CEA1:
                    block_name = 'CJK_UNIFIED_IDEOGRAPHS'
        except ValueError:
            block_name = '_UNDEFINED_'
        self.char_to_block_dict[char] = block_name
        return block_name

    def unicode_script(self, unicode_block: str) -> Optional[str]:
        """Maps character to script.
        Examples: 'a' -> 'LATIN', 'ä' -> 'LATIN' (collapses multiple Latin blocks to 'Latin')"""
        if unicode_block:
            if s := self.unicode_block_to_script_dict[unicode_block]:
                return s
            s = unicode_block
            s = re.sub(r'^Basic[-_ ]+', '', s, flags=re.IGNORECASE)
            s = re.sub(r'^Supplemental[-_ ]+', '', s, flags=re.IGNORECASE)
            s = re.sub(r'[-_ ]+Supplementary(?:[-_ ][A-Z])?$', '', s, flags=re.IGNORECASE)
            s = re.sub(r'[-_ ]+Additional(?:[-_ ][A-Z])?$', '', s, flags=re.IGNORECASE)
            s = re.sub(r'[-_ ]+Supplement(?:[-_ ][A-Z])?$', '', s, flags=re.IGNORECASE)
            s = re.sub(r'[-_ ]+Extended(?:[-_ ]Letter)?(?:[-_ ][A-Z])?$', '', s, flags=re.IGNORECASE)
            s = re.sub(r'[-_ ]+Extension(?:[-_ ][A-Z])?$', '', s, flags=re.IGNORECASE)
            s = re.sub(r'[-_ ]+(?:Alphabetic[-_ ]?)?Presentation[-_ ]?Forms(?:[-_ ][A-Z])?$',
                       '', s, flags=re.IGNORECASE)
            s = re.sub(r'(?:-[A-Z1-9])?$', '', s, flags=re.IGNORECASE)
            s = re.sub(r'^(ENCLOSED[-_ ]ALPHANUMERIC)$', r'\1S', s)
            s = re.sub(r'^([Ee]nclosed[-_ ][Aa]lphanumeric)$', r'\1s', s)
            if s in ('CJK_UNIFIED_IDEOGRAPHS', 'CJK_COMPATIBILITY_IDEOGRAPHS'):
                s = 'CJK'
            self.unicode_block_to_script_dict[unicode_block] = s
            return s
        else:
            return None

    @staticmethod
    def unicode_form(s: str, default: Optional[str] = None) -> str:
        if ud.normalize('NFC', s) == s:
            return 'NFC'
        elif ud.normalize('NFD', s) == s:
            return 'NFD'
        elif ud.normalize('NFKC', s) == s:
            return 'NFKC'
        elif ud.normalize('NFKD', s) == s:
            return 'NFKD'
        else:
            return default

    @staticmethod
    def modified_unicode_script(unicode_cat: str, unicode_script: str) -> str:
        if unicode_script:
            if unicode_cat.startswith('M') and not regex.search(r'(?:MODIFIER|MARK|SELECTOR)',
                                                                unicode_script, regex.IGNORECASE):
                unicode_script += "_MODIFIERS"
            elif unicode_cat.startswith('P') and not regex.search(r'(?:PUNCT)', unicode_script):
                unicode_script += "_PUNCTUATION"
        return unicode_script

    def build_char_to_script_dict(self) -> None:
        for cp in range(0x20000):
            char = chr(cp)
            unicode_cat = self.unicode_category(char)
            unicode_block = self.unicode_block(char)
            unicode_script = self.unicode_script(unicode_block)
            unicode_script = self.modified_unicode_script(unicode_cat, unicode_script)
            if unicode_script:
                self.char_to_script_dict[char] = unicode_script

    def assess_pattern(self, pattern_character_of_interest: str, pattern: str) -> Tuple[str, str]:
        ass_class, ass_descr = '', ''
        if len(pattern_character_of_interest) == 1:
            ass_char_name = self.unicode_name(pattern_character_of_interest) or pattern_character_of_interest
        else:
            ass_char_name = pattern_character_of_interest
        a = "an" if regex.match('AEIOU', ass_char_name, re.IGNORECASE) else "a"
        # count = self.pattern_count[pattern]
        if (pattern_character_of_interest in '।॥.።։!?,፣;፤:፦،؛؟۔)]>”’›»⌟') and pattern.startswith(pattern_character_of_interest):
            ass_class = '-'
            ass_descr = (f'Token starts with {a} {ass_char_name} {pattern_character_of_interest}\n'
                         f'Please check whether there is any spurious space before it.')
        if (pattern_character_of_interest in '([<“‘‹«⌞‚„') and pattern.endswith(pattern_character_of_interest):
            ass_class = '-'
            ass_descr = (f'Token ends in {a} {ass_char_name} {pattern_character_of_interest}\n'
                         f'Please check whether there is any spurious space after it.')
        if regex.search(r'''Word:?[„“”]?[.።։।॥!?,፣;፤:፦،؛؟۔«»'][„“”]?Word''', pattern):
            ass_class = '-'
            ass_descr = (f'Word token includes {a} {ass_char_name} {pattern_character_of_interest}\n'
                         f'Please check for any missing space.')
        if regex.search(r'[:፦;፤,፣،.።।։]{2}', pattern) and not ('..' in pattern):
            ass_class = '-'
            ass_descr = (f'Word token includes {a} {ass_char_name} {pattern_character_of_interest}\n'
                         f'with multiple competing end-of-clause marks.')
        if regex.search(r'[`−]', pattern):
            ass_class = '-'
            ass_descr = (f'Word token includes {a} {ass_char_name} {pattern_character_of_interest}\n'
                         f'which is an unusual character.')
        # ?? etc.
        if (pattern_character_of_interest in '-?!,？՞') and ((pattern_character_of_interest * 2) in pattern):
                ass_class = '-'
                ass_descr = f'Word token includes a double {ass_char_name} {pattern_character_of_interest}\n'
        for bad_substring in ["//", "\u00AD\u00AD", "<SOFT HYPHEN><SOFT HYPHEN>"]:
            if bad_substring in pattern:
                ass_class = '-'
                ass_descr = (f"Word token includes suspicious sub-sequence "
                             f"'{self.repl_invisible_chars_in_pattern(bad_substring)}'\n")
        if regex.match(
                #  \u202f is narrow space
                f'([\\(\\[])?([“‘‚„«‹⌞]|“‘|“[ \u202f]*‘|‘[ \u202f]“)?(Word(?:ʼWord)*(-Word(?:ʼWord)*)*ʼ?|WordWLM|Number|NumberWP|NumberWC)([।॥.።։,፣;፤!?:፦،؛؟۔])?((?:”[ \u202f]’[ \u202f]”|”[ \u202f]’|’[.።?! \u202f]”|’”|[”’»›⌟"])[.።]?)?([\)\]])?$',
                pattern):
            ass_class = '+'
        elif regex.match(
                f'([\\(\\[])?([“‘‚„«‹⌞]|“‘|“[ \u202f]*‘|‘[ \u202f]“)?(Word(?:ʼWord)*(-Word(?:ʼWord)*)*ʼ?|WordWLM|Number|NumberWP|NumberWC)([।॥.።։,፣;፤!?:፦،؛؟۔])?[\)\]]((?:”[ \u202f]’[ \u202f]”|”[ \u202f]’|’[.።?! \u202f]”|’”|[”’»›⌟"]))?$',
                pattern):
            ass_class = '+'
        elif regex.match(
                f'([\\(\\[])?([“‘‚„«‹⌞]|“‘|“[ \u202f]*‘|‘[ \u202f]“)?(Word(?:ʼWord)*(-Word(?:ʼWord)*)*ʼ?|WordWLM|Number|NumberWP|NumberWC)[\)\]]([।॥.።։,፣;፤!?:፦،؛؟۔])?((?:”[ \u202f]’[ \u202f]”|”[ \u202f]’|’[.።?! \u202f]”|’”|[”’»›⌟"]))?$',
                pattern):
            ass_class = '+'
        elif regex.match(f'([\\(\\[])?([“‘‚„«‹⌞]|“‘|“[ \u202f]‘|“[ \u202f]‘[ \u202f]“|‘[ \u202f]“)?(Word(?:ʼWord)*(-Word(?:ʼWord)*)*ʼ?|WordWLM|Number|NumberWP|NumberWC)([”’»›⌟"])?([\)\]])?([।॥.።։,፣;፤!?:፦،؛؟۔])?$',
                       pattern):
            ass_class = '+'
        elif regex.search(r'^Word(ʼWord)+$', pattern):  # ʼ (U+02BC MODIFIER LETTER APOSTROPHE)
            ass_class = '+'
        elif regex.search(r'^(?:(?:“|‘)?Word(?:”|’)?(?:）|\))?(?:？|՞|，|՝|：|、|；|．|）))+(?:(?:“|‘|（)?Word(?:？|՞|，|՝|：|:|、|；|．|）)*(?:”|’|’”)?)?$',
                          pattern):
            ass_class = '+'
        elif regex.search(r'^（?“?Word(?:？|՞|．)?(?:’|”|’”)?）?$', pattern):
            ass_class = '+'
        elif regex.search(r'^Word（“?Word？?(?:’|”)?）?$', pattern):
            ass_class = '+'
        if (pattern_character_of_interest == "ORPHAN MODIFIER") and ("Modifier" in pattern):
            if "Word" not in pattern:
                ass_class = '-'
                ass_descr = 'Word token includes a Modifier without any Letter'
            elif not regex.search('Modifiers?Word', pattern) or regex.search('WordModifier', pattern):
                ass_class = '-'
                ass_descr = 'Modifier in pattern disconnected from any Letter'
        # if ass_class.startswith('-'): sys.stderr.write(f"{ass_class} {pattern} ({count}) {ass_descr}\n")
        return ass_class, ass_descr

    def update_pattern_class_counts(self, pattern_character_of_interest: str, pattern: Optional[str],
                                    assess_class: str, pattern_count: int) -> None:
        updated_counts = self.pattern_class_counts[(pattern_character_of_interest, pattern)]
        if assess_class == '-':
            updated_counts[0] += pattern_count
        elif assess_class == '+':
            updated_counts[2] += pattern_count
        else:
            updated_counts[1] += pattern_count
        self.pattern_class_counts[(pattern_character_of_interest, pattern)] = updated_counts

    def aggregate(self) -> None:
        """Aggregate raw counts and examples into result Wildebeest analysis structure."""
        # Collect info on letter scripts (e.g. LATIN, CYRILLIC), number scripts (e.g. ASCII_DIGIT, ARABIC_INDIC_DIGIT),
        #    other scripts (e.g. ASCII_PUNCTUATION, GENERAL_PUNCTUATION, SPACE)
        for char in sorted(self.character_count):
            unicode_cat = self.unicode_category(char)
            unicode_block = self.unicode_block(char)
            unicode_script = self.unicode_script(unicode_block)
            unicode_script = self.modified_unicode_script(unicode_cat, unicode_script)
            if unicode_cat.startswith('L') \
                    and unicode_block not in ('SPACING_MODIFIER_LETTERS', 'MODIFIER_TONE_LETTERS'):
                if unicode_script:
                    count = self.character_count[char]
                    self.script_count_letter[unicode_script] += count
                    self.script_examples_letter[unicode_script] += char
            elif unicode_cat.startswith('N'):  # number
                if unicode_script:
                    count = self.character_count[char]
                    self.script_count_number[unicode_script] += count
                    self.script_examples_number[unicode_script] += char
            else:
                if unicode_script:
                    unicode_script = self.modified_unicode_script(unicode_cat, unicode_script)
                    count = self.character_count[char]
                    self.script_count_other[unicode_script] += count
                    self.script_examples_other[unicode_script] += char
        unicode_scripts_letter = sorted(self.script_count_letter, key=self.script_count_letter.get, reverse=True)
        unicode_scripts_number = sorted(self.script_count_number, key=self.script_count_number.get, reverse=True)
        unicode_scripts_other = sorted(self.script_count_other, key=self.script_count_other.get, reverse=True)
        dominant_script_letter = unicode_scripts_letter[0] if unicode_scripts_letter else None
        dominant_script_number = unicode_scripts_number[0] if unicode_scripts_number else None
        for unicode_script in unicode_scripts_letter:
            self.analysis['letter-script'][unicode_script] = {'count': self.script_count_letter[unicode_script]}
            script_examples_letter = self.script_examples_letter.get(unicode_script, "")
            if unicode_script != dominant_script_letter and len(script_examples_letter) <= 500:
                self.analysis['letter-script'][unicode_script]['ex'] = script_examples_letter
                self.analysis['letter-script'][unicode_script]['lines'] = sorted(self.script_lines[unicode_script])
        for unicode_script in unicode_scripts_number:
            self.analysis['number-script'][unicode_script] = {'count': self.script_count_number[unicode_script]}
            script_examples_number = self.script_examples_number.get(unicode_script, "")
            if ((len(script_examples_number) <= 80)
                    or (unicode_script != dominant_script_number and len(script_examples_number) <= 500)):
                self.analysis['number-script'][unicode_script]['ex'] = script_examples_number
                self.analysis['number-script'][unicode_script]['lines'] = sorted(self.script_lines[unicode_script])
        for unicode_script in unicode_scripts_other:
            self.analysis['other-script'][unicode_script] = {'count': self.script_count_other[unicode_script]}
            script_examples_other = self.script_examples_other.get(unicode_script, "")
            if len(script_examples_other) <= 80:
                self.analysis['other-script'][unicode_script]['ex'] = script_examples_other
                self.analysis['other-script'][unicode_script]['lines'] = sorted(self.script_lines[unicode_script])
        # Collect info of characters by block (e.g. BASIC_LATIN, ASCII_PUNCTUATION).
        for char in sorted(self.character_count):
            count = self.character_count[char]
            code_point = ord(char)
            unicode_id = 'U+%04X' % code_point
            unicode_name = self.unicode_name(char)
            unicode_block = self.unicode_block(char)
            # unicode_cat = self.unicode_category(char)
            # if (unicode_cat.startswith('L') and (dominant_script_letter == 'LATIN' and re.match('[a-zA-Z]$', char))) \
            #         or (dominant_script_letter == 'ETHIOPIC' and char in '፡።፣፤፥፦') \
            #         or (dominant_script_letter == 'ARABIC' and char in '۔،؛؟') \
            #         or (dominant_script_letter == 'HEBREW' and char in '־׀׃׆׳״') \
            #         or (dominant_script_letter in ['DEVANAGARI', 'BENGALI', 'GURMUKHI', 'ORIYA', 'TELUGU']
            #             and char in '।॥॰') \
            #         or (dominant_script_letter == 'TIBETAN' and char in '་༌།༎༼༽྅') \
            #         or (dominant_script_letter in ['CJK_UNIFIED_IDEOGRAPHS', 'HIRAGANA']
            #             and char in '·、。！（），：；？「」『』《》') \
            #         or (dominant_script_letter == 'GREEK' and char in ';·᾽΄᾿') \
            #         or (dominant_script_letter == 'MYANMAR' and char in '၊။၌၍၎၏႟') \
            #         or (dominant_script_letter == 'KHMER' and char in '។៕៖៚') \
            #         or (dominant_script_letter == 'SYRIAC' and char in '܀܁܅܈') \
            #         or (dominant_script_letter == 'UNIFIED_CANADIAN_ABORIGINAL_SYLLABICS' and char in '᙭᙮'):
            #     continue
            is_surrogate = code_point in range(0xDC80, 0xDD00)
            self.analysis['block'][unicode_block][char] \
                = {'char': '�' if is_surrogate else char,
                   'id': f'0x{(code_point - 0xDC00):X}' if is_surrogate else unicode_id,
                   'name': f'UTF-8 ENCODING ERROR (BYTE SURROGATE: {unicode_id})' if is_surrogate else unicode_name,
                   'count': count,
                   'ex': self.token_examples[char]}
        # noinspection PyBroadException
        try:
            _sorted_tokens = sorted(list(self.token_count.keys()) + list(self.character_count.keys()))
        except Exception:
            sys.stderr.write(f'sorted_tokens*** {self.token_count.keys()} :: {self.character_count.keys()}\n')
        for token in sorted(list(self.token_count.keys()) + list(self.character_count.keys())):
            # Check token for any non-canonical form (e.g. e + ́ instead of composed é; wrong order of modifiers)
            self.wildebeest.set_lv(token)
            count = self.token_count[token] or self.character_count[token]
            if regex.match(r'\pL\pM*$', token):
                norm0 = token
                norm1 = self.wildebeest.normalize_arabic_pres_form_characters(norm0)
                norm2 = self.wildebeest.normalize_ligatures(norm1)
                norm3 = self.wildebeest.normalize_hangul(norm2)
                norm4 = self.wildebeest.repair_combining_modifiers_with_nukta(norm3)
                norm5 = self.wildebeest.apply_combining_modifiers_compose(norm4)
                norm6 = self.wildebeest.apply_combining_modifiers_decompose(norm5)
                norm = norm6
                if norm != token:
                    count2 = self.token_count[norm] or self.character_count[norm]
                    changes = []
                    if norm1 != norm0:
                        changes.append('arabic-presentation')
                    if norm2 != norm1:
                        changes.append('ligature')
                    if norm3 != norm2:
                        changes.append('hangul')
                    if norm4 != norm3:
                        changes.append('moved-nukta')
                    if norm5 != norm4:
                        changes.append('compose')
                    if norm6 != norm5:
                        changes.append('decompose')
                    unicode_form = self.unicode_form(token)
                    unicode_form2 = self.unicode_form(norm)
                    if sorted(token) == sorted(norm):
                        form_clause = ''
                        form_clause2 = 'REORDERED, '
                    elif sorted(set(token)) == sorted(set(norm)):
                        form_clause = ''
                        form_clause2 = 'REMOVED-DUPLICATE-DIACRITIC, '
                    elif changes == ['arabic-presentation']:
                        form_clause = ''
                        form_clause2 = 'NORM-ARABIC-PRES-FORM, '
                    elif changes == ['moved-nukta', 'compose']:
                        form_clause = ''
                        form_clause2 = 'REORDERED-AND-COMPOSED, '
                    elif unicode_form == 'NFD' and unicode_form2 == 'NFC' and changes == ['compose']:
                        form_clause = f'{unicode_form}, '
                        form_clause2 = f'{unicode_form2}, '
                    elif unicode_form is None and unicode_form2 in ['NFC', 'NFD'] \
                            and (changes == ['compose'] or changes == ['decompose']):
                        form_clause = ''
                        form_clause2 = f'{unicode_form2}, '
                    else:
                        form_clause = f'{unicode_form}, '
                        form_clause2 = f'{unicode_form2}, '
                    self.analysis['non-canonical'][token] \
                        = {'orig': token, 'norm': norm, 'orig-count': count, 'norm-count': count2,
                           'orig-form': form_clause, 'norm-form': form_clause2, 'changes': changes}
            elif self.token_count[token] == 0:
                pass
            # Check for XML escape token
            elif token.startswith('&'):
                # noinspection SpellCheckingInspection
                if regex.match(r'&(?:amp|apos|gt|lt|nbsp|quot);$', token, regex.IGNORECASE):
                    self.analysis['notable-token']['XML ESCAPE TOKENS (BASIC)'][token] \
                        = {'token': token,
                           'count': self.token_count[token],
                           'ex': self.token_examples[token]}
                elif regex.match(r'&(?:[a-z]{1,6});$', token, regex.IGNORECASE):
                    self.analysis['notable-token']['XML ESCAPE TOKENS (EXTENDED)'][token] \
                        = {'token': token,
                           'count': self.token_count[token],
                           'ex': self.token_examples[token]}
                elif regex.match(r'&#\d{1,7};$', token, regex.IGNORECASE):
                    self.analysis['notable-token']['XML ESCAPE TOKENS (DECIMAL)'][token] \
                        = {'token': token,
                           'count': self.token_count[token],
                           'ex': self.token_examples[token]}
                elif regex.match(r'&#X[0-9A-F]{1,6};$', token, regex.IGNORECASE):
                    self.analysis['notable-token']['XML ESCAPE TOKENS (HEX)'][token] \
                        = {'token': token,
                           'count': self.token_count[token],
                           'ex': self.token_examples[token]}
                elif regex.match(r'&(?:amp;)+(?:#X[0-9A-F]{1,6}|#\d{1,7}|[a-z]{1,6});$', token, regex.IGNORECASE):
                    self.analysis['notable-token']['XML ESCAPE TOKENS (NESTED)'][token] \
                        = {'token': token,
                           'count': self.token_count[token],
                           'ex': self.token_examples[token]}
            else:
                # Check for token with characters with multiple scripts
                script_dict = {}
                for char in token:
                    if char.isalpha():
                        unicode_block = self.unicode_block(char)
                        unicode_script = self.unicode_script(unicode_block)
                        script_dict[unicode_script] = True
                n_base_scripts = len(script_dict)
                for script in ('SPACING_MODIFIER_LETTERS', 'MODIFIER_TONE_LETTERS'):
                    if script_dict.get(script):
                        n_base_scripts -= 1
                if n_base_scripts >= 2:
                    key2 = f"WORDS WITH CHARACTERS FROM MULTIPLE SCRIPTS ({', '.join(sorted(script_dict.keys()))})"
                    self.analysis['notable-token'][key2][token] \
                        = {'token': token,
                           'count': self.token_count[token],
                           'ex': self.token_examples[token]}
        # Check for patters with characters of interest (such as @)
        corpus_rtl = self.script_direction.is_right_to_left()
        for orig_pattern in self.pattern_count:
            pattern = orig_pattern
            if corpus_rtl and self.script_direction.text_contains_switchable_chars(pattern):
                adj_pattern = self.script_direction.switch_delimiters_for_rtl_scripts(orig_pattern, skip_rtl_check=True)
                pattern = adj_pattern
            self.wildebeest.set_lv(pattern)
            for pattern_character_of_interest in self.pattern_characters_of_interest:
                if pattern_character_of_interest in orig_pattern:
                    key2 = f"TOKENS WITH {pattern_character_of_interest} " \
                           f"({'U+%04X' % ord(pattern_character_of_interest)} " \
                           f"{self.unicode_name(pattern_character_of_interest)})"
                    pattern_count = self.pattern_count[orig_pattern]
                    self.analysis['pattern'][key2][orig_pattern] \
                        = {'pattern': self.repl_invisible_chars_in_pattern(pattern),
                           'count': pattern_count,
                           'ex': self.pattern_examples[orig_pattern],
                           'lines': sorted(self.pattern_lines[orig_pattern])}
                    ass_class, ass_descr = self.assess_pattern(pattern_character_of_interest, pattern)
                    self.update_pattern_class_counts(key2, orig_pattern, ass_class, pattern_count)
                    self.update_pattern_class_counts(key2, None, ass_class, pattern_count)
                    if ass_class and isinstance(ass_descr, str):
                        self.analysis['pattern'][key2][orig_pattern]['ass-class'] = ass_class
                        self.analysis['pattern'][key2][orig_pattern]['ass-descr'] = ass_descr
                    if highlight_regex := self.pattern_to_regex(pattern):
                        self.analysis['pattern'][key2][orig_pattern]['highlight-regex'] = highlight_regex
            if ('Modifier' in pattern) or ('WordWLM' in pattern):
                key2 = f"TOKENS WITH ORPHAN MODIFIER"
                pattern_count = self.pattern_count[orig_pattern]
                self.analysis['pattern'][key2][orig_pattern] \
                    = {'pattern': self.repl_invisible_chars_in_pattern(pattern),
                       'count': pattern_count,
                       'ex': self.pattern_examples[orig_pattern],
                       'lines': sorted(self.pattern_lines[orig_pattern])}
                ass_class, ass_descr = self.assess_pattern("ORPHAN MODIFIER", pattern)
                self.update_pattern_class_counts(key2, orig_pattern, ass_class, pattern_count)
                self.update_pattern_class_counts(key2, None, ass_class, pattern_count)
                if ass_class and isinstance(ass_descr, str):
                    self.analysis['pattern'][key2][orig_pattern]['ass-class'] = ass_class
                    self.analysis['pattern'][key2][orig_pattern]['ass-descr'] = ass_descr
        # Check for conflict sets (e.g. text containing both Arabic k and Farsi k)
        char_conflict_set = ['əǝә', # LATIN SMALL LETTER SCHWA, LATIN SMALL LETTER TURNED E, CYRILLIC SMALL LETTER SCHWA
                             'كک',  # Arabic/Farsi k
                             'يی',  # Arabic/Farsi y
                             'μµ',  # Greek letter mu/micro sign
                             '"“',  # ASCII QUOTATION MARK/LEFT DOUBLE QUOTATION MARK
                             '"”',  # ASCII QUOTATION MARK/RIGHT DOUBLE QUOTATION MARK
                             "'‘",  # ASCII APOSTROPHE/LEFT SINGLE QUOTATION MARK
                             "'’",  # ASCII APOSTROPHE/RIGHT SINGLE QUOTATION MARK
                             "'ʼ",  # ASCII APOSTROPHE/MODIFIER LETTER APOSTROPHE
                             "'ꞌ",  # ASCII APOSTROPHE/LATIN SMALL LETTER SALTILLO
                             "'՛",  # ASCII APOSTROPHE/ARMENIAN emphasis sign
                             "‚‘",  # ASCII LOW/LEFT SINGLE QUOTATION MARK
                             "„“",  # ASCII LOW/LEFT DOUBLE QUOTATION MARK
                             "·‧",  # MIDDLE DOT, HYPHENATION POINT
                             "/⁄",  # SOLIDUS, FRACTION SLASH

                             ',\u060C，',  # ASCII/Arabic/Chinese comma
                             ';\u061B፤；',  # ASCII/Arabic/Ethiopic/Chinese semicolon
                             ':꞉፥：',        # ASCII/modifier letter/Ethiopic/Chinese colon
                             '!！',        # ASCII/Chinese exclamation mark
                             '?\u061F፧？',  # ASCII/ARABIC/Ethiopic/Chinese question mark
                             '.\u06D4।።。．', # ASCII/ARABIC full stop/DANDA/Ethiopic/CHINESE PERIOD/FULLWIDTH PERIOD
                             '–—―',        # EN DASH/EM DASH/HORIZONTAL BAR
                             '-−',         # HYPHEN-MINUS, MINUS SIGN
                             '|।৷',         # VERTICAL LINE/DEVANAGARI DANDA/BENGALI CURRENCY NUMERATOR FOUR
                             '(（',        # ASCII/Chinese left parenthesis
                             ')）',        # ASCII/Chinese right parenthesis
                             '«《⟪',       # ASCII/Chinese/mathematical left double angle bracket/quotation mark
                             '»》⟫',       # ASCII/Chinese/mathematical right double angle bracket/quotation mark
                             '!՜',         # ASCII/Armenian exclamation mark
                             ',՝',         # ASCII/Armenian comma
                             '?՞',         # ASCII/Armenian question mark
                             '.։',         # ASCII/Armenian full stop
                             ':։',         # ASCII colon/Armenian full stop
                             '`՝',          # ASCII grave accent/Armenian comma

                            ]
        for char_conflict in char_conflict_set:
            char_list = []
            info_list = []
            count_info_list = []
            for char in list(char_conflict):
                if count := self.character_count[char]:
                    unicode_int = ord(char)
                    unicode_id = 'U+%04X' % unicode_int
                    unicode_name = self.unicode_name(char)
                    count_info_list.append(f'{char} {unicode_id} ({unicode_name}) count: {count}')
                    char_list.append(char)
                    info_list.append([char, unicode_id, unicode_name, count])
            if len(count_info_list) >= 2:
                conflict_key = '/'.join(char_list)
                for info_elem in info_list:
                    self.analysis['rival-char-sets'][conflict_key].append({'char': info_elem[0],
                                                                           'id': info_elem[1],
                                                                           'name': info_elem[2],
                                                                           'count': info_elem[3]})

    def sort_pattern_headings_in_analysis_pattern(self):
        sorted_analysis_pattern = defaultdict(dict)
        for pattern_heading in sorted(self.analysis['pattern'].keys(),
                                      key=lambda ph: self.pattern_class_counts[(ph, None)],
                                      reverse=True):
            sorted_analysis_pattern[pattern_heading] = self.analysis['pattern'][pattern_heading]
            sorted_analysis_pattern_pattern_heading = {}
            if patterns := self.analysis['pattern'][pattern_heading].keys():
                for pattern in sorted(patterns,
                                      key=lambda p: self.pattern_class_counts[(pattern_heading, p)],
                                      reverse=True):
                    sorted_analysis_pattern_pattern_heading[pattern] = sorted_analysis_pattern[pattern_heading][pattern]
            sorted_analysis_pattern[pattern_heading] = sorted_analysis_pattern_pattern_heading
        self.analysis['pattern'] = sorted_analysis_pattern

    def format_examples(self, examples: list, s: str) -> str:
        """Group examples in pretty format string"""
        max_display_len = self.max_n_viz_examples
        ex_l_dict = defaultdict(list)
        ex_r_dict = defaultdict(list)
        ref_id_p = False
        for example in examples:
            example_s, line_number_s = example[0], str(example[1])
            if line_number_s not in ex_l_dict[example_s]:
                ex_l_dict[example_s].append(line_number_s)
                if self.ref_id_dict and (ref_id := self.ref_id_dict[int(line_number_s)]):
                    ex_r_dict[example_s].append(ref_id)
                    ref_id_p = True
                else:
                    ex_r_dict[example_s].append(f'l.{line_number_s}')
        if (len(ex_l_dict) == 1) and ex_l_dict.get(s) and not ref_id_p:
            line_numbers = ex_l_dict[s]
            return f"line{'' if len(line_numbers) == 1 else 's'}: {', '.join(line_numbers)[:max_display_len]}"
        else:
            formatted_examples = []
            for example in ex_l_dict.keys():
                if ref_id_p:
                    formatted_examples.append(f"{example} ({', '.join(ex_r_dict[example][:max_display_len])})")
                else:
                    formatted_examples.append(f"{example} (l.{', '.join(ex_l_dict[example][:max_display_len])})")
            return f"example{'' if len(formatted_examples) == 1 else 's'}: {', '.join(formatted_examples)}"

    @staticmethod
    def insert_spaces_before_any_letter_modifiers(s: str):
        """for better human legibility"""
        return ''.join(list(map(lambda c: f' {c}' if regex.match(r'\pM$', c) else c, s)))

    @staticmethod
    def repl_invisible_chars_in_pattern(s: str):
        """for better human legibility"""
        result = ''.join(list(map(lambda c: f'<U+{ord(c):04X}>'  # {self.unicode_name(c)}'
                 if (regex.match(r'(?:\pC|\pZ|\pM)', c) and (not c in ' \u00AD\u202F')) else c, s)))
        for old, new in (('\u00AD', '<SOFT HYPHEN>'),):
            result = result.replace(old, new)
        return result

    @staticmethod
    def string_contains_right_to_left_letters(s: str):
        return regex.search(r'(?V1)[[\p{Arabic}||\p{Hebrew}||\p{Syriac}||\p{Thaana}]&&\pL]', s)

    def pretty_print(self, output_file: TextIO) -> None:
        """Output Wildebeest analysis in human-readable format."""
        n_lines = self.analysis['n_lines']
        n_empty_lines = self.analysis['n_empty_lines']
        n_non_empty_lines = n_lines - n_empty_lines
        output_file.write("OVERVIEW:\n")
        output_file.write(f"File size: {count_plus_noun(n_lines, 'line')}")
        if n_empty_lines:
            output_file.write(f" ({count_plus_noun(n_non_empty_lines, 'non-empty line')},"
                              f" {count_plus_noun(n_empty_lines, 'empty line')})")
        output_file.write(f", {count_plus_noun(self.analysis['n_characters'], 'character')}\n")
        for heading, keyword in (('Letter scripts', 'letter-script'),
                                 ('Number scripts', 'number-script'),
                                 ('Other character groups', 'other-script')):
            output_file.write(f"{heading}: {len(self.analysis[keyword])}\n")
            for unicode_script in self.analysis[keyword].keys():
                letter_script_dict = self.analysis[keyword][unicode_script]
                count = letter_script_dict['count']
                output_file.write(f"    {unicode_script} ({count_plus_noun(count, 'instance')})")
                if ((unicode_script not in ('C0_CONTROL', 'C1_CONTROL', 'SPACE', 'ZERO_WIDTH', 'DIRECTIONAL',
                                            'VARIATION_SELECTORS', 'LOW_SURROGATES'))
                        and (ex_s := letter_script_dict.get('ex'))):
                    ex_s = self.insert_spaces_before_any_letter_modifiers(ex_s)
                    try:
                        output_file.write(f": {ex_s}")
                    except UnicodeError as error:
                        sys.stderr.write(f"*** Unicode error: {error}\n")
                output_file.write("\n")
        non_canonical_char_combs = self.analysis['non-canonical'].keys()
        if n_non_canonical_char_combs := len(non_canonical_char_combs):
            output_file.write(f"Non-canonical character combinations: {n_non_canonical_char_combs}\n")
        char_conflicts = self.analysis['rival-char-sets'].keys()
        if n_char_conflicts := len(char_conflicts):
            output_file.write(f"Rival character sets: {n_char_conflicts}\n")
        notable_dict = defaultdict(dict)
        # {'XML escape tokens': {'GROUP_COUNT': 0, 'TYPE_COUNT': 0, 'TOKEN_COUNT': 0}, ...}
        for notable_heading in sorted(self.analysis['notable-token'].keys()):
            if re.search(r'XML', notable_heading, re.IGNORECASE):
                key1 = 'XML escape tokens'
            elif re.search(r'multi.*script', notable_heading, re.IGNORECASE):
                key1 = 'Words with characters from multiple scripts'
            else:
                continue
            notable_dict[key1]['GROUP_COUNT'] = notable_dict[key1].get('GROUP_COUNT', 0) + 1
            tokens = self.analysis['notable-token'][notable_heading].keys()
            for token in tokens:
                notable_dict[key1]['TYPE_COUNT'] = notable_dict[key1].get('TYPE_COUNT', 0) + 1
                notable_dict[key1]['TOKEN_COUNT'] = notable_dict[key1].get('TOKEN_COUNT', 0) \
                                                    + self.analysis['notable-token'][notable_heading][token]['count']
        for key1 in notable_dict.keys():
            group_count = notable_dict[key1]['GROUP_COUNT']
            type_count = notable_dict[key1]['TYPE_COUNT']
            token_count = notable_dict[key1]['TOKEN_COUNT']
            output_file.write(f"{key1}: "
                              f"{group_count} {'category' if (group_count == 1) else 'categories'}, "
                              f"{type_count} {'unique type' if type_count == 1 else 'unique types'}, "
                              f"{token_count} {'instance' if token_count == 1 else 'instances'}\n")

        output_file.write("\nDETAILS:\n")
        output_file.write(f"Non-canonical character combinations: {len(non_canonical_char_combs)}\n")
        for char_comb in self.analysis['non-canonical'].keys():
            non_canonical_dict = self.analysis['non-canonical'][char_comb]
            orig = non_canonical_dict.get('orig')
            norm = non_canonical_dict.get('norm')
            orig_seq = ' + '.join(list(orig))
            norm_seq = ' + '.join(list(norm))
            orig_count = non_canonical_dict.get('orig-count')
            norm_count = non_canonical_dict.get('norm-count')
            orig_form = non_canonical_dict.get('orig-form')
            norm_form = non_canonical_dict.get('norm-form')
            changes = non_canonical_dict.get('changes')
            output_info = f"Non-canonical: {orig} ({orig_form}{orig_seq}, count: {orig_count})" \
                          f"  Canonical: {norm} ({norm_form}{norm_seq}, count: {norm_count})"
            if self.string_contains_right_to_left_letters(output_info):
                output_file.write(self.lrm)
            output_file.write(f'    {output_info}')
            if changes and not norm_form:
                output_file.write(f"  Changes: {', '.join(changes)}")
            output_file.write("\n")
        output_file.write(f"Rival character sets: {len(char_conflicts)}\n")
        for char_conflict_key in char_conflicts:
            # noinspection SpellCheckingInspection
            char_infos = []
            info_list = self.analysis['rival-char-sets'][char_conflict_key]
            for info_elem in info_list:
                char_infos.append(f"{info_elem['char']} {info_elem['id']} ({info_elem['name']}) "
                                  f"count: {info_elem['count']}")
            output_info = f"{'; '.join(char_infos)}"
            if self.string_contains_right_to_left_letters(output_info):
                output_file.write(self.lrm)
            output_file.write(f"    {output_info}\n")
        if n := self.n_tatweels():
            output_file.write(f"Number of Arabic tatweel characters: {n}\n")
        for notable_heading in sorted(self.analysis['notable-token'].keys()):
            tokens = self.analysis['notable-token'][notable_heading].keys()
            if tokens:
                output_file.write(f"{notable_heading}:\n")
                for i, token in enumerate(tokens, 1):
                    if i > self.max_n_cases:
                        output_file.write('    ...\n')
                        break
                    d = self.analysis['notable-token'][notable_heading][token]
                    output_info = f"{d['token']} count: {d['count']}, {self.format_examples(d['ex'], token)}"
                    if self.string_contains_right_to_left_letters(output_info):
                        output_file.write(self.lrm)
                    output_file.write(f'    {output_info}\n')
        for unicode_block in self.analysis['block'].keys():
            chars = self.analysis['block'][unicode_block].keys()
            if chars:
                output_file.write(f"{unicode_block} characters:\n")
                for i, char in enumerate(chars, 1):
                    if i > self.max_n_cases:
                        output_file.write('    ...\n')
                        break
                    d = self.analysis['block'][unicode_block][char]
                    output_info = f"{self.insert_spaces_before_any_letter_modifiers(d['char'])} " \
                                  f"{d['id']} {d['name']} count: {d['count']}, " \
                                  f"{self.format_examples(d['ex'], char)}"
                    if (decomp_s := ud.decomposition(char)) \
                            and regex.match(r'[0-9A-Z]{4,}$', decomp_s) \
                            and (decomp_c := chr(int(f"0x{decomp_s}", 0))):
                        decomp_name = self.unicode_name(decomp_c)
                        output_info += f", decomposition: {decomp_c} ({decomp_name})"
                    if self.string_contains_right_to_left_letters(output_info):
                        output_file.write(self.lrm)
                    output_file.write(f'    {output_info}\n')
        # for pattern_heading in sorted(self.analysis['pattern'].keys()):
        for pattern_heading in self.analysis['pattern'].keys():
            patterns = self.analysis['pattern'][pattern_heading].keys()
            if patterns:
                output_file.write(f"{pattern_heading}:\n")
                # for i, pattern in enumerate(sorted(patterns, key=lambda p: self.analysis['pattern'][pattern_heading][p]['count'], reverse=True), 1):
                for i, pattern in enumerate(patterns, 1):
                    if i > self.max_n_cases:
                        output_file.write('    ...\n')
                        break
                    d = self.analysis['pattern'][pattern_heading][pattern]
                    ass_class = d.get('ass-class', '')
                    if ass_class.startswith('-'):
                        ass_class_marker = '[-]'
                    elif ass_class.startswith('+'):
                        ass_class_marker = '[+]'
                    else:
                        ass_class_marker = '   '
                    output_info = (f"{ass_class_marker} {d['pattern']} count: {d['count']}, "
                                   f"{self.format_examples(d['ex'], pattern)}")
                    if self.string_contains_right_to_left_letters(output_info):
                        output_file.write(self.lrm)
                    output_file.write(f'    {output_info}\n')

    def n_tatweels(self) -> int:
        # noinspection SpellCheckingInspection
        """Number of Arabic tatweels (also called kahida), a character for non-white-space justification)"""
        try:
            return self.analysis['block']['ARABIC']['\u0640']['count'] or 0
        except KeyError:
            return 0

    def summary_list_of_issues(self) -> List[str]:
        """List of major issues found in Wildebeest analysis, for a 1-line summary, useful for multi-file input"""
        result = []
        letter_scripts = sorted(self.analysis['letter-script'].keys(),
                                key=lambda script: self.analysis['letter-script'][script]['count'], reverse=True)
        if len(letter_scripts) >= 2:
            letter_script_info_list = []
            for letter_script in letter_scripts:
                if (ex_s := self.analysis['letter-script'][letter_script].get('ex')) and len(ex_s) < 10:
                    letter_script_info_list.append(f"{letter_script} "
                                                   f"({self.insert_spaces_before_any_letter_modifiers(ex_s)})")
                else:
                    letter_script_info_list.append(letter_script)
            result.append(f"{count_plus_noun(len(letter_scripts), 'letter script')}: "
                          f"{', '.join(letter_script_info_list)}")
        number_scripts = sorted(self.analysis['number-script'].keys(),
                                key=lambda script: self.analysis['number-script'][script]['count'], reverse=True)
        if (len(number_scripts) >= 2) and not number_scripts == ['ASCII_DIGIT', 'VULGAR_FRACTION']:
            number_script_info_list = []
            for number_script in number_scripts:
                if (ex_s := self.analysis['number-script'][number_script].get('ex')) and len(ex_s) < 10:
                    number_script_info_list.append(f"{number_script} ({ex_s})")
                else:
                    number_script_info_list.append(number_script)
            result.append(f"{count_plus_noun(len(number_scripts), 'number script')}: "
                          f"{', '.join(number_script_info_list)}")
        if self.analysis['other-script']['C0_CONTROL']:
            result.append('C0_CONTROL')
        if self.analysis['other-script']['C1_CONTROL']:
            result.append('C1_CONTROL')
        non_canonical_char_combs = self.analysis['non-canonical'].keys()
        if n_non_canonical_char_combs := len(non_canonical_char_combs):
            n_instances = 0
            for char_comb in non_canonical_char_combs:
                n_instances += self.analysis['non-canonical'][char_comb]['orig-count']
            result.append(f"{count_plus_noun(n_non_canonical_char_combs, 'non-canonical character combination')} "
                          f"({count_plus_noun(n_instances, 'instance')})")
        char_conflicts = self.analysis['rival-char-sets'].keys()
        if n_char_conflicts := len(char_conflicts):
            result.append(count_plus_noun(n_char_conflicts, 'character set conflict'))
        flag_class_dict = {r'^XML ESCAPE': 'XML escape token',
                           r'^REPLACEMENT': 'Replacement character',
                           r'ORPHAN.?MODIFIER': 'Orphan modifier',
                           r'VARIATION.?SELECTOR': 'Variation selector',
                           r'IPA.?EXTENSION': 'IPA character',
                           r'WORDS.?WITH.?CHARACTERS.?FROM.?MULTIPLE.?SCRIPTS': 'multi-script word',
                           r'PRIVATE.?USE': 'Private use character',
                           r'SURROGATES': 'Surrogate'}
        flag_bool_dict = {}
        for key2 in sorted(list(self.analysis['notable-token'].keys())
                           + list(self.analysis['pattern'].keys())
                           + list(self.analysis['letter-script'].keys())
                           + list(self.analysis['other-script'].keys())):
            for regex_term in flag_class_dict.keys():
                if regex.search(regex_term, key2):
                    flag_bool_dict[flag_class_dict[regex_term]] = True
        for flag_class in flag_bool_dict.keys():
            result.append(flag_class)
        if self.n_tatweels():
            result.append('Tatweel')
        return result

    @staticmethod
    def load_ref_ids(filename) -> dict:
        """Load file mapping line numbers to sentence IDs."""
        ref_id_dict = defaultdict(str)
        with open(filename, 'r', encoding='utf-8') as f:
            line_number = 0
            for line in f:
                line_number += 1
                ref_id_dict[line_number] = line.strip()
        return ref_id_dict

    def load_cross_snt_spans(self, filename) -> None:
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                s = f.read()
        except (NameError, TypeError, ValueError, OSError) as err:
            sys.stderr.write(f'*** {type(err).__name__}: Could not read file {filename}\n{err}\n')
            return
        try:
            d = json.loads(s)
        except (NameError, TypeError, ValueError) as err:
            sys.stderr.write(f'*** {type(err).__name__}: Could not load cross-snt info from {filename}\n{err}\n')
            return
        translation = d.get("translation")
        corpus = d.get("corpus")
        refresher_dict = defaultdict(list)
        cross_snt_span_dict = defaultdict(list)
        triple_nesting_dict = defaultdict(list)
        line_length = defaultdict(int)
        char_count = defaultdict(int)
        cross_snt_span_list = d.get("cross-snt-spans", [])
        refresher_left_list = d.get("refresher-lefts", [])
        triple_nesting_list = d.get("triple-nesting", [])
        ref_translation_elem = {'translation': translation, 'corpus': corpus, 'line-length': line_length,
                                'refresher-dict': refresher_dict, 'cross-snt-span-dict': cross_snt_span_dict,
                                'cross_snt_spans': cross_snt_span_list, 'char_count': char_count,
                                'triple-dict': triple_nesting_dict}
        self.punct_analysis['ref_translations'].append(ref_translation_elem)
        for c in cross_snt_span_list:
            char_count[c] += 1
            for cross_snt_span in cross_snt_span_list[c]:
                open_pos, close_pos = cross_snt_span[0], cross_snt_span[1]
                open_line_number, open_char_pos, open_line_len = open_pos
                close_line_number, close_char_pos, close_line_len = close_pos
                for line_number in range(open_line_number, close_line_number+1):
                    cross_snt_span_dict[(c, line_number)].append(cross_snt_span)
        for c in triple_nesting_list:
            for cross_snt_span in triple_nesting_list[c]:
                open_pos, close_pos = cross_snt_span[0], cross_snt_span[1]
                open_line_number, open_char_pos, open_line_len = open_pos
                close_line_number, close_char_pos, close_line_len = close_pos
                for line_number in range(open_line_number, close_line_number+1):
                    triple_nesting_dict[(c, line_number)].append(cross_snt_span)
        for c in refresher_left_list:
            prev_refresher_line_number = None
            refresher_lefts = refresher_left_list[c]
            for refresher_left in refresher_lefts:
                line_number, char_pos, line_len, *optional_args = refresher_left
                cross_snt_span = None
                for cross_snt_span_cand in cross_snt_span_dict[(c, line_number)]:
                    open_pos, close_pos = cross_snt_span_cand[0], cross_snt_span_cand[1]
                    open_line_number, open_char_pos, open_line_len = open_pos
                    close_line_number, close_char_pos, close_line_len = close_pos
                    if (open_line_number == line_number) and (char_pos < open_char_pos):
                        continue
                    elif (close_line_number == line_number) and (char_pos > close_char_pos):
                        continue
                    else:
                        cross_snt_span = cross_snt_span_cand
                        break
                refresher_dict[(c, line_number)].append((char_pos, prev_refresher_line_number, cross_snt_span))
                if char_pos:
                    line_length[line_number] = line_len
                prev_refresher_line_number = line_number

def plural_noun_form(noun: str) -> str:
    """Quick and dirty plural form, e.g. 'baby' -> 'babies'"""
    if noun.endswith('y'):
        return regex.sub(r'y$', 'ies', noun)
    else:
        return noun + 's'


def count_plus_noun(count: int, noun: str) -> str:
    """Quick and dirty count + plural form, e.g. (2, 'baby') -> '2 babies'"""
    return f'{count} {noun if count == 1 else plural_noun_form(noun)}'


def process_args(args) -> WildebeestAnalysis:
    """Perform Wildebeest analysis for 1 file, using argparse args."""
    wb = WildebeestAnalysis(args)
    if args.ref_id_dict:
        wb.ref_id_dict = args.ref_id_dict
    wb.corpus = defaultdict(str)
    wb.corpus_w_rtf_delimiter_adjustments = defaultdict(str)
    wb.build_char_to_script_dict()
    if args.input is sys.stdin:
        args.total_bytes = None
        args.input = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8', errors='surrogateescape')
        if not re.search('utf-8', sys.stdin.encoding, re.IGNORECASE):
            log.error(f"Bad STDIN encoding '{sys.stdin.encoding}' as opposed to 'utf-8'. "
                      f"Suggestion: 'export PYTHONIOENCODING=UTF-8' or use '--input FILENAME' option")
    elif args.input:
        inp_path = args.input
        assert isinstance(inp_path, Path)
        if not inp_path.exists():
            raise ValueError(f"{inp_path} does not exist.")
        args.total_bytes = inp_path.stat().st_size
        args.input = argparse.FileType('r', encoding='utf-8', errors='surrogateescape')(str(inp_path))
        wb.filename = inp_path

    for ref_cross_snt_span_file in args.ref_cross_snt_span_files:
        print(f'Load ref {ref_cross_snt_span_file}')
        wb.load_cross_snt_spans(ref_cross_snt_span_file)
    if args.output is sys.stdout and not re.search('utf-8', sys.stdout.encoding, re.IGNORECASE):
        log.error(f"Error: Bad STDIN/STDOUT encoding '{sys.stdout.encoding}' as opposed to 'utf-8'. \
                        Suggestion: 'export PYTHONIOENCODING=UTF-8' or use use '--output FILENAME' option")
    if args.input:
        wb.collect_counts_and_examples_in_file(args.input,
                                               total_bytes=args.total_bytes,
                                               progress_bar=args.progress_bar)
    elif args.strings:
        line_number = 0
        n_empty_lines = 0
        for line in args.strings:
            line_number += 1
            if not re.match(r'\S', line):
                n_empty_lines += 1
            wb.collect_counts_and_examples_in_line(line, line_number)
            wb.punct_analysis_in_line(line, line_number)
        wb.analysis['n_lines'] = line_number
        wb.analysis['n_empty_lines'] = n_empty_lines
        wb.punct_analysis_at_end()
    else:  # nothing to process
        log.warning('Called function process_with_args with neither args.input nor args.strings')
    wb.aggregate()  # Aggregate raw counts and examples into analysis.
    wb.remove_empty_dicts()  # Remove empty dictionaries that were created to impose a specific order
    wb.sort_pattern_headings_in_analysis_pattern()
    if args.json:
        args.json.write(json.dumps(wb.analysis) + "\n")
    if args.summary or args.summary_file:
        summary = '; '.join(wb.summary_list_of_issues())
        if args.summary:
            args.output.write(f"{args.file_id}: {summary}\n")
        if args.summary_file:
            with open(args.summary_file, 'w') as f_summary:
                f_summary.write(f"{summary}\n")
    elif args.output:
        wb.pretty_print(args.output)
    if args.output:
        args.output.flush()
    return wb


def process(in_file: str | None = None,     # provide exactly one input: input filename, strings or string
            strings: list[str] | None = None,
            string: str | None = None,
            pp_output: TextIO | None = None,    # output filename (for pretty-print)
            json_output: TextIO | None = None,  # output filename (in json)
            lang_code: str | None = None,
            ref_cross_snt_span_files: list[str] = (),
            max_cases: int = 500,                  # max cases per block (e.g. number of characters in script)
            max_examples: int = 100,               # max examples per case
            max_examples_viz: int = 5,             # max examples per case in visualization
            max_script_lines: int = 200,
            max_pattern_lines: int = 200,
            max_bad_pattern_lines: int = 2000,
            max_non_canonical_lines: int = 100,
            max_char_conflict_lines: int = 100,
            max_notable_token_lines: int = 1000,
            # ref_id_dict is a dictionary mapping line_numbers/string_indexes (int, starting at 1) to snt IDs (str)
            summary_file: Optional[str] = None,
            ref_id_dict: Optional[dict] = None) -> WildebeestAnalysis:
    """Entry point when Wildebeest Analysis for non-CLI use; maps to CLI interface"""
    return process_args(argparse.Namespace(strings=[string] if string and not strings else strings,
                                           input=Path(in_file) if in_file else None,
                                           output=pp_output, json=json_output,
                                           lc=lang_code, max_cases=max_cases,
                                           ref_cross_snt_span_files=ref_cross_snt_span_files,
                                           max_examples=max_examples,
                                           max_examples_viz=max_examples_viz,
                                           max_script_lines=max_script_lines,
                                           max_pattern_lines=max_pattern_lines,
                                           max_bad_pattern_lines=max_bad_pattern_lines,
                                           max_non_canonical_lines=max_non_canonical_lines,
                                           max_char_conflict_lines=max_char_conflict_lines,
                                           max_notable_token_lines=max_notable_token_lines,
                                           summary=None, summary_file=summary_file,
                                           progress_bar=None, ref_id_dict=ref_id_dict))


def main():
    """Wrapper around Wildebeest analysis that takes care of argument parsing and prints change stats to STDERR."""
    # parse arguments
    parser = argparse.ArgumentParser(description='Analyzes a given text for a wide range of anomalies', prog="wb-ana")
    parser.add_argument('-i', '--input', type=Path,
                        default=sys.stdin, metavar='INPUT-FILENAME', help='(default: STDIN)')
    parser.add_argument('--batch', type=Path, default=None, metavar='BATCH_DIR',
                        help='Directory with batch of input files (BATCH_DIR/*.txt)')
    parser.add_argument('-s', '--summary', action='count', default=0, help='single summary line per file')
    parser.add_argument('--summary_file', type=Path, default=None, help='file with single summary line')
    parser.add_argument('-o', '--output', type=argparse.FileType('w', encoding='utf-8', errors='ignore'),
                        default=sys.stdout, metavar='OUTPUT-FILENAME', help='(default: STDOUT)')
    parser.add_argument('-j', '--json', type=argparse.FileType('w', encoding='utf-8', errors='ignore'),
                        default=None, metavar='JSON-OUTPUT-FILENAME', help='(default: None)')
    parser.add_argument('--html_output_filename', type=str, default=None)
    parser.add_argument('--html_example_dir', type=str, default=None)
    parser.add_argument('--file_id', type=str, default=None)
    parser.add_argument('--lc', type=str, default=None,
                        metavar='LANGUAGE-CODE', help="ISO 639-3, e.g. 'fas' for Persian")
    parser.add_argument('-v', '--verbose', action='count', default=0, help='write change log etc. to STDERR')
    parser.add_argument('-pb', '--progress_bar', action='store_true', default=False, help='Show progress bar')
    parser.add_argument('-n', '--max_cases', type=int, default=100, help='max number of cases per group')
    parser.add_argument('-x', '--max_examples_viz', type=int, default=5, help='max number of examples per viz line')
    parser.add_argument('--max_examples', type=int, default=100, help='max number of examples per line')
    parser.add_argument('--max_pattern_lines', type=int, default=200)
    parser.add_argument('--max_bad_pattern_lines', type=int, default=2000)
    parser.add_argument('--max_script_lines', type=int, default=200)
    parser.add_argument('--max_non_canonical_lines', type=int, default=100)
    parser.add_argument('--max_char_conflict_lines', type=int, default=100)
    parser.add_argument('--max_notable_token_lines', type=int, default=1000)
    parser.add_argument('-r', '--ref_id_file', type=Path, metavar='REF-FILENAME',
                        help='(optional file with sentence reference IDs)')
    parser.add_argument('--ref_cross_snt_span_files', type=Path, nargs='*', default=(),
                        help='optional; input; format: json; content: cross-sentence quotations, open quotation marks')
    parser.add_argument('--version', action='version',
                        version=f'%(prog)s {__version__} last modified: {last_mod_date}')
    parser.add_argument('--ref_id_dict', default=None, help=argparse.SUPPRESS)
    parser.add_argument('--strings', default=None, help=argparse.SUPPRESS)
    parser.add_argument('--back_versification', type=str, default='vers/back_versification.json')
    args = parser.parse_args()
    start_time = datetime.datetime.now()
    if args.verbose:
        log.info('Script: wb-analysis.py')
        log.info(f'Start: {start_time}')
        if args.input is not sys.stdin:
            log.info(f'Input: {args.input.name}')
        if args.output is not sys.stdout:
            log.info(f'Output: {args.output.name}')
    bv = BackVersification(args.back_versification)
    if args.ref_id_file:
        print(f'Load ref {args.ref_id_file}')
        args.ref_id_dict = WildebeestAnalysis.load_ref_ids(args.ref_id_file)
    if args.batch:
        directory_str = args.batch
        directory_path = Path(directory_str)
        args.batch = None
        files = list(Path(directory_path).glob('*.txt'))
        files.sort()
        n_files = 0
        for file in files:
            filename = file.name
            if file.is_file() and filename.endswith('.txt'):
                n_files += 1
                args.input = file
                args.file_id = filename
                sys.stderr.write(f'{args.file_id}\n')
                process_args(args)
        if args.verbose:
            log.info(f"Processed {count_plus_noun(n_files, 'file')}")
    else:
        wb_ana = process_args(args)
        if args.html_output_filename:
            wb_pp.main_with_args(args, wb_ana)
    sys.stderr.write(bv.report_stats())
    if args.verbose:
        end_time = datetime.datetime.now()
        log.info(f'End: {end_time}')
        elapsed_time = end_time - start_time
        log.info(f'Time: {elapsed_time}')

if __name__ == "__main__":
    main()
