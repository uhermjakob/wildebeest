"""
Written by Ulf Hermjakob, USC/ISI
Ported from Perl to Python on August 27, 2020.
This script normalizes and cleans text (details below).
Examples:
  norm_clean_text.py -h  # for full usage info
  norm_clean_text.py --version
  norm_clean_text.py --lc fas -i 3S-dev-ssplit.src.tok -o 3S-dev-ssplit.src.clean2.tok
  norm_clean_text.py --lc fas --verbose --skip digit,norm-punct < 3S-dev-ssplit.src.tok > 3S-dev-ssplit.src.clean1.tok
List of available normalization/cleaning-types (default: all are applied):
 * repair-windows-1252 (maps characters encoded in Windows-1252 to UTF8)
 * del-surrogate (deletes surrogate characters (representing non-UTF8 characters in input),
        alternative/backup to windows-1252)
 * del-ctrl-char (deletes control characters (expect tab and linefeed), zero-width characters, byte order mark,
        directional marks, join marks, variation selectors, Arabic tatweel)
 * farsi-char-norm (e.g. maps Arabic yeh, kaf to Farsi versions)
 * pres-form-norm (e.g. maps from presentation form (isolated, initial, medial, final) to standard form)
 * ring-char-norm (e.g. maps ring-characters that are common in Pashto to non-ring characters)
 * del-diacr (e.g. deletes diacritics such as Arabic fatha, damma, kasra)
 * indic-diacr (e.g. canonical form of composed/decomposed Indic characters; order nukta/vowel-sign)
 * digit (e.g. maps Arabic-Indic digits and extended Arabic-Indic digits to ASCII digits)
 * norm-punct (e.g. maps Arabic exlamation mark etc. to ASCII equivalent)
 * repair-token (e.g. splits +/-/*/digits off Arabic words; maps not-sign inside Arabic to token-separating hyphen)
When using STDIN and/or STDOUT, if might be necessary, particularly for older versions of Python, to do
'export PYTHONIOENCODING=UTF-8' before calling this Python script to ensure UTF-8 encoding.
"""
# -*- encoding: utf-8 -*-
import argparse
import logging as log
import re
import sys
import unicodedata as ud
from typing import Callable, Match, TextIO

log.basicConfig(level=log.INFO)

__version__ = '0.4.2'
last_mod_date = 'September 21, 2020'


def reg_surrogate_to_utf8(match: Match[str]) -> str:
    # Map surrogate character (U+DCA0 - U+DCFF) to Latin+ characters (U+00A0-U+00FF)
    s = match.group()
    return chr(ord(s[0]) - 0xDC00)


def repair_windows1252(s: str, undef_default: str = '') -> str:
    """Interpret non-UTF8 characters (read in as surrogate characters \uDC80-\uDCFF]) as Windows 1252 characters."""
    if re.search(r"[\uDC80-\uDCFF]", s):
        if re.search(r"[\uDC80-\uDC9F]", s):
            s = s.replace('\uDC80', '\u20AC')  # Euro Sign
            # \81 unassigned in Windows-1252
            s = s.replace('\uDC82', '\u201A')  # Single Low-9 Quotation Mark
            s = s.replace('\uDC83', '\u0192')  # Latin Small Letter F With Hook
            s = s.replace('\uDC84', '\u201E')  # Double Low-9 Quotation Mark
            s = s.replace('\uDC85', '\u2026')  # Horizontal Ellipsis
            s = s.replace('\uDC86', '\u2020')  # Dagger
            s = s.replace('\uDC87', '\u2021')  # Double Dagger
            s = s.replace('\uDC88', '\u02C6')  # Modifier Letter Circumflex Accent
            s = s.replace('\uDC89', '\u2030')  # Per Mille Sign
            s = s.replace('\uDC8A', '\u0160')  # Latin Capital Letter S With Caron
            s = s.replace('\uDC8B', '\u2039')  # Single Left-Pointing Angle Quotation Mark
            s = s.replace('\uDC8C', '\u0152')  # Latin Capital Ligature OE
            # \8D unassigned in Windows-1252
            s = s.replace('\uDC8E', '\u017D')  # Latin Capital Letter Z With Caron
            # \8F unassigned in Windows-1252
            # \90 unassigned in Windows-1252
            s = s.replace('\uDC91', '\u2018')  # Left Single Quotation Mark
            s = s.replace('\uDC92', '\u2019')  # Right Single Quotation Mark
            s = s.replace('\uDC93', '\u201C')  # Left Double Quotation Mark
            s = s.replace('\uDC94', '\u201D')  # Right Double Quotation Mark
            s = s.replace('\uDC95', '\u2022')  # Bullet
            s = s.replace('\uDC96', '\u2013')  # En Dash
            s = s.replace('\uDC97', '\u2014')  # Em Dash
            s = s.replace('\uDC98', '\u02DC')  # Small Tilde
            s = s.replace('\uDC99', '\u2122')  # Trade Mark Sign
            s = s.replace('\uDC9A', '\u0161')  # Latin Small Letter S With Caron
            s = s.replace('\uDC9B', '\u203A')  # Single Right-Pointing Angle Quotation Mark
            s = s.replace('\uDC9C', '\u0153')  # Latin Small Ligature OE
            # \9D unassigned in Windows-1252
            s = s.replace('\uDC9E', '\u017E')  # Latin Small Letter Z With Caron
            s = s.replace('\uDC9F', '\u0178')  # Latin Capital Letter Y With Diaeresis
            s = re.sub(r'[\uDC80-\uDC9F]', undef_default, s)  # for undefined Windows 1252 codepoints (81,8D,8F,90,9D)
        s = re.sub(r'[\uDCA0-\uDCFF]', reg_surrogate_to_utf8, s)
    return s


def delete_control_characters(s: str) -> str:
    """Deletes control chacters (except tab and linefeed), zero-width characters, byte order mark,
       directional marks, join marks, variation selectors, Arabic tatweel"""
    s = re.sub(r'[\u0000-\u0008\u000B-\u001F\u007F-\u009F]', '', s)  # control characters (except tab x9, linefeed xA)
    s = s.replace('\u0640', '')                       # Arabic tatweel
    s = re.sub(r'[\u200B-\u200F]', '', s)             # zero width space/non-joiner/joiner, direction marks
    s = re.sub(r'[\uFE00-\uFE0F]', '', s)             # variation selectors 1-16
    s = s.replace('\uFEFF', '')                       # byte order mark, zero width no-break space
    s = re.sub(r'[\U000E0100-\U000E01EF]', '', s)     # variation selectors 17-256
    return s


def delete_surrogates(s: str, default: str = '') -> str:
    """As an alternative or backup to windows1252_to_utf8, delete all surrogate characters \uDC80-\uDCFF])."""
    return re.sub(r"[\uDC80-\uDCFF]", default, s)


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


def normalize_farsi_characters(s: str) -> str:
    s = s.replace('\u064A', '\u06CC')  # Arabic to Farsi yeh
    s = s.replace('\u0649', '\u06CC')  # Arabic alef maksura to Farsi yeh
    s = s.replace('\u06CD', '\u06CC')  # Arabic yeh with tail to Farsi yeh
    s = s.replace('\u0643', '\u06A9')  # Arabic kaf to keheh
    return s


def normalize_ring_characters(s: str) -> str:
    s = s.replace('\u06AB', '\u06AF')  # Arabic kaf with ring to gaf
    s = s.replace('\u067C', '\u062A')  # Arabic teh with ring to Arabic teh
    s = s.replace('\u0689', '\u062F')  # Arabic dal with ring to Arabic dal
    s = s.replace('\u0693', '\u0631')  # Arabic reh with ring to Arabic reh
    return s


def normalize_arabic_pres_form_characters(s: str) -> str:
    if re.search(r"[\uFB50-\uFEFC]", s):
        s = s.replace('\uFB56', '\u067E')  # U+FB56 peh isolated form
        s = s.replace('\uFB57', '\u067E')  # U+FB57 peh final form
        s = s.replace('\uFB58', '\u067E')  # U+FB58 peh initial form
        s = s.replace('\uFB59', '\u067E')  # U+FB59 peh medial form
        s = s.replace('\uFB7A', '\u0686')  # U+FB7A tcheh isolated form
        s = s.replace('\uFB7B', '\u0686')  # U+FB7B tcheh final form
        s = s.replace('\uFB7C', '\u0686')  # U+FB7C tcheh initial form
        s = s.replace('\uFB7D', '\u0686')  # U+FB7D tcheh medial form
        s = s.replace('\uFB8A', '\u0698')  # U+FB8A jeh isolated form
        s = s.replace('\uFB8B', '\u0698')  # U+FB8B jeh final form
        s = s.replace('\uFB8E', '\u06A9')  # U+FB8E keheh isolated form
        s = s.replace('\uFB8F', '\u06A9')  # U+FB8F keheh final form
        s = s.replace('\uFB90', '\u06A9')  # U+FB90 keheh initial form
        s = s.replace('\uFB91', '\u06A9')  # U+FB91 keheh medial form
        s = s.replace('\uFB92', '\u06AF')  # U+FB92 gaf isolated form
        s = s.replace('\uFB93', '\u06AF')  # U+FB93 gaf final form
        s = s.replace('\uFB94', '\u06AF')  # U+FB94 gaf initial form
        s = s.replace('\uFB95', '\u06AF')  # U+FB95 gaf medial form
        s = s.replace('\uFBE4', '\u06D0')  # U+FBE4 e isolated form
        s = s.replace('\uFBE5', '\u06D0')  # U+FBE5 e final form
        s = s.replace('\uFBE6', '\u06D0')  # U+FBE6 e initial form
        s = s.replace('\uFBE7', '\u06D0')  # U+FBE7 e medial form
        s = s.replace('\uFBFC', '\u06CC')  # U+FBFC Farsi yeh isolated form
        s = s.replace('\uFBFD', '\u06CC')  # U+FBFD Farsi yeh final form
        s = s.replace('\uFBFE', '\u06CC')  # U+FBFE Farsi yeh initial form
        s = s.replace('\uFBFF', '\u06CC')  # U+FBFF Farsi yeh medial form
        s = s.replace('\uFE80', '\u0621')  # U+FE80 hamza isolated form
        s = s.replace('\uFE81', '\u0622')  # U+FE81 alef with madda above isolated form
        s = s.replace('\uFE82', '\u0622')  # U+FE82 alef with madda above final form
        s = s.replace('\uFE83', '\u0623')  # U+FE83 alef with hamza above isolated form
        s = s.replace('\uFE84', '\u0623')  # U+FE84 alef with hamza above final form
        s = s.replace('\uFE85', '\u0624')  # U+FE85 waw with hamza above isolated form
        s = s.replace('\uFE86', '\u0624')  # U+FE86 waw with hamza above final form
        s = s.replace('\uFE87', '\u0625')  # U+FE87 alef with hamza below isolated form
        s = s.replace('\uFE88', '\u0625')  # U+FE88 alef with hamza below final form
        s = s.replace('\uFE89', '\u0626')  # U+FE89 yeh with hamza above isolated form
        s = s.replace('\uFE8A', '\u0626')  # U+FE8A yeh with hamza above final form
        s = s.replace('\uFE8B', '\u0626')  # U+FE8B yeh with hamza above initial form
        s = s.replace('\uFE8C', '\u0626')  # U+FE8C yeh with hamza above medial form
        s = s.replace('\uFE8D', '\u0627')  # U+FE8D alef isolated form
        s = s.replace('\uFE8E', '\u0627')  # U+FE8E alef final form
        s = s.replace('\uFE8F', '\u0628')  # U+FE8F beh isolated form
        s = s.replace('\uFE90', '\u0628')  # U+FE90 beh final form
        s = s.replace('\uFE91', '\u0628')  # U+FE91 beh initial form
        s = s.replace('\uFE92', '\u0628')  # U+FE92 beh medial form
        s = s.replace('\uFE93', '\u0629')  # U+FE93 teh marbuta isolated form
        s = s.replace('\uFE94', '\u0629')  # U+FE94 teh marbuta final form
        s = s.replace('\uFE95', '\u062A')  # U+FE95 teh isolated form
        s = s.replace('\uFE96', '\u062A')  # U+FE96 teh final form
        s = s.replace('\uFE97', '\u062A')  # U+FE97 teh initial form
        s = s.replace('\uFE98', '\u062A')  # U+FE98 teh medial form
        s = s.replace('\uFE99', '\u062B')  # U+FE99 theh isolated form
        s = s.replace('\uFE9A', '\u062B')  # U+FE9A theh final form
        s = s.replace('\uFE9B', '\u062B')  # U+FE9B theh initial form
        s = s.replace('\uFE9C', '\u062B')  # U+FE9C theh medial form
        s = s.replace('\uFE9D', '\u062C')  # U+FE9D jeem isolated form
        s = s.replace('\uFE9E', '\u062C')  # U+FE9E jeem final form
        s = s.replace('\uFE9F', '\u062C')  # U+FE9F jeem initial form
        s = s.replace('\uFEA0', '\u062C')  # U+FEA0 jeem medial form
        s = s.replace('\uFEA1', '\u062D')  # U+FEA1 hah isolated form
        s = s.replace('\uFEA2', '\u062D')  # U+FEA2 hah final form
        s = s.replace('\uFEA3', '\u062D')  # U+FEA3 hah initial form
        s = s.replace('\uFEA4', '\u062D')  # U+FEA4 hah medial form
        s = s.replace('\uFEA5', '\u062E')  # U+FEA5 khah isolated form
        s = s.replace('\uFEA6', '\u062E')  # U+FEA6 khah final form
        s = s.replace('\uFEA7', '\u062E')  # U+FEA7 khah initial form
        s = s.replace('\uFEA8', '\u062E')  # U+FEA8 khah medial form
        s = s.replace('\uFEA9', '\u062F')  # U+FEA9 dal isolated form
        s = s.replace('\uFEAA', '\u062F')  # U+FEAA dal final form
        s = s.replace('\uFEAB', '\u0630')  # U+FEAB thal isolated form
        s = s.replace('\uFEAC', '\u0630')  # U+FEAC thal final form
        s = s.replace('\uFEAD', '\u0631')  # U+FEAD reh isolated form
        s = s.replace('\uFEAE', '\u0631')  # U+FEAE reh final form
        s = s.replace('\uFEAF', '\u0632')  # U+FEAF zain isolated form
        s = s.replace('\uFEB0', '\u0632')  # U+FEB0 zain final form
        s = s.replace('\uFEB1', '\u0633')  # U+FEB1 seen isolated form
        s = s.replace('\uFEB2', '\u0633')  # U+FEB2 seen final form
        s = s.replace('\uFEB3', '\u0633')  # U+FEB3 seen initial form
        s = s.replace('\uFEB4', '\u0633')  # U+FEB4 seen medial form
        s = s.replace('\uFEB5', '\u0634')  # U+FEB5 sheen isolated form
        s = s.replace('\uFEB6', '\u0634')  # U+FEB6 sheen final form
        s = s.replace('\uFEB7', '\u0634')  # U+FEB7 sheen initial form
        s = s.replace('\uFEB8', '\u0634')  # U+FEB8 sheen medial form
        s = s.replace('\uFEB9', '\u0635')  # U+FEB9 sad isolated form
        s = s.replace('\uFEBA', '\u0635')  # U+FEBA sad final form
        s = s.replace('\uFEBB', '\u0635')  # U+FEBB sad initial form
        s = s.replace('\uFEBC', '\u0635')  # U+FEBC sad medial form
        s = s.replace('\uFEBD', '\u0636')  # U+FEBD dad isolated form
        s = s.replace('\uFEBE', '\u0636')  # U+FEBE dad final form
        s = s.replace('\uFEBF', '\u0636')  # U+FEBF dad initial form
        s = s.replace('\uFEC0', '\u0636')  # U+FEC0 dad medial form
        s = s.replace('\uFEC1', '\u0637')  # U+FEC1 tah isolated form
        s = s.replace('\uFEC2', '\u0637')  # U+FEC2 tah final form
        s = s.replace('\uFEC3', '\u0637')  # U+FEC3 tah initial form
        s = s.replace('\uFEC4', '\u0637')  # U+FEC4 tah medial form
        s = s.replace('\uFEC5', '\u0638')  # U+FEC5 zah isolated form
        s = s.replace('\uFEC6', '\u0638')  # U+FEC6 zah final form
        s = s.replace('\uFEC7', '\u0638')  # U+FEC7 zah initial form
        s = s.replace('\uFEC8', '\u0638')  # U+FEC8 zah medial form
        s = s.replace('\uFEC9', '\u0639')  # U+FEC9 ain isolated form
        s = s.replace('\uFECA', '\u0639')  # U+FECA ain final form
        s = s.replace('\uFECB', '\u0639')  # U+FECB ain initial form
        s = s.replace('\uFECC', '\u0639')  # U+FECC ain medial form
        s = s.replace('\uFECD', '\u063A')  # U+FECD ghain isolated form
        s = s.replace('\uFECE', '\u063A')  # U+FECE ghain final form
        s = s.replace('\uFECF', '\u063A')  # U+FECF ghain initial form
        s = s.replace('\uFED0', '\u063A')  # U+FED0 ghain medial form
        s = s.replace('\uFED1', '\u0641')  # U+FED1 feh isolated form
        s = s.replace('\uFED2', '\u0641')  # U+FED2 feh final form
        s = s.replace('\uFED3', '\u0641')  # U+FED3 feh initial form
        s = s.replace('\uFED4', '\u0641')  # U+FED4 feh medial form
        s = s.replace('\uFED5', '\u0642')  # U+FED5 qaf isolated form
        s = s.replace('\uFED6', '\u0642')  # U+FED6 qaf final form
        s = s.replace('\uFED7', '\u0642')  # U+FED7 qaf initial form
        s = s.replace('\uFED8', '\u0642')  # U+FED8 qaf medial form
        s = s.replace('\uFED9', '\u0643')  # U+FED9 kaf isolated form
        s = s.replace('\uFEDA', '\u0643')  # U+FEDA kaf final form
        s = s.replace('\uFEDB', '\u0643')  # U+FEDB kaf initial form
        s = s.replace('\uFEDC', '\u0643')  # U+FEDC kaf medial form
        s = s.replace('\uFEDD', '\u0644')  # U+FEDD lam isolated form
        s = s.replace('\uFEDE', '\u0644')  # U+FEDE lam final form
        s = s.replace('\uFEDF', '\u0644')  # U+FEDF lam initial form
        s = s.replace('\uFEE0', '\u0644')  # U+FEE0 lam medial form
        s = s.replace('\uFEE1', '\u0645')  # U+FEE1 meem isolated form
        s = s.replace('\uFEE2', '\u0645')  # U+FEE2 meem final form
        s = s.replace('\uFEE3', '\u0645')  # U+FEE3 meem initial form
        s = s.replace('\uFEE4', '\u0645')  # U+FEE4 meem medial form
        s = s.replace('\uFEE5', '\u0646')  # U+FEE5 noon isolated form
        s = s.replace('\uFEE6', '\u0646')  # U+FEE6 noon final form
        s = s.replace('\uFEE7', '\u0646')  # U+FEE7 noon initial form
        s = s.replace('\uFEE8', '\u0646')  # U+FEE8 noon medial form
        s = s.replace('\uFEE9', '\u0647')  # U+FEE9 heh isolated form
        s = s.replace('\uFEEA', '\u0647')  # U+FEEA heh final form
        s = s.replace('\uFEEB', '\u0647')  # U+FEEB heh initial form
        s = s.replace('\uFEEC', '\u0647')  # U+FEEC heh medial form
        s = s.replace('\uFEED', '\u0648')  # U+FEED waw isolated form
        s = s.replace('\uFEEE', '\u0648')  # U+FEEE waw final form
        s = s.replace('\uFEEF', '\u0649')  # U+FEEF alef maksura isolated form
        s = s.replace('\uFEF0', '\u0649')  # U+FEF0 alef maksura final form
        s = s.replace('\uFEF1', '\u064A')  # U+FEF1 yeh isolated form
        s = s.replace('\uFEF2', '\u064A')  # U+FEF2 yeh final form
        s = s.replace('\uFEF3', '\u064A')  # U+FEF3 yeh initial form
        s = s.replace('\uFEF4', '\u064A')  # U+FEF4 yeh medial form

        # expand Arabic ligatures
        s = s.replace('\uFEF5', '\u0644\u0622')  # U+FEF5 lam with alef with madda above i.f.
        s = s.replace('\uFEF6', '\u0644\u0622')  # U+FEF6 lam with alef with madda above f.f.
        s = s.replace('\uFEF7', '\u0644\u0623')  # U+FEF7 lam with alef with hamza above i.f.
        s = s.replace('\uFEF8', '\u0644\u0623')  # U+FEF8 lam with alef with hamza above f.f.
        s = s.replace('\uFEF9', '\u0644\u0625')  # U+FEF9 lam with alef with hamza below i.f.
        s = s.replace('\uFEFA', '\u0644\u0625')  # U+FEFA lam with alef with hamza below f.f.
        s = s.replace('\uFEFB', '\u0644\u0627')  # U+FEFB lam with alef isolated form
        s = s.replace('\uFEFC', '\u0644\u0627')  # U+FEFC lam with alef final form
    return s


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
        s = s.replace('\u0928\u093C', '\u0929')    # U+0929 DEVANAGARI LETTER NNNA ऩ -> ऩ
        s = s.replace('\u0930\u093C', '\u0931')    # U+0931 DEVANAGARI LETTER RRA ऱ -> ऱ
        s = s.replace('\u0933\u093C', '\u0934')    # U+0934 DEVANAGARI LETTER LLLA ऴ -> ऴ
    if re.search(r"[\u0958-\u095F]", s):
        # On the other hand, for the following 8 Devanagari letters, use the decomposed form.
        s = s.replace('\u0958', '\u0915\u093C')    # U+0958 DEVANAGARI LETTER QA क़ -> क़
        s = s.replace('\u0959', '\u0916\u093C')    # U+0959 DEVANAGARI LETTER KHHA ख़ -> ख़
        s = s.replace('\u095A', '\u0917\u093C')    # U+095A DEVANAGARI LETTER GHHA ग़ -> ग़
        s = s.replace('\u095B', '\u091C\u093C')    # U+095B DEVANAGARI LETTER ZA ज़ -> ज़
        s = s.replace('\u095C', '\u0921\u093C')    # U+095C DEVANAGARI LETTER DDDHA ड़ -> ड़
        s = s.replace('\u095D', '\u0922\u093C')    # U+095D DEVANAGARI LETTER RHA ढ़ -> ढ़
        s = s.replace('\u095E', '\u092B\u093C')    # U+095E DEVANAGARI LETTER FA फ़ -> फ़
        s = s.replace('\u095F', '\u092F\u093C')    # U+095F DEVANAGARI LETTER YYA य़ -> य़
    return s


def normalize_arabic_punctuation(s: str) -> str:
    s = s.replace('\u0640', '')       # U+0640 Arabic tatweel
    s = s.replace('\u060C', ',')      # U+060C Arabic comma
    s = s.replace('\u060D', ',')      # U+060C Arabic date separator
    s = s.replace('\u061B', ';')      # U+061B Arabic semicolon
    s = s.replace('\u061F', '?')      # U+061F Arabic question mark
    s = s.replace('\u066A', '%')      # U+066A Arabic percent sign
    s = s.replace('\u066B', '.')      # U+066B Arabic decimal separator
    s = s.replace('\u066C', ',')      # U+066C Arabic thousands separator
    s = s.replace('\u066D', '*')      # U+066D Arabic five pointed star
    s = s.replace('\u06D4', '.')      # U+06D4 Arabic full stop
    return s


def map_digits_to_ascii(s: str) -> str:
    """
    This function replaces non-ASCII (Arabic, Indic) digits by ASCII digits.
    This does not include non-digit numbers such Chinese/Japanese 百 (100).
    """
    if not re.search(r"[\u0660-\u0DEF]", s):
       return s
    if re.search(r"[\u0660-\u0669]", s):
        s = s.replace('\u0660', '0')  # U+0660 ARABIC-INDIC DIGIT ZERO ٠ -> 0
        s = s.replace('\u0661', '1')  # U+0661 ARABIC-INDIC DIGIT ONE ١ -> 1
        s = s.replace('\u0662', '2')  # U+0662 ARABIC-INDIC DIGIT TWO ٢ -> 2
        s = s.replace('\u0663', '3')  # U+0663 ARABIC-INDIC DIGIT THREE ٣ -> 3
        s = s.replace('\u0664', '4')  # U+0664 ARABIC-INDIC DIGIT FOUR ٤ -> 4
        s = s.replace('\u0665', '5')  # U+0665 ARABIC-INDIC DIGIT FIVE ٥ -> 5
        s = s.replace('\u0666', '6')  # U+0666 ARABIC-INDIC DIGIT SIX ٦ -> 6
        s = s.replace('\u0667', '7')  # U+0667 ARABIC-INDIC DIGIT SEVEN ٧ -> 7
        s = s.replace('\u0668', '8')  # U+0668 ARABIC-INDIC DIGIT EIGHT ٨ -> 8
        s = s.replace('\u0669', '9')  # U+0669 ARABIC-INDIC DIGIT NINE ٩ -> 9
    if re.search(r"[\u06F0-\u06F9]", s):
        s = s.replace('\u06F0', '0')    # U+06F0 EXTENDED ARABIC-INDIC DIGIT ZERO ۰ -> 0
        s = s.replace('\u06F1', '1')    # U+06F1 EXTENDED ARABIC-INDIC DIGIT ONE ۱ -> 1
        s = s.replace('\u06F2', '2')    # U+06F2 EXTENDED ARABIC-INDIC DIGIT TWO ۲ -> 2
        s = s.replace('\u06F3', '3')    # U+06F3 EXTENDED ARABIC-INDIC DIGIT THREE ۳ -> 3
        s = s.replace('\u06F4', '4')    # U+06F4 EXTENDED ARABIC-INDIC DIGIT FOUR ۴ -> 4
        s = s.replace('\u06F5', '5')    # U+06F5 EXTENDED ARABIC-INDIC DIGIT FIVE ۵ -> 5
        s = s.replace('\u06F6', '6')    # U+06F6 EXTENDED ARABIC-INDIC DIGIT SIX ۶ -> 6
        s = s.replace('\u06F7', '7')    # U+06F7 EXTENDED ARABIC-INDIC DIGIT SEVEN ۷ -> 7
        s = s.replace('\u06F8', '8')    # U+06F8 EXTENDED ARABIC-INDIC DIGIT EIGHT ۸ -> 8
        s = s.replace('\u06F9', '9')    # U+06F9 EXTENDED ARABIC-INDIC DIGIT NINE ۹ -> 9
    if re.search(r"[\u0966-\u096F]", s):
        s = s.replace('\u0966', '0')  # U+0966 DEVANAGARI DIGIT ZERO ० -> 0
        s = s.replace('\u0967', '1')  # U+0967 DEVANAGARI DIGIT ONE १ -> 1
        s = s.replace('\u0968', '2')  # U+0968 DEVANAGARI DIGIT TWO २ -> 2
        s = s.replace('\u0969', '3')  # U+0969 DEVANAGARI DIGIT THREE ३ -> 3
        s = s.replace('\u096A', '4')  # U+096A DEVANAGARI DIGIT FOUR ४ -> 4
        s = s.replace('\u096B', '5')  # U+096B DEVANAGARI DIGIT FIVE ५ -> 5
        s = s.replace('\u096C', '6')  # U+096C DEVANAGARI DIGIT SIX ६ -> 6
        s = s.replace('\u096D', '7')  # U+096D DEVANAGARI DIGIT SEVEN ७ -> 7
        s = s.replace('\u096E', '8')  # U+096E DEVANAGARI DIGIT EIGHT ८ -> 8
        s = s.replace('\u096F', '9')  # U+096F DEVANAGARI DIGIT NINE ९ -> 9
    if re.search(r"[\u09E6-\u09EF]", s):
        s = s.replace('\u09E6', '0')    # U+09E6 BENGALI DIGIT ZERO ০ -> 0
        s = s.replace('\u09E7', '1')    # U+09E7 BENGALI DIGIT ONE ১ -> 1
        s = s.replace('\u09E8', '2')    # U+09E8 BENGALI DIGIT TWO ২ -> 2
        s = s.replace('\u09E9', '3')    # U+09E9 BENGALI DIGIT THREE ৩ -> 3
        s = s.replace('\u09EA', '4')    # U+09EA BENGALI DIGIT FOUR ৪ -> 4
        s = s.replace('\u09EB', '5')    # U+09EB BENGALI DIGIT FIVE ৫ -> 5
        s = s.replace('\u09EC', '6')    # U+09EC BENGALI DIGIT SIX ৬ -> 6
        s = s.replace('\u09ED', '7')    # U+09ED BENGALI DIGIT SEVEN ৭ -> 7
        s = s.replace('\u09EE', '8')    # U+09EE BENGALI DIGIT EIGHT ৮ -> 8
        s = s.replace('\u09EF', '9')    # U+09EF BENGALI DIGIT NINE ৯ -> 9
    if re.search(r"[\u0A66-\u0A6F]", s):
        s = s.replace('\u0A66', '0')    # U+0A66 GURMUKHI DIGIT ZERO ੦ -> 0
        s = s.replace('\u0A67', '1')    # U+0A67 GURMUKHI DIGIT ONE ੧ -> 1
        s = s.replace('\u0A68', '2')    # U+0A68 GURMUKHI DIGIT TWO ੨ -> 2
        s = s.replace('\u0A69', '3')    # U+0A69 GURMUKHI DIGIT THREE ੩ -> 3
        s = s.replace('\u0A6A', '4')    # U+0A6A GURMUKHI DIGIT FOUR ੪ -> 4
        s = s.replace('\u0A6B', '5')    # U+0A6B GURMUKHI DIGIT FIVE ੫ -> 5
        s = s.replace('\u0A6C', '6')    # U+0A6C GURMUKHI DIGIT SIX ੬ -> 6
        s = s.replace('\u0A6D', '7')    # U+0A6D GURMUKHI DIGIT SEVEN ੭ -> 7
        s = s.replace('\u0A6E', '8')    # U+0A6E GURMUKHI DIGIT EIGHT ੮ -> 8
        s = s.replace('\u0A6F', '9')    # U+0A6F GURMUKHI DIGIT NINE ੯ -> 9
    if re.search(r"[\u0AE6-\u0AEF]", s):
        s = s.replace('\u0AE6', '0')    # U+0AE6 GUJARATI DIGIT ZERO ૦ -> 0
        s = s.replace('\u0AE7', '1')    # U+0AE7 GUJARATI DIGIT ONE ૧ -> 1
        s = s.replace('\u0AE8', '2')    # U+0AE8 GUJARATI DIGIT TWO ૨ -> 2
        s = s.replace('\u0AE9', '3')    # U+0AE9 GUJARATI DIGIT THREE ૩ -> 3
        s = s.replace('\u0AEA', '4')    # U+0AEA GUJARATI DIGIT FOUR ૪ -> 4
        s = s.replace('\u0AEB', '5')    # U+0AEB GUJARATI DIGIT FIVE ૫ -> 5
        s = s.replace('\u0AEC', '6')    # U+0AEC GUJARATI DIGIT SIX ૬ -> 6
        s = s.replace('\u0AED', '7')    # U+0AED GUJARATI DIGIT SEVEN ૭ -> 7
        s = s.replace('\u0AEE', '8')    # U+0AEE GUJARATI DIGIT EIGHT ૮ -> 8
        s = s.replace('\u0AEF', '9')    # U+0AEF GUJARATI DIGIT NINE ૯ -> 9
    if re.search(r"[\u0B66-\u0B6F]", s):
        s = s.replace('\u0B66', '0')    # U+0B66 ORIYA DIGIT ZERO ୦ -> 0
        s = s.replace('\u0B67', '1')    # U+0B67 ORIYA DIGIT ONE ୧ -> 1
        s = s.replace('\u0B68', '2')    # U+0B68 ORIYA DIGIT TWO ୨ -> 2
        s = s.replace('\u0B69', '3')    # U+0B69 ORIYA DIGIT THREE ୩ -> 3
        s = s.replace('\u0B6A', '4')    # U+0B6A ORIYA DIGIT FOUR ୪ -> 4
        s = s.replace('\u0B6B', '5')    # U+0B6B ORIYA DIGIT FIVE ୫ -> 5
        s = s.replace('\u0B6C', '6')    # U+0B6C ORIYA DIGIT SIX ୬ -> 6
        s = s.replace('\u0B6D', '7')    # U+0B6D ORIYA DIGIT SEVEN ୭ -> 7
        s = s.replace('\u0B6E', '8')    # U+0B6E ORIYA DIGIT EIGHT ୮ -> 8
        s = s.replace('\u0B6F', '9')    # U+0B6F ORIYA DIGIT NINE ୯ -> 9
    if re.search(r"[\u0BE6-\u0BEF]", s):
        s = s.replace('\u0BE6', '0')    # U+0BE6 TAMIL DIGIT ZERO ௦ -> 0
        s = s.replace('\u0BE7', '1')    # U+0BE7 TAMIL DIGIT ONE ௧ -> 1
        s = s.replace('\u0BE8', '2')    # U+0BE8 TAMIL DIGIT TWO ௨ -> 2
        s = s.replace('\u0BE9', '3')    # U+0BE9 TAMIL DIGIT THREE ௩ -> 3
        s = s.replace('\u0BEA', '4')    # U+0BEA TAMIL DIGIT FOUR ௪ -> 4
        s = s.replace('\u0BEB', '5')    # U+0BEB TAMIL DIGIT FIVE ௫ -> 5
        s = s.replace('\u0BEC', '6')    # U+0BEC TAMIL DIGIT SIX ௬ -> 6
        s = s.replace('\u0BED', '7')    # U+0BED TAMIL DIGIT SEVEN ௭ -> 7
        s = s.replace('\u0BEE', '8')    # U+0BEE TAMIL DIGIT EIGHT ௮ -> 8
        s = s.replace('\u0BEF', '9')    # U+0BEF TAMIL DIGIT NINE ௯ -> 9
    if re.search(r"[\u0C66-\u0C6F]", s):
        s = s.replace('\u0C66', '0')    # U+0C66 TELUGU DIGIT ZERO ౦ -> 0
        s = s.replace('\u0C67', '1')    # U+0C67 TELUGU DIGIT ONE ౧ -> 1
        s = s.replace('\u0C68', '2')    # U+0C68 TELUGU DIGIT TWO ౨ -> 2
        s = s.replace('\u0C69', '3')    # U+0C69 TELUGU DIGIT THREE ౩ -> 3
        s = s.replace('\u0C6A', '4')    # U+0C6A TELUGU DIGIT FOUR ౪ -> 4
        s = s.replace('\u0C6B', '5')    # U+0C6B TELUGU DIGIT FIVE ౫ -> 5
        s = s.replace('\u0C6C', '6')    # U+0C6C TELUGU DIGIT SIX ౬ -> 6
        s = s.replace('\u0C6D', '7')    # U+0C6D TELUGU DIGIT SEVEN ౭ -> 7
        s = s.replace('\u0C6E', '8')    # U+0C6E TELUGU DIGIT EIGHT ౮ -> 8
        s = s.replace('\u0C6F', '9')    # U+0C6F TELUGU DIGIT NINE ౯ -> 9
    if re.search(r"[\u0CE6-\u0CEF]", s):
        s = s.replace('\u0CE6', '0')    # U+0CE6 KANNADA DIGIT ZERO ೦ -> 0
        s = s.replace('\u0CE7', '1')    # U+0CE7 KANNADA DIGIT ONE ೧ -> 1
        s = s.replace('\u0CE8', '2')    # U+0CE8 KANNADA DIGIT TWO ೨ -> 2
        s = s.replace('\u0CE9', '3')    # U+0CE9 KANNADA DIGIT THREE ೩ -> 3
        s = s.replace('\u0CEA', '4')    # U+0CEA KANNADA DIGIT FOUR ೪ -> 4
        s = s.replace('\u0CEB', '5')    # U+0CEB KANNADA DIGIT FIVE ೫ -> 5
        s = s.replace('\u0CEC', '6')    # U+0CEC KANNADA DIGIT SIX ೬ -> 6
        s = s.replace('\u0CED', '7')    # U+0CED KANNADA DIGIT SEVEN ೭ -> 7
        s = s.replace('\u0CEE', '8')    # U+0CEE KANNADA DIGIT EIGHT ೮ -> 8
        s = s.replace('\u0CEF', '9')    # U+0CEF KANNADA DIGIT NINE ೯ -> 9
    if re.search(r"[\u0D66-\u0D6F]", s):
        s = s.replace('\u0D66', '0')    # U+0D66 MALAYALAM DIGIT ZERO ൦ -> 0
        s = s.replace('\u0D67', '1')    # U+0D67 MALAYALAM DIGIT ONE ൧ -> 1
        s = s.replace('\u0D68', '2')    # U+0D68 MALAYALAM DIGIT TWO ൨ -> 2
        s = s.replace('\u0D69', '3')    # U+0D69 MALAYALAM DIGIT THREE ൩ -> 3
        s = s.replace('\u0D6A', '4')    # U+0D6A MALAYALAM DIGIT FOUR ൪ -> 4
        s = s.replace('\u0D6B', '5')    # U+0D6B MALAYALAM DIGIT FIVE ൫ -> 5
        s = s.replace('\u0D6C', '6')    # U+0D6C MALAYALAM DIGIT SIX ൬ -> 6
        s = s.replace('\u0D6D', '7')    # U+0D6D MALAYALAM DIGIT SEVEN ൭ -> 7
        s = s.replace('\u0D6E', '8')    # U+0D6E MALAYALAM DIGIT EIGHT ൮ -> 8
        s = s.replace('\u0D6F', '9')    # U+0D6F MALAYALAM DIGIT NINE ൯ -> 9
    if re.search(r"[\u0DE6-\u0DEF]", s):
        s = s.replace('\u0DE6', '0')    # U+0DE6 SINHALA LITH DIGIT ZERO ෦ -> 0
        s = s.replace('\u0DE7', '1')    # U+0DE7 SINHALA LITH DIGIT ONE ෧ -> 1
        s = s.replace('\u0DE8', '2')    # U+0DE8 SINHALA LITH DIGIT TWO ෨ -> 2
        s = s.replace('\u0DE9', '3')    # U+0DE9 SINHALA LITH DIGIT THREE ෩ -> 3
        s = s.replace('\u0DEA', '4')    # U+0DEA SINHALA LITH DIGIT FOUR ෪ -> 4
        s = s.replace('\u0DEB', '5')    # U+0DEB SINHALA LITH DIGIT FIVE ෫ -> 5
        s = s.replace('\u0DEC', '6')    # U+0DEC SINHALA LITH DIGIT SIX ෬ -> 6
        s = s.replace('\u0DED', '7')    # U+0DED SINHALA LITH DIGIT SEVEN ෭ -> 7
        s = s.replace('\u0DEE', '8')    # U+0DEE SINHALA LITH DIGIT EIGHT ෮ -> 8
        s = s.replace('\u0DEF', '9')    # U+0DEF SINHALA LITH DIGIT NINE ෯ -> 9
    return s


def repair_tokenization(s: str) -> str:
    """Detach certain punctuation -_+*|% and ASCII digits from Arabic characters."""
    s = re.sub(r"([-_+*|%0-9]+)([\u0600-\u06FF])", r"\1 \2", s)
    s = re.sub(r"([\u0600-\u06FF])([-_+*|%0-9]+)", r"\1 \2", s)
    return s


def increment_dict_count(ht: dict, key: str, increment=1):
    """For example ht['NUMBER-OF-LINES']"""
    ht[key] = ht.get(key, 0) + increment


def norm_clean_string_group(s: str, ht: dict, group_name: str, group_function: Callable[[str], str]) -> str:
    """For a given normalization/cleaning group, call appropriate function and update stats."""
    if f'SKIP-{group_name}' not in ht:
        orig_s = s
        s = group_function(s)
        if s != orig_s:
            increment_dict_count(ht, f'COUNT-{group_name}')
    return s


def norm_clean_string(s: str, ht: dict, lang_code='') -> str:
    """Go through a list of applicable normalization/cleaning steps and keep track of the number of changes."""
    number_of_lines = ht.get('NUMBER-OF-LINES', 0) + 1
    ht['NUMBER-OF-LINES'] = number_of_lines
    orig_s = s
    s = norm_clean_string_group(s, ht, 'repair-windows-1252', repair_windows1252)
    s = norm_clean_string_group(s, ht, 'del-surrogate', delete_surrogates)  # alternative/backup to windows-1252
    s = norm_clean_string_group(s, ht, 'del-ctrl-char', delete_control_characters)
    s = norm_clean_string_group(s, ht, 'del-diacr', delete_arabic_diacritics)
    s = norm_clean_string_group(s, ht, 'pres-form-norm', normalize_arabic_pres_form_characters)
    s = norm_clean_string_group(s, ht, 'indic-diacr', normalize_indic_diacritics)
    s = norm_clean_string_group(s, ht, 'norm-punct', normalize_arabic_punctuation)
    s = norm_clean_string_group(s, ht, 'digit', map_digits_to_ascii)
    if lang_code == 'fas':
        s = norm_clean_string_group(s, ht, 'farsi-char-norm', normalize_farsi_characters)
        s = norm_clean_string_group(s, ht, 'ring-char-norm', normalize_ring_characters)
    s = norm_clean_string_group(s, ht, 'repair-token', repair_tokenization)
    if s != orig_s:
        increment_dict_count(ht, 'COUNT-ALL')
    return s


def norm_clean_lines(ht: dict, input_file: TextIO, output_file: TextIO, lang_code=''):
    """Apply normalization/cleaning to a file (or STDIN/STDOUT)."""
    for line in input_file:
        output_file.write(norm_clean_string(line.rstrip(), ht, lang_code=lang_code) + "\n")


def unicode_table_mappings(codeblock: str = 'Devanagari', indent_level: int = 2) -> None:
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
        codepoints = range(0x0900, 0x0980)
        decomposition_exclusions = range(0x0958, 0x0960)
    elif codeblock == 'Indic':
        codepoints = range(0x0900, 0x0E00)
        decomposition_exclusions = range(0x0958, 0x0960)  # probably incomplete
    elif codeblock == 'Arabic':
        codepoints = range(0x0600, 0x0700)
    else:
        codepoints = range(0x0000, 0x007F)  # ASCII
    indent = ' ' * indent_level * 4
    for codepoint in codepoints:
        char = chr(codepoint)
        char_name = ud.name(char, '')           # e.g. 'DEVANAGARI LETTER YYA'
        hex_str = ('%04x' % codepoint).upper()  # e.g. 095F
        uplus = 'U+' + hex_str                  # e.g. U+095F
        us = '\\u' + hex_str                    # e.g. \u095F
        decomp_ssv = ud.decomposition(char)     # e.g. '092F 093C'
        decomp_ssv = re.sub(r'<.*?>\s*', '', decomp_ssv)  # remove decomp type info, e.g. <compat>, <isolated>
        if decomp_ssv:
            # log.info(f'{uplus} decomp_ssv: {decomp_ssv}')
            decomp_codes = decomp_ssv.split()   # e.g. ['092F', '093C']
            decomp_chars = [chr(int(x, 16)) for x in decomp_codes]   # e.g. ['य', '़']
            decomp_str = ''.join(decomp_chars)  # e.g. 'य़' (2 characters)
            decomp_uss = [('\\u' + ('%04x' % int(x, 16)).upper()) for x in decomp_codes]  # e.g. ['\u092F', '\u093C']
            decomp_us = ''.join(decomp_uss)     # e.g. '\u092F\u093C'
            if codepoint in decomposition_exclusions:
                #    s = s.replace('\u095F', '\u092F\u093C')    # U+095F DEVANAGARI LETTER YYA य़ -> य़
                print(f"{indent}s = s.replace('{us}', '{decomp_us}')    # {uplus} {char_name} {char} -> {decomp_str}")
            else:
                #    s = s.replace('\u0928\u093C', '\u0929')  # U+0929 DEVANAGARI LETTER NNNA ऩ -> ऩ
                print(f"{indent}s = s.replace('{decomp_us}', '{us}')    # {uplus} {char_name} {decomp_str} -> {char}")
        digit = ud.digit(char, '')
        if digit != '':
            #   s = s.replace('\u0967', '1')    # U+0967 DEVANAGARI DIGIT ONE १ -> 1
            print(f"{indent}s = s.replace('{us}', '{digit}')    # {uplus} {char_name} {char} -> {digit}")


def main(argv):
    """Wrapper around normalization/cleaning that takes care of argument parsing and prints change stats to STDERR."""
    # parse arguments
    all_skip_elems = ['farsi-char-norm', 'pres-form-norm', 'ring-char-norm', 'del-diacr', 'indic-diacr',
                      'digit', 'norm-punct', 'repair-token']
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
        log.info(f'# ISO 639-3 language code = {lang_code}')
    # The following line is the core call. ht is a dictionary (empty if no steps are to be skipped).
    norm_clean_lines(ht, input_file=args.input, output_file=args.output, lang_code=lang_code)
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
