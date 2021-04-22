#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Written by Ulf Hermjakob, USC/ISI
Ported Pashto and Farsi-specific normalization from Perl to Python in August 2020.
Ported general normalization from Perl to Python in September 2020.
This script normalizes and cleans text (details below).
Examples:
  wildebeest_normalize.py -h  # for full usage info
  wildebeest_normalize.py --version
  wildebeest_normalize.py --lc fas -i 3S-dev-ssplit.aux.tok -o 3S-dev-ssplit.aux.clean2.tok
  wildebeest_normalize.py --lc fas --verbose --skip digit,punct < 3S-dev-ssplit.aux.tok > 3S-dev-ssplit.aux.clean1.tok
List of available normalization/cleaning-types (default: all are applied):
 * repair-encodings-errors (repairs missing, wrong, or double conversion from Windows-1252 or Latin-1 to UTF8)
 * del-surrogate (deletes surrogate characters (representing non-UTF8 characters in input),
                  alternative/backup to windows-1252)
 * del-ctrl-char (deletes control characters (expect tab and linefeed), zero-width characters, byte order mark,
                          directional marks, join marks, variation selectors, Arabic tatweel)
 * core-compat (normalizes Hangul Compatibility characters to Unicode standard Hangul characters)
 * arabic-char (to Arabic canonical forms, e.g. maps Farsi kaf/yeh to Arabic versions)
 * farsi-char (to Farsi canonical forms, e.g. maps Arabic yeh, kaf to Farsi versions)
 * pashto-char (to Pashto canonical forms, e.g. maps Arabic kaf to Farsi version)
 * georgian-char (to Georgian canonical forms, e.g. to standard script, map archaic characters)
 * pres-form (e.g. maps from presentation form (isolated, initial, medial, final) to standard form)
 * ligatures (e.g. decomposes ligatures)
 * signs-and-symbols (e.g. maps symbols (e.g. kappa symbol), signs (e.g. micro sign))
 * cjk
 * width (e.g. maps fullwidth and halfwidth characters to ASCII, e.g. Ａ to A)
 * font (maps font-variations characters such as ℂ, ℹ, 𝒜 to regular characters; Roman numerals to ASCII)
 * small (maps small versions of characters to normal versions, such as small ampersand ﹠ to regular &)
 * vertical (maps vertical versions of punctuation characters with normal horizontal version,
                  such as vertical em-dash ︱ to horizontal em-dash —)
 * enclosure (decomposes circled, squared and parenthesized characters)
 * hangul (combine Hangul jamos onto Hangul syllables)
 * repair-combining (e.g. order of nukta/vowel-sign)
 * combining-compose (e.g. applies combining-modifiers to preceding character, e.g. ö (o +  ̈) -> ö)
 * combining-decompose (e.g. for some Indian characters, splits off Nukta)
 * del-arabic-diacr (e.g. deletes diacritics such as Arabic fatha, damma, kasra)
 * del-hebrew-diacr (e.g. deletes Hebrew points)
 * digit (e.g. maps Arabic-Indic digits and extended Arabic-Indic digits to ASCII digits)
 * punct (e.g. maps ellipsis … to periods ... and two-dot-lead ‥ to ..; a few math symbols ∭; ⒛ 🄆 )
 * punct-dash (e.g. maps various dashes, hyphens, minus signs to ASCII hyphen-minus)
 * punct-arabic (e.g. Arabic exclamation mark etc. to ASCII equivalent)
 * punct-cjk (e.g. Chinese Ideographic Full Stop etc. to ASCII equivalent)
 * punct-greek (e.g. Greek question mark etc. to ASCII equivalent)
 * punct-misc-f (e.g. Tibetan punctuation to ASCII equivalent)
 * space (e.g. normalizes non-zero spaces to normal space)
 * look-alike (normalizes Latin/Cyrillic/Greek look-alike characters,
               e.g. Latin character A to Greek Α (capital alpha) in otherwise Greek word)
 * repair-xml (e.g. repairs multi-escaped tokens such as &amp;quot; or &amp;amp;#x200C;)
 * repair-url-escapes (e.g. repairs multi-escaped url substrings such as Jo%25C3%25ABlle_Aubron)
 * repair-token (e.g. splits +/-/*/digits off Arabic words; maps not-sign inside Arabic to token-separating hyphen)
When using STDIN and/or STDOUT, if might be necessary, particularly for older versions of Python, to do
'export PYTHONIOENCODING=UTF-8' before calling this Python script to ensure UTF-8 encoding.
"""
# -*- encoding: utf-8 -*-
import argparse
from itertools import chain
import datetime
import logging as log
import os
from pathlib import Path
import re
import sys
from typing import Callable, Match, Optional, TextIO

log.basicConfig(level=log.INFO)

__version__ = '0.6.3'
last_mod_date = 'April 21, 2021'


class Wildebeest:
    # noinspection PyPep8
    def __init__(self):
        # The following dictionary captures the irregular mappings from Windows1252 to UTF8.
        # noinspection SpellCheckingInspection
        self.spec_windows1252_to_utf8_dict = {
            '\x80': '\u20AC',  # Euro Sign
            #  81 is unassigned in Windows-1252
            '\x82': '\u201A',  # Single Low-9 Quotation Mark
            '\x83': '\u0192',  # Latin Small Letter F With Hook
            '\x84': '\u201E',  # Double Low-9 Quotation Mark
            '\x85': '\u2026',  # Horizontal Ellipsis
            '\x86': '\u2020',  # Dagger
            '\x87': '\u2021',  # Double Dagger
            '\x88': '\u02C6',  # Modifier Letter Circumflex Accent
            '\x89': '\u2030',  # Per Mille Sign
            '\x8A': '\u0160',  # Latin Capital Letter S With Caron
            '\x8B': '\u2039',  # Single Left-Pointing Angle Quotation Mark
            '\x8C': '\u0152',  # Latin Capital Ligature OE
            #  8D is unassigned in Windows-1252
            '\x8E': '\u017D',  # Latin Capital Letter Z With Caron
            #  8F is unassigned in Windows-1252
            #  90 is unassigned in Windows-1252
            '\x91': '\u2018',  # Left Single Quotation Mark
            '\x92': '\u2019',  # Right Single Quotation Mark
            '\x93': '\u201C',  # Left Double Quotation Mark
            '\x94': '\u201D',  # Right Double Quotation Mark
            '\x95': '\u2022',  # Bullet
            '\x96': '\u2013',  # En Dash
            '\x97': '\u2014',  # Em Dash
            '\x98': '\u02DC',  # Small Tilde
            '\x99': '\u2122',  # Trade Mark Sign
            '\x9A': '\u0161',  # Latin Small Letter S With Caron
            '\x9B': '\u203A',  # Single Right-Pointing Angle Quotation Mark
            '\x9C': '\u0153',  # Latin Small Ligature OE
            #  9D is unassigned in Windows-1252
            '\x9E': '\u017E',  # Latin Small Letter Z With Caron
            '\x9F': '\u0178'  # Latin Capital Letter Y With Diaeresis
        }
        self.char_type_vector_dict = {}
        # Initialize elementary bit vectors (integers each with a different bit set) will be used in bitwise operations.
        # To be expanded.
        self.lv = 0
        bit_vector = 1
        self.char_is_deletable_control_character = bit_vector
        bit_vector = bit_vector << 1
        self.char_is_decomposable_ligature = bit_vector
        bit_vector = bit_vector << 1
        self.char_is_decomposable_sign_symbol = bit_vector
        bit_vector = bit_vector << 1
        self.char_is_decomposable_with_combining = bit_vector
        bit_vector = bit_vector << 1
        self.char_is_composable_anchor_with_combining = bit_vector
        bit_vector = bit_vector << 1
        self.char_is_composable_combining_diacritic = bit_vector
        bit_vector = bit_vector << 1
        self.char_is_decomposable_arabic_punctuation = bit_vector
        bit_vector = bit_vector << 1
        self.char_is_decomposable_cjk_punctuation = bit_vector
        bit_vector = bit_vector << 1
        self.char_is_decomposable_greek_punctuation = bit_vector
        bit_vector = bit_vector << 1
        self.char_is_decomposable_misc_f_punctuation = bit_vector
        bit_vector = bit_vector << 1
        self.char_is_decomposable_dash = bit_vector
        bit_vector = bit_vector << 1
        self.char_is_decomposable_non_zero_space = bit_vector
        bit_vector = bit_vector << 1
        self.char_is_decomposable_enclosure = bit_vector
        bit_vector = bit_vector << 1
        self.char_is_decomposable_cjk = bit_vector
        bit_vector = bit_vector << 1
        self.char_is_mappable_decimal_digit = bit_vector
        bit_vector = bit_vector << 1
        self.char_is_font_small_vertical = bit_vector
        bit_vector = bit_vector << 1
        self.char_is_core_compatibility = bit_vector
        bit_vector = bit_vector << 1
        self.char_is_detachable_from_token = bit_vector
        bit_vector = bit_vector << 1
        self.char_is_ampersand = bit_vector
        bit_vector = bit_vector << 1
        self.char_is_semicolon = bit_vector
        bit_vector = bit_vector << 1
        self.char_is_percent_sign = bit_vector
        bit_vector = bit_vector << 1
        self.char_is_encoding_repair_anchor = bit_vector
        bit_vector = bit_vector << 1
        self.char_is_100_plus_block_of_interest = bit_vector  # code_points >= 0x10000 and of interest (e.g. digit)
        bit_vector = bit_vector << 1
        self.char_is_latin = bit_vector
        bit_vector = bit_vector << 1
        self.char_is_greek = bit_vector
        bit_vector = bit_vector << 1
        self.char_is_cyrillic = bit_vector
        bit_vector = bit_vector << 1
        self.char_is_hebrew = bit_vector
        bit_vector = bit_vector << 1
        self.char_is_deletable_hebrew_diacritic = bit_vector
        bit_vector = bit_vector << 1
        self.char_is_arabic = bit_vector  # includes Arabic presentation forms
        bit_vector = bit_vector << 1
        self.char_is_arabic_presentation_form = bit_vector
        bit_vector = bit_vector << 1
        self.char_is_deletable_arabic_diacritic = bit_vector
        bit_vector = bit_vector << 1
        self.char_is_mappable_in_arabic = bit_vector
        bit_vector = bit_vector << 1
        self.char_is_mappable_in_farsi = bit_vector
        bit_vector = bit_vector << 1
        self.char_is_mappable_in_pashto = bit_vector
        bit_vector = bit_vector << 1
        self.char_is_georgian = bit_vector
        bit_vector = bit_vector << 1
        self.char_is_thaana_plus = bit_vector  # Thaana, Nko, Samaritan, Mandaic, Syriac
        bit_vector = bit_vector << 1
        self.char_is_devanagari = bit_vector
        bit_vector = bit_vector << 1
        # Bengali, Gurmukhi, Gujarati, Oriya, Tamil, Telugu, Kannada, Malayalam, Sinhala
        self.char_is_bengali_plus = bit_vector
        bit_vector = bit_vector << 1
        self.char_is_nukta = bit_vector
        bit_vector = bit_vector << 1
        self.char_is_thai_plus = bit_vector  # Thai, Lao, Tibetan, Myanmar, Georgian
        bit_vector = bit_vector << 1
        # Khmer, Mongolian, Canadian Syllabics, Limbu, Tai Le, New Tai Lue
        # Buginese, Tai Tham, Balinese, Sundanese, Batak, Lepcha, Ol Chiki
        self.char_is_khmer_plus = bit_vector
        bit_vector = bit_vector << 1
        # Lisu, Vai Syllable, Banum, Sloti Nagri, Phags-Pa, Saurashtra,
        # Kayah Li, Rejang, Javanese, Cham, Tai Viet, Meetei Mayek
        self.char_is_lisu_plus = bit_vector
        bit_vector = bit_vector << 1
        self.char_is_surrogate = bit_vector
        bit_vector = bit_vector << 1
        self.char_is_fullwidth_or_halfwidth = bit_vector
        bit_vector = bit_vector << 1
        # Korean
        self.char_is_mappable_hangul = bit_vector
        # self.char_is_armenian = bit
        # self.char_is_japanese_kana = bit
        self.range_init_char_type_vector_dict()
        #
        # Initialize general mapping dictionary, which normalizes source strings (of length 1-3 characters)
        # to target strings (of length 0-5 characters).
        self.mapping_dict = {}
        self.init_mapping_dict()
        self.look_alike_dict = {}
        self.look_alike_unchanged_dict = {}
        self.look_alike_split_dict = {}
        self.look_alike_url_dict = {}
        self.look_alike_scripts = ['Latin', 'Greek', 'Cyrillic']
        self.repair_tok_punct_arabic_match = re.compile(r"([-_+*|%0-9]+)([\u0600-\u06FF])")
        self.repair_tok_arabic_punct_match = re.compile(r"([\u0600-\u06FF])([-_+*|%0-9]+)")
        self.georgian_intab = "\u1C90\u1C91\u1C92\u1C93\u1C94\u1C95\u1C96\u1C97\u1C98\u1C99\u1C9A\u1C9B\u1C9C\u1C9D\u1C9E\u1C9F\u1CA0\u1CA1\u1CA2\u1CA3\u1CA4\u1CA5\u1CA6\u1CA7\u1CA8\u1CA9\u1CAA\u1CAB\u1CAC\u1CAD\u1CAE\u1CAF\u1CB0\u1CB1\u1CB2\u1CB3\u1CB4\u1CB5\u1CB6\u1CB7\u1CB8\u1CB9\u1CBA\u1CBD\u1CBE\u1CBF\u10A0\u10A1\u10A2\u10A3\u10A4\u10A5\u10A6\u10A7\u10A8\u10A9\u10AA\u10AB\u10AC\u10AD\u10AE\u10AF\u10B0\u10B1\u10B2\u10B3\u10B4\u10B5\u10B6\u10B7\u10B8\u10B9\u10BA\u10BB\u10BC\u10BD\u10BE\u10BF\u10C0\u10C1\u10C2\u10C3\u10C4\u10C5\u10C7\u10CD\u2D00\u2D01\u2D02\u2D03\u2D04\u2D05\u2D06\u2D07\u2D08\u2D09\u2D0A\u2D0B\u2D0C\u2D0D\u2D0E\u2D0F\u2D10\u2D11\u2D12\u2D13\u2D14\u2D15\u2D16\u2D17\u2D18\u2D19\u2D1A\u2D1B\u2D1C\u2D1D\u2D1E\u2D1F\u2D20\u2D21\u2D22\u2D23\u2D24\u2D25\u2D27\u2D2D"
        self.georgian_outtab = "\u10D0\u10D1\u10D2\u10D3\u10D4\u10D5\u10D6\u10D7\u10D8\u10D9\u10DA\u10DB\u10DC\u10DD\u10DE\u10DF\u10E0\u10E1\u10E2\u10E3\u10E4\u10E5\u10E6\u10E7\u10E8\u10E9\u10EA\u10EB\u10EC\u10ED\u10EE\u10EF\u10F0\u10F1\u10F2\u10F3\u10F4\u10F5\u10F6\u10F7\u10F8\u10F9\u10FA\u10FD\u10FE\u10FF\u10D0\u10D1\u10D2\u10D3\u10D4\u10D5\u10D6\u10D7\u10D8\u10D9\u10DA\u10DB\u10DC\u10DD\u10DE\u10DF\u10E0\u10E1\u10E2\u10E3\u10E4\u10E5\u10E6\u10E7\u10E8\u10E9\u10EA\u10EB\u10EC\u10ED\u10EE\u10EF\u10F0\u10F1\u10F2\u10F3\u10F4\u10F5\u10F7\u10FD\u10D0\u10D1\u10D2\u10D3\u10D4\u10D5\u10D6\u10D7\u10D8\u10D9\u10DA\u10DB\u10DC\u10DD\u10DE\u10DF\u10E0\u10E1\u10E2\u10E3\u10E4\u10E5\u10E6\u10E7\u10E8\u10E9\u10EA\u10EB\u10EC\u10ED\u10EE\u10EF\u10F0\u10F1\u10F2\u10F3\u10F4\u10F5\u10F7\u10FD"
        self.georgian_trantab = str.maketrans(self.georgian_intab, self.georgian_outtab)

    def windows1252_to_utf8_char(self, index: int) -> str:
        """ Typical input: 0x80       Typical output: '€' """
        s = chr(index)
        if s in self.spec_windows1252_to_utf8_dict:
            return self.spec_windows1252_to_utf8_dict[s]
        else:
            return s

    def set_mapping_dict(self, key: str, value: str, index: int, byte_string: Optional[bytes], loc: str,
                         verbose: bool = False) -> None:
        self.mapping_dict[key] = value
        if verbose:
            log.info(f'map-{loc} {index} {key} -> {value}   byte_string:{byte_string}')

    def range_init_char_type_vector_dict(self) -> None:
        # Deletable control characters
        for code_point in chain(range(0x0000, 0x0009), range(0x000B, 0x000D), range(0x000E, 0x0020), [0x007F],  # C0
                                range(0x0080, 0x00A0),     # C1 block of control characters
                                [0x0640],                  # Arabic tatweel
                                range(0x200B, 0x2010),     # zero width space/non-joiner/joiner, direction marks
                                range(0xFE00, 0xFE10),     # variation selectors 1-16
                                [0xFEFF],                  # byte order mark, zero width no-break space
                                range(0xE0100, 0xE01F0)):  # variation selectors 17-256
            char = chr(code_point)
            self.char_type_vector_dict[char] \
                = self.char_type_vector_dict.get(char, 0) | self.char_is_deletable_control_character
        # Surrogate
        for code_point in range(0xDC80, 0xDD00):
            char = chr(code_point)
            self.char_type_vector_dict[char] \
                = self.char_type_vector_dict.get(char, 0) | self.char_is_surrogate
        # Decomposable ligatures (partial list)
        for code_point in [0x0E33, 0x0EB3, 0x0EDC, 0x0EDD, 0x1E9B]:
            char = chr(code_point)
            self.char_type_vector_dict[char] \
                = self.char_type_vector_dict.get(char, 0) | self.char_is_decomposable_ligature
        # Decomposable dash
        for code_point in chain([0x00AD],
                                range(0x2010, 0x2016),
                                [0x2212, 0x2500, 0x2501, 0x2E3A, 0x2E3B, 0xFE31, 0xFE32, 0xFE58, 0xFE63, 0xFF0D]):
            char = chr(code_point)
            self.char_type_vector_dict[char] \
                = self.char_type_vector_dict.get(char, 0) | self.char_is_decomposable_dash
        # Decomposable non-zero space
        for code_point in chain(range(0x2000, 0x200B), [0x00A0, 0x202F, 0x205F, 0x3000]):
            char = chr(code_point)
            self.char_type_vector_dict[char] \
                = self.char_type_vector_dict.get(char, 0) | self.char_is_decomposable_non_zero_space
        # Detachable from token
        for char in ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '-', '_', '+', '*', '|', '%']:
            self.char_type_vector_dict[char] \
                = self.char_type_vector_dict.get(char, 0) | self.char_is_detachable_from_token
        # XML, URL escapes
        self.char_type_vector_dict['&'] = self.char_type_vector_dict.get('&', 0) | self.char_is_ampersand
        self.char_type_vector_dict[';'] = self.char_type_vector_dict.get(';', 0) | self.char_is_semicolon
        self.char_type_vector_dict['%'] = self.char_type_vector_dict.get('%', 0) | self.char_is_percent_sign
        # Fullwidth, halfwidth
        for code_point in range(0xFF01, 0xFFEF):
            char = chr(code_point)
            self.char_type_vector_dict[char] \
                = self.char_type_vector_dict.get(char, 0) | self.char_is_fullwidth_or_halfwidth
        # Latin
        for code_point in chain(range(0x0041, 0x005B), range(0x0061, 0x007B), range(0x00C0, 0x00D7),
                                range(0x00D8, 0x00F7), range(0x00F8, 0x02B0), range(0x2C60, 0x2080),
                                range(0xA720, 0xA800), range(0xAB30, 0xAB70)):
            char = chr(code_point)
            self.char_type_vector_dict[char] \
                = self.char_type_vector_dict.get(char, 0) | self.char_is_latin
        # Greek
        for code_point in chain(range(0x0370, 0x0400), range(0x1F00, 0x2000)):
            char = chr(code_point)
            self.char_type_vector_dict[char] \
                = self.char_type_vector_dict.get(char, 0) | self.char_is_greek
        # Cyrillic
        for code_point in chain(range(0x0400, 0x0530), range(0x1C80, 0x1C90), range(0x2DE0, 0x2E00),
                                range(0xA640, 0xA6A0)):
            char = chr(code_point)
            self.char_type_vector_dict[char] \
                = self.char_type_vector_dict.get(char, 0) | self.char_is_cyrillic
        # Hebrew
        for code_point in chain(range(0x0590, 0x0600), range(0xFB1D, 0xFB50)):
            char = chr(code_point)
            self.char_type_vector_dict[char] \
                = self.char_type_vector_dict.get(char, 0) | self.char_is_hebrew
        for code_point in chain(range(0x05B0, 0x05BE), [0x05BF, 0x05C1, 0x05C2, 0x05C7]):
            char = chr(code_point)
            self.char_type_vector_dict[char] \
                = self.char_type_vector_dict.get(char, 0) | self.char_is_deletable_hebrew_diacritic
        # Arabic
        for code_point in chain(range(0x0600, 0x0700), range(0x0750, 0x0780), range(0x08A0, 0x0900)):
            char = chr(code_point)
            self.char_type_vector_dict[char] \
                = self.char_type_vector_dict.get(char, 0) | self.char_is_arabic
        for code_point in chain(range(0xFB50, 0xFE00), range(0xFE70, 0xFEFF)):
            char = chr(code_point)
            self.char_type_vector_dict[char] \
                = self.char_type_vector_dict.get(char, 0) | self.char_is_arabic | self.char_is_arabic_presentation_form
        for code_point in range(0x064B, 0x0653):
            char = chr(code_point)
            self.char_type_vector_dict[char] \
                = self.char_type_vector_dict.get(char, 0) | self.char_is_deletable_arabic_diacritic
        for code_point in [0x06A9, 0x06CC, 0x0675, 0x0676, 0x0678, 0x067C, 0x0689, 0x0693, 0x06AB, 0x06BC, 0x06CD]:
            char = chr(code_point)
            self.char_type_vector_dict[char] \
                = self.char_type_vector_dict.get(char, 0) | self.char_is_mappable_in_arabic
        for code_point in [0x064A, 0x0649, 0x06CD, 0x0643, 0x06AB, 0x067C, 0x0689, 0x0693, 0x06BC, 0x06CD]:
            char = chr(code_point)
            self.char_type_vector_dict[char] \
                = self.char_type_vector_dict.get(char, 0) | self.char_is_mappable_in_farsi
        for code_point in [0x0649, 0x06CD, 0x0643]:
            char = chr(code_point)
            self.char_type_vector_dict[char] \
                = self.char_type_vector_dict.get(char, 0) | self.char_is_mappable_in_pashto
        # Georgian
        for code_point in chain(range(0x10A0, 0x10FF), range(0x1C90, 0x1CBF), range(0x2D00, 0x2D2F)):
            char = chr(code_point)
            self.char_type_vector_dict[char] \
                = self.char_type_vector_dict.get(char, 0) | self.char_is_georgian
        # Thaana+
        for code_point in range(0x0780, 0x08A0):
            char = chr(code_point)
            self.char_type_vector_dict[char] \
                = self.char_type_vector_dict.get(char, 0) | self.char_is_thaana_plus
        # Devanagari
        for code_point in chain(range(0x0900, 0x0980), range(0xA8E0, 0xA900)):
            char = chr(code_point)
            self.char_type_vector_dict[char] \
                = self.char_type_vector_dict.get(char, 0) | self.char_is_devanagari
        # Bengali+
        for code_point in range(0x0980, 0x0E00):
            char = chr(code_point)
            self.char_type_vector_dict[char] \
                = self.char_type_vector_dict.get(char, 0) | self.char_is_bengali_plus
        # Nukta
        for code_point in [0x093C, 0x09BC, 0x0A3C, 0x0ABC, 0x0B3C, 0x0CBC, 0x1C37, 0x110BA, 0x11173, 0x111CA, 0x11236,
                           0x112E9, 0x1133C, 0x11446, 0x114C3, 0x115C0, 0x116B7, 0x1183A, 0x11943, 0x11D42, 0x1E94A]:
            char = chr(code_point)
            self.char_type_vector_dict[char] \
                = self.char_type_vector_dict.get(char, 0) | self.char_is_nukta
            if code_point >= 0x10000:
                self.char_type_vector_dict[char] \
                    = self.char_type_vector_dict.get(char, 0) | self.char_is_100_plus_block_of_interest
        # Thai+
        for code_point in range(0x0E00, 0x1100):
            char = chr(code_point)
            self.char_type_vector_dict[char] \
                = self.char_type_vector_dict.get(char, 0) | self.char_is_thai_plus
        # Korean
        for code_point in range(0x1161, 0x1176):
            char = chr(code_point)
            self.char_type_vector_dict[char] \
                = self.char_type_vector_dict.get(char, 0) | self.char_is_mappable_hangul
        # Khmer+
        for code_point in chain(range(0x1780, 0x1AB0), range(0x1B00, 0x1C80), range(0x1CC0, 0x1CD0)):
            char = chr(code_point)
            self.char_type_vector_dict[char] \
                = self.char_type_vector_dict.get(char, 0) | self.char_is_khmer_plus
        # Lisu+
        for code_point in chain(range(0xA4D0, 0xA630), range(0xA6A0, 0xA700), range(0xA800, 0xA830),
                                range(0xA840, 0xA8E0), range(0xA900, 0xA960), range(0xA980, 0xA9E0),
                                range(0xAA00, 0xAA60), range(0xAA80, 0xAB00)):
            char = chr(code_point)
            self.char_type_vector_dict[char] \
                = self.char_type_vector_dict.get(char, 0) | self.char_is_lisu_plus

    def load_look_alike_file(self) -> None:
        src_dir_path = os.path.dirname(os.path.realpath(__file__))
        data_dir_path = os.path.join(src_dir_path, "data")
        look_alike_filename = os.path.join(data_dir_path, 'look-alikes.txt')
        line_number = 0
        n_entries = 0
        look_alike_category = None
        with open(look_alike_filename, 'r', encoding='utf-8') as f:
            for line in f:
                line_number += 1
                line_contains_entry = False
                script_dict = {}  # local mapping from script (e.g. Latin|Greek|Cyrillic) to character (e.g. w|θ|ж)
                if re.search('::section', line):
                    if re.search('Identical-looking characters', line):
                        look_alike_category = 'identical'
                    elif re.search('Similar-looking characters', line):
                        look_alike_category = 'similar'
                    else:
                        look_alike_category = None
                else:
                    char_list = re.split(r'\s+', line.rstrip())
                    if look_alike_category == 'identical':
                        for char in char_list:
                            script = self.char_script(char)
                            if script and script_dict.get(script, None) is None:
                                script_dict[script] = char
                        for script1 in self.look_alike_scripts:
                            char1 = script_dict.get(script1, None)
                            if char1:
                                for script2 in self.look_alike_scripts:
                                    if script1 != script2:
                                        char2 = script_dict.get(script2, None)
                                        if char2:
                                            self.look_alike_dict[f'{script1} {script2} {char1}'] = char2
                                            line_contains_entry = True
                if line_contains_entry:
                    n_entries += 1
            log.info(f'Loaded {n_entries} entries from {look_alike_filename}')

    def update_char_type_vector_dict(self, source: str, target: str, filename_core: str) -> None:
        if filename_core == 'Digit':
            self.char_type_vector_dict[source] \
                = self.char_type_vector_dict.get(source, 0) | self.char_is_mappable_decimal_digit
            if len(source) >= 1 and ord(source[0]) >= 0x10000:
                self.char_type_vector_dict[source] \
                    = self.char_type_vector_dict.get(source, 0) | self.char_is_100_plus_block_of_interest
        elif filename_core == 'FontSmallVertical':
            self.char_type_vector_dict[source] \
                = self.char_type_vector_dict.get(source, 0) | self.char_is_font_small_vertical
        elif filename_core == 'CoreCompatibility':
            self.char_type_vector_dict[source] \
                = self.char_type_vector_dict.get(source, 0) | self.char_is_core_compatibility
        elif filename_core == 'CJKCompatibility':
            self.char_type_vector_dict[source] \
                = self.char_type_vector_dict.get(source, 0) | self.char_is_decomposable_cjk
        elif filename_core == 'PythonWildebeest':
            if len(source) == 1:
                code_point = ord(source)
                if (0x0132 <= code_point <= 0x01F3) or (0xFB00 <= code_point <= 0xFB4F):
                    self.char_type_vector_dict[source] \
                        = self.char_type_vector_dict.get(source, 0) | self.char_is_decomposable_ligature
                elif (code_point == 0x00B5) or (0x03D0 <= code_point <= 0x03F9) or (0x20A8 <= code_point <= 0x213B):
                    self.char_type_vector_dict[source] \
                        = self.char_type_vector_dict.get(source, 0) | self.char_is_decomposable_sign_symbol
                elif 0x0340 <= code_point <= 0x0387:
                    self.char_type_vector_dict[source] \
                        = self.char_type_vector_dict.get(source, 0) | self.char_is_decomposable_greek_punctuation
                elif 0x060C <= code_point <= 0x06D4:
                    self.char_type_vector_dict[source] \
                        = self.char_type_vector_dict.get(source, 0) | self.char_is_decomposable_arabic_punctuation
                elif ((0x3008 <= code_point <= 0x3011) or (0x3014 <= code_point <= 0x301B)  # Chinese brackets
                        or (0xFF61 <= code_point <= 0xFF64)  # Chinese halfwidth punctuation
                        or (code_point in [0x3001, 0x3002, 0xFE11, 0xFE12, 0xFE51])):  # periods, commas
                    self.char_type_vector_dict[source] \
                        = self.char_type_vector_dict.get(source, 0) | self.char_is_decomposable_cjk_punctuation
                elif code_point == 0x0F0C:
                    self.char_type_vector_dict[source] \
                        = self.char_type_vector_dict.get(source, 0) | self.char_is_decomposable_misc_f_punctuation
        elif filename_core == 'Enclosure':
            if len(source) >= 1:
                char = source[0]
                self.char_type_vector_dict[char] \
                    = self.char_type_vector_dict.get(char, 0) | self.char_is_decomposable_enclosure
        elif filename_core == 'EncodingRepair':
            if len(source) >= 1:
                char = source[0]
                self.char_type_vector_dict[char] \
                    = self.char_type_vector_dict.get(char, 0) | self.char_is_encoding_repair_anchor
        elif filename_core == 'CombiningModifier':
            if len(source) == 1:
                self.char_type_vector_dict[source] \
                    = self.char_type_vector_dict.get(source, 0) | self.char_is_decomposable_with_combining
            elif (len(source) >= 2) and (len(target) == 1):
                self.char_type_vector_dict[source[0]] \
                    = self.char_type_vector_dict.get(source[0], 0) | self.char_is_composable_anchor_with_combining
                self.char_type_vector_dict[source[1]] \
                    = self.char_type_vector_dict.get(source[1], 0) | self.char_is_composable_combining_diacritic
            else:
                log.info('Unexpected CombiningModifier entry {source}/{target}')

    # noinspection SpellCheckingInspection
    def init_mapping_dict(self, undef_default: str = '') -> None:
        """Initialize mapping_dict that maps from various misencodings to proper UTF8."""
        # Misencodings that resulted from missing conversion from Windows1252/Latin1 to UTF8.
        # Control characters section in surrogate code block
        for index in range(0x80, 0xA0):
            spec_windows1252_char = chr(index)
            surrogate_char = chr(index + 0xDC00)
            if spec_windows1252_char in self.spec_windows1252_to_utf8_dict:
                self.set_mapping_dict(surrogate_char, self.spec_windows1252_to_utf8_dict[spec_windows1252_char],
                                      index, None, 's1')
            else:  # x81,x8D,x8F,x90,x9D
                self.set_mapping_dict(surrogate_char, undef_default, index, None, 's2')
        # Other characters in surrogate code block
        for index in range(0xA0, 0x100):
            latin1_char = chr(index)
            surrogate_char = chr(index + 0xDC00)
            self.set_mapping_dict(surrogate_char, latin1_char, index, None, 's3')
        src_dir_path = os.path.dirname(os.path.realpath(__file__))
        data_dir_path = os.path.join(src_dir_path, "data")
        for tsv_filename in ('PythonWildebeestMapping.tsv',
                             'ArabicPresentationFormMapping.tsv',
                             'CJKCompatibilityMapping.tsv',
                             'CombiningModifierMapping.tsv',
                             'CoreCompatibilityMapping.tsv',
                             'DigitMapping.tsv',
                             'EnclosureMapping.tsv',
                             'EncodingRepairMapping.tsv',
                             'FontSmallVerticalMapping.tsv'):
            filename_core = tsv_filename.replace('Mapping.tsv', '')
            full_tsv_filename = os.path.join(data_dir_path, tsv_filename)
            filenames_considered = [full_tsv_filename]
            if not Path(full_tsv_filename).is_file():
                full_tsv_filename = os.path.join(data_dir_path, tsv_filename.replace('.tsv', 'Annotated.tsv'))
                filenames_considered += [full_tsv_filename]
            try:
                with open(full_tsv_filename, 'r', encoding='utf-8', errors='ignore') as f:
                    line_number = 0
                    for line in f:
                        line_number += 1
                        tsv_list = re.split(r'\t', line.rstrip())
                        if (len(tsv_list) >= 2) and (line_number >= 2):
                            self.mapping_dict[tsv_list[0]] = tsv_list[1]
                            self.update_char_type_vector_dict(tsv_list[0], tsv_list[1], filename_core)
            except FileNotFoundError:
                log.error(f"Could not open {' or '.join(filenames_considered)}")

    def apply_mapping_dict(self, match: Match[str]) -> str:
        """Maps substring resulting from misencoding to repaired UTF8."""
        s = match.group()
        if s in self.mapping_dict:
            return self.mapping_dict[s]
        else:
            return s

    # noinspection SpellCheckingInspection
    def repair_encoding_errors(self, s: str) -> str:
        """
        Interpret non-UTF8 characters (standalone \x80-\xFF, read in as surrogate characters \uDC80-\uDCFF])
        as one-byte Windows-1252/Latin-1 (ISO-8859-1) characters. Please note that ASCII characters (\u0000-\u007F)
        are encoded identically in UTF-8, Latin-1, and Windows-1252, so no conversion is necessary in that case.
        """
        # Correct missing conversion to UTF8
        s = re.sub(r'[\uDC80-\uDCFF]', self.apply_mapping_dict, s)
        # Correct UTF8 misencodings due to wrong or double application of Windows1252/Latin1-to-UTF converter
        s = re.sub(r'\u00E2[\u0080-\u00BF][\u0080-\u00BF]', self.apply_mapping_dict, s)
        s = re.sub(r'[\u00C2-\u00C3\u00C5\u00C6\u00CB][\u0080-\u02FF\u2000-\u21FF]', self.apply_mapping_dict, s)
        s = re.sub(r'[\u0080-\u009F]', self.apply_mapping_dict, s)
        return s

    # noinspection SpellCheckingInspection
    @staticmethod
    def delete_surrogates(s: str, default: str = '') -> str:
        """As an alternative or backup to windows1252_to_utf8, delete all surrogate characters \uDC80-\uDCFF])."""
        return re.sub(r"[\uDC80-\uDCFF]", default, s)

    @staticmethod
    def delete_control_characters(s: str) -> str:
        """Deletes control characters (except tab and linefeed), zero-width characters, byte order mark,
           directional marks, join marks, variation selectors, Arabic tatweel"""
        s = s.replace('\u00AD', '')  # U+00AD soft hyphen
        s = re.sub(r'[\u0000-\u0008]', '', s)  # control characters C0 code block (except tab \x09, linefeed \x0A)
        s = re.sub(r'[\u000B-\u000C]', '', s)  # control characters C0 code block (continued, except CR \x0D)
        s = re.sub(r'[\u000E-\u001F]', '', s)  # control characters C0 code block (continued)
        s = re.sub(r'[\u007F-\u009F]', '', s)  # control characters 'DELETE' and C1 code block
        s = s.replace('\u0640', '')  # Arabic tatweel
        s = re.sub(r'[\u200B-\u200F]', '', s)  # zero width space/non-joiner/joiner, direction marks
        s = re.sub(r'[\uFE00-\uFE0F]', '', s)  # variation selectors 1-16
        # noinspection SpellCheckingInspection
        s = s.replace('\uFEFF', '')  # byte order mark, zero width no-break space
        s = re.sub(r'[\U000E0100-\U000E01EF]', '', s)  # variation selectors 17-256
        return s

    @staticmethod
    def delete_arabic_diacritics(s: str) -> str:
        s = s.replace('\u064B', '')  # delete Arabic fathatan
        s = s.replace('\u064C', '')  # delete Arabic dammatan
        s = s.replace('\u064D', '')  # delete Arabic kasratan
        s = s.replace('\u064E', '')  # delete Arabic fatha
        s = s.replace('\u064F', '')  # delete Arabic damma
        s = s.replace('\u0650', '')  # delete Arabic kasra
        s = s.replace('\u0651', '')  # delete Arabic shadda
        s = s.replace('\u0652', '')  # delete Arabic sukun
        return s

    @staticmethod
    def delete_hebrew_diacritics(s: str) -> str:
        s = s.replace('\u05B0', '')  # HEBREW POINT SHEVA
        s = s.replace('\u05B1', '')  # HEBREW POINT HATAF SEGOL
        s = s.replace('\u05B2', '')  # HEBREW POINT HATAF PATAH
        s = s.replace('\u05B3', '')  # HEBREW POINT HATAF QAMATS
        s = s.replace('\u05B4', '')  # HEBREW POINT HIRIQ
        s = s.replace('\u05B5', '')  # HEBREW POINT TSERE
        s = s.replace('\u05B6', '')  # HEBREW POINT SEGOL
        s = s.replace('\u05B7', '')  # HEBREW POINT PATAH
        s = s.replace('\u05B8', '')  # HEBREW POINT QAMATS
        s = s.replace('\u05B9', '')  # HEBREW POINT HOLAM
        s = s.replace('\u05BA', '')  # HEBREW POINT HOLAM HASER FOR VAV
        s = s.replace('\u05BB', '')  # HEBREW POINT QUBUTS
        s = s.replace('\u05BC', '')  # HEBREW POINT DAGESH OR MAPIQ
        s = s.replace('\u05BD', '')  # HEBREW POINT METEG
        s = s.replace('\u05BF', '')  # HEBREW POINT RAFE
        s = s.replace('\u05C1', '')  # HEBREW POINT SHIN DOT
        s = s.replace('\u05C2', '')  # HEBREW POINT SIN DOT
        s = s.replace('\u05C7', '')  # HEBREW POINT QAMATS QATAN
        return s

    # noinspection SpellCheckingInspection
    @staticmethod
    def normalize_arabic_characters(s: str) -> str:
        # For any additions below, also update setting of char_is_mappable_in_arabic
        # Some of the below, particularly the alef maksura, might be too aggressive. Too be verified.
        #    More conservative: keep alef maksura and map final/isolated Farsi yeh to alef maksura.
        # s = s.replace('\u0649', '\u064A')  # alef maksura to yeh
        s = s.replace('\u06A9', '\u0643')  # Farsi kaf/keheh to (Arabic) kaf
        s = s.replace('\u06CC', '\u064A')  # Farsi yeh to (Arabic) yeh
        s = s.replace('\u0675', '\u0623')  # (Kazakh) high hamza alef to alef with hamza above
        s = s.replace('\u0676', '\u0624')  # (Kazakh) high hamza waw to waw with hamza above
        s = s.replace('\u0678', '\u0626')  # (Kazakh) high hamza yeh to yeh with hamza above
        s = s.replace('\u067C', '\u062A')  # (Pashto) teh with ring to teh
        s = s.replace('\u0689', '\u062F')  # (Pashto) dal with ring to dal
        s = s.replace('\u0693', '\u0631')  # (Pashto) reh with ring to reh
        s = s.replace('\u06AB', '\u06AF')  # (Pashto) kaf with ring to gaf
        s = s.replace('\u06BC', '\u0646')  # (Pashto) noon with ring to noon
        s = s.replace('\u06CD', '\u064A')  # (Pashto) yeh with tail to yeh
        # Not necessarily complete.
        return s

    # noinspection SpellCheckingInspection
    @staticmethod
    def normalize_farsi_characters(s: str) -> str:
        # For any additions below, also update setting of char_is_mappable_in_farsi
        s = s.replace('\u064A', '\u06CC')  # Arabic to Farsi yeh
        s = s.replace('\u0649', '\u06CC')  # Arabic alef maksura to Farsi yeh
        s = s.replace('\u06CD', '\u06CC')  # Arabic yeh with tail to Farsi yeh
        s = s.replace('\u0643', '\u06A9')  # Arabic kaf to keheh
        s = s.replace('\u06AB', '\u06AF')  # (Pashto) kaf with ring to gaf
        s = s.replace('\u067C', '\u062A')  # (Pashto) teh with ring to Arabic teh
        s = s.replace('\u0689', '\u062F')  # (Pashto) dal with ring to Arabic dal
        s = s.replace('\u0693', '\u0631')  # (Pashto) reh with ring to Arabic reh
        s = s.replace('\u06BC', '\u0646')  # (Pashto) noon with ring to noon
        s = s.replace('\u06CD', '\u064A')  # (Pashto) yeh with tail to yeh
        return s

    @staticmethod
    def normalize_pashto_characters(s: str) -> str:
        # For any additions below, also update setting of char_is_mappable_in_pashto
        s = s.replace('\u0649', '\u06CC')  # Arabic alef maksura to Farsi yeh
        s = s.replace('\u06CD', '\u06CC')  # Arabic yeh with tail to Farsi yeh
        s = s.replace('\u0643', '\u06A9')  # Arabic kaf to keheh
        return s

    def normalize_georgian_characters(self, s: str) -> str:
        s = s.translate(self.georgian_trantab)
        s = s.replace('ჱ', 'ე')   # archaic Georgian letter he
        s = s.replace('ჲ', 'ი')   # archaic Georgian letter hie
        s = s.replace('ჳ', 'ვი')  # archaic Georgian letter we
        s = s.replace('ჴ', 'ხე')  # archaic Georgian letter har
        s = s.replace('ჵ', 'ჰოი') # archaic Georgian letter hoe
        return s

    # noinspection SpellCheckingInspection
    def normalize_arabic_pres_form_characters(self, s: str) -> str:
        """This includes some Arabic ligatures."""
        s = re.sub(r'[\uFB50-\uFDFF\uFE70-\uFEFC]', self.apply_mapping_dict, s)
        return s

    # noinspection SpellCheckingInspection
    @staticmethod
    def normalize_ligatures(s: str) -> str:
        """Arabic ligatures are already covered by function normalize_arabic_pres_form_characters."""
        s = s.replace('\u0132', '\u0049\u004A')  # U+0132 LATIN CAPITAL LIGATURE IJ Ĳ -> IJ
        s = s.replace('\u0133', '\u0069\u006A')  # U+0133 LATIN SMALL LIGATURE IJ ĳ -> ij
        s = s.replace('\u013F', '\u004C\u00B7')  # U+013F LATIN CAPITAL LETTER L WITH MIDDLE DOT Ŀ -> L·
        s = s.replace('\u0140', '\u006C\u00B7')  # U+0140 LATIN SMALL LETTER L WITH MIDDLE DOT ŀ -> l·
        s = s.replace('\u0149', '\u02BC\u006E')  # U+0149 LATIN SMALL LETTER N PRECEDED BY APOSTROPHE ŉ -> ʼn \
        s = s.replace('\u017F', '\u0073')        # U+017F LATIN SMALL LETTER LONG S ſ -> s
        s = s.replace('\u01C4', '\u0044\u017D')  # U+01C4 LATIN CAPITAL LETTER DZ WITH CARON Ǆ -> DŽ
        s = s.replace('\u01C5', '\u0044\u017E')  # U+01C5 LATIN CAPITAL D WITH SMALL Z WITH CARON ǅ -> Dž
        s = s.replace('\u01C6', '\u0064\u017E')  # U+01C6 LATIN SMALL LETTER DZ WITH CARON ǆ -> dž
        s = s.replace('\u01C7', '\u004C\u004A')  # U+01C7 LATIN CAPITAL LETTER LJ Ǉ -> LJ
        s = s.replace('\u01C8', '\u004C\u006A')  # U+01C8 LATIN CAPITAL LETTER L WITH SMALL LETTER J ǈ -> Lj
        s = s.replace('\u01C9', '\u006C\u006A')  # U+01C9 LATIN SMALL LETTER LJ ǉ -> lj
        s = s.replace('\u01CA', '\u004E\u004A')  # U+01CA LATIN CAPITAL LETTER NJ Ǌ -> NJ
        s = s.replace('\u01CB', '\u004E\u006A')  # U+01CB LATIN CAPITAL LETTER N WITH SMALL LETTER J ǋ -> Nj
        s = s.replace('\u01CC', '\u006E\u006A')  # U+01CC LATIN SMALL LETTER NJ ǌ -> nj
        s = s.replace('\u01F1', '\u0044\u005A')  # U+01F1 LATIN CAPITAL LETTER DZ Ǳ -> DZ
        s = s.replace('\u01F2', '\u0044\u007A')  # U+01F2 LATIN CAPITAL LETTER D WITH SMALL LETTER Z ǲ -> Dz
        s = s.replace('\u01F3', '\u0064\u007A')  # U+01F3 LATIN SMALL LETTER DZ ǳ -> dz
        s = s.replace('\u1E9B', '\u1E61')        # U+1E9B LATIN SMALL LETTER LONG S WITH DOT ABOV ẛ -> ṡ
        s = s.replace('\uFB00', '\u0066\u0066')  # U+FB00 LATIN SMALL LIGATURE FF ﬀ -> ff
        s = s.replace('\uFB01', '\u0066\u0069')  # U+FB01 LATIN SMALL LIGATURE FI ﬁ -> fi
        s = s.replace('\uFB02', '\u0066\u006C')  # U+FB02 LATIN SMALL LIGATURE FL ﬂ -> fl
        s = s.replace('\uFB03', '\u0066\u0066\u0069')  # U+FB03 LATIN SMALL LIGATURE FFI ﬃ -> ffi
        s = s.replace('\uFB04', '\u0066\u0066\u006C')  # U+FB04 LATIN SMALL LIGATURE FFL ﬄ -> ffl
        s = s.replace('\uFB05', '\u0073\u0074')  # U+FB05 LATIN SMALL LIGATURE LONG S T ﬅ -> ſt
        s = s.replace('\uFB06', '\u0073\u0074')  # U+FB06 LATIN SMALL LIGATURE ST ﬆ -> st
        s = s.replace('\uFB13', '\u0574\u0576')  # U+FB13 ARMENIAN SMALL LIGATURE MEN NOW ﬓ -> մն
        s = s.replace('\uFB14', '\u0574\u0565')  # U+FB14 ARMENIAN SMALL LIGATURE MEN ECH ﬔ -> մե
        s = s.replace('\uFB15', '\u0574\u056B')  # U+FB15 ARMENIAN SMALL LIGATURE MEN INI ﬕ -> մի
        s = s.replace('\uFB16', '\u057E\u0576')  # U+FB16 ARMENIAN SMALL LIGATURE VEW NOW ﬖ -> վն
        s = s.replace('\uFB17', '\u0574\u056D')  # U+FB17 ARMENIAN SMALL LIGATURE MEN XEH ﬗ -> մխ
        s = s.replace('\uFB49', '\u05E9\u05BC')  # U+FB49 HEBREW LETTER SHIN WITH DAGESH שּ -> שּ
        s = s.replace('\uFB4F', '\u05D0\u05DC')  # U+FB4F HEBREW LIGATURE ALEF LAMED ﭏ -> אל
        return s

    @staticmethod
    def normalize_signs_and_symbols(s: str) -> str:
        s = s.replace('\u00B5', '\u03BC')        # U+00B5 MICRO SIGN µ -> μ (GREEK SMALL LETTER MU)
        s = s.replace('\u03D0', '\u03B2')        # U+03D0 GREEK BETA SYMBOL ϐ -> β
        s = s.replace('\u03D1', '\u03B8')        # U+03D1 GREEK THETA SYMBOL ϑ -> θ
        s = s.replace('\u03D2', '\u03A5')        # U+03D2 GREEK UPSILON WITH HOOK SYMBOL ϒ -> Υ
        s = s.replace('\u03D3', '\u038E')        # U+03D3 GREEK UPSILON WITH ACUTE AND HOOK SYMBOL ϓ -> Ύ
        s = s.replace('\u03D4', '\u03AB')        # U+03D4 GREEK UPSILON WITH DIAERESIS AND HOOK SYMBOL ϔ -> Ϋ
        s = s.replace('\u03D5', '\u03C6')        # U+03D5 GREEK PHI SYMBOL ϕ -> φ
        s = s.replace('\u03D6', '\u03C0')        # U+03D6 GREEK PI SYMBOL ϖ -> π
        s = s.replace('\u03F0', '\u03BA')        # U+03F0 GREEK KAPPA SYMBOL ϰ -> κ
        s = s.replace('\u03F1', '\u03C1')        # U+03F1 GREEK RHO SYMBOL ϱ -> ρ
        s = s.replace('\u03F2', '\u03C2')        # U+03F2 GREEK LUNATE SIGMA SYMBOL ϲ -> ς
        s = s.replace('\u03F4', '\u0398')        # U+03F4 GREEK CAPITAL THETA SYMBOL ϴ -> Θ
        s = s.replace('\u03F5', '\u03B5')        # U+03F5 GREEK LUNATE EPSILON SYMBOL ϵ -> ε
        s = s.replace('\u03F9', '\u03A3')        # U+03F9 GREEK CAPITAL LUNATE SIGMA SYMBOL Ϲ -> Σ
        s = s.replace('\u20A8', 'Rs')            # U+20A8 RUPEE SIGN ₨ -> Rs
        s = s.replace('\u2103', '\u00B0C')       # U+2103 DEGREE CELIUS ℃ -> °C
        s = s.replace('\u2107', '\u0190')        # U+2107 EULER CONSTANT ℇ -> Ɛ
        s = s.replace('\u2109', '\u00B0F')       # U+2109 DEGREE FAHRENHEIT ℉ -> °F
        s = s.replace('\u2116', 'No.')           # U+2116 NUMERO SIGN № -> No.
        s = s.replace('\u2126', '\u03A9')        # U+2126 OHM SIGN Ω -> Ω (GREEK CAPITAL LETTER OMEGA)
        s = s.replace('\u212A', '\u004B')        # U+212A KELVIN SIGN K -> K (LATIN CAPITAL LETTER K)
        s = s.replace('\u212B', '\u00C5')        # U+212B ANGSTROM SIGN Å -> Å (LATIN CAP. LETTER A WITH RING ABOVE)
        s = s.replace('\u2135', '\u05D0')        # U+2135 ALEF SYMBOL ℵ -> א
        s = s.replace('\u2136', '\u05D1')        # U+2136 BET SYMBOL ℶ -> ב
        s = s.replace('\u2137', '\u05D2')        # U+2137 GIMEL SYMBOL ℷ -> ג
        s = s.replace('\u2138', '\u05D3')        # U+2138 DALET SYMBOL ℸ -> ד
        s = s.replace('\u213B', 'FAX')           # U+213B FACSIMILE SIGN ℻ -> FAX
        return s

    def normalize_cjk(self, s: str) -> str:
        # CJK Compatibility (e.g. ㋀ ㌀ ㍰ ㎢ ㏾ ㏿)
        s = re.sub(r'[\u2F00-\u2FDF\u3038-\u303A\u3250\u32C0-\u33FF\uF900-\uFAFF]', self.apply_mapping_dict, s)
        s = re.sub(r'[\U0001F190\U0001F200\U0002F800-\U0002FA1F]', self.apply_mapping_dict, s)
        return s

    def apply_combining_modifiers_compose(self, s: str) -> str:
        """
        Combines 2 Unicode characters (incl. combining modifier) into one Unicode character, e.g. ö (o +  ̈) -> ö
        Must be applied after normalize_ligatures and normalize_signs_and_symbols.
        """
        # U+0300 - U+036F general combining modifier block
        # U+0653 - U+0655 Arabic modifiers: madda above, hamza above, hamza below
        # U+3099 COMBINING KATAKANA-HIRAGANA VOICED SOUND MARK  ゙(e.g. ka -> ga)
        # U+309A COMBINING KATAKANA-HIRAGANA SEMI-VOICED SOUND MARK  ゚(e.g. ha -> pa)
        if re.search(r'[\u0300-\u036F\u0653-\u0655\u3099\u309A]', s):
            s = re.sub(r'.[\u0300-\u036F\u0653-\u0655\u3099\u309A]', self.apply_mapping_dict, s)
        # U+093C Devanagari sign nukta, other South Asian
        if re.search(r'[\u093C\u09BE-\u102E\u1B35\U00011000-\U000115FF]', s):
            s = re.sub(r'.[\u093C\u09BE-\u102E\u1B35\U00011000-\U000115FF]', self.apply_mapping_dict, s)
        # Armenian
        # Hrayr Harutyunyan confirmed that և U+0587 is (1) considered a single letter in the Armenian alphabet,
        # (2) is included on Armenian keyboards and that (3) the decomposition եւ (U+0565 U+0582) should always
        # be re-composed back to և. (This is at variance with NFKC).
        s = s.replace('\u0565\u0582', '\u0587')  # U+0587 ARMENIAN SMALL LIGATURE ECH YIWN եւ -> և
        return s

    def apply_combining_modifiers_decompose(self, s: str) -> str:
        """Decompose character, splitting off combining/modifying character."""
        # Indic, Tibetan, Hebrew, 'forking'
        if re.search(r'[\u0344\u0958-\u095F\u09DC-\u0B5D\u0F43-\u0FB9\u2ADC\uFB1D-\uFB4E]', s):
            s = re.sub(r'[\u0344\u0958-\u095F\u09DC-\u0B5D\u0F43-\u0FB9\u2ADC\uFB1D-\uFB4E]', self.apply_mapping_dict,
                       s)
        # Musical symbols
        if re.search(r'[\U0001D100-\U0001D1FF]', s):
            s = re.sub(r'[\U0001D100-\U0001D1FF]', self.apply_mapping_dict, s)
        return s

    @staticmethod
    def hangul_jamo_triple_to_syllable(leading_jamo: str, vowel_jamo: str, trailing_jamo: str) -> str:
        """
        Convert triple of Hangul jamos to Hangul syllable
        (1) one of U+1100-U+1112: the 19 modern Hangul leading consonant jamos           (19 alternatives)
        (2) one of U+1161-U+1175: the 21 modern Hangul vowel jamos                       (21 alternatives)
        (3) none, or one of U+11A8-U+11C2: the 27 modern Hangul trailing consonant jamos (28 alternatives)
        """
        assert len(leading_jamo) == 1 and ord(leading_jamo) in range(0x1100, 0x1113)
        assert len(vowel_jamo) == 1 and ord(vowel_jamo) in range(0x1161, 0x1176)
        assert (trailing_jamo == '') or (len(trailing_jamo) == 1 and ord(trailing_jamo) in range(0x11A8, 0x11C3))
        leading_index = ord(leading_jamo) - 0x1100
        vowel_index = ord(vowel_jamo) - 0x1161
        trailing_index = 0 if trailing_jamo == '' else ord(trailing_jamo) - 0x11A7   # first trailing jamo maps to 1
        # Notes for below:  (1) 588 = 21 * 28  (2) 0xAC00 is the start of standard Hangul syllable code block
        result = chr((leading_index * 588) + (vowel_index * 28) + trailing_index + 0xAC00)
        return result

    def hangul_jamo_triple_match_to_syllable(self, m: Match[str]) -> str:
        return self.hangul_jamo_triple_to_syllable(m.group(1), m.group(2), m.group(3))

    def normalize_hangul(self, s: str) -> str:
        """Convert all Hangul jamo triples/doubles in string to Hangul syllables."""
        if re.search(r'[\u1161-\u1175]', s):  # string includes a Hangul vowel jamo
            s = re.sub(r'([\u1100-\u1112])([\u1161-\u1175])([\u11A8-\u11C2]|)',  # trailing jamo can be ''
                       self.hangul_jamo_triple_match_to_syllable, s)
        return s

    def repair_combining_modifiers_with_nukta(self, s: str) -> str:
        """This function repairs the order of combining modifiers."""
        # If an Indic vowel-sign (incl. virama) is followed by a nukta, reverse the order of the two diacritics.
        if self.lv & self.char_is_devanagari:
            s = re.sub(r'([\u093E-\u094D])(\u093C)', r'\2\1', s)  # Devanagari
        # Bengali, Gurmukhi, Gujarati, Oriya, Tamil, Telugu, Kannada, Malayalam, Sinhala
        if self.lv & self.char_is_bengali_plus:
            s = re.sub(r'([\u09BE-\u09CD])(\u09BC)', r'\2\1', s)  # Bengali
            s = re.sub(r'([\u0A3E-\u0A4D])(\u0A3C)', r'\2\1', s)  # Gurmukhi
            s = re.sub(r'([\u0ABE-\u0ACD])(\u0ABC)', r'\2\1', s)  # Gujarati
            s = re.sub(r'([\u0B3E-\u0B4D])(\u0B3C)', r'\2\1', s)  # Oriya
            s = re.sub(r'([\u0CBE-\u0CCD])(\u0CBC)', r'\2\1', s)  # Kannada
        if self.lv & self.char_is_khmer_plus:
            s = re.sub(r'([\u1C26-\u1C2C])(\u1C37)', r'\2\1', s)  # Lepcha
        if self.lv & self.char_is_100_plus_block_of_interest:
            s = re.sub(r'([\U000110B0-\U000110B8])(\U000110BA)', r'\2\1', s)  # Kaithi
            s = re.sub(r'([\U000111B3-\U000111C0])(\U000111CA)', r'\2\1', s)  # Sharada
            s = re.sub(r'([\U0001122C-\U00011235])(\U00011236)', r'\2\1', s)  # Khojki
            s = re.sub(r'([\U000112E0-\U000112E8\U000112EA])(\U000112E9)', r'\2\1', s)  # Khudawadi
            s = re.sub(r'([\U0001133E-\U0001134D])(\U0001133C)', r'\2\1', s)  # Grantha
            s = re.sub(r'([\U00011435-\U00011442])(\U00011446)', r'\2\1', s)  # Newa
            s = re.sub(r'([\U000114B0-\U000114C2])(\U000114C3)', r'\2\1', s)  # Tirhuta
            s = re.sub(r'([\U000115AF-\U000115BF])(\U000115C0)', r'\2\1', s)  # Siddham
            s = re.sub(r'([\U000116AD-\U000116B6])(\U000116B7)', r'\2\1', s)  # Takri
            s = re.sub(r'([\U0001182C-\U00011839])(\U0001183A)', r'\2\1', s)  # Dogra
            s = re.sub(r'([\U00011930-\U0001193E])(\U00011943)', r'\2\1', s)  # Dives Akuru
            s = re.sub(r'([\U00011D31-\U00011D3F\U00011D45])(\U00011D42)', r'\2\1', s)  # Masaram Gondi
        return s

    # noinspection SpellCheckingInspection
    @staticmethod
    def normalize_devanagari_diacritics(s: str) -> str:
        """
        NOTE: This function is no longer used in wildebeest.
        It has been subsumed by functions repair_combining_modifiers_with_nukta and the more general
        apply_combining_modifiers.
        This function normalizes strings in the Devanagari script (used in Hindi etc.) by
         - mapping letters to the canonical composed or decomposed form and
         - putting diacritics in the canonical order (nukta before vowel sign).
        """
        if '\u093C' in s:  # Devanagari nukta
            # If a vowel-sign (incl. virama) is followed by a nukta, reverse the order of the two diacritics.
            s = re.sub(r"([\u093E-\u094D])(\u093C)", r"\2\1", s)
            # For the following 3 Devanagari letters, used to transcribe Dravidian letters, use the composed form.
            s = s.replace('\u0928\u093C', '\u0929')  # U+0929 DEVANAGARI LETTER NNNA ऩ -> ऩ
            s = s.replace('\u0930\u093C', '\u0931')  # U+0931 DEVANAGARI LETTER RRA ऱ -> ऱ
            s = s.replace('\u0933\u093C', '\u0934')  # U+0934 DEVANAGARI LETTER LLLA ऴ -> ऴ
        if re.search(r"[\u0958-\u095F]", s):
            # On the other hand, for the following 8 Devanagari letters, use the decomposed form.
            s = s.replace('\u0958', '\u0915\u093C')  # U+0958 DEVANAGARI LETTER QA क़ -> क़
            s = s.replace('\u0959', '\u0916\u093C')  # U+0959 DEVANAGARI LETTER KHHA ख़ -> ख़
            s = s.replace('\u095A', '\u0917\u093C')  # U+095A DEVANAGARI LETTER GHHA ग़ -> ग़
            s = s.replace('\u095B', '\u091C\u093C')  # U+095B DEVANAGARI LETTER ZA ज़ -> ज़
            s = s.replace('\u095C', '\u0921\u093C')  # U+095C DEVANAGARI LETTER DDDHA ड़ -> ड़
            s = s.replace('\u095D', '\u0922\u093C')  # U+095D DEVANAGARI LETTER RHA ढ़ -> ढ़
            s = s.replace('\u095E', '\u092B\u093C')  # U+095E DEVANAGARI LETTER FA फ़ -> फ़
            s = s.replace('\u095F', '\u092F\u093C')  # U+095F DEVANAGARI LETTER YYA य़ -> य़
        return s

    @staticmethod
    def normalize_arabic_punctuation(s: str) -> str:
        s = s.replace('\u0640', '')         # U+0640 Arabic tatweel (always to be deleted)
        s = s.replace('\u060C', ',')        # U+060C Arabic comma
        s = s.replace('\u060D', '/')        # U+060C Arabic date separator
        s = s.replace('\u061B', ';')        # U+061B Arabic semicolon
        s = s.replace('\u061F', '?')        # U+061F Arabic question mark
        s = s.replace('\u066A', '%')        # U+066A Arabic percent sign
        s = s.replace('\u066B', '.')        # U+066B Arabic decimal separator
        s = s.replace('\u066C', ',')        # U+066C Arabic thousands separator
        s = s.replace('\u066D', '*')        # U+066D Arabic five pointed star
        s = s.replace('\u06D4', '.')        # U+06D4 Arabic full stop
        return s

    @staticmethod
    def normalize_greek_punctuation(s: str) -> str:
        s = s.replace('\u0340', '\u0300')   # U+0340 combining grave tone mark -> combining grave accent
        s = s.replace('\u0341', '\u0301')   # U+0341 combining acute tone mark -> combining acute accent
        s = s.replace('\u0343', '\u0313')   # U+0342 combining Greek koronis -> combining comma above
        s = s.replace('\u0374', '\u02B9')   # U+0374 Greek numeral sign -> modifier letter prime
        s = s.replace('\u037E', ';')        # U+037E Greek question mark
        s = s.replace('\u0387', '\u00B7')   # U+0387 Greek ano teleia -> middle dot
        return s

    @staticmethod
    def normalize_cjk_punctuation(s: str) -> str:
        s = s.replace('\u3001', ',')        # U+3001 ideographic comma
        s = s.replace('\u3002', '.')        # U+3002 ideographic full stop
        s = s.replace('\u3008', '<')        # U+3008 left angle bracket
        s = s.replace('\u3009', '>')        # U+3009 right angle bracket
        s = s.replace('\u300A', '\u201C')   # U+300A left double angle bracket -> left double quotation mark
        s = s.replace('\u300B', '\u201D')   # U+300B right double angle bracket -> right double quotation mark
        s = s.replace('\u300C', '\u201C')   # U+300C left corner bracket -> left double quotation mark
        s = s.replace('\u300D', '\u201D')   # U+300D right corner bracket -> right double quotation mark
        s = s.replace('\u300E', '\u201C')   # U+300E left white corner bracket -> left double quotation mark
        s = s.replace('\u300F', '\u201D')   # U+300F right white corner bracket -> right double quotation mark
        s = s.replace('\u3010', '[')        # U+3010 left black lenticular bracket
        s = s.replace('\u3011', ']')        # U+3011 right black lenticular bracket
        s = s.replace('\u3014', '[')        # U+3014 left tortoise shell bracket
        s = s.replace('\u3015', ']')        # U+3015 right tortoise shell bracket
        s = s.replace('\u3016', '[')        # U+3016 left white lenticular bracket
        s = s.replace('\u3017', ']')        # U+3017 right white lenticular bracket
        s = s.replace('\u3018', '[')        # U+3018 left white tortoise shell bracket
        s = s.replace('\u3019', ']')        # U+3019 right white tortoise shell bracket
        s = s.replace('\u301A', '[')        # U+301A left white square bracket
        s = s.replace('\u301B', ']')        # U+301B right white square bracket
        return s

    @staticmethod
    def normalize_misc_f_punctuation(s: str) -> str:
        # Tibetan
        s = s.replace('\u0F0C', '\u0F0B')   # U+0F0C Tibetan no-break morpheme delimiter
        return s

    def normalize_punctuation(self, s: str) -> str:
        # Excludes cases in normalize_dashes.
        # punctuation
        s = s.replace('\u00AB', '\u201C')  # U+201E left double-angle quotation mark -> left double quotation mark
        s = s.replace('\u00BB', '\u201D')  # U+201F right double-angle quotation mark -> right double quotation mark
        s = s.replace('\u201A', '\u2018')  # U+201A single low-9 quotation mark -> left single quotation mark
        s = s.replace('\u201B', '\u2018')  # U+201B single high-reversed-9 quotation mark -> left single quotation mark
        s = s.replace('\u201E', '\u201C')  # U+201E double low-9 quotation mark -> left double quotation mark
        s = s.replace('\u201F', '\u201C')  # U+201F double high-reversed-9 quotation mark -> left double quotation mark
        s = s.replace('\u2039', '\u2018')  # U+2039 left single-angle quotation mark -> left single quotation mark
        s = s.replace('\u203A', '\u2019')  # U+203A right single-angle quotation mark -> right single quotation mark
        s = re.sub(r'[\u2011\u2024-\u2026\u2033-\u203C\u2047-\u2057]', self.apply_mapping_dict, s)  # e.g. …
        s = re.sub(r'[\u2329-\u232A\u2A74-\u2A76]',  self.apply_mapping_dict, s)                    # e.g. 〈〉
        # math symbols
        s = s.replace('\u2212', '-')       # U+2212 minus sign
        s = s.replace('\u2215', '/')       # U+2215 division slash
        s = s.replace('\u2216', '\\')      # U+2216 set minus
        s = s.replace('\u2217', '*')       # U+2217 asterisk operator
        s = s.replace('\u2218', '\u25E6')  # U+2218 ring operator -> white bullet
        s = s.replace('\u2219', '\u2022')  # U+2219 bullet operator -> bullet
        s = s.replace('\u2223', '|')       # U+2223 divides
        s = s.replace('\u2236', ':')       # U+2236 ratio
        s = s.replace('\u2254', ':=')      # U+2254 colon equals
        s = s.replace('\u2255', '=:')      # U+2255 equals colon
        s = s.replace('\u22C5', '\u00B7')  # U+22C5 dot operator -> middle dot
        s = re.sub(r'[\u222C-\u2230\u2A0C]', self.apply_mapping_dict, s)  # e.g. ∭
        # integer plus period or comma ⒛ 🄆
        s = re.sub(r'[\u2488-\u249B\U0001F100-\U0001F10A]', self.apply_mapping_dict, s)
        return s

    @staticmethod
    def normalize_dash_punctuation(s: str) -> str:
        # hyphen, non-breaking hyphen, figure dash, en dash, em dash, horizontal bar
        s = re.sub(r'[\u2010-\u2015]', '-', s)
        s = s.replace('\u2212', '-')  # U+2212 minus sign
        s = s.replace('\u2500', '-')  # U+2500 box drawings light horizontal
        s = s.replace('\u2501', '-')  # U+2501 box drawings heavy horizontal,
        s = s.replace('\u2E3A', '-')  # U+2E3A two-em dash
        s = s.replace('\u2E3B', '-')  # U+2E3B three-em dash
        return s

    @staticmethod
    def normalize_non_zero_spaces(s: str) -> str:
        """
        Map NO-BREAK SPACE, EN QUAD, EM QUAD, EN SPACE, EM SPACE, THREE-PER-EM SPACE, FOUR-PER-EM SPACE,
        SIX-PER-EM SPACE, FIGURE SPACE, PUNCTUATION SPACE, THIN SPACE, HAIR SPACE, NARROW NO-BREAK SPACE,
        MEDIUM MATHEMATICAL SPACE, IDEOGRAPHIC SPACE
        to regular SPACE.
        **Not** included: tab (= horizontal tabulation/character tabulation)
        """
        s = s.replace('\u00A0', ' ')  # U+00A0 NO-BREAK SPACE
        s = re.sub(r'[\u2000-\u200A]', ' ', s)
        s = s.replace('\u202F', ' ')  # U+00A0 NARROW NO-BREAK SPACE
        s = s.replace('\u205F', ' ')  # U+00A0 MEDIUM MATHEMATICAL SPACE
        s = s.replace('\u3000', ' ')  # U+3000 IDEOGRAPHIC SPACE
        return s

    # noinspection SpellCheckingInspection
    def normalize_half_and_full_width_characters(self, s: str) -> str:
        """Replace fullwidth and halfwidth characters such as Ａ with regular Latin letters such as A."""
        if re.search(r'[\uFF01-\uFFEE]', s):
            s = re.sub(r'[\uFF01-\uFFEE]', self.apply_mapping_dict, s)
        return s

    def normalize_font_characters(self, s: str) -> str:
        # Replace font-variation characters such as ℂℹ𝒜 to CiA.
        s = re.sub(r'[\u2102-\u2149\uFB20-\uFB29\U0001D400-\U0001D7FF\U0001EE00-\U0001EEBB\U0001FBF0-\U0001FBF9]',
                   self.apply_mapping_dict, s)
        return s

    def normalize_small_characters(self, s: str) -> str:
        """Replace small version of characters with normal version, such as small ampersand ﹠ to regular &"""
        s = re.sub(r'[\uFE50-\uFE6F]', self.apply_mapping_dict, s)
        return s

    def normalize_vertical_characters(self, s: str) -> str:
        """
        Replace vertical version of punctuation characters with normal horizontal version,
        such as vertical em-dash ︱ to horizontal em-dash —
        """
        s = re.sub(r'[\u309F\u30FF\uFE10-\uFE19\uFE30-\uFE48]', self.apply_mapping_dict, s)
        return s

    def normalize_enclosure_characters(self, s: str) -> str:
        """
        Decompose enclosed (circled, squared, parenthesized) characters, e.g. 🄐 to (A).
        """
        s = re.sub(r'[\u2460-\u2488\u249C-\u2500\u3036\u3200-\u3250\u3251-\u32C0\u32D0-\u32FF]',
                   self.apply_mapping_dict, s)
        s = re.sub(r'[\U0001F110-\U0001F16A\U0001F201-\U0001F260]', self.apply_mapping_dict, s)
        return s

    def normalize_core_compat_characters(self, s: str) -> str:
        # Replace Roman numeral characters to ASCII.
        s = re.sub(r'[\u2160-\u217F]', self.apply_mapping_dict, s)
        # Replace Hangul Compatibility characters with Unicode standard Hangul versions, e.g. ㄱ to ᄀ.
        s = re.sub(r'[\u3131-\u318E]', self.apply_mapping_dict, s)
        # Thai, Lao
        s = re.sub(r'[\u0E33\u0EB3\u0EDC\u0EDD]', self.apply_mapping_dict, s)
        return s

    # noinspection SpellCheckingInspection
    def map_digits_to_ascii(self, s: str) -> str:
        """
        This function replaces non-ASCII decimal digits by ASCII digits, e.g.
            ۱۲۳ (Arabic) -> 123
            ൯൦ (Mayalayam) -> 90
        This function does not map any numbers from non-decimal systems such as
            Roman numerals (MDCCLXXVI = 1776),
            Chinese/Japanese (二百 = 200) or
            Ethiopic languages (፱፻ = 900),
        as the characters of those numbers do not match one-to-one onto ASCII digits.
        """
        if self.lv & self.char_is_arabic:
            s = re.sub(r'[\u0660-\u0669]', self.apply_mapping_dict, s)  # ARABIC-INDIC digits
            s = re.sub(r'[\u06F0-\u06F9]', self.apply_mapping_dict, s)  # EXTENDED ARABIC-INDIC digits
        if self.lv & self.char_is_thaana_plus:
            s = re.sub(r'[\u07C0-\u07C9]', self.apply_mapping_dict, s)  # NKO digits
        if self.lv & self.char_is_devanagari:
            s = re.sub(r'[\u0966-\u096F]', self.apply_mapping_dict, s)  # DEVANAGARI digits
        if self.lv & self.char_is_bengali_plus:
            s = re.sub(r'[\u09E6-\u09EF]', self.apply_mapping_dict, s)  # BENGALI digits
            s = re.sub(r'[\u0A66-\u0A6F]', self.apply_mapping_dict, s)  # GURMUKHI digits
            s = re.sub(r'[\u0AE6-\u0AEF]', self.apply_mapping_dict, s)  # GUJARATI digits
            s = re.sub(r'[\u0B66-\u0B6F]', self.apply_mapping_dict, s)  # ORIYA digits
            s = re.sub(r'[\u0BE6-\u0BEF]', self.apply_mapping_dict, s)  # TAMIL digits
            s = re.sub(r'[\u0C66-\u0C6F]', self.apply_mapping_dict, s)  # TELUGU digits
            s = re.sub(r'[\u0CE6-\u0CEF]', self.apply_mapping_dict, s)  # KANNADA digits
            s = re.sub(r'[\u0D66-\u0D6F]', self.apply_mapping_dict, s)  # MALAYALAM digits
            s = re.sub(r'[\u0DE6-\u0DEF]', self.apply_mapping_dict, s)  # SINHALA LITH digits
        if self.lv & self.char_is_thai_plus:
            s = re.sub(r'[\u0E50-\u0E59]', self.apply_mapping_dict, s)  # THAI digits
            s = re.sub(r'[\u0ED0-\u0ED9]', self.apply_mapping_dict, s)  # LAO digits
            s = re.sub(r'[\u0F20-\u0F29]', self.apply_mapping_dict, s)  # TIBETAN digits
            s = re.sub(r'[\u1040-\u1049]', self.apply_mapping_dict, s)  # MYANMAR digits
            s = re.sub(r'[\u1090-\u1099]', self.apply_mapping_dict, s)  # MYANMAR SHAN digits
        if self.lv & self.char_is_khmer_plus:
            s = re.sub(r'[\u17E0-\u17E9]', self.apply_mapping_dict, s)  # KHMER digits
            s = re.sub(r'[\u1810-\u1819]', self.apply_mapping_dict, s)  # MONGOLIAN digits
            s = re.sub(r'[\u1946-\u194F]', self.apply_mapping_dict, s)  # LIMBU digits
            s = re.sub(r'[\u19D0-\u19DA]', self.apply_mapping_dict, s)  # NEW TAI LUE digits
            s = re.sub(r'[\u1A80-\u1A89]', self.apply_mapping_dict, s)  # TAI THAM HORA digits
            s = re.sub(r'[\u1A90-\u1A99]', self.apply_mapping_dict, s)  # TAI THAM THAM digits
            s = re.sub(r'[\u1B50-\u1B59]', self.apply_mapping_dict, s)  # BALINESE digits
            s = re.sub(r'[\u1BB0-\u1BB9]', self.apply_mapping_dict, s)  # SUNDANESE digits
            s = re.sub(r'[\u1C40-\u1C49]', self.apply_mapping_dict, s)  # LEPCHA digits
            s = re.sub(r'[\u1C50-\u1C59]', self.apply_mapping_dict, s)  # OL CHIKI digits
        if self.lv & self.char_is_lisu_plus:
            s = re.sub(r'[\uA620-\uA629]', self.apply_mapping_dict, s)  # VAI digits
            s = re.sub(r'[\uA8D0-\uA8D9]', self.apply_mapping_dict, s)  # SAURASHTRA digits
            s = re.sub(r'[\uA900-\uA909]', self.apply_mapping_dict, s)  # KAYAH LI digits
            s = re.sub(r'[\uA9D0-\uA9D9]', self.apply_mapping_dict, s)  # JAVANESE digits
            s = re.sub(r'[\uA9F0-\uA9F9]', self.apply_mapping_dict, s)  # MYANMAR TAI LAING digits
            s = re.sub(r'[\uAA50-\uAA59]', self.apply_mapping_dict, s)  # CHAM digits
            s = re.sub(r'[\uABF0-\uABF9]', self.apply_mapping_dict, s)  # MEETEI MAYEK digits
        if self.lv & self.char_is_100_plus_block_of_interest:
            s = re.sub(r'[\U000104A0-\U000104A9]', self.apply_mapping_dict, s)  # OSMANYA digits
            s = re.sub(r'[\U00010D30-\U00010D39]', self.apply_mapping_dict, s)  # HANIFI ROHINGYA digits
            s = re.sub(r'[\U00011066-\U0001106F]', self.apply_mapping_dict, s)  # BRAHMI digits
            s = re.sub(r'[\U000110F0-\U000110F9]', self.apply_mapping_dict, s)  # SORA SOMPENG digits
            s = re.sub(r'[\U00011136-\U0001113F]', self.apply_mapping_dict, s)  # CHAKMA digits
            s = re.sub(r'[\U000111D0-\U000111D9]', self.apply_mapping_dict, s)  # SHARADA digits
            s = re.sub(r'[\U000112F0-\U000112F9]', self.apply_mapping_dict, s)  # KHUDAWADI digits
            s = re.sub(r'[\U00011450-\U00011459]', self.apply_mapping_dict, s)  # NEWA digits
            s = re.sub(r'[\U000114D0-\U000114D9]', self.apply_mapping_dict, s)  # TIRHUTA digits
            s = re.sub(r'[\U00011650-\U00011659]', self.apply_mapping_dict, s)  # MODI digits
            s = re.sub(r'[\U000116C0-\U000116C9]', self.apply_mapping_dict, s)  # TAKRI digits
            s = re.sub(r'[\U00011730-\U00011739]', self.apply_mapping_dict, s)  # AHOM digits
            s = re.sub(r'[\U000118E0-\U000118E9]', self.apply_mapping_dict, s)  # WARANG CITI digits
            s = re.sub(r'[\U00011C50-\U00011C59]', self.apply_mapping_dict, s)  # BHAIKSUKI digits
            s = re.sub(r'[\U00011D50-\U00011D59]', self.apply_mapping_dict, s)  # MASARAM GONDI digits
            s = re.sub(r'[\U00011DA0-\U00011DA9]', self.apply_mapping_dict, s)  # GUNJALA GONDI digits
            s = re.sub(r'[\U00016A60-\U00016A69]', self.apply_mapping_dict, s)  # MRO digits
            s = re.sub(r'[\U00016B50-\U00016B59]', self.apply_mapping_dict, s)  # PAHAWH HMONG digits
            s = re.sub(r'[\U0001E950-\U0001E959]', self.apply_mapping_dict, s)  # ADLAM digits
        return s

    # noinspection SpellCheckingInspection
    @staticmethod
    def repair_xml(s: str) -> str:
        # Repair multi-level xml-escapes such as &amp;amp;quot; to &quot;
        s = re.sub(r'(?<=&)(?:amp;)+(?=(?:amp|apos|gt|lt|nbsp|quot|#\d{1,6}|#x[0-9A-F]{1,5});)',
                   '', s, flags=re.IGNORECASE)
        return s

    # noinspection SpellCheckingInspection
    @staticmethod
    def repair_url_escapes(s: str) -> str:
        # Repair double url-escapes such as https://en.wikipedia.org/wiki/Jo%25C3%25ABlle_Aubron
        s = re.sub(r"(%)25([CD][0-9A-F]%)25([89AB][0-9A-F])", r"\1\2\3", s)
        s = re.sub(r'(%)25(E[0-9A-F]%)25([89AB][0-9A-F]%)25([89AB][0-9A-F])', r"\1\2\3\4", s)
        return s

    def repair_arabic_tokenization(self, s: str) -> str:
        """Detach certain punctuation -_+*|% and ASCII digits from Arabic characters."""
        # s = re.sub(r"([-_+*|%0-9]+)([\u0600-\u06FF])", r"\1 \2", s)
        # s = re.sub(r"([\u0600-\u06FF])([-_+*|%0-9]+)", r"\1 \2", s)
        s = self.repair_tok_punct_arabic_match.sub(r"\1 \2", s)
        s = self.repair_tok_arabic_punct_match.sub(r"\1 \2", s)
        return s

    def char_script(self, char: str) -> Optional[str]:
        char_type_vector = self.char_type_vector_dict.get(char, 0)
        if char_type_vector & self.char_is_latin:
            return 'Latin'
        elif char_type_vector & self.char_is_greek:
            return 'Greek'
        elif char_type_vector & self.char_is_cyrillic:
            return 'Cyrillic'
        else:
            return None

    def tokenize_mixed_script_tokens(self, orig_token: str) -> str:
        token = ''
        script = None
        script_start = 0
        position = -1
        orig_token_len = len(orig_token)
        last_char_is_punctuation = False
        for char in orig_token:
            position += 1
            if char in ['.', '/', '_', '-']:
                last_char_is_punctuation = True
            else:
                new_script = self.char_script(char)
                if new_script != script:
                    if (position - script_start >= 3
                            and orig_token_len - position >= 3
                            and not last_char_is_punctuation
                            and script in self.look_alike_scripts
                            and new_script in self.look_alike_scripts)\
                            and new_script == self.char_script(orig_token[position+1]):
                        token += ' '
                    script = new_script
                    script_start = position
                last_char_is_punctuation = False
            token += char
        return token

    @staticmethod
    def is_mixed_script_url(s: str) -> bool:
        return bool(re.match(r'(?:https?://)?[a-zA-Z][-_./0-9a-zA-Z]*\.(?:bg|by|me|mk|kg|kz|rs|ru|tj|tm|ua|uz|'
                             r'com|info)/[-_./#0-9\u0400-\u04FF]+$', s, flags=re.IGNORECASE)
                    or re.match(r'(?:https?://)?[\u0400-\u04FF][-_./0-9\u0400-\u04FF]*'
                                r'\.(bg|by|me|mk|kg|kz|rs|ru|tj|tm|ua|uz|com|info)$', s))

    def map_look_alikes_to_script(self, s: str, source_script: str, target_script: str) -> str:
        result = ''
        for char in s:
            result += self.look_alike_dict.get(f'{source_script} {target_script} {char}', char)
        return result

    def correct_look_alikes(self, s: str) -> str:
        # orig_s = s
        result = ''
        while True:
            m = re.match(r'(\s*)(\S+)(.*)$', s)
            if m:
                result += m.group(1)
                orig_token = m.group(2)
                stat_dict = {}
                for char in orig_token:
                    script = self.char_script(char)
                    if script:
                        stat_dict[script] = stat_dict.get(script, 0) + 1
                        for target_script in self.look_alike_scripts:
                            if script != target_script:
                                target_char = self.look_alike_dict.get(f'{script} {target_script} {char}', None)
                                if target_char:
                                    key = f'{script} {target_script}'
                                    stat_dict[key] = stat_dict.get(key, 0) + 1
                target_script = None
                mixed_token = False
                n_scripts = 0
                for script in ['Latin', 'Greek', "Cyrillic"]:
                    if stat_dict.get(script, 0) >= 1:
                        n_scripts += 1
                if n_scripts >= 2:
                    mixed_token = True
                    if (stat_dict.get('Cyrillic Latin', 0) == stat_dict.get('Cyrillic', 0)
                            and stat_dict.get('Latin Cyrillic', 0) < stat_dict.get('Latin', 0)):
                        target_script = 'Latin'
                    elif (stat_dict.get('Latin Cyrillic', 0) == stat_dict.get('Latin', 0)
                          and stat_dict.get('Cyrillic Latin', 0) < stat_dict.get('Cyrillic', 0)):
                        target_script = 'Cyrillic'
                    elif (stat_dict.get('Cyrillic', 0) == 1 and stat_dict.get('Cyrillic Latin', 0) == 1
                          and stat_dict.get('Latin', 0) >= 3):
                        target_script = 'Latin'
                    elif (stat_dict.get('Latin', 0) == 1 and stat_dict.get('Latin Cyrillic', 0) == 1
                          and stat_dict.get('Cyrillic', 0) >= 3):
                        target_script = 'Cyrillic'
                    else:
                        lat_token = self.map_look_alikes_to_script(orig_token, 'Cyrillic', 'Latin')
                        if (lat_token in ['SpA', 'USA']
                            or (len(orig_token) >= 2
                                and re.match(r'(?:X|XX|XXX|XL|L|LX|LXX|LXXX|XC|)(?:I|II|III|IV|V|VI|VII|VIII|IX|)$',
                                             lat_token))):
                            target_script = 'Latin'
                        cyr_token = self.map_look_alikes_to_script(orig_token, 'Latin', 'Cyrillic')
                        if cyr_token in ['әр', 'Әр', 'әрі', 'сі', 'Сі', 'іс', 'Іс', 'ісі', 'ірі']:
                            target_script = 'Cyrillic'
                if target_script:
                    token = ''
                    for char in orig_token:
                        script = self.char_script(char)
                        target_char = self.look_alike_dict.get(f'{script} {target_script} {char}', char)
                        token += target_char
                    key = 'n-to-' + target_script
                    self.look_alike_dict[key] = self.look_alike_dict.get(key, 0) + 1
                else:
                    retok_orig_token = self.tokenize_mixed_script_tokens(orig_token)
                    if retok_orig_token != orig_token:
                        token = retok_orig_token
                        key = 'n-split'
                        if self.look_alike_split_dict.get(orig_token, None) is None:
                            log.debug(f'   correct-look-alike split {orig_token} -> {token}')
                            self.look_alike_split_dict[orig_token] = token
                        self.look_alike_dict[key] = self.look_alike_dict.get(key, 0) + 1
                    else:
                        token = orig_token
                        if mixed_token:
                            key = 'n-unchanged'
                            self.look_alike_dict[key] = self.look_alike_dict.get(key, 0) + 1
                # if token != orig_token:
                #     log.info(f'   correct-look-alike {orig_token} -> {token} (to {target_script})')
                if mixed_token and token == orig_token:
                    if self.is_mixed_script_url(orig_token):
                        if self.look_alike_url_dict.get(orig_token, None) is None:
                            log.debug(f'mixed-script-URL: {orig_token}')
                            self.look_alike_url_dict[orig_token] = True
                    else:
                        self.look_alike_unchanged_dict[token] = self.look_alike_unchanged_dict.get(token, 0) + 1
                result += token
                s = m.group(3)
            else:
                result += s
                # log.info(f'  look-alike {orig_s} -> {result}')
                return result

    @staticmethod
    def increment_dict_count(ht: dict, key: str, increment=1) -> int:
        """For example ht['NUMBER-OF-LINES']"""
        ht[key] = ht.get(key, 0) + increment
        return ht[key]

    def ncs_group(self, s: str, ht: dict, group_name: str, group_function: Callable[[str], str],
                  loc_id: str) -> str:
        """
        ncs_group: normalize and clean string group.
        For a given normalization/cleaning group, call appropriate function and update stats.
        """
        if f'SKIP-{group_name}' not in ht:
            self.increment_dict_count(ht, f'CALL-{group_name}')  # keep track of how often norm-group is called
            orig_s = s
            s = group_function(s)
            if s != orig_s:
                count_key = f'COUNT-{group_name}'
                count = self.increment_dict_count(ht, count_key)
                if loc_id and (count <= 20):
                    loc_key = f'{count_key}-{count}'
                    ht[loc_key] = loc_id
        return s

    # noinspection SpellCheckingInspection,SpellCheckingInspection
    def norm_clean_string(self, s: str, ht: dict, lang_code: str = '', loc_id: str = '') -> str:
        """Go through a list of applicable normalization/cleaning steps and keep track of the number of changes."""
        number_of_lines = ht.get('NUMBER-OF-LINES', 0) + 1
        ht['NUMBER-OF-LINES'] = number_of_lines
        orig_s = s
        self.lv = 0  # line_char_type_vector
        # Each bit in this vector is to capture character type info, e.g. char_is_arabic
        for char in s:
            char_type_vector = self.char_type_vector_dict.get(char, 0)
            if char_type_vector:
                # A set bit in the lv means that the bit has been set by at least one char.
                # So we will easily know whether e.g. a line contains an Arabic character.
                # If not, some Arabic-specific normalization steps can be skipped to improve run-time.
                self.lv = self.lv | char_type_vector
        if self.lv & self.char_is_encoding_repair_anchor:
            s = self.ncs_group(s, ht, 'repair-encodings-errors', self.repair_encoding_errors, loc_id)
        # Cleaning step 'del-surrogate' is an alternative/backup to windows-1252.
        # It should not be skipped because surrogates are not printable.
        if self.lv & self.char_is_surrogate:
            s = self.ncs_group(s, ht, 'del-surrogate', self.delete_surrogates, loc_id)
        if self.lv & self.char_is_deletable_control_character:
            s = self.ncs_group(s, ht, 'del-ctrl-char', self.delete_control_characters, loc_id)
        if self.lv & self.char_is_deletable_arabic_diacritic:
            s = self.ncs_group(s, ht, 'del-arabic-diacr', self.delete_arabic_diacritics, loc_id)
        if self.lv & self.char_is_deletable_hebrew_diacritic:
            s = self.ncs_group(s, ht, 'del-hebrew-diacr', self.delete_hebrew_diacritics, loc_id)
        if self.lv & self.char_is_core_compatibility:
            s = self.ncs_group(s, ht, 'core-compat', self.normalize_core_compat_characters, loc_id)
        if self.lv & self.char_is_arabic_presentation_form:
            s = self.ncs_group(s, ht, 'pres-form', self.normalize_arabic_pres_form_characters, loc_id)
        if self.lv & self.char_is_decomposable_ligature:
            s = self.ncs_group(s, ht, 'ligatures', self.normalize_ligatures, loc_id)
        if self.lv & self.char_is_decomposable_sign_symbol:
            s = self.ncs_group(s, ht, 'signs-and-symbols', self.normalize_signs_and_symbols, loc_id)
        if self.lv & self.char_is_decomposable_cjk:
            s = self.ncs_group(s, ht, 'cjk', self.normalize_cjk, loc_id)
        if self.lv & self.char_is_fullwidth_or_halfwidth:
            s = self.ncs_group(s, ht, 'width', self.normalize_half_and_full_width_characters, loc_id)
        if self.lv & self.char_is_font_small_vertical:
            s = self.ncs_group(s, ht, 'font', self.normalize_font_characters, loc_id)
            s = self.ncs_group(s, ht, 'small', self.normalize_small_characters, loc_id)
            s = self.ncs_group(s, ht, 'vertical', self.normalize_vertical_characters, loc_id)
        if self.lv & self.char_is_decomposable_enclosure:
            s = self.ncs_group(s, ht, 'enclosure', self.normalize_enclosure_characters, loc_id)
        if self.lv & self.char_is_mappable_hangul:
            s = self.ncs_group(s, ht, 'hangul', self.normalize_hangul, loc_id)
        if self.lv & self.char_is_nukta:
            s = self.ncs_group(s, ht, 'repair-combining', self.repair_combining_modifiers_with_nukta, loc_id)
        if (self.lv & self.char_is_composable_anchor_with_combining) \
                and (self.lv & self.char_is_composable_combining_diacritic):
            s = self.ncs_group(s, ht, 'combining-compose', self.apply_combining_modifiers_compose, loc_id)
        if self.lv & self.char_is_decomposable_with_combining:
            s = self.ncs_group(s, ht, 'combining-decompose', self.apply_combining_modifiers_decompose, loc_id)
        if self.lv & self.char_is_core_compatibility:
            s = self.ncs_group(s, ht, 'punct', self.normalize_punctuation, loc_id)
        if self.lv & self.char_is_decomposable_arabic_punctuation:
            s = self.ncs_group(s, ht, 'punct-arabic', self.normalize_arabic_punctuation, loc_id)
        if self.lv & self.char_is_decomposable_cjk_punctuation:
            s = self.ncs_group(s, ht, 'punct-cjk', self.normalize_cjk_punctuation, loc_id)
        if self.lv & self.char_is_decomposable_greek_punctuation:
            s = self.ncs_group(s, ht, 'punct-greek', self.normalize_greek_punctuation, loc_id)
        if self.lv & self.char_is_decomposable_misc_f_punctuation:
            s = self.ncs_group(s, ht, 'punct-misc-f', self.normalize_misc_f_punctuation, loc_id)
        if self.lv & self.char_is_decomposable_dash:
            s = self.ncs_group(s, ht, 'punct-dash', self.normalize_dash_punctuation, loc_id)
        if self.lv & self.char_is_decomposable_non_zero_space:
            s = self.ncs_group(s, ht, 'space', self.normalize_non_zero_spaces, loc_id)
        if self.lv & self.char_is_mappable_decimal_digit:
            s = self.ncs_group(s, ht, 'digit', self.map_digits_to_ascii, loc_id)
        if self.lv & self.char_is_arabic:
            if lang_code == 'fas':
                if (self.lv & self.char_is_mappable_in_farsi) or (self.lv & self.char_is_arabic_presentation_form):
                    s = self.ncs_group(s, ht, 'farsi-char', self.normalize_farsi_characters, loc_id)
            elif lang_code == 'pas':
                if (self.lv & self.char_is_mappable_in_pashto) or (self.lv & self.char_is_arabic_presentation_form):
                    s = self.ncs_group(s, ht, 'pashto-char', self.normalize_pashto_characters, loc_id)
            else:
                if (self.lv & self.char_is_mappable_in_arabic) or (self.lv & self.char_is_arabic_presentation_form):
                    s = self.ncs_group(s, ht, 'arabic-char', self.normalize_arabic_characters, loc_id)
        if self.lv & self.char_is_georgian:
            s = self.ncs_group(s, ht, 'georgian-char', self.normalize_georgian_characters, loc_id)
        n_scripts = 0
        for script_lv in [self.char_is_latin, self.char_is_greek, self.char_is_cyrillic]:
            if self.lv & script_lv:
                n_scripts += 1
        if n_scripts >= 2:
            s = self.ncs_group(s, ht, 'look-alike', self.correct_look_alikes, loc_id)
        if (self.lv & self.char_is_ampersand) and (self.lv & self.char_is_semicolon):
            s = self.ncs_group(s, ht, 'repair-xml', self.repair_xml, loc_id)
        if self.lv & self.char_is_percent_sign:
            s = self.ncs_group(s, ht, 'repair-url-espaces', self.repair_url_escapes, loc_id)
        if ((self.lv & self.char_is_arabic)
                and ((self.lv & self.char_is_detachable_from_token)
                     or (self.lv & self.char_is_mappable_decimal_digit))):
            s = self.ncs_group(s, ht, 'repair-token', self.repair_arabic_tokenization, loc_id)
        if s != orig_s:
            self.increment_dict_count(ht, 'COUNT-ALL')
        return s

    def norm_clean_lines(self, ht: dict, input_file: TextIO, output_file: TextIO, lang_code=''):
        """Apply normalization/cleaning to a file (or STDIN/STDOUT)."""
        line_number = 0
        for line in input_file:
            line_number += 1
            output_file.write(self.norm_clean_string(line.rstrip(), ht, lang_code=lang_code, loc_id=str(line_number))
                              + "\n")


# noinspection SpellCheckingInspection
def main(argv):
    """Wrapper around normalization/cleaning that takes care of argument parsing and prints change stats to STDERR."""
    # parse arguments
    all_skip_elems = ['repair-encodings-errors', 'del-surrogate', 'del-ctrl-char', 'del-arabic-diacr',
                      'del-hebrew-diacr', 'core-compat', 'pres-form', 'ligatures', 'signs-and-symbols', 'cjk',
                      'width', 'font', 'small', 'vertical', 'enclosure', 'hangul',
                      'repair-combining', 'combining-compose', 'combining-decompose',
                      'punct', 'punct-dash', 'punct-arabic', 'punct-cjk', 'punct-greek', 'punct-misc-f',
                      'space', 'digit', 'arabic-char', 'farsi-char', 'pashto-char', 'georgian-char',
                      'look-alike', 'repair-xml', 'repair-url-escapes', 'repair-token']
    skip_help = f"comma-separated list of normalization/cleaning steps to be skipped: {','.join(all_skip_elems)} \
    (default: nothing skipped)"
    parser = argparse.ArgumentParser(description='Normalizes and cleans a given text')
    parser.add_argument('-i', '--input', type=argparse.FileType('r', encoding='utf-8', errors='surrogateescape'),
                        default=sys.stdin, metavar='INPUT-FILENAME', help='(default: STDIN)')
    parser.add_argument('-o', '--output', type=argparse.FileType('w', encoding='utf-8', errors='ignore'),
                        default=sys.stdout, metavar='OUTPUT-FILENAME', help='(default: STDOUT)')
    parser.add_argument('--lc', type=str, default='', metavar='LANGUAGE-CODE', help="ISO 639-3, e.g. 'fas' for Persian")
    parser.add_argument('--skip', type=str, default='', metavar='NORM-STEPS', help=skip_help)
    parser.add_argument('-v', '--verbose', action='count', default=0, help='write change log etc. to STDERR')
    parser.add_argument('--version', action='version',
                        version=f'%(prog)s {__version__} last modified: {last_mod_date}')
    args = parser.parse_args(argv)
    lang_code = args.lc
    skip_list_csv = args.skip
    wb = Wildebeest()

    # Open any input or output files. Make sure utf-8 encoding is properly set (in older Python3 versions).
    if args.input is sys.stdin and not re.search('utf-8', sys.stdin.encoding, re.IGNORECASE):
        log.error(f"Bad STDIN encoding '{sys.stdin.encoding}' as opposed to 'utf-8'. \
                    Suggestion: 'export PYTHONIOENCODING=UTF-8' or use '--input FILENAME' option")
    if args.output is sys.stdout and not re.search('utf-8', sys.stdout.encoding, re.IGNORECASE):
        log.error(f"Error: Bad STDIN/STDOUT encoding '{sys.stdout.encoding}' as opposed to 'utf-8'. \
                    Suggestion: 'export PYTHONIOENCODING=UTF-8' or use use '--output FILENAME' option")

    ht = {}
    if skip_list_csv != '':
        for skip_elem in re.split(r',\s*', skip_list_csv):
            ht[f'SKIP-{skip_elem}'] = 1
    # Add a little language code robustness for Persian language code, more comprehensive solution to come
    if lang_code == 'fa':
        lang_code = 'fas'
    start_time = datetime.datetime.now()
    if args.verbose:
        log.info(f'Start: {start_time}')
        log.info('Script wildebeest_normalize.py')
        if args.input is not sys.stdin:
            log.info(f'Input: {args.input.name}')
        if args.output is not sys.stdout:
            log.info(f'Output: {args.output.name}')
        if args.skip:
            log.info(f'Skip: {args.skip}')
        if lang_code:
            log.info(f'ISO 639-3 language code: {lang_code}')
    wb.load_look_alike_file()
    # The following line is the core call. ht is a dictionary (empty if no steps are to be skipped).
    wb.norm_clean_lines(ht, input_file=args.input, output_file=args.output, lang_code=lang_code)
    # Log some change stats.
    if args.verbose:
        n_unchanged = 0
        for unchanged_token in sorted(wb.look_alike_unchanged_dict.keys(),
                                      key=lambda s: wb.look_alike_unchanged_dict[s],
                                      reverse=True):
            n_unchanged += 1
            if n_unchanged <= 100:
                count = wb.look_alike_unchanged_dict[unchanged_token]
                log.debug(f'   unchanged mixed token: {unchanged_token} ({count})')
        change_count = ht.get('COUNT-ALL', 0)
        number_of_lines = ht.get('NUMBER-OF-LINES', 0)
        lines = 'line' if change_count == 1 else 'lines'
        log_info = f"{str(change_count)} out of {str(number_of_lines)} {lines} changed"
        for skip_elem in all_skip_elems:
            n_changed_lines = ht.get(f'COUNT-{skip_elem}', 0)
            n_lines_with_call = ht.get(f'CALL-{skip_elem}', 0)
            if n_changed_lines:
                lines = 'line' if n_changed_lines == 1 else 'lines'
                log_info += f'; {skip_elem} in {str(n_changed_lines)}/{str(n_lines_with_call)} {lines}'
                if skip_elem == 'look-alike':
                    n_change_list = []
                    for key in ['n-to-Latin', 'n-to-Cyrillic', 'n-to-Greek', 'n-split', 'n-unchanged']:
                        n_change_list.append(str(wb.look_alike_dict.get(key, 0)))
                    log_info += f" ({'/'.join(n_change_list)} L/C/G/S/-)"
        log.info(log_info)
        end_time = datetime.datetime.now()
        log.info(f'End: {end_time}')
        elapsed_time = end_time - start_time
        log.info(f'Time: {elapsed_time}')


if __name__ == "__main__":
    main(sys.argv[1:])
