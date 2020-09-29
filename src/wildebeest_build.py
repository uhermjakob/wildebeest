"""
Written by Ulf Hermjakob, USC/ISI
This file contains functions that build UnicodeData-based data tables or Python code lines for wildebeest.py
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

log.basicConfig(level=log.INFO)

mapping_dict = {}        # general dict used to build Mapping.tsv files
core_mapping_dict = {}   # special dict for PythonWildebeest and CoreCompatibility mappings

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
        if ((codeblock == 'ligature')
                and (  # (not decomp_ssv.startswith('<compat>'))
                       # or
                     (not ('SYMBOL' in char_name)))):
            continue
        decomp_ssv = re.sub(r'<.*?>\s*', '', decomp_ssv)  # remove decomp type info, e.g. <compat>, <isolated>
        if decomp_ssv:
            # log.info(f'{uplus} decomp_ssv: {decomp_ssv}')
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
        digit = ud.digit(char, '')
        if digit != '':
            #   s = s.replace('\u0967', '1')    # U+0967 DEVANAGARI DIGIT ONE १ -> 1
            print(f"{indent}s = s.replace('{us}', '{digit}')    # {uplus} {char_name} {char} -> {digit}")


def norm_string_by_mapping_dict(s: str, m_dict: dict, verbose: bool = True) -> str:
    """Function greedily applies character-based mapping-dictionary to string."""
    result = ''
    i, n = 0, len(s)
    while i < n:
        for l in (3, 2, 1):
            sub_map = m_dict.get(s[i:i+l])
            if sub_map:
                result += sub_map
                i += l
                break
        if sub_map is None:
            result += s[i:i+1]
            i += 1
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
    char_name = ud.name(char, None)
    if char_name is None:
        if ud.category(char) == 'Cc':
            char_name = 'Control character'
        else:
            char_name = 'NO_NAME'
    return char_name


def string_to_character_unicode_descriptions(s: str) -> str:
    """Map"""
    return " ".join([f"U+{('%04x' % ord(char)).upper()} ({safe_unicode_name(char)})" for char in s])


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
    if codeblock in ('ArabicPresentationFormMapping',  # includes Arabic ligatures
                     'CJKCompatibilityMapping',        # includes IDEOGRAPHIC TELEGRAPH SYMBOL FOR months
                     'CombiningModifierMapping',       # e.g. maps "é" (2 Unicode characters) to "é" (1 character)
                     'CoreCompatibilityMapping',       # includes Hangul compatibility (KS X 1001)
                     'DigitMapping',
                     'FontSmallVerticalMapping'):      # for Unicode keywords <font>, <small>, <vertical>
        if codeblock == 'ArabicPresentationFormMapping':
            code_points = chain(range(0xFB50, 0xFE00), range(0xFE70, 0xFF00))
        elif codeblock == 'CJKCompatibilityMapping':
            code_points = chain(range(0x32C0, 0x3400), range(0xFF01, 0xFFEF))
        elif codeblock == 'CoreCompatibilityMapping':
            code_points = chain(range(0x3130, 0x3190))
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
                            and (len(decomp_elements) >= 2)
                            and (decomp_elements[0] in ['<compat>', '<square>', '<wide>', '<narrow>'])):
                        decomp_chars = decomp_elements[1:]
                        decomp_str = ''.join([chr(int(x, 16)) for x in decomp_chars])
                        decomp_str = decomp_str.replace('\u2113', 'l')  # map ℓ (script small l) to regular l (as in ml)
                        action = 'decomposition'
                    elif ((codeblock == 'CombiningModifierMapping')
                            and (len(decomp_elements) >= 2)
                            and (not decomp_elements[0].startswith('<'))):
                        decomp_char1 = chr(int(decomp_elements[1], 16))
                        decomp_char1_name = ud.name(decomp_char1, '')
                        decomp_chars = decomp_elements
                        decomp_str = ''.join([chr(int(x, 16)) for x in decomp_chars])
                        if ((len(decomp_elements) == 2)
                                and (('COMBINING' in decomp_char1_name)
                                     or re.match(r'[\u0653-\u0655]', decomp_char1))):
                            action = 'composition'
                        else:
                            char_descr = string_to_character_unicode_descriptions(char)
                            decomp_descr = string_to_character_unicode_descriptions(decomp_str)
                            log.info(f'{codeblock}: No entry added for {char} {char_descr}'
                                     f' -> {decomp_str} {decomp_descr}')
                    elif ((codeblock == 'CoreCompatibilityMapping')
                            and (len(decomp_elements) >= 2)
                            and (decomp_elements[0] == '<compat>')):
                        decomp_chars = decomp_elements[1:]
                        decomp_str = ''.join([chr(int(x, 16)) for x in decomp_chars])
                        action = 'decomposition'
                    elif ((codeblock == 'FontSmallVerticalMapping')
                            and (len(decomp_elements) >= 2)
                            and (decomp_elements[0] in ['<font>', '<small>', '<vertical>'])):
                        decomp_chars = decomp_elements[1:]
                        decomp_str = ''.join([chr(int(x, 16)) for x in decomp_chars])
                        action = 'decomposition'
                elif codeblock == 'DigitMapping':
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
                        if (digit == 0) and supplementary_code_mode:
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
                        decomp_str = norm_string_by_mapping_dict(decomp_str, core_mapping_dict)
                    elif action == 'composition':
                        char = norm_string_by_mapping_dict(char, core_mapping_dict)
                    decomp_descr = string_to_character_unicode_descriptions(decomp_str)
                if action == 'decomposition':
                    f.write(char + '\t' + decomp_str)
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
        output_tsv_filename = f'../data/{output_file_basename}'
        n_input_lines = 0
        output_lines = []
        current_function_name = ''
        with open('wildebeest.py', 'r', encoding='utf-8') as f_in:
            for line in f_in:
                n_input_lines += 1
                if re.match(r'\s*#', line):
                    continue  # skip comment line
                mf = re.match(r'.*def\s+([_a-zA-Z0-9]+)', line)
                if mf:
                    current_function_name = mf.group(1)
                elif current_function_name in ['normalize_farsi_characters', 'normalize_ring_characters',
                                               'normalize_arabic_punctuation', 'normalize_font_characters',
                                               'repair_tokenization', 'repair_xml', 'delete_surrogates',
                                               'init_mapping_dict']:
                    continue  # because replacements are language-specific
                elif re.search(r'(?:\.replace|re\.sub)\(', line):
                    mr = re.match(r".*\.replace\('([^']+)',\s*'([^']*)'\)", line)
                    source_strings = []
                    target_string = None
                    if mr:
                        source_string = codecs.unicode_escape_decode(mr.group(1))[0]
                        source_strings = [source_string]
                        target_string = codecs.unicode_escape_decode(mr.group(2))[0]
                    else:
                        ms = re.match(r".*re\.sub\(r'\[([^-'\[\]]+)-([^-'\[\]]+)\]',\s*'([^']*)',", line)
                        if ms:
                            source_string_from = codecs.unicode_escape_decode(ms.group(1))[0]
                            source_string_to = codecs.unicode_escape_decode(ms.group(2))[0]
                            target_string = codecs.unicode_escape_decode(ms.group(3))[0]
                            if (len(source_string_from) == 1) and (len(source_string_to) == 1):
                                code_points = range(ord(source_string_from), ord(source_string_to)+1)
                                source_strings = [chr(x) for x in code_points]
                    if target_string is not None:
                        target_string = norm_string_by_mapping_dict(target_string, core_mapping_dict)
                        target_string = norm_string_by_mapping_dict(target_string, mapping_dict)
                    for source_string in source_strings:
                        out_line = ''
                        if re.search(r'[\u0080-\u009F]', source_string) and (target_string == ''):
                            continue  # control characters in C1 block will be handled by encoding repair
                        out_line += f'{source_string}\t{target_string}'
                        mapping_dict[source_string] = target_string
                        if verbose:
                            source_comment = ''
                            target_comment = ''
                            if len(source_string) == 1:
                                source_comment = string_to_character_unicode_descriptions(source_string)
                            if len(target_string) == 1:
                                target_comment = string_to_character_unicode_descriptions(target_string)
                            out_line += '\t'
                            if source_comment or target_comment:
                                if source_comment:
                                    out_line += source_comment + ' '
                                if target_comment:
                                    out_line += '-> ' + target_comment
                                elif source_comment and (len(target_string) == 0):
                                    out_line += 'deleted'
                                elif source_comment and (len(target_string) >= 2):
                                    out_line += 'decomposed'
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
        # For control characters section in surrogate code block, see wildbeest.py
        # Misencodings that resulted applying conversion from wrong or double Windows1252/Latin1-to-UTF8 conversion.
        for index in range(0x80, 0x100):
            latin1_char = chr(index)
            windows1252_char = windows1252_to_utf8_char(index)
            windows1252_char2 = re.sub(r'[\u0080-\u009F]', '', windows1252_char)
            byte_string = latin1_char.encode('utf-8')
            latin1_latin1_char = ''.join([chr(x) for x in byte_string])
            repl_char = latin1_char if index >= 0xA0 else windows1252_char2
            # to repair Latin1-to-UTF8 plus Latin1-to-UTF8
            encoding_repair_mapping_dict[latin1_latin1_char] = repl_char
            if byte_string[1] < 0xA0:
                latin1_windows1252_char = ''.join([windows1252_to_utf8_char(x) for x in byte_string])
                # to repair Latin1-to-UTF8 plus Windows1252-to-UTF8
                encoding_repair_mapping_dict[latin1_windows1252_char] = repl_char
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
                output_line = f'{source_string}\t{target_string}'
                if verbose:
                    output_line += '\t' + string_to_character_unicode_descriptions(source_string)
                    if target_string == '':
                        output_line += ' deleted'
                    else:
                        output_line += ' -> ' + string_to_character_unicode_descriptions(target_string)
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


def main(argv):
    init_core_mapping_dict()
    if (len(argv) >= 2) and (argv[0] == 'python-code'):
        codeblock = argv[1]  # e.g. 'Devanagari', 'Indic', 'Arabic'
        build_python_code_from_unicode(codeblock)
    elif (len(argv) >= 2) and (argv[0] == 'tsv-file'):
        codeblock = argv[1]  # e.g. 'ArabicPresentationFormMapping'
        build_wildebeest_tsv_file(codeblock)


if __name__ == "__main__":
    main(sys.argv[1:])
