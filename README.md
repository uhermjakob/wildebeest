# norm-clean-text

### norm_clean_text.py

Script normalizes and cleans up a number of issues, so far mostly for Pashto, Farsi, Devanagari.
* farsi-char-norm (e.g. maps Arabic yeh, kaf to Farsi versions)
* pres-form-norm (e.g. maps from presentation form (isolated, initial, medial, final) to standard form)
* ring-char-norm (e.g. maps ring-characters that are common in Pashto to non-ring characters)
* del-diacr (e.g. deletes diacritics such as Arabic fatha, damma, kasra)
* indic-diacr (e.g. canonical form of composed/decomposed Indic characters; order nukta/vowel-sign)
* digit (e.g. maps Arabic-Indic digits and extended Arabic-Indic digits to ASCII digits)
* norm-punct (e.g. maps Arabic exlamation mark etc. to ASCII equivalent)
* repair-token (e.g. splits +/-/*/digits off Arabic words; maps not-sign inside Arabic to token-separating hyphen)

### wildebeest

Script searches a tokenized text for a range of potential problems,
such as UTF-8 encoding violations, control characters, non-ASCII punctuation,
characters from a variety of language groups, very long tokens, unsplit 's,
unsplit punctuation, script mixing; split URLs, email addresses, filenames,
XML tokens.

It will report the number of instances in each category and give examples.

Currently available: wildebeest.pl (Perl) v2.3 (September 18, 2020)

