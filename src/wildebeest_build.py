"""
Written by Ulf Hermjakob, USC/ISI
This file contains functions that build UnicodeData-based data tables or Python code lines for wildebeest.py
"""

from datetime import datetime
from itertools import chain
import logging as log
import re
import unicodedata as ud
import sys

log.basicConfig(level=log.INFO)


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
    if codeblock == 'Devanagari':
        code_points = range(0x0900, 0x0980)
        decomposition_exclusions = range(0x0958, 0x0960)
    elif codeblock == 'Indic':
        code_points = range(0x0900, 0x0E00)
        decomposition_exclusions = range(0x0958, 0x0960)  # probably incomplete
    elif codeblock == 'Arabic':
        code_points = range(0x0600, 0x0700)
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


def build_wildebeest_tsv_file(codeblock: str, verbose: bool = True, supplementary_code_mode: str = 'w') -> None:
    """
    This function builds tsv files in the data directory that map from non-standard encoding (first field)
    to standard encoding (second field).
    """
    timestamp = datetime.now().strftime("%b %d, %Y, %H:%M:%S")
    output_file_basename = f"{codeblock}{'Annotated' if verbose else ''}.tsv"
    head_info = f'MapFromString\tMapToString\tComment # File {output_file_basename}, automatically generated by' \
                f' script wildebeest_build.py (Ulf Hermjakob, USC/ISI) based on UnicodeData on {timestamp}\n'
    supplementary_code = ''
    if codeblock in ('ArabicPresentationFormMapping',  # includes Arabic ligatures
                     'DigitMapping'):
        if codeblock == 'ArabicPresentationFormMapping':
            code_points = chain(range(0xFB50, 0xFE00), range(0xFE70, 0xFF00))
        else:
            code_points = chain(range(0x0000, 0x3400), range(0xA000, 0xAC00), range(0xF900, 0x18D00),
                                range(0x1B000, 0x1B300), range(0x1BC00, 0x1BD00), range(0x1D000, 0x1FC00),
                                range(0x2F800, 0x2FA20), range(0xE0000, 0xE0200))
        output_tsv_filename = f'../data/{output_file_basename}'
        n_output_lines = 0

        with open(output_tsv_filename, 'w', encoding='utf-8') as f:
            f.write(head_info)
            for code_point in code_points:
                char = chr(code_point)
                decomp_ssv = ud.decomposition(char)
                action = ''
                if decomp_ssv:
                    decomp_elements = decomp_ssv.split()
                    if (codeblock == 'ArabicPresentationFormMapping') \
                            and (len(decomp_elements) >= 2) \
                            and (decomp_elements[0] in ['<initial>', '<medial>', '<final>', '<isolated>']):
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
                        decomp_chars = [('%04x' % (digit + 0x0030)).upper()]
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
                            supplementary_code += f"    s = re.sub(r'{unicode_range}', self.map_encoding_char, s)"
                            if char_name.endswith(char_name_suffix):
                                supplementary_code += f"    # {char_name[:-len(char_name_suffix)]} digits\n"
                            else:
                                supplementary_code += '\n'
                if action and verbose:
                    char_name = ud.name(char, None)
                    char_name_clause = f' ({char_name})' if char_name else ''
                    char_hex = 'U+' + ('%04x' % code_point).upper()
                    decomp_hex = ' '.join([('U+' + x) for x in decomp_chars])
                if action == 'decomposition':
                    f.write(char + '\t' + decomp_str)
                    if verbose:
                        f.write(f'\t{char_hex}{char_name_clause} -> {decomp_hex}')
                    f.write('\n')
                    n_output_lines += 1
                elif action == 'composition':
                    f.write(decomp_str + '\t' + char)
                    if verbose:
                        f.write(f'\t{decomp_hex} -> {char_hex}{char_name_clause}')
                    f.write('\n')
                    n_output_lines += 1
        log.info(f'Wrote {n_output_lines} entries to {output_tsv_filename}')
    if supplementary_code_mode in ('w', 'a'):
        output_supplementary_code_filename = '../data/supplementary_python_code.txt'
        with open(output_supplementary_code_filename, supplementary_code_mode, encoding='utf-8') as f:
            f.write(supplementary_code)


def main(argv):
    if (len(argv) >= 2) and (argv[0] == 'python-code'):
        codeblock = argv[1]  # e.g. 'Devanagari', 'Indic', 'Arabic'
        build_python_code_from_unicode(codeblock)
    elif (len(argv) >= 2) and (argv[0] == 'tsv-file'):
        codeblock = argv[1]  # e.g. 'ArabicPresentationFormMapping'
        build_wildebeest_tsv_file(codeblock)


if __name__ == "__main__":
    main(sys.argv[1:])
