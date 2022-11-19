#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Written by Ulf Hermjakob, USC/ISI
This script is analyzes a given text for a wide range of anomalies.
When using STDIN and/or STDOUT, if might be necessary, particularly for older versions of Python, to do
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
from pathlib import Path
import re
import regex
import sys
from tqdm.auto import tqdm
from typing import IO, Optional, TextIO, Union, List
import unicodedata as ud
import unicodeblock.blocks
from wildebeest.wb_normalize import Wildebeest
from wildebeest import __version__, last_mod_date


log.basicConfig(level=log.INFO)


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
        self.pattern_characters_of_interest = "-‐‑−‒–—―+~*_.,:;!¡?/§'‘’ʼˊˋˈˀˆˉ、。@#&%$€£¥₪¢¤₨₹µ‌¦|‍"
        self.pattern_characters_of_interest += 'ـ'  # Arabic tatweel
        self.pattern_characters_of_interest_re = regex.compile(rf'[{self.pattern_characters_of_interest}]')
        self.pattern_count = defaultdict(int)
        self.pattern_examples = defaultdict(list)
        self.max_n_token_examples = args.max_examples
        self.max_n_cases = args.max_cases
        self.script_count_letter = defaultdict(int)
        self.script_count_number = defaultdict(int)
        self.script_count_other = defaultdict(int)
        self.script_examples_letter = defaultdict(str)
        self.script_examples_number = defaultdict(str)
        self.script_examples_other = defaultdict(str)
        self.mixed_script_count_letter = defaultdict(int)
        self.mixed_script_instances_letter = defaultdict(list)
        self.analysis = {'n_lines': 0,
                         'n_characters': 0,
                         'letter-script': defaultdict(dict),
                         'number-script': defaultdict(dict),
                         'other-script': defaultdict(dict),
                         'non-canonical': defaultdict(dict),
                         'char-conflict': defaultdict(list),
                         'notable-token': defaultdict(dict),
                         'pattern': defaultdict(dict),
                         'block': defaultdict(dict)}
        # The following blocks will be printed out in order as specified below:
        for block in ['LOW_SURROGATES', 'REPLACEMENT', 'C0_CONTROL', 'C1_CONTROL', 'ZERO_WIDTH', 'DIRECTIONAL',
                      'VARIATION_SELECTORS', 'VARIATION_SELECTORS_SUPPLEMENT',
                      'ASCII_PUNCTUATION', 'GENERAL_PUNCTUATION', 'CURRENCY_SYMBOLS', 'SPACE',
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
            '': 'INFORMATION SEPARATOR ONE',
            '': 'DELETE',
            '': 'PADDING CHARACTER (W1252: Euro Sign)',
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
        self.populate_char_to_block_dict()
        self.token_to_pattern_dict = defaultdict(list)
        self.ref_id_dict = None
        self.lrm = '‎'  # left-to-right directional mark

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
        for char in '               ':
            self.set_new_char_to_block_dict_entry(char, 'SPACE')
        for char in '­​‌‍﻿':
            self.set_new_char_to_block_dict_entry(char, 'ZERO_WIDTH')
        for char in '‏‎':
            self.set_new_char_to_block_dict_entry(char, 'DIRECTIONAL')
        for char in '$¢£¤¥':
            self.set_new_char_to_block_dict_entry(char, 'CURRENCY_SYMBOLS')
        for char in "ʌɓɗɖɛəɡɠɨᵻɟᴋɫɲⁿɔɵᵽɹʃʉʋʊʒɣɩʔ":
            self.set_new_char_to_block_dict_entry(char, 'LATIN')
        self.set_new_char_to_block_dict_entry('ᵸ', 'CYRILLIC')
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
        self.set_new_char_to_block_dict_entry(0xB5, 'LETTERLIKE_SYMBOLS')  # micro sign

    def token_to_patterns(self, token: str) -> List[str]:
        # check for cached result
        if result := self.token_to_pattern_dict[token]:
            return result
        pattern = token
        pattern = regex.sub(r'', '', pattern)
        pattern = regex.sub('\u0640', '', pattern)  # tatweel
        pattern = regex.sub(r'&(?:[aA][mM][pP];)*(?:#[xX][0-9A-Fa-f]{1,6}|#\d{1,7}|[A-Za-z]{1,6});',
                            r'&;', pattern, regex.IGNORECASE)  # problem with IGNORECASE
        pattern = regex.sub(r'(?:%(?:25)*[0-9A-Fa-f]{2}){2,}',
                            r'%', pattern, regex.IGNORECASE)  # problem with IGNORECASE
        pattern = regex.sub(r'(?:\pL\pM*)+', 'Word', pattern)
        pattern = regex.sub(r'\pM{2,}', 'Modifiers', pattern)
        pattern = regex.sub(r'\pM', 'Modifier', pattern)
        pattern = regex.sub(r'\pN+', 'Number', pattern)
        pattern = regex.sub(r'', 'Xml', pattern)
        pattern = regex.sub(r'', '\u0640', pattern)
        pattern1 = pattern
        pattern2 = regex.sub(r'(?:Word)+\u0640+(?:Word)+', 'Word', pattern)
        result = [pattern1]
        if pattern2 != pattern1:
            result.append(pattern2)
        # Cache result, but avoid clogging run-time memory space
        if len(self.token_to_pattern_dict) < 1000000:
            self.token_to_pattern_dict[token] = result
        return result

    def collect_counts_and_examples_in_line(self, line: str, line_number: int):
        self.analysis['n_characters'] += len(line)
        line = line.strip()
        if line == '<range>':
            return
        # line_id = str(line_number)
        char_position = 0
        for char in line:
            self.character_count[char] += 1
            char_position += 1
            if len(self.token_examples[char]) < self.max_n_token_examples:
                # if char.isalpha():
                if regex.search(r'(?:\pL|\pM|�)', char):
                    token_examples = regex.findall(rf'((?:\pL\pM*|�)*\pM*{char}\pM*(?:\pL\pM*|�)*)', line)
                elif char.isnumeric():
                    token_examples = regex.findall(rf'(\pN*{char}\pN*)', line)
                else:
                    token_examples = [char]
                for token_example in token_examples:
                    token_tuple = [token_example, line_number]
                    if len(self.token_examples[char]) < self.max_n_token_examples \
                            and (token_tuple not in self.token_examples[char]):
                        self.token_examples[char].append(token_tuple)
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
            if (len(self.token_examples[token]) < self.max_n_token_examples) \
                    and (token_tuple not in self.token_examples[token]):
                self.token_examples[token].append(token_tuple)
        for token in regex.findall(r'(\S+)', line):
            if self.pattern_characters_of_interest_re.search(token) \
                    or regex.search(r'(?<!\pL\pM*)\pM', token):
                token_tuple = [token, line_number]
                for pattern in self.token_to_patterns(token):
                    self.pattern_count[pattern] += 1
                    if len(self.pattern_examples[pattern]) < self.max_n_token_examples \
                            and (token_tuple not in self.pattern_examples[pattern]):
                        self.pattern_examples[pattern].append(token_tuple)

    def collect_counts_and_examples_in_file(self, input_file: IO, total_bytes=None, progress_bar=True) -> None:
        """Collect counts and examples for characters, tokens, and patterns occurring in file."""
        line_number = 0
        st = time.time()
        prefix = 'Checking'
        with tqdm(input_file, total=total_bytes, disable=not progress_bar, unit='b', unit_scale=True,
                  dynamic_ncols=True, desc=prefix) as data_bar:
            try:
                for line in data_bar:
                    line_number += 1
                    if progress_bar:
                        line_speed = int(line_number / (time.time() - st))
                        data_bar.set_postfix_str(f'{line_speed}L/s', refresh=False)
                        data_bar.set_description_str(f'{prefix} {line_number}', refresh=False)
                        data_bar.update(len(line.encode()))  # bytes
                    self.collect_counts_and_examples_in_line(line, line_number)
            # Exception for safety only. Should not occur.
            except UnicodeError as error:
                sys.stderr.write(f"*** Unicode error: {error}\n")
                sys.stderr.write(f"***    Input aborted. The input is not in valid UTF-8 encoding.\n")
                if input_file is sys.stdin:
                    sys.stderr.write(f"***    For a more encoding-robust input, consider using -i <input-filename> "
                                     f"instead of reading from STDIN.\n")
        self.analysis['n_lines'] = line_number

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

    def aggregate(self) -> None:
        """Aggregate raw counts and examples into result Wildebeest analysis structure."""
        # Collect info on letter scripts (e.g. LATIN, CYRILLIC), number scripts (e.g. ASCII_DIGIT, ARABIC_INDIC_DIGIT),
        #    other scripts (e.g. ASCII_PUNCTUATION, GENERAL_PUNCTUATION, SPACE)
        for char in sorted(self.character_count):
            unicode_cat = self.unicode_category(char)
            unicode_block = self.unicode_block(char)
            unicode_script = self.unicode_script(unicode_block)
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
                    if unicode_cat.startswith('M') and not regex.search(r'(?:MODIFIER|MARK|SELECTOR)',
                                                                        unicode_script, regex.IGNORECASE):
                        unicode_script += "_MODIFIERS"
                    elif unicode_cat.startswith('P') and not regex.search(r'(?:PUNCT)', unicode_script):
                        unicode_script += "_PUNCTUATION"
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
        for unicode_script in unicode_scripts_number:
            self.analysis['number-script'][unicode_script] = {'count': self.script_count_number[unicode_script]}
            script_examples_number = self.script_examples_number.get(unicode_script, "")
            if ((len(script_examples_number) <= 80)
                    or (unicode_script != dominant_script_number and len(script_examples_number) <= 500)):
                self.analysis['number-script'][unicode_script]['ex'] = script_examples_number
        for unicode_script in unicode_scripts_other:
            self.analysis['other-script'][unicode_script] = {'count': self.script_count_other[unicode_script]}
            script_examples_other = self.script_examples_other.get(unicode_script, "")
            if len(script_examples_other) <= 80:
                self.analysis['other-script'][unicode_script]['ex'] = script_examples_other
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
        for pattern in self.pattern_count:
            self.wildebeest.set_lv(pattern)
            for pattern_character_of_interest in self.pattern_characters_of_interest:
                if pattern_character_of_interest in pattern:
                    key2 = f"TOKENS WITH {pattern_character_of_interest} " \
                           f"({'U+%04X' % ord(pattern_character_of_interest)} " \
                           f"{self.unicode_name(pattern_character_of_interest)})"
                    self.analysis['pattern'][key2][pattern] \
                        = {'pattern': self.repl_invisible_chars_in_pattern(pattern),
                           'count': self.pattern_count[pattern],
                           'ex': self.pattern_examples[pattern]}
            if 'Modifier' in pattern:
                key2 = f"TOKENS WITH ORPHAN MODIFIER"
                self.analysis['pattern'][key2][pattern] \
                    = {'pattern': self.repl_invisible_chars_in_pattern(pattern),
                       'count': self.pattern_count[pattern],
                       'ex': self.pattern_examples[pattern]}
        # Check for conflict sets (e.g. text containing both Arabic k and Farsi k)
        char_conflict_set = ['كک',  # Arabic/Farsi k
                             'يی']  # Arabic/Farsi y
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
                    self.analysis['char-conflict'][conflict_key].append({'char': info_elem[0],
                                                                         'id': info_elem[1],
                                                                         'name': info_elem[2],
                                                                         'count': info_elem[3]})

    def format_examples(self, examples: list, s: str) -> str:
        """Group examples in pretty format string"""
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
            return f"line{'' if len(line_numbers) == 1 else 's'}: {', '.join(line_numbers)}"
        else:
            formatted_examples = []
            for example in ex_l_dict.keys():
                if ref_id_p:
                    formatted_examples.append(f"{example} ({', '.join(ex_r_dict[example])})")
                else:
                    formatted_examples.append(f"{example} (l.{', '.join(ex_l_dict[example])})")
            return f"example{'' if len(formatted_examples) == 1 else 's'}: {', '.join(formatted_examples)}"

    @staticmethod
    def insert_spaces_before_any_letter_modifiers(s: str):
        """for better human legibility"""
        return ''.join(list(map(lambda c: f' {c}' if regex.match(r'\pM$', c) else c, s)))

    @staticmethod
    def repl_invisible_chars_in_pattern(s: str):
        """for better human legibility"""
        return ''.join(list(map(lambda c: f'<U+{ord(c):04X}>'  # {self.unicode_name(c)}'
        if regex.match(r'(?:\pC|\pZ|\pM)', c) else c, s)))

    @staticmethod
    def string_contains_right_to_left_letters(s: str):
        return regex.search(r'(?V1)[[\p{Arabic}||\p{Hebrew}||\p{Syriac}||\p{Thaana}]&&\pL]', s)

    def pretty_print(self, output_file: TextIO) -> None:
        """Output Wildebeest analysis in human-readable format."""
        output_file.write("OVERVIEW:\n")
        output_file.write(f"File size: {count_plus_noun(self.analysis['n_lines'], 'line')}, "
                          f"{count_plus_noun(self.analysis['n_characters'], 'character')}\n")
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
                        and (ex_s := letter_script_dict.get('ex', None))):
                    ex_s = self.insert_spaces_before_any_letter_modifiers(ex_s)
                    try:
                        output_file.write(f": {ex_s}")
                    except UnicodeError as error:
                        sys.stderr.write(f"*** Unicode error: {error}\n")
                output_file.write("\n")
        non_canonical_char_combs = self.analysis['non-canonical'].keys()
        if n_non_canonical_char_combs := len(non_canonical_char_combs):
            output_file.write(f"Non-canonical character combinations: {n_non_canonical_char_combs}\n")
        char_conflicts = self.analysis['char-conflict'].keys()
        if n_char_conflicts := len(char_conflicts):
            output_file.write(f"Character conflict sets: {n_char_conflicts}\n")
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
        output_file.write(f"Character conflict sets: {len(char_conflicts)}\n")
        for char_conflict_key in char_conflicts:
            char_infos = []
            info_list = self.analysis['char-conflict'][char_conflict_key]
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
        for pattern_heading in sorted(self.analysis['pattern'].keys()):
            patterns = self.analysis['pattern'][pattern_heading].keys()
            if patterns:
                output_file.write(f"{pattern_heading}:\n")
                for i, pattern in enumerate(sorted(patterns,
                                                   key=lambda p:
                                                   self.analysis['pattern'][pattern_heading][p]['count'],
                                                   reverse=True),
                                            1):
                    if i > self.max_n_cases:
                        output_file.write('    ...\n')
                        break
                    d = self.analysis['pattern'][pattern_heading][pattern]
                    output_info = f"{d['pattern']} count: {d['count']}, {self.format_examples(d['ex'], pattern)}"
                    if self.string_contains_right_to_left_letters(output_info):
                        output_file.write(self.lrm)
                    output_file.write(f'    {output_info}\n')

    def n_tatweels(self) -> int:
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
                if (ex_s := self.analysis['letter-script'][letter_script].get('ex', None)) and len(ex_s) < 10:
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
                if (ex_s := self.analysis['number-script'][number_script].get('ex', None)) and len(ex_s) < 10:
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
        char_conflicts = self.analysis['char-conflict'].keys()
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


def plural_noun_form(noun: str) -> str:
    """Quick and dirty plural form, e.g. 'baby' -> 'babies'"""
    if noun.endswith('y'):
        return regex.sub(r'y$', 'ies', noun)
    else:
        return noun + 's'


def count_plus_noun(count: int, noun: str) -> str:
    """Quick and dirty count + plural form, e.g. (2, 'baby') -> '2 babies'"""
    return f'{count} {noun if count == 1 else plural_noun_form(noun)}'


def load_ref_ids(filename) -> dict:
    """Load file mapping line numbers to sentence IDs."""
    ref_id_dict = defaultdict(str)
    with open(filename, 'r', encoding='utf-8') as f:
        line_number = 0
        for line in f:
            line_number += 1
            ref_id_dict[line_number] = line.strip()
    return ref_id_dict


def process_args(args) -> WildebeestAnalysis:
    """Perform Wildebeest analysis for 1 file, using argparse args."""
    wb = WildebeestAnalysis(args)
    if args.ref_id_dict:
        wb.ref_id_dict = args.ref_id_dict
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

    if args.output is sys.stdout and not re.search('utf-8', sys.stdout.encoding, re.IGNORECASE):
        log.error(f"Error: Bad STDIN/STDOUT encoding '{sys.stdout.encoding}' as opposed to 'utf-8'. \
                        Suggestion: 'export PYTHONIOENCODING=UTF-8' or use use '--output FILENAME' option")
    if args.input:
        wb.collect_counts_and_examples_in_file(args.input, total_bytes=args.total_bytes, progress_bar=args.progress_bar)
    elif args.strings:
        line_number = 0
        for line in args.strings:
            line_number += 1
            wb.collect_counts_and_examples_in_line(line, line_number)
        wb.analysis['n_lines'] = line_number
    else:  # nothing to process
        log.warning('Called function process_with_args with neither args.input nor args.strings')
    wb.aggregate()  # Aggregate raw counts and examples into analysis.
    wb.remove_empty_dicts()  # Remove empty dictionaries that were created to impose a specific order
    if args.json:
        args.json.write(json.dumps(wb.analysis) + "\n")
    if args.summary:
        args.output.write(f"{args.file_id}: {'; '.join(wb.summary_list_of_issues())}\n")
    elif args.output:
        wb.pretty_print(args.output)
    if args.output:
        args.output.flush()
    return wb


def process(in_file: Optional[str] = None,     # provide exactly one input: input filename, strings or string
            strings: Optional[List[str]] = None,
            string: Optional[str] = None,
            pp_output: Optional[TextIO] = None,    # output filename (for pretty-print)
            json_output: Optional[TextIO] = None,  # output filename (in json)
            lang_code: Optional[str] = None,
            max_cases: int = 100,                  # max cases per block (e.g. number of characters in script)
            max_examples: int = 5,                 # max examples per case
            # ref_id_dict is a dictionary mapping line_numbers/string_indexes (int, starting at 1) to snt IDs (str)
            ref_id_dict: Optional[dict] = None) -> WildebeestAnalysis:
    """Entry point when Wildebeest Analysis for non-CLI use; maps to CLI interface"""
    return process_args(argparse.Namespace(strings=[string] if string and not strings else strings,
                                           input=Path(in_file) if in_file else None,
                                           output=pp_output, json=json_output,
                                           lc=lang_code, max_cases=max_cases, max_examples=max_examples,
                                           summary=None, progress_bar=None, ref_id_dict=ref_id_dict))


def main():
    """Wrapper around Wildebeest analysis that takes care of argument parsing and prints change stats to STDERR."""
    # parse arguments
    parser = argparse.ArgumentParser(description='Analyzes a given text for a wide range of anomalies', prog="wb-ana")
    parser.add_argument('-i', '--input', type=Path,
                        default=sys.stdin, metavar='INPUT-FILENAME', help='(default: STDIN)')
    parser.add_argument('--batch', type=Path, default=None, metavar='BATCH_DIR',
                        help='Directory with batch of input files (BATCH_DIR/*.txt)')
    parser.add_argument('-s', '--summary', action='count', default=0, help='single summary line per file')
    parser.add_argument('-o', '--output', type=argparse.FileType('w', encoding='utf-8', errors='ignore'),
                        default=sys.stdout, metavar='OUTPUT-FILENAME', help='(default: STDOUT)')
    parser.add_argument('-j', '--json', type=argparse.FileType('w', encoding='utf-8', errors='ignore'),
                        default=None, metavar='JSON-OUTPUT-FILENAME', help='(default: None)')
    parser.add_argument('--file_id', type=str, default=None)
    parser.add_argument('--lc', type=str, default=None,
                        metavar='LANGUAGE-CODE', help="ISO 639-3, e.g. 'fas' for Persian")
    parser.add_argument('-v', '--verbose', action='count', default=0, help='write change log etc. to STDERR')
    parser.add_argument('-pb', '--progress_bar', action='store_true', default=False, help='Show progress bar')
    parser.add_argument('-n', '--max_cases', type=int, default=100, help='max number of cases per group')
    parser.add_argument('-x', '--max_examples', type=int, default=5, help='max number of examples per line')
    parser.add_argument('-r', '--ref_id_file', type=Path, metavar='REF-FILENAME',
                        help='(optional file with sentence reference IDs)')
    parser.add_argument('--version', action='version',
                        version=f'%(prog)s {__version__} last modified: {last_mod_date}')
    parser.add_argument('--ref_id_dict', default=None, help=argparse.SUPPRESS)
    parser.add_argument('--strings', default=None, help=argparse.SUPPRESS)
    args = parser.parse_args()
    start_time = datetime.datetime.now()
    if args.verbose:
        log.info('Script: wb-analysis.py')
        log.info(f'Start: {start_time}')
        if args.input is not sys.stdin:
            log.info(f'Input: {args.input.name}')
        if args.output is not sys.stdout:
            log.info(f'Output: {args.output.name}')
    if args.ref_id_file:
        args.ref_id_dict = load_ref_ids(args.ref_id_file)
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
        process_args(args)
    if args.verbose:
        end_time = datetime.datetime.now()
        log.info(f'End: {end_time}')
        elapsed_time = end_time - start_time
        log.info(f'Time: {elapsed_time}')

if __name__ == "__main__":
    main()
