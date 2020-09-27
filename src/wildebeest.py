# noinspection SpellCheckingInspection,SpellCheckingInspection
"""
Written by Ulf Hermjakob, USC/ISI
Ported Pashto and Farsi-specific normalization from Perl to Python in August 2020.
Ported general normalization from Perl to Python in September 2020.
This script normalizes and cleans text (details below).
Examples:
  wildebeest.py -h  # for full usage info
  wildebeest.py --version
  wildebeest.py --lc fas -i 3S-dev-ssplit.src.tok -o 3S-dev-ssplit.src.clean2.tok
  wildebeest.py --lc fas --verbose --skip digit,punct < 3S-dev-ssplit.src.tok > 3S-dev-ssplit.src.clean1.tok
List of available normalization/cleaning-types (default: all are applied):
 * repair-encodings-errors (repairs missing, wrong, or double conversion from Windows-1252 or Latin-1 to UTF8)
 * del-surrogate (deletes surrogate characters (representing non-UTF8 characters in input),
        alternative/backup to windows-1252)
 * del-ctrl-char (deletes control characters (expect tab and linefeed), zero-width characters, byte order mark,
        directional marks, join marks, variation selectors, Arabic tatweel)
 * farsi-char (e.g. maps Arabic yeh, kaf to Farsi versions)
 * pres-form (e.g. maps from presentation form (isolated, initial, medial, final) to standard form)
 * ligatures-symbols (e.g. maps ligatures, symbols (e.g. kappa symbol), signs (e.g. micro sign), CJK square composites)
 * ring-char (e.g. maps ring-characters that are common in Pashto to non-ring characters)
 * fullwidth (e.g. maps fullwidth characters to ASCII, e.g. Ａ to A)
 * combining (e.g. applies combining-modifiers to preceding character, e.g. ö (o +  ̈) -> ö)
 * del-diacr (e.g. deletes diacritics such as Arabic fatha, damma, kasra)
 * indic-diacr (e.g. canonical form of composed/decomposed Indic characters; order nukta/vowel-sign)
 * digit (e.g. maps Arabic-Indic digits and extended Arabic-Indic digits to ASCII digits)
 * punct (e.g. maps Arabic exclamation mark etc. to ASCII equivalent)
 * space (e.g. normalizes non-zero spaces to normal space)
 * repair-xml (e.g. repairs multi-escaped tokens such as &amp;quot; or &amp;amp;#x200C;)
 * repair-token (e.g. splits +/-/*/digits off Arabic words; maps not-sign inside Arabic to token-separating hyphen)
When using STDIN and/or STDOUT, if might be necessary, particularly for older versions of Python, to do
'export PYTHONIOENCODING=UTF-8' before calling this Python script to ensure UTF-8 encoding.
"""
# -*- encoding: utf-8 -*-
import argparse
import logging as log
import os
import re
import sys
from typing import Callable, Match, Optional, TextIO

log.basicConfig(level=log.INFO)

__version__ = '0.4.5'
last_mod_date = 'September 26, 2020'


class Wildebeest:
    def __init__(self):
        self.encoding_map_dict = {}
        # This dictionary captures the irregular mappings from Windows1252 to UTF8.
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
        self.init_encoding_map_dict()

    def windows1252_to_utf8_char(self, index: int) -> str:
        """ Typical input: 0x80       Typical output: '€' """
        s = chr(index)
        if s in self.spec_windows1252_to_utf8_dict:
            return self.spec_windows1252_to_utf8_dict[s]
        else:
            return s

    def set_encoding_map_dict(self, key: str, value: str, index: int, byte_string: Optional[bytes], loc: str,
                              verbose: bool = False) -> None:
        self.encoding_map_dict[key] = value
        if verbose:
            log.info(f'map-{loc} {index} {key} -> {value}   byte_string:{byte_string}')

    # noinspection SpellCheckingInspection
    def init_encoding_map_dict(self, undef_default: str = '') -> None:
        """Initialize encoding_map_dict that maps from various misencodings to proper UTF8."""
        # Misencodings that resulted from missing conversion from Windows1252/Latin1 to UTF8.
        # Control characters section in surrogate code block
        for index in range(0x80, 0xA0):
            spec_windows1252_char = chr(index)
            surrogate_char = chr(index + 0xDC00)
            if spec_windows1252_char in self.spec_windows1252_to_utf8_dict:
                self.set_encoding_map_dict(surrogate_char, self.spec_windows1252_to_utf8_dict[spec_windows1252_char],
                                           index, None, 's1')
            else:  # x81,x8D,x8F,x90,x9D
                self.set_encoding_map_dict(surrogate_char, undef_default, index, None, 's2')
        # Other characters in surrogate code block
        for index in range(0xA0, 0x100):
            latin1_char = chr(index)
            surrogate_char = chr(index + 0xDC00)
            self.set_encoding_map_dict(surrogate_char, latin1_char, index, None, 's3')
        # Misencodings that resulted applying conversion from wrong or double Windows1252/Latin1-to-UTF8 conversion.
        for index in range(0x80, 0x100):
            latin1_char = chr(index)
            windows1252_char = self.windows1252_to_utf8_char(index)
            byte_string = latin1_char.encode('utf-8')
            latin1_latin1_char = ''.join([chr(x) for x in byte_string])
            repl_char = latin1_char if index >= 0xA0 else windows1252_char
            # to repair Latin1-to-UTF8 plus Latin1-to-UTF8
            self.set_encoding_map_dict(latin1_latin1_char, repl_char, index, byte_string, 'm1')
            if byte_string[1] < 0xA0:
                latin1_windows1252_char = ''.join([self.windows1252_to_utf8_char(x) for x in byte_string])
                # to repair Latin1-to-UTF8 plus Windows1252-to-UTF8
                self.set_encoding_map_dict(latin1_windows1252_char, repl_char, index, None, 'm2')
            if index < 0xA0:
                # to repair Latin1-to-UTF8 instead of Windows1252-to-UTF8
                self.set_encoding_map_dict(latin1_char, windows1252_char, index, None, 'm3')
                byte_string = windows1252_char.encode('utf-8')
                windows1252_latin1_char = ''.join([chr(x) for x in byte_string])
                # to repair Windows1252-to-UTF8 plus Latin1-to-UTF8
                self.set_encoding_map_dict(windows1252_latin1_char, windows1252_char, index, byte_string, 'm4')
        for index in range(0xFF01, 0xFF5F):
            fullwidth_char = chr(index)
            standard_char = chr(index - 0xFEE0)  # starting at code point \u0021
            self.set_encoding_map_dict(fullwidth_char, standard_char, index, None, 'f1')
        src_dir_path = os.path.dirname(os.path.realpath(__file__))
        data_dir_path = os.path.join(src_dir_path, "../data")
        for tsv_filename in ('ArabicPresentationFormMappingAnnotated.tsv',
                             'CJKCompatibilityMappingAnnotated.tsv',
                             'CombiningModifierMappingAnnotated.tsv',
                             'DigitMappingAnnotated.tsv'):
            full_tsv_filename = os.path.join(data_dir_path, tsv_filename)
            try:
                with open(full_tsv_filename, 'r', encoding='utf-8', errors='ignore') as f:
                    line_number = 0
                    for line in f:
                        line_number += 1
                        tsv_list = re.split(r'\t', line.rstrip())
                        if (len(tsv_list) >= 2) and (line_number >= 2):
                            self.encoding_map_dict[tsv_list[0]] = tsv_list[1]
            except FileNotFoundError:
                log.error(f'Could not open file {full_tsv_filename}')

    def map_encoding_char(self, match: Match[str]) -> str:
        """Maps substring resulting from misencoding to repaired UTF8."""
        s = match.group()
        if s in self.encoding_map_dict:
            return self.encoding_map_dict[s]
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
        if re.search(r"[\uDC80-\uDCFF]", s):
            s = re.sub(r'[\uDC80-\uDCFF]', self.map_encoding_char, s)
        # Correct UTF8 misencodings due to wrong or double application of Windows1252/Latin1-to-UTF converter
        if re.search(r'\u00E2[\u0080-\u00BF][\u0080-\u00BF]', s):
            s = re.sub(r'\u00E2[\u0080-\u00BF][\u0080-\u00BF]', self.map_encoding_char, s)
        if re.search(r'[\u00C2-\u00C3\u00C5\u00C6\u00CB][\u0080-\u00BF]', s):
            s = re.sub(r'[\u00C2-\u00C3\u00C5\u00C6\u00CB][\u0080-\u00BF]', self.map_encoding_char, s)
        if re.search(r'[\u0080-\u00BF]', s):
            s = re.sub(r'[\u0080-\u00BF]', self.map_encoding_char, s)
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
        s = re.sub(r'[\u0000-\u0008\u000B-\u001F\u007F-\u009F]', '',
                   s)  # control characters (except tab x9, linefeed xA)
        s = s.replace('\u0640', '')  # Arabic tatweel
        s = re.sub(r'[\u200B-\u200F]', '', s)  # zero width space/non-joiner/joiner, direction marks
        s = re.sub(r'[\uFE00-\uFE0F]', '', s)  # variation selectors 1-16
        # noinspection SpellCheckingInspection
        s = s.replace('\uFEFF', '')  # byte order mark, zero width no-break space
        s = re.sub(r'[\U000E0100-\U000E01EF]', '', s)  # variation selectors 17-256
        return s

    @staticmethod
    def delete_arabic_diacritics(s: str) -> str:
        s = s.replace('\u064E', '')  # delete Arabic fatha
        s = s.replace('\u064F', '')  # delete Arabic damma
        s = s.replace('\u0650', '')  # delete Arabic kasra
        s = s.replace('\u0651', '')  # delete Arabic shadda
        s = s.replace('\u0652', '')  # delete Arabic sukun
        s = s.replace('\u064B', '')  # delete Arabic fathatan
        s = s.replace('\u064C', '')  # delete Arabic dammatan
        s = s.replace('\u064D', '')  # delete Arabic kasratan
        return s

    # noinspection SpellCheckingInspection
    @staticmethod
    def normalize_farsi_characters(s: str) -> str:
        s = s.replace('\u064A', '\u06CC')  # Arabic to Farsi yeh
        s = s.replace('\u0649', '\u06CC')  # Arabic alef maksura to Farsi yeh
        s = s.replace('\u06CD', '\u06CC')  # Arabic yeh with tail to Farsi yeh
        s = s.replace('\u0643', '\u06A9')  # Arabic kaf to keheh
        return s

    @staticmethod
    def normalize_ring_characters(s: str) -> str:
        s = s.replace('\u06AB', '\u06AF')  # Arabic kaf with ring to gaf
        s = s.replace('\u067C', '\u062A')  # Arabic teh with ring to Arabic teh
        s = s.replace('\u0689', '\u062F')  # Arabic dal with ring to Arabic dal
        s = s.replace('\u0693', '\u0631')  # Arabic reh with ring to Arabic reh
        return s

    # noinspection SpellCheckingInspection
    def normalize_arabic_pres_form_characters(self, s: str) -> str:
        """This includes some Arabic ligatures."""
        if re.search(r"[\uFB50-\uFEFC]", s):
            s = re.sub(r'[\uFB50-\uFEFC]', self.map_encoding_char, s)
        return s

    # noinspection SpellCheckingInspection
    def normalize_ligatures_and_symbols(self, s: str) -> str:
        """Arabic ligatures are already covered by function normalize_arabic_pres_form_characters."""
        s = s.replace('\u00B5', '\u03BC')            # U+00B5 MICRO SIGN µ -> μ (GREEK SMALL LETTER MU)
        if re.search(r"[\u0132-\u01F3]", s):
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
        # U+0587 ARMENIAN SMALL LIGATURE ECH YIWN և is considered a single letter, not to be split into եւ U+0565 U+0582
        if re.search(r"[\uFB00-\uFB4F]", s):
            s = s.replace('\uFB00', '\u0066\u0066')  # U+FB00 LATIN SMALL LIGATURE FF ﬀ -> ff
            s = s.replace('\uFB01', '\u0066\u0069')  # U+FB01 LATIN SMALL LIGATURE FI ﬁ -> fi
            s = s.replace('\uFB02', '\u0066\u006C')  # U+FB02 LATIN SMALL LIGATURE FL ﬂ -> fl
            s = s.replace('\uFB03', '\u0066\u0066\u0069')  # U+FB03 LATIN SMALL LIGATURE FFI ﬃ -> ffi
            s = s.replace('\uFB04', '\u0066\u0066\u006C')  # U+FB04 LATIN SMALL LIGATURE FFL ﬄ -> ffl
            s = s.replace('\uFB05', '\u017F\u0074')  # U+FB05 LATIN SMALL LIGATURE LONG S T ﬅ -> ſt
            s = s.replace('\uFB06', '\u0073\u0074')  # U+FB06 LATIN SMALL LIGATURE ST ﬆ -> st
            s = s.replace('\uFB13', '\u0574\u0576')  # U+FB13 ARMENIAN SMALL LIGATURE MEN NOW ﬓ -> մն
            s = s.replace('\uFB14', '\u0574\u0565')  # U+FB14 ARMENIAN SMALL LIGATURE MEN ECH ﬔ -> մե
            s = s.replace('\uFB15', '\u0574\u056B')  # U+FB15 ARMENIAN SMALL LIGATURE MEN INI ﬕ -> մի
            s = s.replace('\uFB16', '\u057E\u0576')  # U+FB16 ARMENIAN SMALL LIGATURE VEW NOW ﬖ -> վն
            s = s.replace('\uFB17', '\u0574\u056D')  # U+FB17 ARMENIAN SMALL LIGATURE MEN XEH ﬗ -> մխ
            s = s.replace('\uFB4F', '\u05D0\u05DC')  # U+FB4F HEBREW LIGATURE ALEF LAMED ﭏ -> אל
        if re.search(r"[\u03D0-\u03F9]", s):
            s = s.replace('\u03D0', '\u03B2')        # U+03D0 GREEK BETA SYMBOL ϐ -> β
            s = s.replace('\u03D1', '\u03B8')        # U+03D1 GREEK THETA SYMBOL ϑ -> θ
            s = s.replace('\u03D2', '\u03A5')        # U+03D2 GREEK UPSILON WITH HOOK SYMBOL ϒ -> Υ
            s = s.replace('\u03D3', '\u03D2\u0301')  # U+03D3 GREEK UPSILON WITH ACUTE AND HOOK SYMBOL ϓ -> ϓ
            s = s.replace('\u03D4', '\u03D2\u0308')  # U+03D4 GREEK UPSILON WITH DIAERESIS AND HOOK SYMBOL ϔ -> ϔ
            s = s.replace('\u03D5', '\u03C6')        # U+03D5 GREEK PHI SYMBOL ϕ -> φ
            s = s.replace('\u03D6', '\u03C0')        # U+03D6 GREEK PI SYMBOL ϖ -> π
            s = s.replace('\u03F0', '\u03BA')        # U+03F0 GREEK KAPPA SYMBOL ϰ -> κ
            s = s.replace('\u03F1', '\u03C1')        # U+03F1 GREEK RHO SYMBOL ϱ -> ρ
            s = s.replace('\u03F2', '\u03C2')        # U+03F2 GREEK LUNATE SIGMA SYMBOL ϲ -> ς
            s = s.replace('\u03F4', '\u0398')        # U+03F4 GREEK CAPITAL THETA SYMBOL ϴ -> Θ
            s = s.replace('\u03F5', '\u03B5')        # U+03F5 GREEK LUNATE EPSILON SYMBOL ϵ -> ε
            s = s.replace('\u03F9', '\u03A3')        # U+03F9 GREEK CAPITAL LUNATE SIGMA SYMBOL Ϲ -> Σ
        if re.search(r"[\u2126-\u2138]", s):
            s = s.replace('\u2126', '\u03A9')        # U+2126 OHM SIGN Ω -> Ω (GREEK CAPITAL LETTER OMEGA)
            s = s.replace('\u212A', '\u004B')        # U+212A KELVIN SIGN K -> K (LATIN CAPITAL LETTER K)
            s = s.replace('\u212B', '\u00C5')        # U+212B ANGSTROM SIGN Å -> Å (LATIN CAP. LETTER A WITH RING ABOVE)
            s = s.replace('\u2135', '\u05D0')        # U+2135 ALEF SYMBOL ℵ -> א
            s = s.replace('\u2136', '\u05D1')        # U+2136 BET SYMBOL ℶ -> ב
            s = s.replace('\u2137', '\u05D2')        # U+2137 GIMEL SYMBOL ℷ -> ג
            s = s.replace('\u2138', '\u05D3')        # U+2138 DALET SYMBOL ℸ -> ד
        if re.search(r"[\u32C0-\u33FF]", s):
            s = re.sub(r'[\u32C0-\u33FF]', self.map_encoding_char, s)  # CJK Compatibility (e.g. ㋀ ㌀ ㍰ ㎢ ㏾ ㏿)
        return s

    def apply_combining_modifiers(self, s: str) -> str:
        """
        Combines 2 Unicode characters (incl. combining modifier) into one Unicode character, e.g. ö (o +  ̈) -> ö
        Must be applied after normalize_ligatures_and_symbols.
        """
        # if preceded by letter:
        # s = s.replace('\u00A8', '\u0308')    # U+00A8 DIAERESIS -> U+0308 COMBINING DIAERESIS
        # s = s.replace('\u1FBF', '\u0313')    # U+1FBF GREEK PSILI -> U+0313 COMBINING COMMA ABOVE
        # s = s.replace('\u1FFE', '\u0314')    # U+1FFE GREEK DASIA -> U+0314 COMBINING REVERSED COMMA ABOVE
        # U+0300 - U+036F general combining modifier block
        # U+0653 - U+0655 Arabic modifiers: madda above, hamza above, hamza below
        # U+3099 COMBINING KATAKANA-HIRAGANA VOICED SOUND MARK  ゙(e.g. ka -> ga)
        # U+309A COMBINING KATAKANA-HIRAGANA SEMI-VOICED SOUND MARK  ゚(e.g. ha -> pa)
        # U+1D165 -U+1D172 MUSICAL SYMBOL COMBINING modifiers
        if re.search(r"[\u0300-\u036F\u0653-\u0655\u3099\u309A]", s):
            s = re.sub(r'.[\u0300-\u036F\u0653-\u0655\u3099\u309A]', self.map_encoding_char, s)
        if re.search(r"[\U0001D100-\U0001D1FF]", s):
            s = re.sub(r'.[\U0001D165-\U0001D172]', self.map_encoding_char, s)  # recursively defined
            s = re.sub(r'.[\U0001D165-\U0001D172]', self.map_encoding_char, s)  # therefore: second iteration
        return s

    # noinspection SpellCheckingInspection
    @staticmethod
    def normalize_indic_diacritics(s: str) -> str:
        """
        This function normalizes Indic (so far only Devanagari) strings by
         - mapping letters to the canonical composed or decomposed form and
         - putting diacritics in the canonical order (nukta before vowel sign).
        """
        if s.find('\u093C'):  # Devanagari nukta
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
        s = s.replace('\u0640', '')  # U+0640 Arabic tatweel
        s = s.replace('\u060C', ',')  # U+060C Arabic comma
        s = s.replace('\u060D', ',')  # U+060C Arabic date separator
        s = s.replace('\u061B', ';')  # U+061B Arabic semicolon
        s = s.replace('\u061F', '?')  # U+061F Arabic question mark
        s = s.replace('\u066A', '%')  # U+066A Arabic percent sign
        s = s.replace('\u066B', '.')  # U+066B Arabic decimal separator
        s = s.replace('\u066C', ',')  # U+066C Arabic thousands separator
        s = s.replace('\u066D', '*')  # U+066D Arabic five pointed star
        s = s.replace('\u06D4', '.')  # U+06D4 Arabic full stop
        return s

    @staticmethod
    def normalize_non_zero_spaces(s: str) -> str:
        """
        Map NO-BREAK SPACE, EN SPACE, EM SPACE, THREE-PER-EM SPACE, FOUR-PER-EM SPACE, SIX-PER-EM SPACE, FIGURE SPACE,
        PUNCTUATION SPACE, THIN SPACE, HAIR SPACE, NARROW NO-BREAK SPACE, MEDIUM MATHEMATICAL SPACE, IDEOGRAPHIC SPACE
        to regular SPACE.
        **Not** included: tab (= horizontal tabulation/character tabulation)
        """
        s = s.replace('\u00A0', ' ')  # U+00A0 NO-BREAK SPACE
        s = re.sub(r'[\u2002-\u200A]', ' ', s)
        s = s.replace('\u202F', ' ')  # U+00A0 NARROW NO-BREAK SPACE
        s = s.replace('\u205F', ' ')  # U+00A0 MEDIUM MATHEMATICAL SPACE
        s = s.replace('\u3000', ' ')  # U+3000 IDEOGRAPHIC SPACE
        return s

    def normalize_fullwidth_characters(self, s: str) -> str:
        """Replace fullwidth characters such as Ａ with regular Latin letters such as A."""
        if re.search(r'[\uFF01-\uFF5E]', s):
            s = re.sub(r'[\uFF01-\uFF5E]', self.map_encoding_char, s)
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
        if not re.search(r"[\u0660-\u1E959]", s):
            return s
        if re.search(r'[\u0660-\u07C9]', s):
            s = re.sub(r'[\u0660-\u0669]', self.map_encoding_char, s)  # ARABIC-INDIC digits
            s = re.sub(r'[\u06F0-\u06F9]', self.map_encoding_char, s)  # EXTENDED ARABIC-INDIC digits
            s = re.sub(r'[\u07C0-\u07C9]', self.map_encoding_char, s)  # NKO digits
        if re.search(r'[\u0966-\u0D6F]', s):
            s = re.sub(r'[\u0966-\u096F]', self.map_encoding_char, s)  # DEVANAGARI digits
            s = re.sub(r'[\u09E6-\u09EF]', self.map_encoding_char, s)  # BENGALI digits
            s = re.sub(r'[\u0A66-\u0A6F]', self.map_encoding_char, s)  # GURMUKHI digits
            s = re.sub(r'[\u0AE6-\u0AEF]', self.map_encoding_char, s)  # GUJARATI digits
            s = re.sub(r'[\u0B66-\u0B6F]', self.map_encoding_char, s)  # ORIYA digits
            s = re.sub(r'[\u0BE6-\u0BEF]', self.map_encoding_char, s)  # TAMIL digits
            s = re.sub(r'[\u0C66-\u0C6F]', self.map_encoding_char, s)  # TELUGU digits
            s = re.sub(r'[\u0CE6-\u0CEF]', self.map_encoding_char, s)  # KANNADA digits
            s = re.sub(r'[\u0D66-\u0D6F]', self.map_encoding_char, s)  # MALAYALAM digits
        if re.search(r'[\u0DE6-\uABF9]', s):
            s = re.sub(r'[\u0DE6-\u0DEF]', self.map_encoding_char, s)  # SINHALA LITH digits
            s = re.sub(r'[\u0E50-\u0E59]', self.map_encoding_char, s)  # THAI digits
            s = re.sub(r'[\u0ED0-\u0ED9]', self.map_encoding_char, s)  # LAO digits
            s = re.sub(r'[\u0F20-\u0F29]', self.map_encoding_char, s)  # TIBETAN digits
            s = re.sub(r'[\u1040-\u1049]', self.map_encoding_char, s)  # MYANMAR digits
            s = re.sub(r'[\u1090-\u1099]', self.map_encoding_char, s)  # MYANMAR SHAN digits
            s = re.sub(r'[\u17E0-\u17E9]', self.map_encoding_char, s)  # KHMER digits
            s = re.sub(r'[\u1810-\u1819]', self.map_encoding_char, s)  # MONGOLIAN digits
            s = re.sub(r'[\u1946-\u194F]', self.map_encoding_char, s)  # LIMBU digits
            s = re.sub(r'[\u19D0-\u19D9]', self.map_encoding_char, s)  # NEW TAI LUE digits
            s = re.sub(r'[\u1A80-\u1A89]', self.map_encoding_char, s)  # TAI THAM HORA digits
            s = re.sub(r'[\u1A90-\u1A99]', self.map_encoding_char, s)  # TAI THAM THAM digits
            s = re.sub(r'[\u1B50-\u1B59]', self.map_encoding_char, s)  # BALINESE digits
            s = re.sub(r'[\u1BB0-\u1BB9]', self.map_encoding_char, s)  # SUNDANESE digits
            s = re.sub(r'[\u1C40-\u1C49]', self.map_encoding_char, s)  # LEPCHA digits
            s = re.sub(r'[\u1C50-\u1C59]', self.map_encoding_char, s)  # OL CHIKI digits
            s = re.sub(r'[\uA620-\uA629]', self.map_encoding_char, s)  # VAI digits
            s = re.sub(r'[\uA8D0-\uA8D9]', self.map_encoding_char, s)  # SAURASHTRA digits
            s = re.sub(r'[\uA900-\uA909]', self.map_encoding_char, s)  # KAYAH LI digits
            s = re.sub(r'[\uA9D0-\uA9D9]', self.map_encoding_char, s)  # JAVANESE digits
            s = re.sub(r'[\uA9F0-\uA9F9]', self.map_encoding_char, s)  # MYANMAR TAI LAING digits
            s = re.sub(r'[\uAA50-\uAA59]', self.map_encoding_char, s)  # CHAM digits
            s = re.sub(r'[\uABF0-\uABF9]', self.map_encoding_char, s)  # MEETEI MAYEK digits
        if re.search(r'[\U000104A0-\U0001E959]', s):
            s = re.sub(r'[\U000104A0-\U000104A9]', self.map_encoding_char, s)  # OSMANYA digits
            s = re.sub(r'[\U00010D30-\U00010D39]', self.map_encoding_char, s)  # HANIFI ROHINGYA digits
            s = re.sub(r'[\U00011066-\U0001106F]', self.map_encoding_char, s)  # BRAHMI digits
            s = re.sub(r'[\U000110F0-\U000110F9]', self.map_encoding_char, s)  # SORA SOMPENG digits
            s = re.sub(r'[\U00011136-\U0001113F]', self.map_encoding_char, s)  # CHAKMA digits
            s = re.sub(r'[\U000111D0-\U000111D9]', self.map_encoding_char, s)  # SHARADA digits
            s = re.sub(r'[\U000112F0-\U000112F9]', self.map_encoding_char, s)  # KHUDAWADI digits
            s = re.sub(r'[\U00011450-\U00011459]', self.map_encoding_char, s)  # NEWA digits
            s = re.sub(r'[\U000114D0-\U000114D9]', self.map_encoding_char, s)  # TIRHUTA digits
            s = re.sub(r'[\U00011650-\U00011659]', self.map_encoding_char, s)  # MODI digits
            s = re.sub(r'[\U000116C0-\U000116C9]', self.map_encoding_char, s)  # TAKRI digits
            s = re.sub(r'[\U00011730-\U00011739]', self.map_encoding_char, s)  # AHOM digits
            s = re.sub(r'[\U000118E0-\U000118E9]', self.map_encoding_char, s)  # WARANG CITI digits
            s = re.sub(r'[\U00011C50-\U00011C59]', self.map_encoding_char, s)  # BHAIKSUKI digits
            s = re.sub(r'[\U00011D50-\U00011D59]', self.map_encoding_char, s)  # MASARAM GONDI digits
            s = re.sub(r'[\U00011DA0-\U00011DA9]', self.map_encoding_char, s)  # GUNJALA GONDI digits
            s = re.sub(r'[\U00016A60-\U00016A69]', self.map_encoding_char, s)  # MRO digits
            s = re.sub(r'[\U00016B50-\U00016B59]', self.map_encoding_char, s)  # PAHAWH HMONG digits
            s = re.sub(r'[\U0001E950-\U0001E959]', self.map_encoding_char, s)  # ADLAM digits
        return s

    # noinspection SpellCheckingInspection
    @staticmethod
    def repair_xml(s: str) -> str:
        """Repair multi-level xml-escapes such as &amp;amp;quot; to &quot;"""
        s = re.sub(r'(?<=&)(?:amp;)+(?=(?:amp|apos|gt|lt|nbsp|quot|#\d{1,6}|#x[0-9A-F]{1,5});)',
                   '', s, flags=re.IGNORECASE)
        return s

    @staticmethod
    def repair_tokenization(s: str) -> str:
        """Detach certain punctuation -_+*|% and ASCII digits from Arabic characters."""
        s = re.sub(r"([-_+*|%0-9]+)([\u0600-\u06FF])", r"\1 \2", s)
        s = re.sub(r"([\u0600-\u06FF])([-_+*|%0-9]+)", r"\1 \2", s)
        return s

    @staticmethod
    def increment_dict_count(ht: dict, key: str, increment=1) -> int:
        """For example ht['NUMBER-OF-LINES']"""
        ht[key] = ht.get(key, 0) + increment
        return ht[key]

    def norm_clean_string_group(self, s: str, ht: dict, group_name: str, group_function: Callable[[str], str],
                                loc_id: str) -> str:
        """For a given normalization/cleaning group, call appropriate function and update stats."""
        if f'SKIP-{group_name}' not in ht:
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
        s = self.norm_clean_string_group(s, ht, 'repair-encodings-errors', self.repair_encoding_errors, loc_id)
        # Cleaning step 'del-surrogate' is an alternative/backup to windows-1252.
        # It should not be skipped because surrogates are not printable.
        s = self.norm_clean_string_group(s, ht, 'del-surrogate', self.delete_surrogates, loc_id)
        s = self.norm_clean_string_group(s, ht, 'del-ctrl-char', self.delete_control_characters, loc_id)
        s = self.norm_clean_string_group(s, ht, 'del-diacr', self.delete_arabic_diacritics, loc_id)
        s = self.norm_clean_string_group(s, ht, 'pres-form', self.normalize_arabic_pres_form_characters, loc_id)
        s = self.norm_clean_string_group(s, ht, 'ligatures-symbols', self.normalize_ligatures_and_symbols, loc_id)
        s = self.norm_clean_string_group(s, ht, 'fullwidth', self.normalize_fullwidth_characters, loc_id)
        s = self.norm_clean_string_group(s, ht, 'combining', self.apply_combining_modifiers, loc_id)
        s = self.norm_clean_string_group(s, ht, 'indic-diacr', self.normalize_indic_diacritics, loc_id)
        s = self.norm_clean_string_group(s, ht, 'punct', self.normalize_arabic_punctuation, loc_id)
        s = self.norm_clean_string_group(s, ht, 'space', self.normalize_non_zero_spaces, loc_id)
        s = self.norm_clean_string_group(s, ht, 'digit', self.map_digits_to_ascii, loc_id)
        if lang_code == 'fas':
            s = self.norm_clean_string_group(s, ht, 'farsi-char', self.normalize_farsi_characters, loc_id)
            s = self.norm_clean_string_group(s, ht, 'ring-char', self.normalize_ring_characters, loc_id)
        s = self.norm_clean_string_group(s, ht, 'repair-xml', self.repair_xml, loc_id)
        s = self.norm_clean_string_group(s, ht, 'repair-token', self.repair_tokenization, loc_id)
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
    all_skip_elems = ['repair-encodings-errors', 'del-surrogate', 'del-ctrl-char', 'del-diacr', 'pres-form',
                      'ligatures-symbols', 'fullwidth', 'combining', 'indic-diacr', 'punct', 'space', 'digit',
                      'farsi-char', 'ring-char', 'repair-xml', 'repair-token']
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
    if args.verbose:
        log.info(f'# ISO 639-3 language code: {lang_code or "(not specified)"}')
    # The following line is the core call. ht is a dictionary (empty if no steps are to be skipped).
    wb.norm_clean_lines(ht, input_file=args.input, output_file=args.output, lang_code=lang_code)
    # Log some change stats.
    if args.verbose:
        change_count = ht.get('COUNT-ALL', 0)
        number_of_lines = ht.get('NUMBER-OF-LINES', 0)
        lines = 'line' if change_count == 1 else 'lines'
        log_info = f"# {str(change_count)} out of {str(number_of_lines)} {lines} changed"
        for skip_elem in all_skip_elems:
            count = ht.get(f'COUNT-{skip_elem}', 0)
            if count:
                lines = 'line' if count == 1 else 'lines'
                log_info += f'; {skip_elem} in {str(count)} {lines}'
        log.info(log_info)


if __name__ == "__main__":
    main(sys.argv[1:])
