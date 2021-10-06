#!/usr/bin/env perl -w

# Author: Ulf Hermjakob (USC Information Sciences Institute)
# First written: September 9, 2009
# Current version: v2.6 (April 28, 2021)

# default values for optional parameters
$max_n_examples = 20;
$max_n_locations = 10;
$show_all_categories_p =  0;
$first_field_is_sentence_id = 0;
$lang_code = "";

$title_abbr_mc = "Adm|Amb|al|Brig|Capt|Co|Col|Cpt|Dj|Dr|Eng|Fr|Ft|Gen|Gov|Hon|Inc|Ing|Inj|Ir|Jen|Jr|Lt|Maj|Mr|Mrs|Ms|Mt|no|Pres|Pr|Prof|Rep|Rev|R\xC3\xA9v|Sen|Sgt|Spt|Sr|St|Sup|Supt|vol|Vol";
$title_abbr_uc = uc $title_abbr_mc;
$mlg_bible_books = "Dan|Deo|Eks|Gen|Hab|Hag|Hos|Isa|Iza|Jer|Joe|Jos|Lev|Lio|Mal|Mat|Mik|Mpan|Oha|Sal|Sam|Zak";
$month_abbr_uc = "Jan|Febr?|Mar|Apr|Jun|Jul|Aug|Sept?|Oct|Nov|Dec";
@language_codes = ("ar", "ara", "chi", "dar", "de", "en", "eng", "es", "far", "fr", "fre", "gr", "jp", "kin", "mlg", "ru", "som", "ur", "zh");
$common_top_domain_suffixes = "cat|com|edu|gov|info|int|mil|museum|net|org|ar|at|au|be|bi|br|ca|ch|cn|co|cz|de|dk|es|eu|fi|fr|gr|hk|hu|id|ie|il|in|is|it|jp|ke|kr|lu|mg|mx|my|nl|no|nz|pl|pt|ro|ru|rw|se|sg|tr|tv|tw|tz|ug|uk|us|za";
$common_file_suffix = "cgi|doc|gif|html|htm|jpeg|jpg|pdf|txt|xml";
$common_arabic_prefixes = "\xD8\xA7\xD9\x84|\xD8\xA8|\xD9\x84|\xD9\x88|\xD9\x88\xD8\xA7\xD9\x84|\xD8\xA8\xD8\xA7\xD9\x84|\xD9\x84\xD9\x84|\xD9\x88\xD8\xA8"; # al-/b-/l-/w-/wal-/bal-/ll-/wb-
$xml_core_tokens = "amp|lt|gt|quot|apos|nbsp";
%ht = ();
%example_ht = ();
$total_n_tokens = 0;
$n_fast_track_tokens = 0;
$long_token_min = 20;
@descr_tags = ();

*SUMMARY = *STDOUT;

sub print_version {
   print STDERR "Script wildebeest_analysis.pl\n";
   print STDERR "   Version 2.5 (April 21, 2021)\n";
   print STDERR "   Author: Ulf Hermjakob - USC Information Sciences Institute\n";
   print STDERR "   Status: Checks for UNSPLIT_PUNCT still rudimentary.\n";
   exit 1;
}

sub print_usage {
   $lang_code_list_s = join(", ", @language_codes);
   print STDERR<<END_USAGE;

Purpose: Script searches a tokenized text for a range of potential problems,
   such as UTF-8 encoding violations, control characters, non-ASCII punctuation, 
   characters from a variety of language groups, very long tokens, unsplit 's,
   unsplit punctuation, script mixing; split URLs, email addresses, filenames, 
   XML tokens.
   It will report the number of instances in each category and give examples.

Usage: wildebeest_analysis.pl [-options] < text.tok
   Input: (tokenized) plain text, from STDIN
      Expected encoding: UTF-8
   Output: analysis of input text, to STDOUT
   Options overview:
      -<lang-code>                 e.g. -ar   for Arabic
      -n<max_number_of_examples>   e.g. -n100 for up to hundred examples per category
      -l<max_number_of_locations>  e.g. -l5   for up to 5 line numbers per example
      -s or -show-all-categories   (even if there are no instances in that category)
      -id                          first field of each line interpreted as sentence ID
      -h or -help
      -v or -version
   Language code option: analysis will tailor analysis for a given language
      Example: -ar will suppress listing of tokens with regular Arabic letters
      Language codes: $lang_code_list_s
   Maximum number of examples option: -n<max_number_of_examples>
      Example: -n3 will set maximum number of examples that are shown per category to 3
      Default: 20
   Maximum number of locations option: -l<max_number_of_locations>
      Example: -l5 will set maximum number of line numbers shown for each example to 5
      Default: 10
   Sample output for category "Unsplit 's" when using options -n3 -l5:
      Unsplit 's (695 instances):
         nations' (18 instances; lines 152701, 587438, 793425, 1163378, 1670017, ...)
         people's (17 instances; lines 37, 38, 318, 6503, 6504, ...)
         systems' (17 instances; lines 628070, 628079, 3655269, 5548967, 5988904, ...)
         ...
Notes: 
   (1) Results are best viewed in an editor or display tool that can deal with unusual 
       characters, as that's one of the things that the tool targets. 
   (2) While some report categories always signal errors (e.g. "Token does not conform 
       to UTF-8"), others are often benign (e.g. "Token contains Latin-Plus alphabetic
       character"). Such categories are included because they sometimes reveal problems
       such as encoding or tokenization problems of words with Latin-Plus characters.
END_USAGE
;
   exit 1;
}

sub init_ht {
   $descr_s = "
      NON_UTF8:             Token does not conform to UTF-8
      UTF8_NON_SHORTEST:    Token does not conform to UTF-8 (character is not rendered in shortest form)

      CONTROL_CHAR:         Token contains control character
      VARIATION_SELECTOR:   Token contains variation selector, used to specify specific glyph variants for Unicode characters (highly unusual)
      REPL_OBJECT:          Token contains replacement object
      REPL_CHAR:            Token contains replacement character
      OTHER_CHAR:           Token contains character of unknown script (possibly junk)
      PRIVATE_USE:          Token contains private use area character (undefined)

      INITIAL_BYTE_ORDER_MARK: Token contains sentence-initial byte-order-mark (often used to mark text as UTF8)
      ZERO_WIDTH:           Token contains zero-width character, incl. byte-order, direction and join marks
      IPA:                  Token contains IPA extension/modifier letter (International Phonetic Alphabet)
      MODIFIER_TONE:        Token contains modifier tone letter
      COMBINING_DIACRITIC:  Token contains combining diacritic
      NON_ASCII_PUNCT_CHAR: Character is non-ASCII punctuation
      NON_ASCII_PUNCT:      Token contains non-ASCII punctuation
      NON_ASCII_WHITESPACE_CHAR: Character is non-ASCII whitespace
      NON_ASCII_WHITESPACE: Token contains non-ASCII whitespace
      GEOMETRIC_SHAPE_CHAR: Character is geometric shape, incl. circles and squares
      GEOMETRIC_SHAPE:      Token contains geometric shape, incl. circles and squares
      LETTERLIKE_SYMBOL_CHAR: Character is letterlike symbol
      LETTERLIKE_SYMBOL:    Token contains letterlike symbol
      MATH_ALPHA_SYMBOL:    Token contains mathematical alphanumeric symbol
      TECHNICAL_SYMBOL_CHAR: Character is technical symbol
      TECHNICAL_SYMBOL:     Token contains technical symbol
      MATHEMATICAL_OPERATOR_CHAR: Character is mathematical operator
      MATHEMATICAL_OPERATOR: Token contains mathematical operator
      ARROW_SYMBOL_CHAR:    Character is arrow symbol
      ARROW_SYMBOL:         Token contains arrow symbol
      MISC_SYMBOL_CHAR:     Character is miscellaneous symbol
      MISC_SYMBOL:          Token contains miscellaneous symbol
      TAG_CHAR:             Character is tag
      TAG:                  Token contains tag
      BOX_DRAWING:          Token contains box drawing element
      CURRENCY:             Token contains currency symbol
      ASCII_LETTER:         Token contains ASCII alphabetic character
      LANGUAGE_SPECIFIC:    Token contains extended alphabetic character typical for specified language
      LATIN_PLUS_ALPHA:     Token contains Latin-Plus alphabetic character
      LATIN_EXTENDED:       Token contains Extended-Latin character
      LATIN_EXTENDED_ADD:   Token contains Additional-Extended-Latin character
      LATIN_TYPOGRAPHIC_LIGATURE: Token contains typographic Latin ligature (deprecated)
      LATIN_EXTENDED_LIGATURE: Token contains Latin ligature, as found in Dutch (ij) and French (oe)
      FULL_WIDTH:           Token contains full-width (Latin) character
      ARABIC_LETTER:        Token contains standard Arabic alphabetic character
      ARABIC_DIGIT:         Token contains Arabic digit
      ARABIC_INDIC_DIGIT:   Token contains extended Arabic-Indic digit
      ARABIC_TATWEEL:       Token contains Arabic tatweel (elongation character)
      ARABIC_PUNCT:         Token contains Arabic punctuation
      ARABIC_NON_STANDARD:  Token contains non-standard Arabic character
      ARABIC_PRESENTATION:  Token contains Arabic character in presentation form
      ARABIC_PREFIX_ASCII:  Token contains Arabic prefix plus ASCII digits/Latin letters
      MIXED_ARABIC_ASCII:   Token contains mix of Arabic and ASCII
      ARABIC_LETTER_YEH:    Token contains the Arabic version of the letter yeh
      FARSI_LETTER_YEH:     Token contains the Farsi version of the letter yeh
      ARABIC_LETTER_KAF:    Token contains the Arabic letter kaf
      FARSI_LETTER_KEHEF:   Token contains the Farsi letter keheh (the Farsi variant of Arabic letter kaf)
      ARMENIAN:             Token contains Armenian character
      BENGALI:              Token contains Bengali character
      BOPOMOFO:             Token contains Bopomofo character (for Chinese/Mandarin pronunciation)
      BUGINESE:             Token contains Buginese character
      CANADIAN_SYLLABIC:    Token contains Canadian Aboriginal Syllabic
      CHEROKEE:             Token contains Cherokee character (Native American)
      CJK:                  Token contains CJK character (Chinese, Japanese kanji)
      CJK_EXTENDED:         Token contains CJK extended character (Chinese, Japanese kanji)
      CJK_SQ_LATIN_ABBREV:  Token contains CJK compatible squared Latin abbreviation character
      MIXED_CJK_ASCII:      Token contains mix of CJK and ASCII
      COPTIC:               Token contains Coptic character (Egypt)
      CUNEIFORM:            Token contains Cuneiform character (Ancient Mesopotamia)
      CYRILLIC:             Token contains Cyrillic character
      CYRILLIC_EXTENDED:    Token contains Cyrillic extended character
      MIXED_CYRILLIC_LATIN: Token contains mix of Cyrillic and Latin
      PUNCT_CYRILLIC:       Token contains punctuation followed by Cyrillic
      CYRILLIC_PUNCT:       Token contains Cyrillic followed by punctuation
      MIXED_CYRILLIC_PUNCT: Token contains mix of Cyrillic and Punctuation
      CYRILLIC_PLUS_PERIOD: Token contains Cyrillic and a period (possibly abbreviation)
      DEVANAGARI:           Token contains Devanagari character (Indian languages)
      STD_SEP_NUKTA:        Token contains separate Nukta character, standard (Devanagari)
      ALT_SEP_NUKTA:        Token contains separate Nukta character, non-standard encoding, should be composed (Devanagari)
      STD_CMP_NUKTA:        Token contains composed character with Nukta, standard encoding (Devanagari)
      ALT_CMP_NUKTA:        Token contains composed character with Nukta, non-standard encoding, should be decomposed (Devanagari)
      DIS_VSGN_NUKTA:       Token contains vowel-sign followed by Nukta, non-standard order (Devanagari)
      EGYPTIAN_HIEROGLYPH:  Token contains Egyptian hieroglyph
      ENCLOSED_ALPHANUMERIC: Token contains Enclosed alphanumeric character
      ETHIOPIC:             Token contains Ethiopic character
      ETHIOPIC_PUNCT:       Token contains Ethiopic punctuation
      GEORGIAN_STANDARD:    Token contains standard Georgian character
      GEORGIAN_ARCHAIC:     Token contains archaic Georgian character in standard script
      GEORGIAN_EMPHASIS:    Token contains Georgian character in non-standard Mkhedruli Mtavruli script (emphasis)
      GEORGIAN_ASOMTAVRULI: Token contains Georgian character in historic Asomtavruli script
      GEORGIAN_NUSHKHURI:   Token contains Georgian character in historic Nuskhuri script
      PUNCT_GEORGIAN:       Token contains punctuation followed by Georgian
      GEORGIAN_PUNCT:       Token contains Georgian followed by punctuation
      MIXED_GEORGIAN_PUNCT: Token contains mix of Georgian and Punctuation
      GEORGIAN_PLUS_PERIOD: Token contains Georgian and a period (possibly abbreviation)
      GOTHIC:               Token contains Gothic character
      GREEK:                Token contains Greek character
      GREEK_EXTENDED:       Token contains Extended-Greek character
      GUJARATI:             Token contains Gujarati character (India)
      GURMUKHI:             Token contains Gurmukhi character (used for Punjabi, India)
      HEBREW:               Token contains Hebrew character
      JAPANESE_KANA:        Token contains Japanese Hiragana/Katakana character
      JAPANESE_PUNCT:       Token contains Japanese punctuation
      JAVANESE:             Token contains Javanese character (Indonesia)
      KANNADA:              Token contains Kannada character (India)
      KHMER:                Token contains Khmer character
      KLINGON:              Token contains Klingon character (pIqaD, ConScript registry)
      KOREAN_HANGUL:        Token contains Korean Hangul character
      LAO:                  Token contains Lao character
      LISU:                 Token contains Lisu character (Burma, China, Thailand, India)
      MALAYALAM:            Token contains Malayalam character (India)
      MEETAI_MAYEK:         Token contains Meetai Mayek character (India)
      MONGOLIAN:            Token contains Mongolian character
      MYANMAR:              Token contains Myanmar/Burmese character
      OGHAM:                Token contains Ogham character (ancient Irish script)
      ORIYA:                Token contains Oriya/Odia character (India)
      PHOENICIAN:           Token contains Phoenician character (Ancient Levant, Punic of Carthage)
      PICTOGRAPH:           Token contains pictograph (incl. dingbat, emoji)
      RUNIC:                Token contains Runic character
      SINHALA:              Token contains Sinhala character (Sri Lanka)
      SUNDANESE:            Token contains Sundanese character (Indonesia)
      SYRIAC_LETTER:        Token contains Syriac letter
      SYRIAC_PUNCT:         Token contains Syriac punctuation
      SYRIAC_DIACRITIC:     Token contains Syriac diacritic, incl. points and marks
      TAMIL:                Token contains Tamil character (India, Sri Lanka)
      TELUGU:               Token contains Telugu character (Indai)
      THAANA:               Token contains Thaana character (Maldives)
      THAI:                 Token contains Thai character
      TIBETAN_PUNCT:        Token contains Tibetan punctuation
      TIBETAN:              Token contains Tibetan character
      TIFINAGH:             Token contains Tifinagh character (Morocco)
      YI_SYLLABLE:          Token contains Yi syllable (China, Vietnam, Thailand)

      BROKEN_EMAIL:         Broken email address
      BROKEN_URL:           Broken URL
      SUSPICIOUS_URL:       Suspicious URL (ill-formed)
      BROKEN_FILENAME:      Broken filename
      BROKEN_EMAIL_FUZZY:   Broken email address (fuzzy)
      BROKEN_URL_FUZZY:     Broken URL (fuzzy)

      UNUSUAL_PUNCT_COMB:   Unusual combination of punctuation
      SPLIT_XML:            Split XML token
      XML_ESC_DEC:          XML escape character, decimal
      XML_ESC_HEX:          XML escape character, hexadecimal
      XML_ESC_STD:          XML escape character, standard
      XML_ESC_ABC:          XML escape character, alphabetic

      UNSPLIT_PUNCT_ALPHA_HYPHEN: Unsplit punctuation alpha+hyphen
      UNSPLIT_PUNCT:        Unsplit punctuation
      UNSPLIT_APO_S:        Unsplit 's
      UNSPLIT_APO_V:        Unsplit 'd/'ll/'m/'ve
      UNSPLIT_NOT:          Unsplit n't/not
      UNSPLIT_PERIOD:       Unsplit period, comma etc.
      NUM_UNSPLIT_PERIOD:   Unsplit number+period
      BEN_UNSPLIT_APO:      Unsplit apostrophe appearing to be benign
      BEN_UNSPLIT_PERIOD:   Unsplit period, comma etc. appearing to be benign
      BEN_UNSPLIT_PUNCT:    Unsplit punctuation appearing to be benign
      HASHTAG:              Hashtag
      HANDLE:               Handle
      URL:                  URL
      EMAIL:                Email

      LONG_TOKEN_20:        Long token ($long_token_min-29 characters)
      LONG_TOKEN_30:        Very long token (30+ characters)
   ";
   # process above description info
   foreach $d (split(/\n/, $descr_s)) {
      $d =~ s/^\s*//;   # clean up spaces
      $d =~ s/\s*$//;
      $d =~ s/\s+/ /g;
      $d =~ s/\#.*$//;  # ignore comment
      next if $d eq ""; # ignore empty line
      if (($descr_tag, $description) = ($d =~ /^([A-Z][A-Z_0-9]+):\s*(\S.*\S)$/)) {
	 $ht{$descr_tag}->{DESCR} = $description;
	 push(@descr_tags, $descr_tag);
      } else {
	 print STDERR "Ignoring unrecognized analysis class $d\n";
      }
   }
}

sub note_issue {
   # make a note of the issue in hashtable (subject to limits on number of examples per category)
   # always returns 1 (for easy use in conditions)
   local($descr_tag, $example, $location, $control, $char) = @_;

   $control = "" unless defined($control);
   $char = "" unless defined($char);

   &note_issue("NON_ASCII_PUNCT_CHAR", $char, $location, $control) if $char && ($descr_tag eq "NON_ASCII_PUNCT");
   &note_issue("NON_ASCII_WHITESPACE_CHAR", $char, $location, $control) if $char && ($descr_tag eq "NON_ASCII_WHITESPACE");
   &note_issue("GEOMETRIC_SHAPE_CHAR", $char, $location, $control) if $char && ($descr_tag eq "GEOMETRIC_SHAPE");
   &note_issue("LETTERLIKE_SYMBOL_CHAR", $char, $location, $control) if $char && ($descr_tag eq "LETTERLIKE_SYMBOL");
   &note_issue("MATHEMATICAL_OPERATOR_CHAR", $char, $location, $control) if $char && ($descr_tag eq "MATHEMATICAL_OPERATOR");
   &note_issue("TECHNICAL_SYMBOL_CHAR", $char, $location, $control) if $char && ($descr_tag eq "TECHNICAL_SYMBOL");
   &note_issue("ARROW_SYMBOL_CHAR", $char, $location, $control) if $char && ($descr_tag eq "ARROW_SYMBOL");
   &note_issue("MISC_SYMBOL_CHAR", $char, $location, $control) if $char && ($descr_tag eq "MISC_SYMBOL");
   &note_issue("TAG_CHAR", $char, $location, $control) if $char && ($descr_tag eq "TAG");

   if ($control eq "initial") { # first character in character-by-character token check
      %example_ht = ();
   } elsif (($control eq "follow-up")
	 && $example_ht{$descr_tag}) { # already noted for this example and descr_tag
      return 1;
   }
   $example_ht{$descr_tag} = 1 if $control;
   $ht{$descr_tag}->{COUNT}  = ($ht{$descr_tag}->{COUNT} || 0) + 1;
   $n_examples = $ht{$descr_tag}->{N_EXAMPLES} || 0;
   if (defined($ht{$descr_tag}->{EXAMPLE}->{$example})) {
      $n_example = $ht{$descr_tag}->{EXAMPLE}->{$example}->{N} || -9;
   } else {
      $n_example = 0;
   }
   if ($n_example) {
      $ht{$descr_tag}->{EXAMPLE}->{$example}->{N} = $n_example + 1;
      if ($n_example < $max_n_locations) {
	 $ht{$descr_tag}->{EXAMPLE}->{$example}->{LOC} .= ", $location";
      }
   } elsif ($n_examples < $max_n_examples) {
      $ht{$descr_tag}->{N_EXAMPLES} = $n_examples + 1;
      $ht{$descr_tag}->{EXAMPLE}->{$example}->{N} = 1;
      $ht{$descr_tag}->{EXAMPLE}->{$example}->{LOC} = $location;
   } else {
      $ht{$descr_tag}->{UNREC_EXAMPLES_P} = 1;
   }
   return 1;
}

sub special_token_type {
   local($token) = @_;

   return "email" if $token =~ /^[a-z][-a-z0-9_]+(\.[a-z][-a-z0-9_]+)*\@[a-z][-a-z0-9_]+(\.[a-z][-a-z0-9_]+)*$/i;
   return "URL" if $token =~ /^www(\.[a-z0-9]([-a-z0-9_]|\xC3[\x80-\x96\x98-\xB6\xB8-\xBF])+)+\.([a-z]{2,2}|$common_top_domain_suffixes)(\/(\.{1,3}|[a-z0-9]([-a-z0-9_%]|\xC3[\x80-\x96\x98-\xB6\xB8-\xBF])+))*(\/[a-z0-9_][-a-z0-9_]+\.(aspx?|docx?|html?|pdf|php|ppt|xml))?$/i;
   return "URL" if $token =~ /^https?:\/\/(|[a-z]\.)([a-z0-9]([-a-z0-9_]|\xC3[\x80-\x96\x98-\xB6\xB8-\xBF])+\.)+[a-z]{2,}(\/(\.{1,3}|([-a-z0-9_%]|\xC3[\x80-\x96\x98-\xB6\xB8-\xBF])+))*(\/[a-z_][-a-z0-9_]+\.(aspx?|docx?|html?|pdf|php|ppt|xml|mp3|mp4))?$/i;
   return "URL" if $token =~ /^https?:\/\/t\.co\/[A-Za-z0-9]{8,12}$/;
   return "URL" if $token =~ /^[a-z][-a-z0-9_]+(\.[a-z][-a-z0-9_]+)*\.($common_top_domain_suffixes)(\/[a-z0-9]([-a-z0-9_%]|\xC3[\x80-\x96\x98-\xB6\xB8-\xBF])+)*(\/[a-z][-a-z0-9_]+\.(aspx?|docx?|html?|pdf|php|ppt|xml))?$/i;
   if ($token =~ /^[#@](?:[a-z]|\xC3[\x80-\x96\x98-\xB6\xB8-\xBF])(?:[_a-z0-9]|\xC3[\x80-\x96\x98-\xB6\xB8-\xBF])*(?:[a-z0-9]|\xC3[\x80-\x96\x98-\xB6\xB8-\xBF])$/i) {
      return "hashtag" if $token =~ /^\#/;
      return "handle"  if $token =~ /^\@/;
   }
   return "XML" if $token =~ /^&($xml_core_tokens);$/;
   return "info" if $token =~ /^(::snt-type|end-of-article)$/;
   return "";
}

&print_usage if ($#ARGV >= 0) && ($ARGV[0] =~ /^--?(h|help)$/i);
&print_version if ($#ARGV >= 0) && ($ARGV[0] =~ /^--?(v|version)$/i);
&print_usage if $#ARGV >= 4;

# process arguments/options
$lang_code_pattern = join("|", @language_codes);
foreach $arg (@ARGV) {
   if ($arg =~ /^-*n\d+$/) {
      ($pot_max_n_examples) = ($arg =~ /^-*n(\d+)$/);
      if ($pot_max_n_examples <= 1000) {
         $max_n_examples = $pot_max_n_examples;
      } else {
         print STDERR "Ignoring argument $arg (max number of examples too large)\n";
      }
   } elsif ($arg =~ /^-*l\d+$/) {
      ($pot_max_n_locations) = ($arg =~ /^-*l(\d+)$/);
      if ($pot_max_n_locations <= 100) {
         $max_n_locations = $pot_max_n_locations;
      } else {
         print STDERR "Ignoring argument $arg (max number of instances too large)\n";
      }
   } elsif ($arg =~ /^-*($lang_code_pattern)$/) {
      if ($lang_code) {
	 print STDERR "Ignoring argument $arg as language code has already been specified by previous argument (language code: $lang_code)\n";
      } else {
         ($lang_code) = ($arg =~ /^-*($lang_code_pattern)$/);
	 $lang_code = "eng" if $lang_code eq "en";
      }
   } elsif ($arg =~ /^-*(s|show-all-categories)$/) {
      $show_all_categories_p = 1;
   } elsif ($arg =~ /^-*(id)$/) {
      $first_field_is_sentence_id = 1;
   } elsif ($arg =~ /^-*long[-_]?token[-_]?min\d+$/i) {
      ($long_token_min) = ($arg =~ /(\d+)$/);
   } else {
      print STDERR "Ignoring unrecognized argument $arg\n";
   }
}
 
&init_ht;

$line_number = 0;
while (<STDIN>) {
   $line_number++;

   if ($line_number =~ /00000$/) {
      if ($line_number =~ /000000$/) {
	  print STDERR $line_number;
      } else {
	  print STDERR ".";
      }
   }

   $line = $_;
   $line =~ s/^\s*//;
   $line =~ s/\s*$//;
   $line =~ s/\s+/ /g;

   ## line level checks
   if ($first_field_is_sentence_id) {
      if (($id, $snt) = ($line =~ /^(\S+)\s+(.*?)\s*$/)) {
         $line_id = $id;
	 $line = $snt;
      } else {
         next;
      }
   } else {
      $line_id = $line_number;
   }
   $s = $line;
   if ($s =~ /(http|www| \@ |& \S+ ;|\\ ")/) {
      while ($s) {

	 # URL with http and www
	 # dir/filename: (?: \@?\/\@? [a-z][a-z0-9_]+)*(?: \. (?:$common_file_suffix))?
	 if (($pre, $url, $post) = ($s =~ /^(|.*? )(https? (?:\@?:\/\/\@? |: \@\/\@ \@\/\@ |: \/ \/ |% 3 a % 2 f % 2 f)www \. [a-z][a-z0-9_]+(?: (?:\.|\@-\@) [a-z][a-z0-9_]+)*(?: \@?\/\@? [a-z][a-z0-9_]+)*(?: \. (?:$common_file_suffix))?)( .*|)$/i)) {
	    &note_issue("BROKEN_URL", $url, $line_id);

	 # URL with http and common top-level domain name
	 } elsif (($pre, $url, $post) = ($s =~ /^(|.*? )(https? (?:\@?:\/\/\@? |: \@\/\@ \@\/\@ |: \/ \/ |% 3 a % 2 f % 2 f)[a-z][a-z0-9_]+(?: (?:\.|\@-\@) [a-z][a-z0-9_]+)* \. (?:$common_top_domain_suffixes)(?: \@?\/\@? [a-z][a-z0-9_]+)*(?: \. (?:$common_file_suffix))?)( .*|)$/i)) {
	    &note_issue("BROKEN_URL", $url, $line_id);

	 # URL with www and common top-level domain name
	 } elsif (($pre, $url, $post) = ($s =~ /^(|.*? )(www \. [a-z][a-z0-9_]+(?: (?:\.|\@-\@) [a-z][a-z0-9_]+)*(?: \@?\/\@? [a-z][a-z0-9_]+)*(?: \. (?:$common_file_suffix))?)( .*|)$/i)) {
	    &note_issue("BROKEN_URL", $url, $line_id);

	 # URL with http ... xxx.com etc.
	 } elsif (($pre, $url, $post) = ($s =~ /^(|.*? )(https? (?:\@?:\/\/\@? |: \@\/\@ \@\/\@ |: \/ \/ |% 3 a % 2 f % 2 f)[a-z][-a-z0-9_]+(?:\.[a-z][-a-z0-9_]+)+(?: \@?\/\@? [a-z][a-z0-9_]+)*(?: \. (?:$common_file_suffix))?)( .*|)$/i)) {
	    &note_issue("BROKEN_URL", $url, $line_id);

	 # Filename
	 } elsif (($pre, $url, $post) = ($s =~ /^(|.*? )([a-z][a-z0-9_]+(?: \@?\/\@? [a-z][a-z0-9_]+)* \. (?:$common_file_suffix))( .*|)$/i)) {
	    &note_issue("BROKEN_FILENAME", $url, $line_id);

	 # Email with @
	 } elsif (($pre, $email, $post) = ($s =~ /^(|.*? )([a-z][a-z0-9_]+ (?:(?:\.|\@-\@) [a-z][a-z0-9_]+ )*\@ [a-z][a-z0-9_]+(?: (?:\.|\@-\@) [a-z][a-z0-9_]+)* \. [a-z]{2,})( .*|)$/i)) {
	    &note_issue("BROKEN_EMAIL", $email, $line_id);

	 # Email with @ and common top-level domain name, possibly with extra period in front of at-sign
	 } elsif (($pre, $email, $post) = ($s =~ /^(|.*? )([a-z][a-z0-9_]+ (?:(?:\.|\@-\@) [a-z][a-z0-9_]+ )*(?:\. )?\@ [a-z][a-z0-9_]+(?: (?:\.|\@-\@) [a-z][a-z0-9_]+)* \. (?:$common_top_domain_suffixes))( .*|)$/i)) {
	    &note_issue("BROKEN_EMAIL", $email, $line_id);

	 # Maybe URL 
	 } elsif ((($pre, $url, $post) = ($s =~ /^(|.*? )((?:https?|www)(?: \S+){4,8})( .*|)$/i))
	       && ($url =~ / \. /)
	       && ($url =~ /( com\b| org\b|http.*www\b|http.*[a-z][-a-z0-9_]+\.[a-z][-a-z0-9_]| \. [a-z]{2,} )/i)) {
	    &note_issue("BROKEN_URL_FUZZY", $url, $line_id);

	 # Maybe Email
	 } elsif ((($pre, $email, $post) = ($s =~ /^(|.*? )((?:\S+ ){1,3}\@(?: \S+){1,8})( .*|)$/i))
	       && ($email =~ / \. /)
	       && ($email =~ / (com|org)\b/i)
	         ) {
	    &note_issue("BROKEN_EMAIL_FUZZY", $email, $line_id);

	 # Split XML
	 } elsif (($pre, $email, $post) = ($s =~ /^(|.*? )(& (?:$xml_core_tokens) ;)( .*|)$/i)) {
	    &note_issue("SPLIT_XML", $email, $line_id);

	 # XML escape character, decimal
	 } elsif (($pre, $xml, $post) = ($s =~ /^(.*?)(&#\d{1,7};)(.*)$/i)) {
	    &note_issue("XML_ESC_DEC", $xml, $line_id);

	 # XML escape character, hexadecimal
	 } elsif (($pre, $xml, $post) = ($s =~ /^(.*?)(&#X[0-9A-F]{1,6};)(.*)$/i)) {
	    &note_issue("XML_ESC_HEX", $xml, $line_id);

	 # XML escape character, standard
	 } elsif (($pre, $xml, $post) = ($s =~ /^(.*?)(&(?:amp|apos|gt|lt|quot);)(.*)$/i)) {
	    &note_issue("XML_ESC_STD", $xml, $line_id);

	 # XML escape character, alphabetic code
	 } elsif (($pre, $xml, $post) = ($s =~ /^(.*?)(&(?:[a-z]{1,6});)(.*)$/i)) {
	    &note_issue("XML_ESC_ABC", $xml, $line_id);

	 # Unusual punctuation combination
	 } elsif (($pre, $punct, $post) = ($s =~ /^(|.*? )(\\ ")( .*|)$/i)) {
	    &note_issue("UNUSUAL_PUNCT_COMB", $punct, $line_id);

	 } else {
	    last;
	 }
	 $s = "$pre  $post";
      }
   } else {
      while ($s) {
	 # XML escape character, decimal
	 if (($pre, $xml, $post) = ($s =~ /^(.*?)(&#\d{1,7};)(.*)$/i)) {
	    &note_issue("XML_ESC_DEC", $xml, $line_id);

	 # XML escape character, hexadecimal
	 } elsif (($pre, $xml, $post) = ($s =~ /^(.*?)(&#X[0-9A-F]{1,6};)(.*)$/i)) {
	    &note_issue("XML_ESC_HEX", $xml, $line_id);

	 # XML escape character, standard
	 } elsif (($pre, $xml, $post) = ($s =~ /^(.*?)(&(?:amp|apos|gt|lt|quot);)(.*)$/i)) {
	    &note_issue("XML_ESC_STD", $xml, $line_id);

	 # XML escape character, alphabetic code
	 } elsif (($pre, $xml, $post) = ($s =~ /^(.*?)(&(?:[a-z]{1,6});)(.*)$/i)) {
	    &note_issue("XML_ESC_ABC", $xml, $line_id);

	 } else {
	    last;
	 }
	 $s = "$pre  $post";
      }
   }

   @tokens = split(/\s+/, $line);
   $i = -1;
   foreach $token (@tokens) {
      $total_n_tokens++;
      $i++;

      ## fast track classification
      # all ASCII alphabetic 
      if (($token =~ /^[a-z]+$/i)
       && (! (length($token) >= $long_token_min))) { # long token
         $n_fast_track_tokens++;
	 &note_issue("UNSPLIT_NOT", $token, $line_id) if $token =~ /^cannot$/i;
	 next if &note_issue("ASCII_LETTER", $token, $line_id);
      # ASCII digits or single regular ASCII punctuation
      } elsif ($token =~ /^([0-9]+|[-_+*="`':;.?!%()])$/) {
	 $n_fast_track_tokens++;
	 next;
      # all normal Arabic letters
      } elsif (($token =~ /^(\xD8[\xA1-\xBA]|\xD9[\x81-\x8A])+$/)
	    && (! (length($token) >= 40))) { # long token
         $n_fast_track_tokens++;
	 next if &note_issue("ARABIC_LETTER", $token, $line_id);
      # all normal CJK characters
      } elsif (($token =~ /^(\xE4[\xB8-\xBF][\x80-\xBF]|[\xE5-\xE9][\x80-\xBF][\x80-\xBF])+$/)
	    && (! (length($token) >= 60))) { # long token
         $n_fast_track_tokens++;
	 next if &note_issue("CJK", $token, $line_id);
      }

      ## checks on whole token
      $special_token_type = &special_token_type($token);
      &note_issue("CONTROL_CHAR", $token, $line_id) if $token =~ /[\x00-\x1F\x7F]/;
      &note_issue("CURRENCY",     $token, $line_id) if $token =~ /\$/;
      &note_issue("UNSPLIT_PUNCT_ALPHA_HYPHEN", $token, $line_id) if ($token =~ /^[a-z]+-+/i)
						                       && ! $special_token_type;
      unless (($token =~ /^[a-z]+-+/i)
	   || ($token =~ /^[a-z]+n't/i)
	   || ($token =~ /^[a-z]+('s|s')$/i)
	   || $special_token_type) {
         &note_issue("UNSPLIT_PUNCT", $token, $line_id) if ($token =~ /[a-z'`]-[a-z'`]/i);
         &note_issue("UNSPLIT_PUNCT", $token, $line_id) if $token =~ /^-[a-z'`]/i;
         &note_issue("UNSPLIT_PUNCT", $token, $line_id) if $token =~ /-{2,}\d/;
         &note_issue("UNSPLIT_PUNCT", $token, $line_id) if ($token =~ /[a-z0-9][-:";,!\?\(\)\/%]+$/i);
         &note_issue("UNSPLIT_PUNCT", $token, $line_id) if $token =~ /\d,[a-z]/i;
      }
      &note_issue("UNSPLIT_APO_S", $token, $line_id) if $token =~ /[a-z]('s|s')$/i;
      &note_issue("UNSPLIT_APO_V", $token, $line_id) if $token =~ /[a-z]'(d|ll|m|ve)$/i;
      &note_issue("UNSPLIT_NOT", $token, $line_id) if $token =~ /[a-z]n't$/i;
      &note_issue("UNSPLIT_NOT", $token, $line_id) if $token =~ /^cannot$/i;
      if ($special_token_type eq "URL") {
         &note_issue("URL", $token, $line_id);
      } elsif ($special_token_type eq "email") {
         &note_issue("EMAIL", $token, $line_id);
      } elsif ($special_token_type eq "hashtag") {
         &note_issue("HASHTAG", $token, $line_id);
      } elsif ($special_token_type eq "handle") {
         &note_issue("HANDLE", $token, $line_id);
      } elsif ($token =~ /^(www\.|https?:)\S/) {
	 &note_issue("SUSPICIOUS_URL", $token, $line_id);
      } elsif ($token =~ /\S\.(com|org)/) {
	 &note_issue("SUSPICIOUS_URL", $token, $line_id);
      } elsif ($token =~ /([.,;!?].|.[.,;!?])/i) {
	 if ($token =~ /^\d+\.$/) {
            &note_issue("NUM_UNSPLIT_PERIOD", $token, $line_id);
	 } elsif (($token =~ /^([A-Z]\.|[A-Z](?:\.[A-Z])+)\.?$/)
	  || ($token =~ /^(a\.m\.|p\.m\.|i\.e\.|vs\.|v\.)$/)
	  || ($token =~ /^(-?\d{1,3}(?:\.\d{3,3})+|-?\d{1,3}\.\d{1,3})$/)
	  || ($token =~ /^(=?\d{1,3}(?:\,\d{3,3})+|-?\d{1,3}\,\d{1,3})$/)
	  || ($token =~ /^($title_abbr_mc)\.$/)
	  || ($token =~ /^($title_abbr_uc)\.$/)
	  || ($token =~ /^($month_abbr_uc)\.$/)
	  || ($token =~ /^((https?:\/\/)?www(\.[a-z]{2,})+\.(com|edu|gov|net|org|fr|rw)|izuba\.org\.rw)$/)
	  || ($token =~ /^([a-z][-a-z0-9.]*[a-z0-9]\@[a-z]{3,}\.(com|edu|gov|net|org|fr|rw))$/i)) {
            &note_issue("BEN_UNSPLIT_PERIOD", $token, $line_id);
	 } elsif (($lang_code eq "mlg") && ($token =~ /^($mlg_bible_books)\.$/)) {
            &note_issue("BEN_UNSPLIT_PERIOD", $token, $line_id);
	 } else {
            &note_issue("UNSPLIT_PERIOD", $token, $line_id);
	 }
      } elsif (($lang_code eq "kin") 
	    && ($token =~ /^(ab|ah|ak|ay|b|bw|by|cy|h|iby|icy|iry|iy|iz|k|kubw|kw|m|muby|mur|mw|n|nab|nd|ng|nk|nt|ny|nyir|rw|ry|s|ubw|ukw|urw|utw|uw|tw|w|y|z)'$/i)) {
         &note_issue("BEN_UNSPLIT_APO", $token, $line_id);
      } elsif (($lang_code eq "mlg")
	    && (($token =~ /(ak|ik|ok|n|tr)'$/i)
	     || ($token =~ /^(mah)'$/i))) {
         &note_issue("BEN_UNSPLIT_APO", $token, $line_id);
      } elsif (($lang_code eq "eng") && ($token =~ /^(o'clock)$/i)) {
         &note_issue("BEN_UNSPLIT_APO", $token, $line_id);
      } elsif ($token =~ /^('d|'ll|'m|n't|'re|'s|'ve|c'|d'|l')$/i) {
         &note_issue("BEN_UNSPLIT_APO", $token, $line_id);
      } elsif ($token =~ /^(\d+-\d+|\d+\/\d+|\d\d?\/\d\d?\/\d\d(\d\d)?|\d\d?-\d\d?-\d\d(\d\d)?|-\d+(\.\d+)?|\d+:\d+(-\d+)?|\d+:\d\d:\d\d)$/i) {
         &note_issue("BEN_UNSPLIT_PUNCT", $token, $line_id);
      } elsif ($token =~ /^((\d|0\d|1\d|2[0-3]):[0-5]\d(am|pm))$/i) {
         &note_issue("BEN_UNSPLIT_PUNCT", $token, $line_id);
      } elsif ($token =~ /^::(article|emphasis|genre|snt-type|source|strong)$/i) {
         &note_issue("BEN_UNSPLIT_PUNCT", $token, $line_id);
      } elsif ($token =~ /^(end-of-article)$/i) {
         &note_issue("BEN_UNSPLIT_PUNCT", $token, $line_id);
      } elsif (($token =~ /^[A-Za-z][a-z]*'[a-z]+$/i) && ($lang_code eq "som") && (($token =~ /[aeiouy]'/i) || ($token =~ /'[aeiou]/i))) {
         &note_issue("BEN_UNSPLIT_PUNCT", $token, $line_id);
      } elsif (($token =~ /[!-\/:-\@\[\\\]^_`{|}~]/) && ($token =~ /../) && ! ($token =~ /^\@?[-:\/"]\@?$/)) {
         &note_issue("UNSPLIT_PUNCT", $token, $line_id);
      }
      if ($token =~ /[\x21-\x7E]/) { # mixed ASCII and ...
         if ($token =~ /[\xD8-\xDB]/) { # ... Arabic
	    if ($token =~ /^($common_arabic_prefixes)(\d+(\.\d+)?|([a-z]|\xC3[\x80-\x96\x98-\xB6\xB8-\xBF]|[\xC4-\xC8][\x80-\xBF])+)$/) {
               &note_issue("ARABIC_PREFIX_ASCII", $token, $line_id);
	    } else {
               &note_issue("MIXED_ARABIC_ASCII", $token, $line_id);
	    }
         }
	 if ($token =~ /(\xE4[\xB8-\xBF][\x80-\xBF]|[\xE5-\xE9][\x80-\xBF][\x80-\xBF])/) { # CJK and ASCII
            &note_issue("MIXED_CJK_ASCII", $token, $line_id);
	 }
      }
      if (($token =~ /[\x41-\x5A\x61-\x7A\xC3-\xC8]/)  # mixed Latin and ...
       || ($token =~ /\xC9[\x80-\x8F]/)) {
         if (($token =~ /[\xD0-\xD3]/)  # ... Cyrillic
          || ($token =~ /\xD4[\x80-\xAF]/)) {
            &note_issue("MIXED_CYRILLIC_LATIN", $token, $line_id);
	 }
      }
      if (($token =~ /(?:[\x21-\x2F\x3A-\x40\x5B-\x60\x7B-\x7E]|\xE2[\x80-\xAF])/)  # Punct
       || ($token =~ /(?:\xC2[\xA0-\xBF]|\xC3[\x97\xB7]|\xE3\x80[\x80-\x91\x94-\x9F\xB0\xBB-\xBD])/)
       || ($token =~ /(?:\xEF\xB8[\x90-\x99\xB0-\xBF]|\xEF\xB9[\x80-\xAB]|\xEF\xBD[\x9B-\xA4]|\xF0\x9F[\xA0-\xA3])/)) {
         if ($token =~ /(?:[\xD0-\xD3]|\xD4[\x80-\xAF])/) { # ... Cyrillic
            if ($token =~ /^(?:(?:[\x21-\x2F\x3A-\x40\x5B-\x60\x7B-\x7E]|\xE2[\x80-\xAF]|\xC2[\xA0-\xBF]|\xC3[\x97\xB7]|\xE3\x80[\x80-\x91\x94-\x9F\xB0\xBB-\xBD]|\xEF\xB8[\x90-\x99\xB0-\xBF]|\xEF\xB9[\x80-\xAB]|\xEF\xBD[\x9B-\xA4]|\xF0\x9F[\xA0-\xA3])[\x80-\xBF]*)+(?:[\xD0-\xD3]|\xD4[\x80-\xAF])/) {
               &note_issue("PUNCT_CYRILLIC", $token, $line_id);
            } elsif ($token =~ /(?:[\xD0-\xD3]|\xD4[\x80-\xAF])(?:[\x80-\xBF]*)\.$/) {
               &note_issue("CYRILLIC_PLUS_PERIOD", $token, $line_id);
            } elsif ($token =~ /(?:[\xD0-\xD3]|\xD4[\x80-\xAF])(?:[\x80-\xBF]*)(?:(?:[\x21-\x2F\x3A-\x40\x5B-\x60\x7B-\x7E]|\xE2[\x80-\xAF]|\xC2[\xA0-\xBF]|\xC3[\x97\xB7]|\xE3\x80[\x80-\x91\x94-\x9F\xB0\xBB-\xBD]|\xEF\xB8[\x90-\x99\xB0-\xBF]|\xEF\xB9[\x80-\xAB]|\xEF\xBD[\x9B-\xA4]|\xF0\x9F[\xA0-\xA3])[\x80-\xBF]*)+$/) {
               &note_issue("CYRILLIC_PUNCT", $token, $line_id);
	    } else {
               &note_issue("MIXED_CYRILLIC_PUNCT", $token, $line_id);
            }
	 }
      }  
      # Georgian and punctuation
      if (($token =~ /(?:[\x21-\x2F\x3A-\x40\x5B-\x60\x7B-\x7E]|\xE2[\x80-\xAF])/)  # Punct
       || ($token =~ /(?:\xC2[\xA0-\xBF]|\xC3[\x97\xB7]|\xE3\x80[\x80-\x91\x94-\x9F\xB0\xBB-\xBD])/)
       || ($token =~ /(?:\xEF\xB8[\x90-\x99\xB0-\xBF]|\xEF\xB9[\x80-\xAB]|\xEF\xBD[\x9B-\xA4]|\xF0\x9F[\xA0-\xA3])/)) {
         if ($token =~ /(?:\xE1\x82[\xA0-\xBF]|\xE1\x83[\x80-\xBF]|\xE1\xB2[\x90-\xBF]|\xE2\xB4[\x80-\xAF])/) { # ... Georgian
            if ($token =~ /^(?:(?:[\x21-\x2F\x3A-\x40\x5B-\x60\x7B-\x7E]|\xE2[\x80-\xAF]|\xC2[\xA0-\xBF]|\xC3[\x97\xB7]|\xE3\x80[\x80-\x91\x94-\x9F\xB0\xBB-\xBD]|\xEF\xB8[\x90-\x99\xB0-\xBF]|\xEF\xB9[\x80-\xAB]|\xEF\xBD[\x9B-\xA4]|\xF0\x9F[\xA0-\xA3])[\x80-\xBF]*)+(?:\xE1\x82[\xA0-\xBF]|\xE1\x83[\x80-\xBF]|\xE1\xB2[\x90-\xBF]|\xE2\xB4[\x80-\xAF])/) {
               &note_issue("PUNCT_GEORGIAN", $token, $line_id);
            } elsif ($token =~ /(?:\xE1\x82[\xA0-\xBF]|\xE1\x83[\x80-\xBF]|\xE1\xB2[\x90-\xBF]|\xE2\xB4[\x80-\xAF]*)\.$/) {
               &note_issue("GEORGIAN_PLUS_PERIOD", $token, $line_id);
            } elsif ($token =~ /(?:\xE1\x82[\xA0-\xBF]|\xE1\x83[\x80-\xBF]|\xE1\xB2[\x90-\xBF]|\xE2\xB4[\x80-\xAF])(?:(?:[\x21-\x2F\x3A-\x40\x5B-\x60\x7B-\x7E]|\xE2[\x80-\xAF]|\xC2[\xA0-\xBF]|\xC3[\x97\xB7]|\xE3\x80[\x80-\x91\x94-\x9F\xB0\xBB-\xBD]|\xEF\xB8[\x90-\x99\xB0-\xBF]|\xEF\xB9[\x80-\xAB]|\xEF\xBD[\x9B-\xA4]|\xF0\x9F[\xA0-\xA3])[\x80-\xBF]*)+$/) {
               &note_issue("GEORGIAN_PUNCT", $token, $line_id);
	    } else {
               &note_issue("MIXED_GEORGIAN_PUNCT", $token, $line_id);
            }
	 }
      }  

      # nukta
      if ($token =~ /\xE0[\xA4-\xA5]/) { # Devanagari
	 if ($token =~ /\xE0\xA4\xBC/) { # Devanagari nukta
	    if ($token =~ /\xE0\xA4[\x95\x96\x97\x9C\xA1\xA2\xAB\xAF](?:\xE0\xA4[\xBE-\xBF]|\xE0\xA5[\x80-\x8D])?\xE0\xA4\xBC/) { # standard separate characters, possibly with vowel signs before nulta
	       &note_issue("STD_SEP_NUKTA", $token, $line_id);
	    }
	    my $token_wo_std_nuktas = $token;
	    $token_wo_std_nuktas =~ s/\xE0\xA4[\x95\x96\x97\x9C\xA1\xA2\xAB\xAF](?:\xE0\xA4[\xBE-\xBF]|\xE0\xA5[\x80-\x8D])?\xE0\xA4\xBC//g;
	    if ($token_wo_std_nuktas =~ /\xE0\xA4\xBC/) {
	       &note_issue("ALT_SEP_NUKTA", $token, $line_id);
	    }
	 }
	 if ($token =~ /\xE0\xA4[\xA9\xB1\xB4]/) { # standard composed characters with nukta
	    &note_issue("STD_CMP_NUKTA", $token, $line_id);
	 }
	 if ($token =~ /\xE0\xA5[\x98-\x9F]/) { # non-standard composed characters with nukta
	    &note_issue("ALT_CMP_NUKTA", $token, $line_id);
	 }
	 if ($token =~ /(\xE0\xA4[\xBE-\xBF]|\xE0\xA5[\x80-\x8D])(\xE0\xA4\xBC)/) { # vowel-sign followed by nukta (wrong order, disorder)
	    &note_issue("DIS_VSGN_NUKTA", $token, $line_id);
	 }
      }

      # long tokens
      if ((length($token) >= $long_token_min)
       && (! $special_token_type)) {
	 $char_head_bytes = $token;
	 $char_head_bytes =~ s/[\x80-\xBF]//g;
	 if (length($char_head_bytes) >= 30) {
            &note_issue("LONG_TOKEN_30", $token, $line_id);
	 } elsif ((length($char_head_bytes) >= $long_token_min)
	     && ! ($token =~ /^(compartmentali[sz]ations?|counterrevolutionaries|counterrevolutionary|deinstitutionali[sz]ations?|hydrochlorofluorocarbons?|institutionali[sz]ations?|instrumentali[sz]ations?|internationali[sz]ation|mischaracteri[sz]ations?|transnationali[sz]ation|uncharacteristically)$/i)) {
            &note_issue("LONG_TOKEN_20", $token, $line_id);
	 }
      }

      ## character level checks
      &note_issue("ASCII_LETTER", $token, $line_id) if $token =~ /[a-z]/i;
      $token_rest = $token;
      $token_rest =~ s/[\x00-\x7F]//g; # remove all ASCII
      if ($token_rest =~ /^[\x80-\xBF]/) {
         &note_issue("NON_UTF8", $token, $line_id, "initial");
	 $token_rest =~ s/^[\x80-\xBF]+//;
	 $next_co = "follow-up";
      } else {
         $next_co = "initial";
      }
      while ($token_rest ne "") {
	 $co = $next_co;
	 $next_co = "follow-up";
	 unless (($c, $next_token_rest) = ($token_rest =~ /^([\xC0-\xFF][\x80-\xBF]+)(.*)$/)) {
	    # should never happen, but just in case
            &note_issue("NON_UTF8", $token, $line_id, $co);
	    last;
	 }
	 $token_rest = $next_token_rest;
         if ($c =~ /^[\xC0-\xDF]/) {
	    next if (! ($c =~ /^[\xC0-\xDF][\x80-\xBF]$/)) && &note_issue("NON_UTF8", $token, $line_id, $co);
            next if ($c =~ /[\xC0-\xC1]/)     && &note_issue("UTF8_NON_SHORTEST", $token, $line_id, $co);
            next if ($c =~ /\xC2[\x80-\x9F]/) && &note_issue("CONTROL_CHAR", $token, $line_id, $co);
            next if ($c =~ /\xC2[\xA2-\xA5]/) && &note_issue("CURRENCY", $token, $line_id, $co);
            next if ($c =~ /\xC2\xA0/)        && &note_issue("NON_ASCII_WHITESPACE", $token, $line_id, $co, $c); # U+00A0 (nbsp)
            next if ($c =~ /\xC2[\xA0-\xBF]/) && &note_issue("NON_ASCII_PUNCT", $token, $line_id, $co, $c);
            next if ($c =~ /\xC3[\x97\xB7]/)  && &note_issue("NON_ASCII_PUNCT", $token, $line_id, $co, $c);
            next if ((($lang_code =~ /^(de|ger)$/) # German umlauts, sharp s
		      && ($c =~ /\xC3[\x84\x96\x9C\x9F\xA4\xB6\xBC]/))
                  || (($lang_code =~ /^(es|spa)$/) # Spanish accents, n-tilde
		      && ($c =~ /\xC3[\x81\x89\x8D\x8F\x91\x93\x9A\xA1\xA9\xAD\xAF\xB1\xB3\xBA]/))
                  || (($lang_code =~ /^(fr|fre)$/) # French accents, c-cedille, oe-ligature
		      && (($c =~ /\xC3[\x80\x82\x87-\x8B\x8E\x8F\x94\x99\x9B]/) # upper case
		       || ($c =~ /\xC3[\xA0\xA2\xA7-\xAB\xAE\xAF\xB4\xB9\xBB]/) # lower case
		       || ($c =~ /\xC5[\x92\x93]/))) # OE/oe ligature
                  || (($lang_code =~ /^(ur|urd)$/) # Urdu ddal, gaf, jeh, peh, rreh, tcheh, tteh, fathatan, yeh barree, farsi yeh, noon ghunna, heh goal, ...
		      && ($c =~ /(\xD9\x8B|\xD9\xB1|\xD9\xB9|\xD9\xBE|\xDA\x86|\xDA\x88|\xDA\x91|\xDA\x98|\xDA\xAF|\xDA\xBA|\xDB\x81|\xDB\x82|\xDB\x8C|\xDB\x92|\xDB\x93)/)))
		  && &note_issue("LANGUAGE_SPECIFIC", $token, $line_id, $co);
            next if ($c =~ /\xC3[\x80-\xBF]/) && &note_issue("LATIN_PLUS_ALPHA", $token, $line_id, $co);
            next if ($c =~ /\xC4[\xB2\xB3]/)  && &note_issue("LATIN_EXTENDED_LIGATURE", $token, $line_id, $co);
            next if ($c =~ /\xC5[\x92\x93]/)  && &note_issue("LATIN_EXTENDED_LIGATURE", $token, $line_id, $co);
            next if ($c =~ /[\xC4-\xC8]/)     && &note_issue("LATIN_EXTENDED", $token, $line_id, $co);
            next if ($c =~ /\xC9[\x80-\x8F]/) && &note_issue("LATIN_EXTENDED", $token, $line_id, $co);
            next if ($c =~ /\xC9[\x90-\xBF]/) && &note_issue("IPA", $token, $line_id, $co);
            next if ($c =~ /\xCA[\x80-\xBF]/) && &note_issue("IPA", $token, $line_id, $co);
            next if ($c =~ /\xCB[\x80-\xBF]/) && &note_issue("IPA", $token, $line_id, $co);
            next if ($c =~ /\xCC[\x80-\xBF]/) && &note_issue("COMBINING_DIACRITIC", $token, $line_id, $co);
            next if ($c =~ /\xCD[\x80-\xAF]/) && &note_issue("COMBINING_DIACRITIC", $token, $line_id, $co);
            next if ($c =~ /\xCD[\xB0-\xBF]/) && &note_issue("GREEK", $token, $line_id, $co);
            next if ($c =~ /\xCE/)            && &note_issue("GREEK", $token, $line_id, $co);
            next if ($c =~ /\xCF[\x80-\xA1]/) && &note_issue("GREEK", $token, $line_id, $co);
            next if ($c =~ /\xCF[\xA2-\xAF]/) && &note_issue("COPTIC", $token, $line_id, $co);
            next if ($c =~ /[\xD0-\xD3]/)     && &note_issue("CYRILLIC", $token, $line_id, $co);
            next if ($c =~ /\xD4[\x80-\xAF]/) && &note_issue("CYRILLIC", $token, $line_id, $co);
            next if ($c =~ /\xD4[\xB0-\xBF]/) && &note_issue("ARMENIAN", $token, $line_id, $co);
            next if ($c =~ /\xD5/)            && &note_issue("ARMENIAN", $token, $line_id, $co);
            next if ($c =~ /\xD6[\x80-\x8F]/) && &note_issue("ARMENIAN", $token, $line_id, $co);
            next if ($c =~ /\xD6[\x90-\xBF]/) && &note_issue("HEBREW", $token, $line_id, $co);
            next if ($c =~ /\xD7/)            && &note_issue("HEBREW", $token, $line_id, $co);
            next if ($c =~ /\xD9\x80/)        && &note_issue("ARABIC_TATWEEL", $token, $line_id, $co);
	         if ($c =~ /\xD9\x8A/) {         &note_issue("ARABIC_LETTER_YEH", $token, $line_id, $co); }
	         if ($c =~ /\xDB\x8C/) {         &note_issue("FARSI_LETTER_YEH", $token, $line_id, $co); }
	         if ($c =~ /\xD9\x83/) {         &note_issue("ARABIC_LETTER_KAF", $token, $line_id, $co); }
	         if ($c =~ /\xDA\xA9/) {         &note_issue("FARSI_LETTER_KEHEF", $token, $line_id, $co); }
            next if ($c =~ /\xD8[\xA1-\xBA]/) && &note_issue("ARABIC_LETTER", $token, $line_id, $co);
            next if ($c =~ /\xD9[\x81-\x8A]/) && &note_issue("ARABIC_LETTER", $token, $line_id, $co);
            next if ($c =~ /\xD9[\xA0-\xA9]/) && &note_issue("ARABIC_DIGIT", $token, $line_id, $co);
            next if ($c =~ /\xD8[\x8C\x8D\x9B\x9F]/) && &note_issue("ARABIC_PUNCT", $token, $line_id, $co);
            next if ($c =~ /\xD9[\xAA-\xAD]/) && &note_issue("ARABIC_PUNCT", $token, $line_id, $co);
            next if ($c =~ /\xDB[\xB0-\xB9]/) && &note_issue("ARABIC_INDIC_DIGIT", $token, $line_id, $co);
            next if ($c =~ /[\xD8-\xDB]/)     && &note_issue("ARABIC_NON_STANDARD", $token, $line_id, $co);
            next if ($c =~ /\xDC[\x80-\x8F]/) && &note_issue("SYRIAC_PUNCT", $token, $line_id, $co);
            next if ($c =~ /\xDC[\x90-\xAF]/) && &note_issue("SYRIAC_LETTER", $token, $line_id, $co);
            next if ($c =~ /\xDC[\xB0-\xBF]/) && &note_issue("SYRIAC_DIACRITIC", $token, $line_id, $co);
            next if ($c =~ /\xDD[\x80-\x8A]/) && &note_issue("SYRIAC_DIACRITIC", $token, $line_id, $co);
            next if ($c =~ /\xDE/)            && &note_issue("THAANA", $token, $line_id, $co);
	 } elsif ($c =~ /^[\xE0-\xEF]/) {
	    next if (! ($c =~ /^[\xE0-\xEF][\x80-\xBF]{2,2}$/)) && &note_issue("NON_UTF8", $token, $line_id, $co);
            next if ($c =~ /\xE0[\x80-\x9F]/)     && &note_issue("UTF8_NON_SHORTEST", $token, $line_id, $co);
            next if ($c =~ /\xE0[\xA4-\xA5]/)     && &note_issue("DEVANAGARI", $token, $line_id, $co);
            next if ($c =~ /\xE0[\xA6-\xA7]/)     && &note_issue("BENGALI", $token, $line_id, $co);
            next if ($c =~ /\xE0[\xA8-\xA9]/)     && &note_issue("GURMUKHI", $token, $line_id, $co);
            next if ($c =~ /\xE0[\xAA-\xAB]/)     && &note_issue("GUJARATI", $token, $line_id, $co);
            next if ($c =~ /\xE0[\xAC-\xAD]/)     && &note_issue("ORIYA", $token, $line_id, $co);
            next if ($c =~ /\xE0[\xAE-\xAF]/)     && &note_issue("TAMIL", $token, $line_id, $co);
            next if ($c =~ /\xE0[\xB0-\xB1]/)     && &note_issue("TELUGU", $token, $line_id, $co);
            next if ($c =~ /\xE0[\xB2-\xB3]/)     && &note_issue("KANNADA", $token, $line_id, $co);
            next if ($c =~ /\xE0[\xB4-\xB5]/)     && &note_issue("MALAYALAM", $token, $line_id, $co);
            next if ($c =~ /\xE0[\xB6-\xB7]/)     && &note_issue("SINHALA", $token, $line_id, $co);
            next if ($c =~ /\xE0[\xB8-\xB9]/)     && &note_issue("THAI", $token, $line_id, $co);
            next if ($c =~ /\xE0[\xBA-\xBB]/)     && &note_issue("LAO", $token, $line_id, $co);
            next if ($c =~ /\xE0\xBC[\x81-\x94]/) && &note_issue("TIBETAN_PUNCT", $token, $line_id, $co);
            next if ($c =~ /\xE0\xBC[\xB4-\xBD]/) && &note_issue("TIBETAN_PUNCT", $token, $line_id, $co);
            next if ($c =~ /\xE0\xBE[\x84-\x85]/) && &note_issue("TIBETAN_PUNCT", $token, $line_id, $co);
            next if ($c =~ /\xE0[\xBC-\xBF]/)     && &note_issue("TIBETAN", $token, $line_id, $co);
            next if ($c =~ /\xE1[\x80-\x81]/)     && &note_issue("MYANMAR", $token, $line_id, $co);
            next if ($c =~ /\xE1\x82[\x80-\x9F]/) && &note_issue("MYANMAR", $token, $line_id, $co);
            next if ($c =~ /\xE1\x82[\xA0-\xBF]/) && &note_issue("GEORGIAN_ASOMTAVRULI", $token, $line_id, $co);
            next if ($c =~ /\xE1\x83[\x80-\x8F]/) && &note_issue("GEORGIAN_ASOMTAVRULI", $token, $line_id, $co);
            next if ($c =~ /\xE1\x83[\xB1-\xB5]/) && &note_issue("GEORGIAN_ARCHAIC", $token, $line_id, $co);
            next if ($c =~ /\xE1\x83[\x90-\xBF]/) && &note_issue("GEORGIAN_STANDARD", $token, $line_id, $co);
            next if ($c =~ /\xE1[\x84-\x87]/)     && &note_issue("KOREAN_HANGUL", $token, $line_id, $co);
            next if ($c =~ /\xE1\x8D[\xA0-\xA8]/) && &note_issue("ETHIOPIC_PUNCT", $token, $line_id, $co);
            next if ($c =~ /\xE1[\x88-\x8D]/)     && &note_issue("ETHIOPIC", $token, $line_id, $co);
            next if ($c =~ /\xE1\x8E[\xA0-\xBF]/) && &note_issue("CHEROKEE", $token, $line_id, $co);
            next if ($c =~ /\xE1\x8F/)            && &note_issue("CHEROKEE", $token, $line_id, $co);
            next if ($c =~ /\xE1[\x90-\x99]/)     && &note_issue("CANADIAN_SYLLABIC", $token, $line_id, $co);
            next if ($c =~ /\xE1\x9A[\x80-\x9F]/) && &note_issue("OGHAM", $token, $line_id, $co);
            next if ($c =~ /\xE1\x9A[\xA0-\xBF]/) && &note_issue("RUNIC", $token, $line_id, $co);
            next if ($c =~ /\xE1\x9B/)            && &note_issue("RUNIC", $token, $line_id, $co);
            next if ($c =~ /\xE1[\x9E-\x9F]/)     && &note_issue("KHMER", $token, $line_id, $co);
            next if ($c =~ /\xE1[\xA0-\xA1]/)     && &note_issue("MONGOLIAN", $token, $line_id, $co);
            next if ($c =~ /\xE1\xA2[\x80-\xAF]/) && &note_issue("MONGOLIAN", $token, $line_id, $co);
            next if ($c =~ /\xE1\xA8[\x80-\x9F]/) && &note_issue("BUGINESE", $token, $line_id, $co);
            next if ($c =~ /\xE1\xAE/)            && &note_issue("SUNDANESE", $token, $line_id, $co);
            next if ($c =~ /\xE1\xB2[\x80-\x8F]/) && &note_issue("CYRILLIC_EXTENDED", $token, $line_id, $co);
            next if ($c =~ /\xE1\xB2[\x90-\xBF]/) && &note_issue("GEORGIAN_EMPHASIS", $token, $line_id, $co);
            next if ($c =~ /\xE1[\xB4-\xB5]/)     && &note_issue("IPA", $token, $line_id, $co);
            next if ($c =~ /\xE1\xB6/)            && &note_issue("IPA", $token, $line_id, $co); # supplement
            next if ($c =~ /\xE1[\xB8-\xBB]/)     && &note_issue("LATIN_EXTENDED_ADD", $token, $line_id, $co);
            next if ($c =~ /\xE1[\xBC-\xBF]/)     && &note_issue("GREEK_EXTENDED", $token, $line_id, $co);
            next if ($c =~ /\xE2\x80[\x80-\x8A\xAF]/) && &note_issue("NON_ASCII_WHITESPACE", $token, $line_id, $co);
            next if ($c =~ /\xE2\x80[\x8B-\x8F\xAA-\xAE]/) && &note_issue("ZERO_WIDTH", $token, $line_id, $co);
            next if ($c =~ /\xE2\x81\x9F/)        && &note_issue("NON_ASCII_WHITESPACE", $token, $line_id, $co); # Medium Mathematical Space
            next if ($c =~ /\xE2\x82[\xA0-\xBF]/) && &note_issue("CURRENCY", $token, $line_id, $co);
	    next if ($c =~ /\xE2\x84/)            && &note_issue("LETTERLIKE_SYMBOL", $token, $line_id, $co, $c);
	    next if ($c =~ /\xE2\x85[\x80-\x8F]/) && &note_issue("LETTERLIKE_SYMBOL", $token, $line_id, $co, $c);
	    next if ($c =~ /\xE2\x86[\x90-\xBF]/) && &note_issue("ARROW_SYMBOL", $token, $line_id, $co, $c);
	    next if ($c =~ /\xE2\x87/)            && &note_issue("ARROW_SYMBOL", $token, $line_id, $co, $c);
	    next if ($c =~ /\xE2[\x88-\x8B]/)     && &note_issue("MATHEMATICAL_OPERATOR", $token, $line_id, $co, $c);
	    next if ($c =~ /\xE2[\x8C-\x8F]/)     && &note_issue("TECHNICAL_SYMBOL", $token, $line_id, $co, $c);
            next if ($c =~ /\xE2\x91[\xA0-\xBF]/) && &note_issue("ENCLOSED_ALPHANUMERIC", $token, $line_id, $co);
            next if ($c =~ /\xE2[\x92-\x93]/)     && &note_issue("ENCLOSED_ALPHANUMERIC", $token, $line_id, $co);
            next if ($c =~ /\xE2[\x94-\x95]/)     && &note_issue("BOX_DRAWING", $token, $line_id, $co);
	    next if ($c =~ /\xE2\x96[\xA0-\xBF]/) && &note_issue("GEOMETRIC_SHAPE", $token, $line_id, $co, $c);
	    next if ($c =~ /\xE2\x97/)            && &note_issue("GEOMETRIC_SHAPE", $token, $line_id, $co, $c);
            next if ($c =~ /\xE2[\x98-\x9E]/)     && &note_issue("PICTOGRAPH", $token, $line_id, $co);
            next if ($c =~ /\xE2\xAC[\x80-\x91\xB0-\xBF]/) && &note_issue("ARROW_SYMBOL", $token, $line_id, $co, $c);
	    next if ($c =~ /\xE2\xAC[\x92-\xAF]/) && &note_issue("GEOMETRIC_SHAPE", $token, $line_id, $co, $c);
	    next if ($c =~ /\xE2\xAD[\x80-\x8F\x9A-\xBF]/) && &note_issue("ARROW_SYMBOL", $token, $line_id, $co, $c);
	    next if ($c =~ /\xE2\xAD[\x90-\x99]/) && &note_issue("GEOMETRIC_SHAPE", $token, $line_id, $co, $c);
	    next if ($c =~ /\xE2\xAE[\x80-\xB9]/) && &note_issue("ARROW_SYMBOL", $token, $line_id, $co, $c);
	    next if ($c =~ /\xE2\xAE[\xBA-\xBF]/) && &note_issue("GEOMETRIC_SHAPE", $token, $line_id, $co, $c);
	    next if ($c =~ /\xE2\xAF[\x80-\x88\x8A-\x8F]/) && &note_issue("GEOMETRIC_SHAPE", $token, $line_id, $co, $c);
	    next if ($c =~ /\xE2[\xAC-\xAF]/)     && &note_issue("MISC_SYMBOL", $token, $line_id, $co, $c);
            next if ($c =~ /\xE2[\x80-\xAF]/)     && &note_issue("NON_ASCII_PUNCT", $token, $line_id, $co, $c);
            next if ($c =~ /\xE2[\xB2-\xB3]/)     && &note_issue("COPTIC", $token, $line_id, $co);
            next if ($c =~ /\xE2\xB4[\x80-\xAF]/) && &note_issue("GEORGIAN_NUSHKHURI", $token, $line_id, $co);
            next if ($c =~ /\xE2\xB4[\xB0-\xBF]/) && &note_issue("TIFINAGH", $token, $line_id, $co);
            next if ($c =~ /\xE2\xB5/)            && &note_issue("TIFINAGH", $token, $line_id, $co);
            next if ($c =~ /\xE2\xB7[\xA0-\xBF]/) && &note_issue("CYRILLIC_EXTENDED", $token, $line_id, $co);
            next if ($c =~ /\xE3\x80\x80/)        && &note_issue("NON_ASCII_WHITESPACE", $token, $line_id, $co, $c); # Ideographic Space
            next if ($c =~ /\xE3\x80[\x81-\x91\x94-\x9F\xB0\xBB-\xBD]/) && &note_issue("NON_ASCII_PUNCT", $token, $line_id, $co, $c);
            next if ($c =~ /\xE3\x83\xBB/)        && &note_issue("JAPANESE_PUNCT", $token, $line_id, $co); # katakana middle dot
            next if ($c =~ /\xE3[\x81-\x83]/)     && &note_issue("JAPANESE_KANA", $token, $line_id, $co);
            next if ($c =~ /\xE3\x84[\x80-\xAF]/) && &note_issue("BOPOMOFO", $token, $line_id, $co);
            next if ($c =~ /\xE3[\x88-\x8B]/)     && &note_issue("MISC_SYMBOL", $token, $line_id, $co, $c);
            next if ($c =~ /\xE3\x8D[\xB1-\xBA]/) && &note_issue("CJK_SQ_LATIN_ABBREV", $token, $line_id, $co);
            next if ($c =~ /\xE3\x8E[\x80-\xBF]/) && &note_issue("CJK_SQ_LATIN_ABBREV", $token, $line_id, $co);
            next if ($c =~ /\xE3\x8F[\x80-\x9F\xBF]/) && &note_issue("CJK_SQ_LATIN_ABBREV", $token, $line_id, $co);
            next if ($c =~ /\xE4[\xB8-\xBF]/)     && &note_issue("CJK", $token, $line_id, $co);
            next if ($c =~ /[\xE5-\xE9]/)         && &note_issue("CJK", $token, $line_id, $co);
            next if ($c =~ /\xEA[\x80-\x92]/)     && &note_issue("YI_SYLLABLE", $token, $line_id, $co);
            next if ($c =~ /\xEA\x93[\x90-\xBF]/) && &note_issue("LISU", $token, $line_id, $co);
            next if ($c =~ /\xEA\x99/)            && &note_issue("CYRILLIC_EXTENDED", $token, $line_id, $co);
            next if ($c =~ /\xEA\x9A[\x80-\x9F]/) && &note_issue("CYRILLIC_EXTENDED", $token, $line_id, $co);
            next if ($c =~ /\xEA\x9C[\x80-\x9F]/) && &note_issue("MODIFIER_TONE", $token, $line_id, $co);
            next if ($c =~ /\xEA\xA6/)            && &note_issue("JAVANESE", $token, $line_id, $co);
            next if ($c =~ /\xEA\xA7[\x80-\x9F]/) && &note_issue("JAVANESE", $token, $line_id, $co);
            next if ($c =~ /\xEA\xAF/)            && &note_issue("MEETAI_MAYEK", $token, $line_id, $co);
            next if ($c =~ /\xEA[\xB0-\xBF]/)     && &note_issue("KOREAN_HANGUL", $token, $line_id, $co);
            next if ($c =~ /[\xEB-\xEC]/)         && &note_issue("KOREAN_HANGUL", $token, $line_id, $co);
            next if ($c =~ /\xED[\x80-\x9E]/)     && &note_issue("KOREAN_HANGUL", $token, $line_id, $co);
            next if ($c =~ /\xEE/)                && &note_issue("PRIVATE_USE", $token, $line_id, $co);
	    next if ($c =~ /\xEF\xA3[\x90-\xBF]/) && &note_issue("KLINGON", $token, $line_id, $co);
            next if ($c =~ /\xEF[\x80-\xA3]/)     && &note_issue("PRIVATE_USE", $token, $line_id, $co);
            next if ($c =~ /\xEF\xAC[\x80-\x86]/) && &note_issue("LATIN_TYPOGRAPHIC_LIGATURE", $token, $line_id, $co);
            next if ($c =~ /\xEF\xAD[\x90-\xBF]/) && &note_issue("ARABIC_PRESENTATION", $token, $line_id, $co);
            next if ($c =~ /\xEF[\xAE-\xB7]/)     && &note_issue("ARABIC_PRESENTATION", $token, $line_id, $co);
            next if ($c =~ /\xEF\xB8[\x80-\x8F]/) && &note_issue("VARIATION_SELECTOR", $token, $line_id, $co);
            next if ($c =~ /\xEF\xB8[\x90-\x99]/) && &note_issue("NON_ASCII_PUNCT", $token, $line_id, $co, $c);
            next if ($c =~ /\xEF\xB8[\xB0-\xBF]/) && &note_issue("NON_ASCII_PUNCT", $token, $line_id, $co, $c);
            next if ($c =~ /\xEF\xB9[\x80-\xAB]/) && &note_issue("NON_ASCII_PUNCT", $token, $line_id, $co, $c);
            next if ($c =~ /\xEF\xB9[\xB0-\xBF]/) && &note_issue("ARABIC_PRESENTATION", $token, $line_id, $co);
            next if ($c =~ /\xEF\xBA/)            && &note_issue("ARABIC_PRESENTATION", $token, $line_id, $co);
            next if ($c =~ /\xEF\xBB[\x80-\xBC]/) && &note_issue("ARABIC_PRESENTATION", $token, $line_id, $co);
            next if ($c =~ /\xEF\xBB\xBF/)        && ($co eq "initial")
						  && &note_issue("INITIAL_BYTE_ORDER_MARK", $token, $line_id, $co);
            next if ($c =~ /\xEF\xBB\xBF/)        && &note_issue("ZERO_WIDTH", $token, $line_id, $co);
            next if ($c =~ /\xEF\xBC[\x81-\xBF]/) && &note_issue("FULL_WIDTH", $token, $line_id, $co); # punct,uc
            next if ($c =~ /\xEF\xBD[\x80-\x9A]/) && &note_issue("FULL_WIDTH", $token, $line_id, $co); # lc
            next if ($c =~ /\xEF\xBD[\x9B-\xA4]/) && &note_issue("NON_ASCII_PUNCT", $token, $line_id, $co, $c);
            next if ($c =~ /\xEF\xBF[\xB0-\xB6]/) && &note_issue("FULL_WIDTH", $token, $line_id, $co); # currency
	    next if ($c =~ /\xEF\xBF\xBC/)        && &note_issue("REPL_OBJECT", $token, $line_id, $co); 
	    next if ($c =~ /\xEF\xBF\xBD/)        && &note_issue("REPL_CHAR", $token, $line_id, $co); 
         } elsif ($c =~ /[\xF0-\xFE]/) {
            next if ($c =~ /\xF0\x90\x8C[\xB0-\xBF]/) && &note_issue("GOTHIC", $token, $line_id, $co);
            next if ($c =~ /\xF0\x90\x8D[\x80-\x8F]/) && &note_issue("GOTHIC", $token, $line_id, $co);
            next if ($c =~ /\xF0\x90\xA4[\x80-\x9F]/) && &note_issue("PHOENICIAN", $token, $line_id, $co);
            next if ($c =~ /\xF0\x92[\x80-\x8F]/) && &note_issue("CUNEIFORM", $token, $line_id, $co);
            next if ($c =~ /\xF0\x93[\x80-\x90]/) && &note_issue("EGYPTIAN_HIEROGLYPH", $token, $line_id, $co);
	    next if ($c =~ /\xF0\x9D[\x90-\x9F]/) && &note_issue("MATH_ALPHA_SYMBOL", $token, $line_id, $co);
            next if ($c =~ /\xF0\x9F[\x80-\x83]/) && &note_issue("MISC_SYMBOL", $token, $line_id, $co, $c);
            next if ($c =~ /\xF0\x9F[\x84-\x87]/) && &note_issue("ENCLOSED_ALPHANUMERIC", $token, $line_id, $co);
            next if ($c =~ /\xF0\x9F[\x88-\x8B]/) && &note_issue("MISC_SYMBOL", $token, $line_id, $co, $c);
            next if ($c =~ /\xF0\x9F[\x8C-\x9B]/) && &note_issue("PICTOGRAPH", $token, $line_id, $co);
	    next if ($c =~ /\xF0\x9F[\x9E-\x9F]/) && &note_issue("GEOMETRIC_SHAPE", $token, $line_id, $co, $c);
            next if ($c =~ /\xF0\x9F[\xA0-\xA3]/) && &note_issue("NON_ASCII_PUNCT", $token, $line_id, $co);
            next if ($c =~ /\xF0\x9F[\xA4-\xAB]/) && &note_issue("PICTOGRAPH", $token, $line_id, $co);
            next if ($c =~ /\xF0\x9F\xAA[\xB0-\xBF]/) && &note_issue("PICTOGRAPH", $token, $line_id, $co);
            next if ($c =~ /\xF0[\xA0-\xAA]/)     && &note_issue("CJK_EXTENDED", $token, $line_id, $co);
            next if ($c =~ /\xF3\xA0[\x80-\x81]/) && &note_issue("TAG", $token, $line_id, $co, $c);
            next if ($c =~ /\xF3\xA0[\x84-\x87]/) && &note_issue("VARIATION_SELECTOR", $token, $line_id, $co);
            next if ($c =~ /\xF3[\xB0-\xBF]/)     && &note_issue("PRIVATE_USE", $token, $line_id, $co);
            next if ($c =~ /\xF4[\x80-\x8F]/)     && &note_issue("PRIVATE_USE", $token, $line_id, $co);
	    next if (!  (($c =~ /[\xF0-\xF7][\x80-\xBF]{3,3}$/)
	              || ($c =~ /[\xF8-\xFB][\x80-\xBF]{4,4}$/)
	              || ($c =~ /[\xFC-\xFD][\x80-\xBF]{5,5}$/)
	              || ($c =~ /[\xFE-\xFE][\x80-\xBF]{6,6}$/)))
                  && &note_issue("NON_UTF8", $token, $line_id, $co);
            next if ($c =~ /\xF0[\x80-\x8F]/) && &note_issue("UTF8_NON_SHORTEST", $token, $line_id, $co);
         } else {
            next if &note_issue("NON_UTF8", $token, $line_id, $co);
	 }
         &note_issue("OTHER_CHAR", $token, $line_id, $co);
      }
   }
}
print STDERR "\n";
print STDERR "Analysed $total_n_tokens tokens (thereof $n_fast_track_tokens fast-track) in $line_number lines\n";

# write out analysis
$lang_code_clause = ($lang_code) ? " (language code: $lang_code)" : "";
print SUMMARY "Encoding, script, and tokenization analysis (wildebeest_analysis.pl):\n";
print SUMMARY "Analysed $total_n_tokens tokens in $line_number lines$lang_code_clause\n";
$consider_skipping_next_blank_line_p = 0;
foreach $descr_tag (@descr_tags) {

   $count = $ht{$descr_tag}->{COUNT} || 0;
   $description = $ht{$descr_tag}->{DESCR} || $descr_tag;
   $instances = ($count == 1) ? "instance" : "instances";

   if ($count == 0) {
      $skip_details_p = 1;
      $expl_clause = "";
   # don't bother reporting tokens containing Arabic characters for Arabic text
   } elsif ((($descr_tag eq "ARABIC_LETTER") && ($lang_code =~ /^(ar|ara|dar|far|ur|urd)$/))
         || (($descr_tag eq "ARABIC_NON_STANDARD") && ($lang_code =~ /^(dar|far|ur|urd)$/))
         || (($descr_tag eq "ASCII_LETTER")  && ($lang_code =~ /^(de|en|eng|es|fr|fre|ger|kin|mlg|som|spa)$/))
         || (($descr_tag eq "CJK")           && ($lang_code =~ /^(chi|jp|zh)/))
         || (($descr_tag eq "CYRILLIC")      && ($lang_code =~ /^(ru)$/))
         || (($descr_tag eq "GREEK")         && ($lang_code =~ /^(gr)$/))
         || (($descr_tag eq "JAPANESE_KANA") && ($lang_code =~ /^(jp)$/))) {
      if ($show_all_categories_p) {
         $skip_details_p = 0;
         $expl_clause = "Note: such characters are normal for specified language ($lang_code)\n";
      } else {
         $skip_details_p = 1;
         $expl_clause = "  No examples shown, as such characters are normal for specified language ($lang_code)\n";
      }
   } else {
      $skip_details_p = 0;
      $expl_clause = "";
   }
   if ($show_all_categories_p || ! $skip_details_p) {
      print SUMMARY "\n" unless $skip_details_p && $consider_skipping_next_blank_line_p;
      print SUMMARY "$description ($count $instances)\n";
      print SUMMARY $expl_clause;
      $consider_skipping_next_blank_line_p = $skip_details_p;
   }
   next if $skip_details_p;

   # sort by instances (higher first) then alphabetically
   foreach $example (sort {    (     $ht{$descr_tag}->{EXAMPLE}->{$b}->{N}
		                 <=> $ht{$descr_tag}->{EXAMPLE}->{$a}->{N} )
			    || ( lc $a cmp lc $b ) }
			  keys %{$ht{$descr_tag}->{EXAMPLE}}) {
      $n = $ht{$descr_tag}->{EXAMPLE}->{$example}->{N} || 0;
      $location = $ht{$descr_tag}->{EXAMPLE}->{$example}->{LOC} || "";
      $note = $example;
      $location_clause = "; lines $location";
      $location_clause = "; line $location" unless $location =~ /, /;
      $location_clause = "; $location" if $first_field_is_sentence_id;
      $location_clause .= ", ..." if $n > $max_n_locations;
      $location_clause = "" if ($max_n_locations == 0) || ($location eq "");
      $instances = ($n == 1) ? "instance" : "instances";
      $note .= " ($n $instances$location_clause)";
      print SUMMARY "  $note\n";
   }
   if ($ht{$descr_tag}->{UNREC_EXAMPLES_P}) {
      print SUMMARY "  ...\n";
   }
}
exit 0;
