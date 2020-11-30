#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Written by Ulf Hermjakob, USC/ISI
This file contains functions that build data files used by wildebeest_normalize.py
These data files are in ../data and most importantly include *Mapping*.tsv files used by wildebeest_normalize.py
A major source used for building these files are standard UnicodeData.txt and UnicodeCompositionExclusions.txt
Other files built are primarily for testing, including assert.tsv and assert-preserve.tsv as well as some log files.
As the data files built by this code is already included in the Wildebeest module, normal users do not need it.
It will be used to recompile data files for any updated versions of UnicodeData.txt, UnicodeCompositionExclusions.txt,
and/or new or updated normalization steps in wildebeest_normalize.py
"""

import codecs
from datetime import datetime
from itertools import chain
import logging as log
import os
from pathlib import Path
import re
import unicodedata as ud
import sys
from wildebeest import wildebeest_normalize

log.basicConfig(level=log.INFO)

mapping_dict = {}        # general dict used to build Mapping.tsv files
core_mapping_dict = {}   # special dict for PythonWildebeest and CoreCompatibility mappings
unicode_composition_exclusion_dict = {}  # for characters that should be decomposed, such as Devanagari फ़
assert_wb_dict = {}      # store previously asserted wildebeest reference mappings
assert_nfkc_dict = {}    # store NFKC reference mappings

spec_windows1252_to_utf8_dict = {
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


# noinspection SpellCheckingInspection,SpellCheckingInspection
def build_python_code_from_unicode(codeblock: str = 'Devanagari', indent_level: int = 2) -> None:
    """
    This function was used only in earlier versions of Wildebeest.
    This function produces Python code to normalize strings. Based on UnicodeData.
    The resulting Python code can be used as a basis for other Python functions in this file.
    Example output:
        s = s.replace('\u0928\u093C', '\u0929')    # U+0929 DEVANAGARI LETTER NNNA ऩ -> ऩ
        s = s.replace('\u095F', '\u092F\u093C')    # U+095F DEVANAGARI LETTER YYA य़ -> य़
        s = s.replace('\u0967', '1')               # U+0967 DEVANAGARI DIGIT ONE १ -> 1
    """
    decomposition_exclusions = ()
    if codeblock == 'Arabic':
        code_points = range(0x0600, 0x0700)
    elif codeblock == 'Devanagari':
        code_points = range(0x0900, 0x0980)
        decomposition_exclusions = range(0x0958, 0x0960)
    elif codeblock == 'Hebrew':
        code_points = range(0x0500, 0x0600)
    elif codeblock == 'Indic':
        code_points = range(0x0900, 0x0E00)
        decomposition_exclusions = range(0x0958, 0x0960)  # probably incomplete
    elif codeblock == 'ligature':
        code_points = range(0x0000, 0xFB50)
        decomposition_exclusions = range(0x0000, 0xFB50)
    else:
        code_points = range(0x0000, 0x007F)  # ASCII
    indent = ' ' * indent_level * 4
    for code_point in code_points:
        char = chr(code_point)
        char_name = ud.name(char, '')            # e.g. 'DEVANAGARI LETTER YYA'
        hex_str = ('%04x' % code_point).upper()  # e.g. 095F
        uplus = 'U+' + hex_str                   # e.g. U+095F
        us = '\\u' + hex_str                     # e.g. \u095F
        decomp_ssv = ud.decomposition(char)      # e.g. '092F 093C'
        if (codeblock == 'ligature') and ('SYMBOL' not in char_name):
            continue
        decomp_ssv = re.sub(r'<.*?>\s*', '', decomp_ssv)  # remove decomp type info, e.g. <compat>, <isolated>
        if decomp_ssv:
            decomp_codes = decomp_ssv.split()   # e.g. ['092F', '093C']
            decomp_chars = [chr(int(x, 16)) for x in decomp_codes]   # e.g. ['य', '़']
            decomp_str = ''.join(decomp_chars)  # e.g. 'य़' (2 characters)
            decomp_uss = [('\\u' + ('%04x' % int(x, 16)).upper()) for x in decomp_codes]  # e.g. ['\u092F', '\u093C']
            decomp_us = ''.join(decomp_uss)     # e.g. '\u092F\u093C'
            if code_point in decomposition_exclusions:
                #    s = s.replace('\u095F', '\u092F\u093C')    # U+095F DEVANAGARI LETTER YYA य़ -> य़
                print(f"{indent}s = s.replace('{us}', '{decomp_us}')    # {uplus} {char_name} {char} -> {decomp_str}")
            else:
                #    s = s.replace('\u0928\u093C', '\u0929')  # U+0929 DEVANAGARI LETTER NNNA ऩ -> ऩ
                print(f"{indent}s = s.replace('{decomp_us}', '{us}')    # {uplus} {char_name} {decomp_str} -> {char}")
        if 'HEBREW POINT' in char_name:
            print(f"{indent}s = s.replace('{us}', '')  # {char_name}")
        digit = ud.digit(char, '')
        if digit != '':
            #   s = s.replace('\u0967', '1')    # U+0967 DEVANAGARI DIGIT ONE १ -> 1
            print(f"{indent}s = s.replace('{us}', '{digit}')    # {uplus} {char_name} {char} -> {digit}")


def norm_string_by_mapping_dict(s: str, m_dict: dict, wb: wildebeest_normalize.Wildebeest,
                                verbose: bool = False) -> str:
    """Function greedily applies to a string the mapping of short sub-strings using a lookup-table."""
    result = ''
    i, n = 0, len(s)
    while i < n:
        for l in range(3, 0, -1):
            sub_map = m_dict.get(s[i:i+l])
            if sub_map is not None:
                result += sub_map
                i += l
                break
        if sub_map is None:
            result += s[i:i+1]
            i += 1
    result = wb.normalize_hangul(result)
    if verbose and (result != s):
        log.info(f'Upgraded {s} to {result}')
    return result


def windows1252_to_utf8_char(index: int) -> str:
    """ Typical input: 0x80       Typical output: '€' """
    s = chr(index)
    if s in spec_windows1252_to_utf8_dict:
        return spec_windows1252_to_utf8_dict[s]
    else:
        return s


def safe_unicode_name(char: str) -> str:
    """
    For a given Unicode character,
    returns UnicodeData name (e.g. 'LATIN SMALL LETTER I'), 'Control character', or 'NO_NAME'
    """
    char_name = ud.name(char, None)
    if char_name is None:
        if ud.category(char) == 'Cc':
            char_name = 'Control character'
        else:
            char_name = 'NO_NAME'
    return char_name


def string_to_character_unicode_descriptions(s: str, ref: str = None) -> str:
    """
    Maps a mapping source or target string to a description (used for human inspection).
    If the primary argument is a target string, the optional ref is typically the source string.
    Example outputs:
    U+0133 (LATIN SMALL LIGATURE IJ)
    -> U+0069 (LATIN SMALL LETTER I) U+006A (LATIN SMALL LETTER J)
    """
    if ref and s == '':
        return 'deleted'
    elif ref and s == ref:
        return 'preserved'
    else:
        return ('-> ' if ref else '') + \
                " ".join([f"U+{('%04x' % ord(char)).upper()} ({safe_unicode_name(char)})" for char in s])


def build_wildebeest_tsv_file(codeblock: str, verbose: bool = True, supplementary_code_mode: str = 'w') -> None:
    """
    This function builds tsv files in the data directory that map from non-standard encoding (first field)
    to standard encoding (second field).
    """
    timestamp = datetime.now().strftime("%b %d, %Y, %H:%M:%S")
    output_file_basename = f"{codeblock}{'Annotated' if verbose else ''}.tsv"
    head_info = 'MapFromString\tMapToString'
    if verbose:
        head_info += f'\tComment # File {output_file_basename}, automatically generated by script' \
                     f' wildebeest_build.py (Ulf Hermjakob, USC/ISI) based on UnicodeData on {timestamp}'
    supplementary_code = ''
    wb = wildebeest_normalize.Wildebeest()
    if codeblock in ('ArabicPresentationFormMapping',  # includes Arabic ligatures
                     'CJKCompatibilityMapping',        # includes IDEOGRAPHIC TELEGRAPH SYMBOL FOR months
                     'CombiningModifierMapping',       # e.g. maps "é" (2 Unicode characters) to "é" (1 character)
                     'CoreCompatibilityMapping',       # includes Hangul compatibility (KS X 1001)
                     'DigitMapping',
                     'EnclosureMapping',               # characters enclosed in circles, parentheses, squares
                     'FontSmallVerticalMapping'):      # for Unicode keywords <font>, <small>, <vertical>
        if codeblock == 'ArabicPresentationFormMapping':
            code_points = chain(range(0xFB50, 0xFE00), range(0xFE70, 0xFF00))
        elif codeblock == 'CJKCompatibilityMapping':
            code_points = chain(range(0x2F00, 0x2FE0), range(0x3038, 0x303B),
                                range(0x3250, 0x3251), range(0x32C0, 0x3400),
                                range(0xF900, 0xFB00), range(0xFF01, 0xFFEF),
                                range(0x1F190, 0x1F191), range(0x1F200, 0x1F201), range(0x2F800, 0x2FA20))
        elif codeblock == 'CoreCompatibilityMapping':
            code_points = chain(range(0x0E33, 0x0E34), range(0x0EB3, 0x0EB4), range(0x0EDC, 0x0EDE),  # Thai, Lao
                                range(0x0F71, 0x0F82),  # Tibetan
                                range(0x2011, 0x2012), range(0x2024, 0x2027), range(0x2033, 0x203D),
                                range(0x2047, 0x2058), range(0x2160, 0x2180), range(0x222C, 0x2231),
                                range(0x2329, 0x232B), range(0x2488, 0x249C),
                                range(0x2A0C, 0x2A0D), range(0x2A74, 0x2A77), range(0x3130, 0x3190),
                                range(0x1F100, 0x1F10B))
        elif codeblock == 'EnclosureMapping':
            code_points = chain(range(0x2460, 0x2488), range(0x249C, 0x2500), range(0x3036, 0x3037),
                                range(0x3200, 0x3250),
                                range(0x3251, 0x32C0), range(0x32D0, 0x32FF), range(0x1F110, 0x1F16A),
                                range(0x1F201, 0x1F260))
        elif codeblock == 'FontSmallVerticalMapping':
            code_points = chain(range(0x2100, 0x2150), range(0x309F, 0x30A0), range(0x30FF, 0x3100),
                                range(0xFB20, 0xFB2A), range(0xFE10, 0xFE70),
                                range(0x1D400, 0x1D800), range(0x1EE00, 0x1EEC0), range(0x1FBF0, 0x1FBFA))
        else:
            code_points = chain(range(0x0000, 0x3400), range(0xA000, 0xAC00), range(0xF900, 0x18D00),
                                range(0x1B000, 0x1B300), range(0x1BC00, 0x1BD00), range(0x1D000, 0x1FC00),
                                range(0x2F800, 0x2FA20), range(0xE0000, 0xE0200))
        output_tsv_filename = f'../data/{output_file_basename}'
        n_output_lines = 0
        with open(output_tsv_filename, 'w', encoding='utf-8') as f:
            f.write(head_info + '\n')
            for code_point in code_points:
                char = chr(code_point)
                decomp_ssv = ud.decomposition(char)
                action = ''
                if decomp_ssv:
                    decomp_elements = decomp_ssv.split()
                    if ((codeblock == 'ArabicPresentationFormMapping')
                            and (len(decomp_elements) >= 2)
                            and (decomp_elements[0] in ['<initial>', '<medial>', '<final>', '<isolated>'])):
                        decomp_chars = decomp_elements[1:]
                        decomp_str = ''.join([chr(int(x, 16)) for x in decomp_chars])
                        action = 'decomposition'
                    elif ((codeblock == 'CJKCompatibilityMapping')
                            and (len(decomp_elements) >= 1)):
                        decomp_chars = None
                        if ((decomp_elements[0] in ['<compat>', '<square>', '<wide>', '<narrow>'])
                                and (len(decomp_elements) >= 2)):
                            decomp_chars = decomp_elements[1:]
                        elif not (decomp_elements[0]).startswith('<'):
                            decomp_chars = decomp_elements
                        if decomp_chars:
                            decomp_str = ''.join([chr(int(x, 16)) for x in decomp_chars])
                            # map ℓ (U+2113, script small l) to regular l (as in ml)
                            decomp_str = decomp_str.replace('\u2113', 'l')
                            action = 'decomposition'
                    elif ((codeblock == 'CombiningModifierMapping')
                            and (len(decomp_elements) >= 2)):
                        if not decomp_elements[0].startswith('<'):
                            decomp_chars = decomp_elements
                        elif code_point == 0x0587:  # ARMENIAN SMALL LIGATURE ECH YIWN
                            decomp_chars = decomp_elements[1:]
                            action = 'composition'
                        elif code_point in [0x0F77, 0x0F79]:  # TIBETAN VOWEL SIGN VOCALIC RR, LL
                            decomp_chars = decomp_elements[1:]
                            action = 'decomposition'
                        else:
                            decomp_chars = None
                        if decomp_chars:
                            decomp_str = ''.join([chr(int(x, 16)) for x in decomp_chars])
                            if not action:
                                if char in unicode_composition_exclusion_dict:
                                    action = 'decomposition'
                                else:
                                    action = 'composition'
                    elif codeblock == 'CoreCompatibilityMapping':
                        # for mappings of Hangul compatibility characters, some punctuation and math symbols,
                        # Roman numerals, numerals with attached punctuation, some complex modifier characters
                        decomp_chars = None
                        if (len(decomp_elements) >= 2) and (decomp_elements[0] in ['<compat>', '<noBreak>']):
                            decomp_chars = decomp_elements[1:]
                        elif (len(decomp_elements) >= 1) and not decomp_elements[0].startswith('<'):
                            decomp_chars = decomp_elements
                        if decomp_chars:
                            decomp_str = ''.join([chr(int(x, 16)) for x in decomp_chars])
                            action = 'decomposition'
                    elif codeblock == 'EnclosureMapping':
                        # build mappings for Unicode characters that are squared, circled etc.
                        char_name = ud.name(char, None)
                        decomp_chars = None
                        left_enclosure = ''
                        right_enclosure = ''
                        if (len(decomp_elements) >= 2) and (decomp_elements[0] == '<circle>'):
                            decomp_chars = decomp_elements[1:]
                            left_enclosure, right_enclosure = '(', ')'
                        elif (len(decomp_elements) >= 2) and (decomp_elements[0] == '<square>'):
                            decomp_chars = decomp_elements[1:]
                            left_enclosure, right_enclosure = '[', ']'
                        elif ((len(decomp_elements) >= 2)
                              and (decomp_elements[0] == '<compat>')
                              and ('CIRCLED' in char_name)):
                            decomp_chars = decomp_elements[1:]
                            left_enclosure, right_enclosure = '(', ')'
                        elif ((len(decomp_elements) >= 2)
                              and (decomp_elements[0] == '<compat>')
                              and ('PARENTHESIZED' in char_name)):
                            decomp_chars = decomp_elements[1:]
                            left_enclosure, right_enclosure = '(', ')'
                        elif ((len(decomp_elements) >= 2)
                              and (decomp_elements[0] == '<compat>')
                              and ('TORTOISE SHELL BRACKETED' in char_name)):
                            decomp_chars = decomp_elements[1:]
                            left_enclosure, right_enclosure = '〔', '〕'
                        if decomp_chars:
                            decomp_str = ''.join([chr(int(x, 16)) for x in decomp_chars])
                            if ((not decomp_str.startswith(left_enclosure))
                                    and (not decomp_str.endswith(right_enclosure))):
                                decomp_str = left_enclosure + decomp_str + right_enclosure
                            action = 'decomposition'
                    elif ((codeblock == 'FontSmallVerticalMapping')
                            and (len(decomp_elements) >= 2)
                            and (decomp_elements[0] in ['<font>', '<small>', '<vertical>'])):
                        # build mapping for Unicode entries with '<font>', '<small>', or '<vertical>'
                        decomp_chars = decomp_elements[1:]
                        decomp_str = ''.join([chr(int(x, 16)) for x in decomp_chars])
                        action = 'decomposition'
                elif codeblock == 'DigitMapping':
                    # build a mapping from all decimal-system digits to ASCII (54 sets in Unicode)
                    digit = ud.digit(char, None)
                    char_name = ud.name(char, None)
                    if ((digit is not None)
                            and (char_name is not None)
                            and re.search(r' DIGIT (ZERO|ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE|TEN)$',
                                          char_name)
                            and ('CIRCLED' not in char_name)
                            and ('ETHIOPIC' not in char_name)    # digits don't map one-to-one to ASCII digits
                            and ('KHAROSHTHI' not in char_name)  # digits don't map one-to-one to ASCII digits
                            and ('RUMI' not in char_name)):      # digits don't map one-to-one to ASCII digits
                        decomp_str = str(digit)
                        action = 'decomposition'
                        if (digit == 0) and supplementary_code_mode:  # used only in early versions of Wildebeest
                            unicode_from = '\\u' + ('%04x' % code_point).upper() if code_point < 0x10000 else \
                                           '\\U' + ('%08x' % code_point).upper()
                            unicode_to = '\\u' + ('%04x' % (code_point + 9)).upper() if code_point < 0x10000 else \
                                         '\\U' + ('%08x' % (code_point + 9)).upper()
                            unicode_range = f'[{unicode_from}-{unicode_to}]'
                            char_name_suffix = ' DIGIT ZERO'
                            supplementary_code += f"if re.search(r'{unicode_range}', s):\n"
                            supplementary_code += f"    s = re.sub(r'{unicode_range}', self.apply_mapping_dict, s)"
                            if char_name.endswith(char_name_suffix):
                                supplementary_code += f"    # {char_name[:-len(char_name_suffix)]} digits\n"
                            else:
                                supplementary_code += '\n'
                if action and verbose:
                    char_name = ud.name(char, None)
                    char_name_clause = f' ({char_name})' if char_name else ''
                    char_hex = 'U+' + ('%04x' % code_point).upper()
                    if action == 'decomposition':
                        # delete any space + deletable Arabic diacritics (fathatan .. sukrun):
                        decomp_str = re.sub(r' [\u064B-\u0652]+', '', decomp_str)
                        decomp_str = norm_string_by_mapping_dict(decomp_str, core_mapping_dict, wb)
                        decomp_str = norm_string_by_mapping_dict(decomp_str, mapping_dict, wb)
                    elif action == 'composition':
                        char = norm_string_by_mapping_dict(char, core_mapping_dict, wb)
                        char = norm_string_by_mapping_dict(char, mapping_dict, wb)
                        decomp_str = norm_string_by_mapping_dict(decomp_str, mapping_dict, wb)
                    decomp_descr = string_to_character_unicode_descriptions(decomp_str)
                if action == 'decomposition':
                    f.write(char + '\t' + decomp_str)
                    mapping_dict[char] = decomp_str
                    if verbose:
                        f.write(f'\t{char_hex}{char_name_clause} -> {decomp_descr}')
                        ud_ref = ud.normalize('NFKC', char)
                        if (ud_ref != decomp_str) and (codeblock not in ['DigitMapping']):
                            f.write(f"   NFKC-ref: {ud_ref}{' (unchanged)' if ud_ref == char else ''}")
                    f.write('\n')
                    n_output_lines += 1
                elif action == 'composition':
                    f.write(decomp_str + '\t' + char)
                    if verbose:
                        f.write(f'\t{decomp_descr} -> {char_hex}{char_name_clause}')
                        ud_ref = ud.normalize('NFKC', decomp_str)
                        if (ud_ref != char) and (codeblock not in ['DigitMapping']):
                            f.write(f"   NFKC-ref: {ud_ref}{' (unchanged)' if ud_ref == decomp_str else ''}")
                    f.write('\n')
                    n_output_lines += 1
        log.info(f'Wrote {n_output_lines} entries to {output_tsv_filename}')
    elif codeblock == 'PythonWildebeestMapping':
        # extract some data mappings from (early) Wildebeest Python code
        output_tsv_filename = f'../data/{output_file_basename}'
        n_input_lines = 0
        output_lines = []
        current_function_name = ''
        with open('../wildebeest_normalize.py', 'r', encoding='utf-8') as f_in:
            for line in f_in:
                n_input_lines += 1
                if re.match(r'\s*#', line):
                    continue  # skip comment line
                mf = re.match(r'.*def\s+([_a-zA-Z0-9]+)', line)
                if mf:
                    current_function_name = mf.group(1)
                elif current_function_name in ['normalize_arabic_characters', 'normalize_farsi_characters',
                                               'normalize_pashto_characters',
                                               'normalize_font_characters',
                                               'normalize_hangul', 'normalize_devanagari_diacritics',
                                               'normalize_enclosure_characters',
                                               'repair_xml', 'repair_url_escapes',
                                               'delete_surrogates', 'init_mapping_dict']:
                    continue  # because replacements are language-specific
                elif re.search(r'(?:\.replace|re\.sub)\(', line):
                    mr = re.match(r".*\.replace\('([^']+)',\s*'([^']*)'\)", line)
                    source_strings = []
                    source_string2 = ''
                    target_string, ms, ms2 = None, None, None
                    if mr:
                        source_string = codecs.unicode_escape_decode(mr.group(1))[0]
                        source_strings = [source_string]
                        target_string = codecs.unicode_escape_decode(mr.group(2))[0]
                    else:
                        ms = re.match(r".*re\.sub\(r'\[([^-'\[\]]+)-([^-'\[\]]+)\]',\s*'([^']*)',", line)
                        ms2 = \
                            re.match(r".*re\.sub\(r'\(\[([^-'\[\]]+)-([^-'\[\]]+)\]\)\(([^-'\[\]]+)\)',\s*r'(\\2\\1)',",
                                     line)
                        if ms:
                            source_string_from = codecs.unicode_escape_decode(ms.group(1))[0]
                            source_string_to = codecs.unicode_escape_decode(ms.group(2))[0]
                            target_string = codecs.unicode_escape_decode(ms.group(3))[0]
                        elif ms2:
                            source_string_from = codecs.unicode_escape_decode(ms2.group(1))[0]
                            source_string_to = codecs.unicode_escape_decode(ms2.group(2))[0]
                            source_string2 = codecs.unicode_escape_decode(ms2.group(3))[0]
                            target_regex = ms2.group(4)
                        if ms or ms2:
                            if (len(source_string_from) == 1) and (len(source_string_to) == 1):
                                code_points = range(ord(source_string_from), ord(source_string_to)+1)
                                source_strings = [chr(x) for x in code_points]
                    if target_string is not None:
                        target_string = norm_string_by_mapping_dict(target_string, core_mapping_dict, wb)
                        target_string = norm_string_by_mapping_dict(target_string, mapping_dict, wb)
                    for source_string1 in source_strings:
                        out_line = ''
                        if (len(source_string1) == 1) and (safe_unicode_name(source_string1) == 'NO_NAME'):
                            continue
                        if re.search(r'[\u0080-\u009F]', source_string1) and (target_string == ''):
                            continue  # control characters in C1 block will be handled by encoding repair
                        if ms2:
                            source_string = source_string1 + source_string2
                            target_string = re.sub(r"\\1", source_string1, target_regex)
                            target_string = re.sub(r"\\2", source_string2, target_string)
                        else:
                            source_string = source_string1
                        out_line += f'{source_string}\t{target_string}'
                        mapping_dict[source_string] = target_string
                        if verbose:
                            source_comment = string_to_character_unicode_descriptions(source_string)
                            target_comment = string_to_character_unicode_descriptions(target_string, ref=source_string)
                            out_line += '\t' + source_comment + ' ' + target_comment
                            ud_ref = ud.normalize('NFKC', source_string)
                            if (ud_ref != target_string) and (target_string != ''):
                                out_line += f"   NFKC-ref: {ud_ref}"
                                if ud_ref == source_string:
                                    out_line += ' (unchanged)'
                        out_line += '\n'
                        output_lines.append(out_line)
                    if ((not source_strings)
                            and not re.search(r'(?:self\.apply_mapping_dict|\\2\\1)', line)):
                        log.info(f'Unprocessed replace/sub statement: {line.rstrip()}')
        with open(output_tsv_filename, 'w', encoding='utf-8') as f_out:
            f_out.write(head_info + '\n')
            prev_source_string = None
            n_output_lines = 0
            for output_line in sorted(set(output_lines)):
                source_string = output_line.partition('\t')[0]
                if source_string == prev_source_string:
                    log.warning(f'Duplicate source_string {source_string}')
                else:
                    prev_source_string = source_string
                f_out.write(output_line)
                n_output_lines += 1
            log.info(f'Wrote {n_output_lines} entries to {output_tsv_filename} ({n_input_lines} Python lines)')
    elif codeblock == 'EncodingRepairMapping':
        output_tsv_filename = f'../data/{output_file_basename}'
        encoding_repair_mapping_dict = {}
        # For control characters section in surrogate code block, see wildebeest_normalize.py
        # Misencodings that resulted applying conversion from wrong or double Windows1252/Latin1-to-UTF8 conversion.
        for index in range(0x80, 0x100):
            latin1_char = chr(index)
            windows1252_char = windows1252_to_utf8_char(index)
            windows1252_char2 = re.sub(r'[\u0080-\u009F]', '', windows1252_char)
            byte_string = latin1_char.encode('utf-8')
            latin1_latin1_char = ''.join([chr(x) for x in byte_string])
            replacement_char = latin1_char if index >= 0xA0 else windows1252_char2
            # to repair Latin1-to-UTF8 plus Latin1-to-UTF8
            encoding_repair_mapping_dict[latin1_latin1_char] = replacement_char
            if byte_string[1] < 0xA0:
                latin1_windows1252_char = ''.join([windows1252_to_utf8_char(x) for x in byte_string])
                # to repair Latin1-to-UTF8 plus Windows1252-to-UTF8
                encoding_repair_mapping_dict[latin1_windows1252_char] = replacement_char
            if index < 0xA0:
                # to repair Latin1-to-UTF8 instead of Windows1252-to-UTF8
                encoding_repair_mapping_dict[latin1_char] = windows1252_char2
                byte_string = windows1252_char.encode('utf-8')
                windows1252_latin1_char = ''.join([chr(x) for x in byte_string])
                # to repair Windows1252-to-UTF8 plus Latin1-to-UTF8
                encoding_repair_mapping_dict[windows1252_latin1_char] = windows1252_char2
        with open(output_tsv_filename, 'w', encoding='utf-8') as f_out:
            f_out.write(head_info + '\n')
            n_output_lines = 0
            for source_string in sorted(encoding_repair_mapping_dict.keys()):
                target_string = encoding_repair_mapping_dict[source_string]
                target_string = norm_string_by_mapping_dict(target_string, core_mapping_dict, wb)
                output_line = f'{source_string}\t{target_string}'
                if verbose:
                    output_line += '\t' + string_to_character_unicode_descriptions(source_string) + \
                                   ' ' + string_to_character_unicode_descriptions(target_string, ref=source_string)
                output_line += '\n'
                f_out.write(output_line)
                n_output_lines += 1
            log.info(f'Wrote {n_output_lines} entries to {output_tsv_filename}')
    if supplementary_code_mode in ('w', 'a'):
        output_supplementary_code_filename = '../data/supplementary_python_code.txt'
        with open(output_supplementary_code_filename, supplementary_code_mode, encoding='utf-8') as f:
            f.write(supplementary_code)


def init_core_mapping_dict() -> None:
    """Loads entries from core mapping files for recursive mapping."""
    src_dir_path = os.path.dirname(os.path.realpath(__file__))
    data_dir_path = os.path.join(src_dir_path, "../data")
    for tsv_filename in ('PythonWildebeestMapping.tsv', 'CoreCompatibilityMapping.tsv'):
        full_tsv_filename = os.path.join(data_dir_path, tsv_filename)
        filenames_considered = [full_tsv_filename]
        if not Path(full_tsv_filename).is_file():
            full_tsv_filename = os.path.join(data_dir_path, tsv_filename.replace('.tsv', 'Annotated.tsv'))
            filenames_considered += [full_tsv_filename]
        try:
            with open(full_tsv_filename, 'r', encoding='utf-8', errors='ignore') as f:
                line_number = 0
                n_entries = 0
                for line in f:
                    line_number += 1
                    tsv_list = re.split(r'\t', line.rstrip())
                    if (len(tsv_list) >= 2) and (line_number >= 2):
                        core_mapping_dict[tsv_list[0]] = tsv_list[1]
                        # log.info(f'  core_mapping_dict[{tsv_list[0]}] = {tsv_list[1]}')
                        n_entries += 1
                log.info(f'Loaded {n_entries} entries from {full_tsv_filename}')
        except FileNotFoundError:
            log.error(f"Could not open {' or '.join(filenames_considered)}")
    unicode_composition_exclusion_filename = 'UnicodeCompositionExclusions.txt'
    full_unicode_composition_exclusion_filename = os.path.join(data_dir_path, unicode_composition_exclusion_filename)
    try:
        with open(full_unicode_composition_exclusion_filename, 'r', encoding='utf-8', errors='ignore') as f:
            line_number = 0
            n_entries = 0
            for line in f:
                line_number += 1
                m = re.match(r'([0-9A-F]{4,5})\s+#\s*(\S.*\S|\S)', line, flags=re.IGNORECASE)
                if m:
                    char = chr(int(m.group(1), 16))
                    unicode_composition_exclusion_dict[char] = m.group(2)
                    n_entries += 1
                    # log.info(f'    unicode_composition_exclusion (explicit) {char} {m.group(1)} {m.group(2)}')
                    continue
                m = re.match(r'#\s*([0-9A-F]{4,5})\.\.([0-9A-F]{4,5})\s', line, flags=re.IGNORECASE)
                if m:
                    for code_point in range(int(m.group(1), 16), int(m.group(2), 16)+1):
                        char = chr(code_point)
                        unicode_composition_exclusion_dict[char] = safe_unicode_name(char)
                        n_entries += 1
                        continue
                m = re.match(r'#\s*([0-9A-F]{4,5})\s+(\S.*\S|\S)', line, flags=re.IGNORECASE)
                if m:
                    char = chr(int(m.group(1), 16))
                    unicode_composition_exclusion_dict[char] = m.group(2)
                    n_entries += 1
                    continue
            log.info(f'Loaded {n_entries} entries from {full_unicode_composition_exclusion_filename}')
    except FileNotFoundError:
        log.error(f"Could not open {full_unicode_composition_exclusion_filename}")


def compare_mappings_with_unicodedata_normalize_nfkc_on_mapping_files() -> None:
    """For testing, compares the mappings in ../data/*MappingAnnotated files with standard NFKC normalization."""
    src_dir_path = os.path.dirname(os.path.realpath(__file__))
    data_dir_path = os.path.join(src_dir_path, "../data")
    log_filename = os.path.join(data_dir_path, 'log-diff-wb-nfkc-mf.txt')
    n_files = 0
    total_n_diffs = 0
    total_n_tests = 0
    with open(log_filename, 'w', encoding='utf-8') as f_out:
        for filename in sorted(os.listdir(data_dir_path)):
            if re.match(r'.*MappingAnnotated\.tsv$', filename):
                full_filename = os.path.join(data_dir_path, filename)
                with open(full_filename, 'r', encoding='utf-8') as f_in:
                    log.info(filename)
                    f_out.write(filename + '\n')
                    n_files += 1
                    n_tests = 0
                    n_diffs = 0
                    line_number = 0
                    reverse_dict = {}
                    for line in f_in:
                        line_number += 1
                        tsv_list = re.split(r'\t', line.rstrip())
                        if (len(tsv_list) >= 2) and (line_number >= 2):
                            wb = wildebeest_normalize.Wildebeest()
                            ht = {}
                            source = tsv_list[0]
                            target = tsv_list[1]
                            reverse_dict[target] = True
                            source_wb = wb.norm_clean_string(source, ht, loc_id=str(f'{filename}.S.{line_number}'))
                            source_nfkc = ud.normalize('NFKC', source)
                            source_descr = string_to_character_unicode_descriptions(source)
                            n_tests += 1
                            total_n_tests += 1
                            if source_wb != source_nfkc:
                                if (source_wb == '') and (source_nfkc == source):
                                    annotation = 'DEL-SAME'
                                else:
                                    annotation = ''
                                n_diffs += 1
                                total_n_diffs += 1
                                f_out.write(f"{annotation}\ts:{source}\twb:{source_wb}\tnfkc:{source_nfkc}"
                                            f"\t{source_descr}\t{filename}\n")
                            elif ('Digit' in filename) or ('Python' in filename):
                                f_out.write(f"IDENTICAL\ts:{source}\twb:{source_wb}\tnfkc:{source_nfkc}"
                                            f"\t{source_descr}\t{filename}\n")
                    for target in sorted(reverse_dict.keys()):
                        if target != '':
                            target_wb = wb.norm_clean_string(target, ht, loc_id=str(f'{filename}.T.{line_number}'))
                            target_nfkc = ud.normalize('NFKC', target)
                            target_descr = string_to_character_unicode_descriptions(target)
                            n_tests += 1
                            total_n_tests += 1
                            if target_wb != target_nfkc:
                                annotation = 'REV'
                                n_diffs += 1
                                total_n_diffs += 1
                                f_out.write(f"{annotation}\ts:{target}\twb:{target_wb}\tnfkc:{target_nfkc}"
                                            f"\t{target_descr}\t{filename}\n")
                    log.info(f'    {n_diffs}/{n_tests} diffs in {filename}')
        log.info(f'{total_n_diffs}/{total_n_tests} total diffs in {n_files} files')


def compare_mappings_with_unicodedata_normalize_nfkc_on_unicode_data() -> None:
    """For testing, for all entries in UnicodeData.txt file, compare Wildebeest and NFKC."""
    src_dir_path = os.path.dirname(os.path.realpath(__file__))
    data_dir_path = os.path.join(src_dir_path, "../data")
    unicode_filename = os.path.join(data_dir_path, 'UnicodeData.txt')
    log_filename = os.path.join(data_dir_path, 'log-diff-wb-nfkc-uc.txt')
    n_diffs, n_tests, line_number = 0, 0, 0
    ht, reverse_dict = {}, {}
    wb = wildebeest_normalize.Wildebeest()
    with open(log_filename, 'w', encoding='utf-8') as f_out:
        with open(unicode_filename, 'r', encoding='utf-8') as f_in:
            for line in f_in:
                line_number += 1
                unicode_record = re.split(r';', line.rstrip())
                if len(unicode_record) >= 2:
                    # 00D4;LATIN CAPITAL LETTER O WITH CIRCUMFLEX;Lu;0;L;004F 0302;;;;N;LATIN...CIRCUMFLEX;;;00F4;
                    hex_string = unicode_record[0]     # e.g. 095F
                    source = chr(int(hex_string, 16))
                    decomp_ssv = unicode_record[5]     # e.g. '092F 093C'
                    decomp_codes = decomp_ssv.split()  # e.g. ['092F', '093C']
                    if (len(decomp_codes) >= 1) and (decomp_codes[0].startswith('<')):
                        decomp_codes = decomp_codes[1:]
                    decomp_chars = [chr(int(x, 16)) for x in decomp_codes]  # e.g. ['य', '़']
                    target = ''.join(decomp_chars)  # e.g. 'य़' (2 characters)
                    reverse_dict[target] = True
                    source_wb = wb.norm_clean_string(source, ht, loc_id=str(f'S.{line_number}'))
                    source_nfkc = ud.normalize('NFKC', source)
                    source_descr = string_to_character_unicode_descriptions(source)
                    n_tests += 1
                    if ((assert_wb_dict.get(source, None) == source_wb)
                            and (assert_nfkc_dict.get(source, None) == source_nfkc)):
                        continue
                    elif source_wb != source_nfkc:
                        if (source_wb == '') and (source_nfkc == source):
                            annotation = 'DEL-SAME'
                        else:
                            annotation = ''
                        n_diffs += 1
                        f_out.write(f"{annotation}\ts:{source}\twb:{source_wb}\tnfkc:{source_nfkc}\t{source_descr}\n")
            for target in sorted(reverse_dict.keys()):
                if target != '':
                    target_wb = wb.norm_clean_string(target, ht, loc_id=str(f'T.{line_number}'))
                    target_nfkc = ud.normalize('NFKC', target)
                    target_descr = string_to_character_unicode_descriptions(target)
                    n_tests += 1
                    if target_wb != target_nfkc:
                        if (target_wb == '') and (target_nfkc == target):
                            annotation = "REV DEL-SAME"
                        else:
                            annotation = 'REV'
                        n_diffs += 1
                        f_out.write(f"{annotation}\ts:{target}\twb:{target_wb}\tnfkc:{target_nfkc}\t{target_descr}\n")
        log.info(f'{n_diffs}/{n_tests} total diffs in {line_number} lines')


def mapping_to_assert_orig_wb_nfkc(filename_i: str, filename_o: str) -> None:
    """
    For testing, build initial draft for an assert.tsv file, which serves as a basis of manual verification.
    Example input filename: ../data/ArabicPresentationFormMappingAnnotated.tsv
    Example output filename: ../data/assert-ArabicPresentationForm.tsv
    """
    log.info(f'assert {filename_i} -> {filename_o}')
    line_number, n_output_lines = 0, 0
    with open(filename_o, 'w', encoding='utf-8') as f_out:
        with open(filename_i, 'r', encoding='utf-8') as f_in:
            for line in f_in:
                line_number += 1
                record = re.split(r'\t', line.rstrip())
                if len(record) >= 3:
                    orig = record[0]
                    wb = record[1]
                    comment = re.sub(r'\s*NFKC-ref.*$', '', record[2])
                    nfkc = ud.normalize('NFKC', orig)
                    if wb != nfkc:
                        f_out.write(f'{orig}\t{wb}\t{nfkc}\t{comment}\n')
                        n_output_lines += 1
    log.info(f'    {line_number} input lines, {n_output_lines} output lines')


def addenda_to_assert_orig_wb_nfkc(filename_i: str, filename_o: str, filename_ref: str,
                                   preservation_category: str = '') -> None:
    """
    Based on manual code point input, build additional assert records for files assert.tsv or assert-preserve.tsv
    filename_ref: with entries that have already been asserted, no need to duplicate
    """
    log.info(f'assert {filename_i} -> {filename_o}')

    valid_preservation_categories = ['SUPERSCRIPT', 'SUBSCRIPT', 'FRACTION', 'RADICAL', 'DIACRITIC']
    if filename_i == 'STDIN':
        if preservation_category == 'PROMPT':
            preservation_category = input(f"Enter preservation category ({'|'.join(valid_preservation_categories)}): ")
        f_in = sys.stdin
        sys.stderr.write('Enter you hex codepoints:\n')
    else:
        f_in = open(filename_i, 'r', encoding='utf-8')
    if (preservation_category != '') and (preservation_category not in valid_preservation_categories):
        log.error(f'Invalid preservation_category {preservation_category}')
        return
    wb = wildebeest_normalize.Wildebeest()
    ht = {}
    pre_existing_dict = {}
    line_number = 0
    with open(filename_ref, 'r', encoding='utf-8') as f_ref:
        for line in f_ref:
            line_number += 1
            if line_number >= 2:
                record = re.split(r'\t', line.rstrip())
                pre_existing_dict[record[0]] = record[1]
    line_number, n_output_lines = 0, 0
    with open(filename_o, 'w', encoding='utf-8') as f_out:
        for line in f_in:
            line = line.rstrip()
            if line == '':
                break
            line_number += 1
            cp_elem_list = re.split(r'(?:,\s*|\s+)', line.rstrip())
            for cp_elem in cp_elem_list:
                if '-' in cp_elem:
                    cp_elem_from_to = re.split('-', cp_elem)
                    cp_elem_from = cp_elem_from_to[0].lstrip('\\uU+0x')
                    cp_elem_to = cp_elem_from_to[1].lstrip('\\uU+0x')
                    cp_list = range(int(cp_elem_from, 16), int(cp_elem_to, 16) + 1)
                else:
                    cp_list = [int(cp_elem.lstrip('\\uU+0x'), 16)]
                for code_point in cp_list:
                    char = chr(code_point)
                    decomp_wb = wb.norm_clean_string(char, ht)
                    decomp_nfkc = ud.normalize('NFKC', char)
                    if ((char not in pre_existing_dict)
                            and (decomp_wb != decomp_nfkc)
                            and ((preservation_category == '') or (char == decomp_wb))):
                        char_descr = string_to_character_unicode_descriptions(char)
                        decomp_descr = string_to_character_unicode_descriptions(decomp_wb, ref=char)
                        comment = (char_descr + ' ' + decomp_descr + ' ' + preservation_category).rstrip()
                        sys.stderr.write(f'{char}\t{decomp_wb}\t{decomp_nfkc}\t{comment}\n')
                        f_out.write(f'{char}\t{decomp_wb}\t{decomp_nfkc}\t{comment}\n')
                        n_output_lines += 1
    if filename_i:
        f_in.close()
    log.info(f'    {line_number} input lines, {n_output_lines} output lines')


def load_assert_files() -> None:
    src_dir_path = os.path.dirname(os.path.realpath(__file__))
    data_dir_path = os.path.join(src_dir_path, "../data")
    assert_filename = os.path.join(data_dir_path, 'assert.tsv')
    assert_preserve_filename = os.path.join(data_dir_path, 'assert-preserve.tsv')
    for filename in [assert_filename, assert_preserve_filename]:
        line_number = 0
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                line_number += 1
                record = re.split(r'\t', line.rstrip())
                if (line_number >= 2) and (len(record) >= 4):
                    orig = record[0]
                    wb = record[1]
                    nfkc = record[2]
                    assert_wb_dict[orig] = wb
                    assert_nfkc_dict[orig] = nfkc
        log.info(f'Loaded {line_number} entries from {filename}')


def rebuild_all_mapping_files() -> None:
    src_dir_path = os.path.dirname(os.path.realpath(__file__))
    data_dir_path = os.path.join(src_dir_path, "../data")
    n_files = 0
    for filename in sorted(os.listdir(data_dir_path)):
        if re.match(r'.*MappingAnnotated\.tsv$', filename):
            codeblock = filename.replace('Annotated.tsv', '')
            log.info(f'Rebuilding {codeblock}')
            build_wildebeest_tsv_file(codeblock)
            n_files += 1
    log.info(f'Rebuilt {n_files} mapping files')


def main(argv):
    init_core_mapping_dict()
    load_assert_files()
    if (len(argv) >= 2) and (argv[0] == 'python-code'):
        codeblock = argv[1]  # e.g. 'Devanagari', 'Indic', 'Arabic'
        build_python_code_from_unicode(codeblock)
    elif (len(argv) >= 2) and (argv[0] == 'tsv-file'):
        codeblock = argv[1]  # e.g. 'ArabicPresentationFormMapping'
        build_wildebeest_tsv_file(codeblock)
    elif (len(argv) >= 1) and (argv[0] == 'rebuild-all-mapping-files'):
        rebuild_all_mapping_files()
    elif (len(argv) >= 1) and (argv[0] == 'compare-wb-nfkc-mf'):
        compare_mappings_with_unicodedata_normalize_nfkc_on_mapping_files()
    elif (len(argv) >= 1) and (argv[0] == 'compare-wb-nfkc-uc'):
        compare_mappings_with_unicodedata_normalize_nfkc_on_unicode_data()
    elif (len(argv) >= 3) and (argv[0] == 'mapping-to-assert-orig-wb-nfkc'):
        mapping_to_assert_orig_wb_nfkc(argv[1], argv[2])
    elif (len(argv) >= 4) and (argv[0] == 'addenda-to-assert-orig-wb-nfkc'):
        addenda_to_assert_orig_wb_nfkc(argv[1], argv[2], argv[3])
    elif (len(argv) >= 4) and (argv[0] == 'addenda-to-assert-preserve-orig-wb-nfkc'):
        addenda_to_assert_orig_wb_nfkc(argv[1], argv[2], argv[3], preservation_category='PROMPT')


if __name__ == "__main__":
    main(sys.argv[1:])
