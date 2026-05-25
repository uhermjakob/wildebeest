#!/usr/bin/env python

from collections import defaultdict
import regex
import sys
import unicodedata as ud


# originally in ualign.py
class ScriptDirection:
    def __init__(self, lang_code: str | None = None, lang_name: str | None = None, text: str | None = None):
        if lang_code and (m := regex.match(r'([a-z]{2,3})-.*\.txt$', str(lang_code))):
            self.lang_code = m.group(1)
        else:
            self.lang_code = lang_code
        self.lang_name = lang_name
        self.bidirectional_class_counts = defaultdict(int)
        self.direction = None  # "left-to-right" or "right-to-left"
        self.monitor = False
        if text:
            self.add_stats(text)

    def add_stats(self, text: str, count: int = 1, loc: int | str | None = None) -> None:
        if text not in (None, 'NULL'):
            for c in text:
                bidirectional_class = ud.bidirectional(c)
                self.bidirectional_class_counts[bidirectional_class] += count
                if self.monitor:
                    if self.lang_code in ('eng', ) and bidirectional_class in ('AL', 'R'):
                        sys.stderr.write(f"RTL char {c} for {self.lang_name or self.lang_code}"
                                         f"{(' in ' + loc) if loc else ''}\n")
                    if self.lang_code in ('ara', 'bal', 'fas', 'heb', 'hbo', 'kas', 'pan', 'pus', 'snd',
                                          'uig', 'urd', 'yid') and bidirectional_class in ('L',):
                        sys.stderr.write(f"LTR char {repr(c)} for {self.lang_name or self.lang_code}"
                                         f"{(' in ' + loc) if loc else ''}\n")

    def direction_class_counts(self) -> tuple[int, int]:
        # Right-to-left: Arabic letters (AL), Hebrew (R)
        # Classes: https://www.unicode.org/reports/tr9/tr9-3.html
        n_ltr = self.bidirectional_class_counts['L']
        n_rtl = self.bidirectional_class_counts['AL'] + self.bidirectional_class_counts['R']
        return n_ltr, n_rtl

    def determine_direction(self) -> str:
        n_ltr, n_rtl = self.direction_class_counts()
        self.direction = "right-to-left" if n_rtl > n_ltr else "left-to-right"
        return self.direction

    def is_right_to_left(self) -> bool:
        return self.determine_direction() == "right-to-left"

    @staticmethod
    def string_is_right_to_left(text: str) -> bool:
        return ScriptDirection(text=text).is_right_to_left()

    def report(self, details: bool = False) -> str:
        message = f"Determined script direction for {self.lang_name or self.lang_code} to be "
        message += self.determine_direction()  # "left-to-right" or "right-to-left"
        if details:
            message += " with character direction counts "
            n_ltr, n_rtl = self.direction_class_counts()
            message += (f"{n_rtl}:{n_ltr}" if self.is_right_to_left() else f"{n_ltr}:{n_rtl}") + " in favor."
        return message + "\n"

    @staticmethod
    def switchable_open_close_delimiters_for_rtl_scripts() -> str:
        return '“”‘’'

    def text_contains_switchable_chars(self, s: str) -> bool:
        return any([x in s for x in self.switchable_open_close_delimiters_for_rtl_scripts()])

    def switch_delimiters_for_rtl_scripts(self, s: str, skip_rtl_check: bool = False) -> str:
        if skip_rtl_check or self.string_is_right_to_left(s):
            s = s.replace('\u0091', '')  # PRIVATE USE ONE character
            rest = self.switchable_open_close_delimiters_for_rtl_scripts()
            while len(rest) >= 2:
                open_delimiter, close_delimiter, rest = rest[0], rest[1], rest[2:]
                s = s.replace(open_delimiter, '\u0091')
                s = s.replace(close_delimiter, open_delimiter)
                s = s.replace('\u0091', close_delimiter)
        return s
