# wildebeest

### wildebeest.py

Script normalizes and cleans up a number of issues, with some modules specific to Pashto, Farsi, Devanagari.
* repair-windows-1252 (character repair: maps characters encoded in Windows-1252 to UTF8)
* del-surrogate (deletes surrogate characters (representing non-UTF8 characters in input), alternative/backup to windows-1252)
* del-ctrl-char (deletes control characters (expect tab and linefeed), zero-width characters, byte order mark, directional marks, join marks, variation selectors, Arabic tatweel)
* farsi-char-norm (e.g. maps Arabic yeh, kaf to Farsi versions)
* pres-form-norm (e.g. maps from presentation form (isolated, initial, medial, final) to standard form)
* ring-char-norm (e.g. maps ring-characters that are common in Pashto to non-ring characters)
* del-diacr (e.g. deletes diacritics such as Arabic fatha, damma, kasra)
* indic-diacr (e.g. canonical form of composed/decomposed Indic characters; order nukta/vowel-sign)
* digit (e.g. maps Arabic-Indic digits and extended Arabic-Indic digits to ASCII digits)
* norm-punct (e.g. maps Arabic exlamation mark etc. to ASCII equivalent)
* repair-token (e.g. splits +/-/*/digits off Arabic words; maps not-sign inside Arabic to token-separating hyphen)

This script is still work in progress.

### wildebeest_analysis

Script searches a tokenized text for a range of potential problems,
such as UTF-8 encoding violations, control characters, non-ASCII punctuation,
characters from a variety of language groups, very long tokens, unsplit 's,
unsplit punctuation, script mixing; split URLs, email addresses, filenames,
XML tokens.

It will report the number of instances in each category and give examples.

Currently available: wildebeest_analysis.pl (Perl) v2.3 (September 18, 2020)

