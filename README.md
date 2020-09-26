# wildebeest

## wildebeest.py

Script repairs common encoding errors, normalizes characters into their canonical form, maps digits and some
punctuation to ASCII, deletes many non-printable characters and performs other repair, normalization and cleaning steps.
A few steps are specific to Pashto, Farsi, or Devanagari (Hindi etc.).
The script contains a list of normalization modules as listed below. The script argument --skip allows users to specify
any normalization modules they want to skip.

### repair-encodings-errors
The script generally expects input encoded in UTF8. However, it will recognize and repair some common text encoding
errors:
* (Some) text is still encoded in Windows1252 or Latin1. Any byte that is not part of a well-formed UTF8 character will
 be interpreted as a Windows1252 character (and mapped to UTF8). This includes printable Latin1 characters as a subset.
* Text in Windows1252 was incorrectly converted to UTF8 by a Latin1-to-UTF8 converter. This maps Windows1252 characters
 \x80-\x9F to \u0080-\uu009F, which is the Unicode block of C1 control characters. These C1 control characters are
 extremely rare, and so our script will interpret such C1 control characters as ill-converted Windows1252 characters,
 as do many major software applications such as Google Chrome, Microsoft Outlook, Github (text files) and PyCharm 
 (where they are often displayed in a slightly different form).
* Text in Windows1252 or Latin1 was converted twice, using some combination of Latin1-to-UTF8 converter and
 Windows1252-to-UTF converter; or a file already in UTF8 was incorrectly subjected to another conversion.
 Sample *wildebeest* repair:
    * Input: Donât tell your âfiancÃ©â â SchÃ¶ne GrÃ¼Ãe aus MÃ¤hrenâ¦ â Ma sÅur trouve Ã§a Â«bÃªteÂ». Â¡CoÃ±o! â¬50 â¢ 25kmÂ² â¢ Â½Âµm
    * Output: Don’t tell your “fiancé” — Schöne Grüße aus Mähren… – Ma sœur trouve ça «bête». ¡Coño! €50 • 25km² • ½µm

### Other normalization modules
* del-surrogate (deletes surrogate characters (representing non-UTF8 characters in input), alternative/backup to windows-1252)
* del-ctrl-char (deletes control characters (expect tab and linefeed), zero-width characters, byte order mark, directional marks, join marks, variation selectors, Arabic tatweel)
* farsi-char (e.g. maps Arabic yeh, kaf to Farsi versions)
* pres-form (e.g. maps from presentation form (isolated, initial, medial, final) to standard form)
* ligatures-symbols (e.g. maps (non-Arabic) ligatures (e.g. ĳ, ﬃ, Ǆ, ﬓ), symbols (e.g. kappa symbol ϰ), signs (e.g. micro sign µ), CJK square composites (e.g. ㋀㏾))
* fullwidth (e.g. maps fullwidth characters to ASCII, e.g. Ａ to A)
* ring-char (e.g. maps ring-characters that are common in Pashto to non-ring characters)
* del-diacr (e.g. deletes diacritics such as Arabic fatha, damma, kasra)
* indic-diacr (e.g. canonical form of composed/decomposed Indic characters; order nukta/vowel-sign)
* digit (e.g. maps Arabic-Indic digits and extended Arabic-Indic digits to ASCII digits)
* punct (e.g. maps Arabic exlamation mark etc. to ASCII equivalent)
* space (e.g. maps non-zero spaces to normal space)
* repair-xml (e.g. repairs multi-escaped tokens such as &amp;quot; or &amp;amp;#x200C;)
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

