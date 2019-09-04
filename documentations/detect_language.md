# Mimino666/langdetect
https://github.com/Mimino666/langdetect
 
> Port of Google's language-detection library to Python.

> Port of Google's language-detection library (version from 03/03/2014) to Python.

## Languages
> langdetect supports 55 languages out of the box (ISO 639-1 codes):
```
af, ar, bg, bn, ca, cs, cy, da, de, el, en, es, et, fa, fi, fr, gu, he,
hi, hr, hu, id, it, ja, kn, ko, lt, lv, mk, ml, mr, ne, nl, no, pa, pl,
pt, ro, ru, sk, sl, so, sq, sv, sw, ta, te, th, tl, tr, uk, ur, vi, zh-cn, zh-tw
```

# spacy-langdetect 0.1.2
https://pypi.org/project/spacy-langdetect/
> Out of the box, under the hood it uses langdetect to detect languages on spaCy's Doc and Span objects.

# List of ISO 639-1 codes
https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes
> ISO 639 is a standardized nomenclature used to classify languages. Each language is assigned a two-letter (639-1) and three-letter (639-2 and 639-3), lowercase abbreviation, amended in later versions of the nomenclature.

# pycountry 18.12.8
https://pypi.org/project/pycountry/
> ISO country, subdivision, language, currency and script definitions and their translations
```python
>>> import pycountry
>>> bengali = pycountry.languages.get(alpha_2='bn')
>>> bengali.name
'Bengali'
>>> bengali.common_name
'Bangla'
```