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
* core-compat (normalizes Hangul Compatibility characters to Unicode standard Hangul characters)
* arabic-char (to Arabic canonical forms, e.g. maps Farsi kaf/yeh to Arabic versions)
* farsi-char (to Farsi canonical forms, e.g. maps Arabic yeh, kaf to Farsi versions)
* pashto-char (to Pashto canonical forms, e.g. maps Arabic kaf to Farsi version)
* georgian-char (to Georgian canonical forms, e.g. to standard script, map archaic characters)
* pres-form (e.g. maps from presentation form (isolated, initial, medial, final) to standard form)
* ligatures (e.g. decomposes non-Arabic ligatures (e.g. ĳ, ﬃ, Ǆ, ﬓ))
* signs-and-symbols (e.g. maps symbols (e.g. kappa symbol) and signs (e.g. micro sign µ))
* cjk (e.g. CJK square composites (e.g. ㋀㏾))
* width (e.g. maps fullwidth and halfwidth characters to ASCII, e.g. Ａ to A)
* font (maps font-variations characters such as ℂ, ℹ, 𝒜 to regular characters)
* small (maps small versions of characters to normal versions, such as small ampersand ﹠ to regular &)
* vertical (maps vertical versions of punctuation characters with normal horizontal version, such as vertical em-dash ︱ to horizontal em-dash —)
* enclosure (decomposes circled, squared and parenthesized characters, e.g. 🄐 to (A))
* hangul (combine Hangul jamos onto Hangul syllables)
* repair-combining (e.g. order of nukta/vowel-sign)
* combining-compose (e.g. applies combining-modifiers to preceding character, e.g. ö (o +  ̈) -> ö)
* combining-decompose (e.g. for some Indian characters, splits off Nukta)
* del-arabic-diacr (e.g. deletes optional Arabic diacritics such as fatha, damma, kasra)
* del-hebrew-diacr (e.g. deletes Hebrew points)
* digit (e.g. maps decimal-system digits of 54 scripts to ASCII digits)
* punct (e.g. maps ellipsis … to periods ... and two-dot-lead ‥ to ..; a few math symbols ∭; ⒛ 🄆 )
* punct-dash (e.g. maps various dashes, hyphens, minus signs to ASCII hyphen-minus)
* punct-arabic (e.g. Arabic exclamation mark etc. to ASCII equivalent)
* punct-cjk (e.g. Chinese Ideographic Full Stop etc. to ASCII equivalent)
* punct-greek (e.g. Greek question mark etc. to ASCII equivalent)
* punct-misc-f (e.g. Tibetan punctuation to ASCII equivalent)
* space (e.g. maps non-zero spaces to normal space)
* look-alike (normalizes Latin/Cyrillic/Greek look-alike characters, e.g. Latin character A to Greek Α (capital alpha) in otherwise Greek word)
* repair-xml (e.g. repairs multi-escaped tokens such as &amp;quot; or &amp;amp;#x200C;)
* repair-url-escapes (e.g. repairs multi-escaped url substrings such as Jo%25C3%25ABlle_Aubron)
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

