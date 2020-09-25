"""
Written by Ulf Hermjakob, USC/ISI
This file contains functions that build UnicodeData-based data tables or Python code lines for wildebeest.py
"""

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


def build_wildebeest_tsv_file(codeblock: str, add_info_field_to_tsv_file_p: bool = True) -> None:
    """
    This function builds tsv files in the data directory that map from non-standard encoding (first field)
    to standard encoding (second field).
    """
    if codeblock == 'Arabic presentation forms':  # includes Arabic ligatures
        output_tsv_filename = '../data/ArabicPresentationForms.tsv'
        n_output_lines = 0
        with open(output_tsv_filename, 'w', encoding='utf-8') as f:
            for code_point in chain(range(0xFB50, 0xFE00), range(0xFE70, 0xFF00)):
                non_standard_char = chr(code_point)
                decomp_ssv = ud.decomposition(non_standard_char)
                if decomp_ssv:
                    decomp_elements = decomp_ssv.split()
                    if (len(decomp_elements) >= 2) \
                            and (decomp_elements[0] in ['<initial>', '<medial>', '<final>', '<isolated>']):
                        standard_string = ''.join([chr(int(x, 16)) for x in decomp_elements[1:]])
                        if add_info_field_to_tsv_file_p:
                            hex_str = ('%04x' % code_point).upper()
                            non_standard_char_name = ud.name(non_standard_char, '')
                            f.write(f"{non_standard_char}\t{standard_string}\tU+{hex_str} {non_standard_char_name}\n")
                        else:
                            f.write(f"{non_standard_char}\t{standard_string}\n")
                        n_output_lines += 1
        log.info(f'Wrote {n_output_lines} to {output_tsv_filename}')


def main(argv):
    if (len(argv) >= 2) and (argv[0] == 'python-code'):
        codeblock = argv[1]  # e.g. 'Devanagari', 'Indic', 'Arabic'
        build_python_code_from_unicode(codeblock)
    elif (len(argv) >= 2) and (argv[0] == 'tsv-file'):
        codeblock = argv[1]  # e.g. 'Arabic presentation forms'
        build_wildebeest_tsv_file(codeblock)


if __name__ == "__main__":
    main(sys.argv[1:])
