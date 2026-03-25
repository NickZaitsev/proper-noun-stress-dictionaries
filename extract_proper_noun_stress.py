#!/usr/bin/env python3

import argparse
import ast
import html
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Sequence, Set, Tuple

try:
    import pymorphy3
except ImportError:  # pragma: no cover - optional dependency
    pymorphy3 = None


ACCENT = "\u0301"
VOWELS = "АЕЁИОУЫЭЮЯаеёиоуыэюя"
WORD_CHARS_RE = re.compile(r"[A-Za-zА-Яа-яЁё\u0301-]+")
WORD_PLUS_RE = re.compile(r"[A-Za-zА-Яа-яЁё+-]+")
BOLD_RE = re.compile(r"'{3,5}(.+?)'{3,5}", re.DOTALL)
CATEGORY_RE = re.compile(r"\[\[Категория:([^\]|]+)")
TEMPLATE_NAME_RE = re.compile(r"\{\{\s*([^\|\}\n<]+)")
TITLE_PAREN_RE = re.compile(r"\s*\([^)]*\)\s*$")
WIKI_LINK_WITH_LABEL_RE = re.compile(r"\[\[[^\]|]+\|([^\]]+)\]\]")
WIKI_LINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
EXTERNAL_LINK_RE = re.compile(r"\[(https?://[^\s\]]+)\s+([^\]]+)\]")
REF_RE = re.compile(r"<ref\b[^>/]*?>.*?</ref>|<ref\b[^>]*/>", re.IGNORECASE | re.DOTALL)
COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
HTML_TAG_RE = re.compile(r"</?[A-Za-z][^>]*>")
HEADING_RE = re.compile(r"^==[^=].*?==\s*$", re.MULTILINE)
STRESS_TEMPLATE_RE = re.compile(r"([A-Za-zА-Яа-яЁё])\s*\{\{\s*ударение\s*\}\}")
NON_LETTER_RE = re.compile(r"[^A-Za-zА-Яа-яЁё-]+")
EMPTY_PARENS_RE = re.compile(r"\s*\(\)\s*$")
OUTER_GUILLEMETS = ("\u00ab", "\u00bb")
ROMAN_NUMERAL_RE = re.compile(r"^[IVXLCDM]+$")
LEADING_NORMALIZATION_JUNK_RE = re.compile(r"^[^0-9A-Za-zА-Яа-яЁё+]+")
TRAILING_NORMALIZATION_JUNK_RE = re.compile(r"[^0-9A-Za-zА-Яа-яЁё]+$")

TOPONYM_CATEGORY_KEYWORDS = (
    "город",
    "сёл",
    "село",
    "деревн",
    "посёл",
    "станиц",
    "хутор",
    "остров",
    "река",
    "озер",
    "море",
    "океан",
    "страны",
    "государств",
    "республик",
    "област",
    "край",
    "район",
    "столиц",
    "провинц",
    "муниципал",
    "регион",
    "топоним",
    "улиц",
    "площад",
    "гора",
    "хребет",
    "водопад",
)

TOPONYM_LEAD_KEYWORDS = (
    "город",
    "столица",
    "страна",
    "река",
    "озеро",
    "село",
    "деревня",
    "посёлок",
    "остров",
    "архипелаг",
    "гора",
    "регион",
    "область",
    "край",
    "район",
    "муниципалитет",
    "провинция",
    "штат",
)

TOPONYM_TEMPLATE_KEYWORDS = (
    "город",
    "населённый пункт",
    "населенный пункт",
    "река",
    "озеро",
    "остров",
    "гора",
    "страна",
    "провинция",
    "регион",
    "район",
    "улица",
    "станция",
    "метрополитен",
)

OTHER_PROPER_CATEGORY_KEYWORDS = (
    "фамилии",
    "персоналии",
    "родившиеся",
    "умершие",
    "династии",
    "имена",
    "мифолог",
    "литературные персонажи",
    "боги",
    "герои",
    "математик",
    "механик",
    "экономист",
    "философ",
    "социолог",
    "историк",
    "физик",
    "химик",
    "биолог",
    "художник",
    "режисс",
    "композитор",
    "пев",
    "журналист",
    "политик",
    "президент",
    "император",
    "корол",
    "цар",
    "княз",
    "герцог",
    "учён",
    "учен",
)

OTHER_PROPER_TEMPLATE_KEYWORDS = (
    "учёный",
    "ученый",
    "писатель",
    "поэт",
    "музыкант",
    "актёр",
    "актер",
    "актриса",
    "футболист",
    "хоккеист",
    "спортсмен",
    "политик",
    "военный деятель",
    "персона",
    "биография",
    "монарх",
    "святой",
    "художник",
    "композитор",
    "режиссёр",
    "режиссер",
    "философ",
    "математик",
    "физик",
    "экономист",
)

OTHER_PROPER_LEAD_KEYWORDS = (
    "фамилия",
    "имя",
    "персонаж",
    "богиня",
    "бог",
    "человек",
    "футболист",
    "писатель",
    "актёр",
    "актриса",
    "поэт",
    "музыкант",
    "династия",
    "математик",
    "механик",
    "экономист",
    "философ",
    "социолог",
    "историк",
    "физик",
    "химик",
    "биолог",
    "художник",
    "режиссёр",
    "режиссер",
    "композитор",
    "певец",
    "певица",
    "журналист",
    "политик",
    "президент",
    "император",
    "король",
    "царь",
    "князь",
    "герцог",
    "учёный",
    "ученый",
)

SURNAME_LIKE_SUFFIXES = (
    "ов",
    "ев",
    "ёв",
    "ин",
    "ын",
    "ский",
    "цкий",
    "енко",
    "ук",
    "юк",
    "дзе",
    "швили",
    "ян",
    "янц",
)

GENERIC_TITLE_BLACKLIST = {
    "город",
    "городок",
    "столица",
    "страна",
    "река",
    "озеро",
    "остров",
    "архипелаг",
    "район",
    "область",
    "край",
    "регион",
    "муниципалитет",
    "провинция",
    "штат",
    "доминион",
    "урбанизация",
    "школа",
    "протеомика",
    "лавра",
    "метрополитен",
}

LOWERCASE_NAME_PARTICLES = {
    "аль",
    "аф",
    "ап",
    "бен",
    "бин",
    "ван",
    "де",
    "дель",
    "дер",
    "ди",
    "дю",
    "ибн",
    "ла",
    "ле",
    "оглы",
    "сан",
    "фон",
    "эль",
}
OUTER_WRAPPER_PAIRS = (
    ("\u00ab", "\u00bb"),
    ('"', '"'),
    ("(", ")"),
    ("[", "]"),
)
NBSP = "\u00a0"
MORPH = pymorphy3.MorphAnalyzer() if pymorphy3 is not None else None


class FormObservation:
    def __init__(self) -> None:
        self.variants = Counter()
        self.evidence_sources = Counter()

    def add(self, stressed_plus: str, evidence: str) -> None:
        self.variants[stressed_plus] += 1
        self.evidence_sources[evidence] += 1

    @property
    def total_count(self) -> int:
        return sum(self.variants.values())

    def winner(self) -> Tuple[Optional[str], int]:
        if not self.variants:
            return None, 0
        stressed, count = self.variants.most_common(1)[0]
        return stressed, count


class LemmaRecord:
    def __init__(self, lemma: str, lemma_stressed: str, noun_class: str, evidence_source: str) -> None:
        self.lemma = lemma
        self.lemma_stressed = lemma_stressed
        self.noun_class = noun_class
        self.evidence_source = evidence_source
        self.observed_count = 0
        self.surface_forms = defaultdict(FormObservation)
        self.lemma_variants = Counter()

    def add_observed(self, surface: str, stressed_plus: str, evidence: str) -> None:
        self.surface_forms[surface].add(stressed_plus, evidence)
        self.observed_count += 1

    def add_lemma_variant(self, stressed_plus: str, evidence: str) -> None:
        self.lemma_variants[stressed_plus] += 1
        self.surface_forms[self.lemma].add(stressed_plus, evidence)

    def canonical_lemma(self) -> str:
        return self.lemma_variants.most_common(1)[0][0] if self.lemma_variants else self.lemma_stressed


def normalize_template_accents(text: str) -> str:
    return STRESS_TEMPLATE_RE.sub(r"\1" + ACCENT, text)


def normalize_spacing(text: str) -> str:
    return text.replace(NBSP, " ")


def strip_wiki_templates(text: str) -> str:
    previous = None
    cleaned = text
    while cleaned != previous:
        previous = cleaned
        cleaned = re.sub(r"\{\{[^{}]*\}\}", "", cleaned)
    return cleaned


def clean_wikitext(text: str) -> str:
    cleaned = normalize_template_accents(normalize_spacing(html.unescape(text)))
    cleaned = COMMENT_RE.sub("", cleaned)
    cleaned = REF_RE.sub("", cleaned)
    cleaned = EXTERNAL_LINK_RE.sub(r"\2", cleaned)
    cleaned = WIKI_LINK_WITH_LABEL_RE.sub(r"\1", cleaned)
    cleaned = WIKI_LINK_RE.sub(r"\1", cleaned)
    cleaned = cleaned.replace("'''", "").replace("''", "")
    cleaned = strip_wiki_templates(cleaned)
    cleaned = HTML_TAG_RE.sub("", cleaned)
    return cleaned


def get_lead_text(text: str, limit: int = 8000) -> str:
    match = HEADING_RE.search(text)
    lead = text[: match.start()] if match else text[:limit]
    return lead[:limit]


def strip_title_disambiguation(title: str) -> str:
    return TITLE_PAREN_RE.sub("", title).strip()


def remove_stress(text: str) -> str:
    return text.replace(ACCENT, "")


def count_stresses(text: str) -> int:
    return text.count(ACCENT) + text.count("ё") + text.count("Ё")


def stressed_to_plus_any(text: str) -> Optional[str]:
    result: List[str] = []
    stress_count = 0
    for char in text:
        if char == ACCENT:
            if not result:
                return None
            result.insert(len(result) - 1, "+")
            stress_count += 1
            continue
        if char in ("ё", "Ё"):
            result.append("+")
            result.append(char)
            stress_count += 1
            continue
        result.append(char)
    if stress_count < 1:
        return None
    return "".join(result)


def stressed_to_plus(text: str) -> Optional[str]:
    plus_text = stressed_to_plus_any(text)
    if plus_text is None or plus_text.count("+") != 1:
        return None
    return plus_text


def plus_to_stressed(text: str) -> str:
    result: List[str] = []
    pending_stress = False
    for char in text:
        if char == "+":
            pending_stress = True
            continue
        result.append(char)
        if pending_stress and char in VOWELS:
            result.append(ACCENT)
            pending_stress = False
    return "".join(result)


def clean_surface_key(text: str) -> str:
    return NON_LETTER_RE.sub("", text).strip("-")


def clean_surface_sequence(text: str) -> str:
    text = remove_stress(text)
    return " ".join(re.sub(r"[^A-Za-zА-Яа-яЁё-]+", " ", text).split())


def normalize_observed_text(text: str) -> str:
    normalized = normalize_spacing(text).strip()
    normalized = EXTERNAL_LINK_RE.sub(r"\2", normalized)
    normalized = strip_wiki_templates(normalized)
    normalized = HTML_TAG_RE.sub("", normalized)
    normalized = EMPTY_PARENS_RE.sub("", normalized)
    changed = True
    while changed and len(normalized) >= 2:
        changed = False
        for left, right in OUTER_WRAPPER_PAIRS:
            if normalized.startswith(left) and normalized.endswith(right):
                inner = normalized[len(left) : len(normalized) - len(right)].strip()
                if re.search(r"[A-Za-zА-Яа-яЁё]", inner):
                    normalized = inner
                    changed = True
                    break
    normalized = LEADING_NORMALIZATION_JUNK_RE.sub("", normalized)
    normalized = TRAILING_NORMALIZATION_JUNK_RE.sub("", normalized)
    return normalized.strip()


def title_surface_variants(title: str) -> List[str]:
    base_title = strip_title_disambiguation(title).strip()
    variants = [base_title]
    if "," in base_title:
        head, tail = [part.strip() for part in base_title.split(",", 1)]
        if head and tail:
            variants.append(f"{tail} {head}".strip())
    return variants


def normalize_stress_mapping(data: Dict[str, str]) -> Dict[str, str]:
    normalized: Dict[str, str] = {}
    for key, value in data.items():
        normalized_key = normalize_observed_text(key)
        normalized_value = normalize_observed_text(value)
        if normalized_key not in normalized:
            normalized[normalized_key] = normalized_value
    return normalized


def is_single_word(text: str) -> bool:
    return bool(text) and " " not in text and "-" not in text


def build_title_match_regex(title: str):
    pieces: List[str] = []
    for char in title:
        if char in VOWELS:
            pieces.append(re.escape(char) + f"{ACCENT}?")
        else:
            pieces.append(re.escape(char))
    return re.compile("".join(pieces))


def is_title_token(token: str) -> bool:
    normalized = token.strip(".,:;!?()[]{}\"'«»")
    if not normalized:
        return False
    if normalized.lower() in LOWERCASE_NAME_PARTICLES:
        return True
    if ROMAN_NUMERAL_RE.fullmatch(normalized):
        return True
    return normalized[0].isupper()


def title_case_score(title: str) -> bool:
    tokens = [t for t in re.split(r"[\s-]+", title) if t]
    if not tokens:
        return False
    return all(is_title_token(token) for token in tokens)


def classify_page(title: str, lead_clean: str, categories: Sequence[str], templates: Sequence[str]) -> Optional[str]:
    title_for_classification = title_surface_variants(title)[-1]
    if not title_case_score(title_for_classification):
        return None

    lower_templates = " | ".join(template.lower() for template in templates)
    lower_categories = " | ".join(category.lower() for category in categories)
    lower_lead = lead_clean[:1500].lower()
    early_lead = lower_lead[:800]
    title_tokens = [token for token in re.split(r"[\s-]+", title_for_classification) if token]
    multi_token_title = len(title_tokens) > 1
    lower_title = title_for_classification.lower()
    surname_like = any(lower_title.endswith(suffix) for suffix in SURNAME_LIKE_SUFFIXES)

    if lower_title in GENERIC_TITLE_BLACKLIST:
        return None

    if any(keyword in lower_templates for keyword in TOPONYM_TEMPLATE_KEYWORDS):
        return "toponym"
    if any(keyword in lower_categories for keyword in TOPONYM_CATEGORY_KEYWORDS):
        return "toponym"
    if multi_token_title and any(re.search(r"\b" + re.escape(keyword) + r"\b", early_lead) for keyword in TOPONYM_LEAD_KEYWORDS):
        return "toponym"

    if any(keyword in lower_templates for keyword in OTHER_PROPER_TEMPLATE_KEYWORDS):
        return "proper_noun_other"
    if any(keyword in lower_categories for keyword in OTHER_PROPER_CATEGORY_KEYWORDS):
        return "proper_noun_other"
    if (multi_token_title or surname_like) and any(
        re.search(r"\b" + re.escape(keyword) + r"\b", early_lead) for keyword in OTHER_PROPER_LEAD_KEYWORDS
    ):
        return "proper_noun_other"

    if multi_token_title and all(token[:1].isupper() for token in title_tokens):
        return "proper_noun_other"

    return None


def iter_stressed_tokens(text: str) -> Iterator[str]:
    for match in WORD_CHARS_RE.finditer(text):
        token = match.group(0)
        if count_stresses(token) != 1:
            continue
        yield token


def extract_matching_bold_candidate(
    title: str,
    lead_wikitext: str,
    allow_multiple_stresses: bool = False,
) -> Optional[Tuple[str, str]]:
    title_keys = {clean_surface_sequence(variant) for variant in title_surface_variants(title)}
    for match in BOLD_RE.finditer(lead_wikitext):
        candidate = clean_wikitext(match.group(1)).strip()
        stress_count = count_stresses(candidate)
        if stress_count < 1:
            continue
        if not allow_multiple_stresses and stress_count != 1:
            continue
        if clean_surface_sequence(candidate) not in title_keys:
            continue
        stressed_plus = stressed_to_plus_any(candidate) if allow_multiple_stresses else stressed_to_plus(candidate)
        if stressed_plus:
            return remove_stress(candidate), stressed_plus
    return None


def extract_canonical_title_form(title: str, lead_wikitext: str) -> Optional[Tuple[str, str]]:
    normalized_lead = clean_wikitext(lead_wikitext)
    for matched in (extract_matching_bold_candidate(title, lead_wikitext),):
        if matched:
            return matched

    base_title = title_surface_variants(title)[-1]
    base_title_clean = clean_surface_key(base_title)
    if not base_title_clean:
        return None

    pattern = build_title_match_regex(base_title)
    for match in pattern.finditer(normalized_lead):
        candidate = match.group(0)
        if count_stresses(candidate) != 1:
            continue
        if clean_surface_key(remove_stress(candidate)) == base_title_clean:
            stressed_plus = stressed_to_plus(candidate)
            if stressed_plus:
                return remove_stress(candidate), stressed_plus
    return None


def extract_person_name_form(title: str, lead_wikitext: str) -> Optional[Tuple[str, str]]:
    title_variants = title_surface_variants(title)
    variant_tokens = [meaningful_name_tokens(variant) for variant in title_variants]

    for match in BOLD_RE.finditer(lead_wikitext):
        candidate = clean_wikitext(match.group(1)).strip()
        if count_stresses(candidate) < 1:
            continue
        candidate_tokens = meaningful_name_tokens(candidate)
        if len(candidate_tokens) < 2:
            continue
        for tokens in variant_tokens:
            if len(tokens) < 2:
                continue
            if candidate_tokens[0] == tokens[0] and candidate_tokens[-1] == tokens[-1]:
                stressed_plus = stressed_to_plus_any(candidate)
                if stressed_plus:
                    return remove_stress(candidate), stressed_plus
    return None


def pick_plural_vowel(stem_last: str) -> str:
    return "и" if stem_last.lower() in "гкхжчшщйь" else "ы"


def apply_stress_by_vowel_index(surface: str, vowel_index: int) -> Optional[str]:
    current = -1
    for idx, char in enumerate(surface):
        if char.lower() in "аеёиоуыэюя":
            current += 1
            if current == vowel_index:
                if char in ("ё", "Ё"):
                    return surface
                return surface[: idx + 1] + ACCENT + surface[idx + 1 :]
    return None


def plus_with_same_vowel(surface: str, lemma_plus: str) -> Optional[str]:
    vowel_index = -1
    target_vowel = None
    pending_plus = False
    for char in lemma_plus:
        if char == "+":
            pending_plus = True
            continue
        if char.lower() in "аеёиоуыэюя":
            vowel_index += 1
            if pending_plus and target_vowel is None:
                target_vowel = vowel_index
                pending_plus = False
    if target_vowel is None or target_vowel < 0:
        return None
    stressed_surface = apply_stress_by_vowel_index(surface, target_vowel)
    return stressed_to_plus(stressed_surface) if stressed_surface else None


def generate_forms_rule_based(lemma: str, lemma_plus: str) -> Dict[str, str]:
    forms: Dict[str, str] = {}

    def add_form(surface: str) -> None:
        stressed_plus = plus_with_same_vowel(surface, lemma_plus)
        if stressed_plus:
            forms[surface] = stressed_plus

    lower = lemma.lower()
    if lower.endswith("а"):
        stem = lemma[:-1]
        plural_vowel = pick_plural_vowel(stem[-1]) if stem else "ы"
        gen_sg = stem + ("и" if stem and stem[-1].lower() in "гкхжчшщ" else "ы")
        for surface in (
            lemma,
            gen_sg,
            stem + "е",
            stem + "у",
            stem + "ой",
            stem + "ою",
            stem + plural_vowel,
            stem,
            stem + "ам",
            stem + "ами",
            stem + "ах",
        ):
            add_form(surface)
        return forms

    if lower.endswith("я"):
        stem = lemma[:-1]
        for surface in (
            lemma,
            stem + "и",
            stem + "е",
            stem + "ю",
            stem + "ей",
            stem + "ею",
            stem + "и",
            stem + "ь",
            stem + "ям",
            stem + "ями",
            stem + "ях",
        ):
            add_form(surface)
        return forms

    if lower.endswith("й") or lower.endswith("ь"):
        stem = lemma[:-1]
        for surface in (
            lemma,
            stem + "я",
            stem + "ю",
            stem + "ем",
            stem + "и",
            stem + "ев",
            stem + "ям",
            stem + "ями",
            stem + "ях",
        ):
            add_form(surface)
        return forms

    if re.search(r"[А-Яа-яЁё]$", lemma):
        stem = lemma
        plural_vowel = pick_plural_vowel(stem[-1])
        gen_pl_suffix = "ев" if stem[-1].lower() in "жчшщц" else "ов"
        for surface in (
            lemma,
            stem + "а",
            stem + "у",
            stem + "ом",
            stem + plural_vowel,
            stem + gen_pl_suffix,
            stem + "ам",
            stem + "ами",
            stem + "ах",
        ):
            add_form(surface)
        return forms

    return forms


def generate_forms_pymorphy3(lemma: str, lemma_plus: str) -> Dict[str, str]:
    if MORPH is None:
        return {}

    target_pos = "NOUN" if lemma and lemma[0].isupper() else None
    lemma_lower = lemma.lower()
    candidates = []
    for parse in MORPH.parse(lemma):
        if parse.normal_form != lemma.lower():
            continue
        if target_pos and parse.tag.POS != target_pos:
            continue
        candidates.append(parse)
    if not candidates:
        candidates = [parse for parse in MORPH.parse(lemma) if parse.tag.POS == "NOUN"] or MORPH.parse(lemma)

    forms: Dict[str, str] = {}
    for parse in candidates[:3]:
        try:
            lexeme = parse.lexeme
        except Exception:
            continue
        candidate_forms: Dict[str, str] = {}
        for form in lexeme:
            surface = form.word
            if not surface or "-" in surface or " " in surface:
                continue
            lower_surface = surface.lower()
            common_prefix = 0
            for expected, actual in zip(lemma_lower, lower_surface):
                if expected != actual:
                    break
                common_prefix += 1
            if common_prefix < max(3, len(lemma_lower) - 1):
                continue
            if lemma[:1].isupper():
                surface = surface[:1].upper() + surface[1:]
            stressed_plus = plus_with_same_vowel(surface, lemma_plus)
            if stressed_plus:
                candidate_forms[surface] = stressed_plus
        if lemma not in candidate_forms:
            continue
        forms.update(candidate_forms)
        if forms:
            break
    return forms


def split_plus_words(text: str) -> List[str]:
    return WORD_PLUS_RE.findall(text)


def meaningful_name_tokens(text: str) -> List[str]:
    return [
        token
        for token in re.split(r"[\s-]+", clean_surface_sequence(text))
        if token and token.lower() not in LOWERCASE_NAME_PARTICLES and not ROMAN_NUMERAL_RE.fullmatch(token)
    ]


def derive_person_aliases(full_surface: str, full_plus: str) -> Dict[str, str]:
    surfaces = split_plus_words(full_surface)
    stressed = split_plus_words(full_plus)
    if len(surfaces) != len(stressed) or not surfaces:
        return {}

    meaningful_indices = [
        index
        for index, surface in enumerate(surfaces)
        if surface.lower() not in LOWERCASE_NAME_PARTICLES and not ROMAN_NUMERAL_RE.fullmatch(surface)
    ]
    if not meaningful_indices:
        return {}

    aliases: Dict[str, str] = {full_surface: full_plus}
    first_index = meaningful_indices[0]
    last_index = meaningful_indices[-1]

    first_surface = surfaces[first_index]
    first_plus = stressed[first_index]
    if first_plus.count("+") == 1:
        aliases[first_surface] = first_plus

    last_surface = surfaces[last_index]
    last_plus = stressed[last_index]
    if last_plus.count("+") == 1:
        aliases[last_surface] = last_plus

    if first_index != last_index and first_plus.count("+") == 1 and last_plus.count("+") == 1:
        aliases[f"{first_surface} {last_surface}"] = f"{first_plus} {last_plus}"
        aliases[f"{last_surface} {first_surface}"] = f"{last_plus} {first_plus}"

    return aliases


def is_priority_full_name(surface: str, stressed_plus: str, noun_class: str) -> bool:
    if noun_class != "proper_noun_other" or " " not in surface:
        return False
    words = split_plus_words(surface)
    if len(words) < 2:
        return False
    meaningful = [word for word in words if word.lower() not in LOWERCASE_NAME_PARTICLES]
    return len(meaningful) >= 2 and stressed_plus.count("+") >= 1


def generate_forms(lemma: str, lemma_plus: str, noun_class: str) -> Dict[str, str]:
    if not is_single_word(lemma):
        return {}
    generated = generate_forms_pymorphy3(lemma, lemma_plus)
    if generated:
        return generated
    return generate_forms_rule_based(lemma, lemma_plus)


def categories_from_text(text: str) -> List[str]:
    return CATEGORY_RE.findall(text)


def templates_from_text(text: str, limit: int = 4000) -> List[str]:
    template_names: List[str] = []
    seen: Set[str] = set()
    for match in TEMPLATE_NAME_RE.finditer(text[:limit]):
        name = match.group(1).strip().lower()
        if not name or name in seen:
            continue
        seen.add(name)
        template_names.append(name)
    return template_names


def extract_observed_forms(
    text: str,
    expected_surfaces: Set[str],
) -> Dict[str, Counter]:
    observed: Dict[str, Counter] = defaultdict(Counter)
    cleaned = clean_wikitext(text)
    for token in iter_stressed_tokens(cleaned):
        surface = remove_stress(token)
        surface = clean_surface_key(surface)
        if surface in expected_surfaces:
            stressed_plus = stressed_to_plus(token)
            if stressed_plus:
                observed[surface][stressed_plus] += 1
    return observed


def pick_class_keys(noun_class: str) -> Sequence[str]:
    if noun_class == "toponym":
        return ("toponym", "all")
    return ("proper_noun_other", "all")


def write_python_dict(path: Path, variable_name: str, data: Dict[str, str]) -> None:
    items = sorted(normalize_stress_mapping(data).items(), key=lambda item: item[0].lower())
    lines = [f"{variable_name} = {{"]
    for key, value in items:
        lines.append(f"    {key!r}: {value!r},")
    lines.append("}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_python_dict(path: Path) -> Tuple[str, Dict[str, str]]:
    module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in module.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            continue
        value = ast.literal_eval(node.value)
        if not isinstance(value, dict):
            continue
        if not all(isinstance(key, str) and isinstance(item, str) for key, item in value.items()):
            continue
        return target.id, value
    raise ValueError(f"Could not find a string-to-string dict assignment in {path}")


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def iter_pages(xml_path: Path) -> Iterator[Tuple[str, str, str, bool]]:
    namespace = "{http://www.mediawiki.org/xml/export-0.11/}"
    for event, elem in ET.iterparse(str(xml_path), events=("end",)):
        if elem.tag != f"{namespace}page":
            continue

        title = elem.findtext(f"{namespace}title") or ""
        ns = elem.findtext(f"{namespace}ns") or ""
        redirect = elem.find(f"{namespace}redirect") is not None
        revision = elem.find(f"{namespace}revision")
        text = ""
        if revision is not None:
            text_elem = revision.find(f"{namespace}text")
            text = text_elem.text or ""

        yield title, ns, text, redirect
        elem.clear()


def build_outputs(records: Dict[Tuple[str, str], LemmaRecord]) -> Tuple[Dict[str, Dict[str, str]], List[dict]]:
    outputs = {
        "toponyms_observed": {},
        "toponyms_observed_generated": {},
        "proper_nouns_observed": {},
        "proper_nouns_observed_generated": {},
        "proper_nouns_priority_full_names": {},
        "all_proper_nouns_observed": {},
        "all_proper_nouns_observed_generated": {},
        "all_proper_nouns_observed_single_variant": {},
        "all_proper_nouns_observed_most_frequent": {},
        "all_proper_nouns_priority_full_names": {},
    }
    diagnostics: List[dict] = []

    for (_, noun_class), record in sorted(records.items()):
        observed_main: Dict[str, str] = {}
        generated_main: Dict[str, str] = {}
        single_variant_main: Dict[str, str] = {}
        priority_full_names_main: Dict[str, str] = {}
        conflict_entries = []

        normalized_surface_forms: Dict[str, FormObservation] = defaultdict(FormObservation)
        for surface, observation in record.surface_forms.items():
            normalized_surface = normalize_observed_text(surface)
            normalized_observation = normalized_surface_forms[normalized_surface]
            for stressed_plus, count in observation.variants.items():
                normalized_observation.variants[normalize_observed_text(stressed_plus)] += count
            for evidence, count in observation.evidence_sources.items():
                normalized_observation.evidence_sources[evidence] += count

        for surface, observation in sorted(normalized_surface_forms.items()):
            winner, winner_count = observation.winner()
            if not winner:
                continue
            total = observation.total_count
            if total > winner_count:
                conflict_entries.append(
                    {
                        "surface": surface,
                        "winner": winner,
                        "winner_count": winner_count,
                        "total_count": total,
                        "variants": dict(observation.variants),
                    }
                )
            observed_main[surface] = winner
            if len(observation.variants) == 1:
                single_variant_main[surface] = winner
            if is_priority_full_name(surface, winner, noun_class):
                priority_full_names_main[surface] = winner

        generated_forms = generate_forms(record.lemma, record.canonical_lemma(), noun_class)
        for surface, stressed_plus in generated_forms.items():
            generated_main[surface] = stressed_plus

        target_names = pick_class_keys(noun_class)
        for target in target_names:
            if target == "toponym":
                outputs["toponyms_observed"].update(observed_main)
                outputs["toponyms_observed_generated"].update(generated_main)
                outputs["toponyms_observed_generated"].update(observed_main)
            elif target == "proper_noun_other":
                outputs["proper_nouns_observed"].update(observed_main)
                outputs["proper_nouns_observed_generated"].update(generated_main)
                outputs["proper_nouns_observed_generated"].update(observed_main)
                outputs["proper_nouns_priority_full_names"].update(priority_full_names_main)
            elif target == "all":
                outputs["all_proper_nouns_observed"].update(observed_main)
                outputs["all_proper_nouns_observed_generated"].update(generated_main)
                outputs["all_proper_nouns_observed_generated"].update(observed_main)
                outputs["all_proper_nouns_observed_single_variant"].update(single_variant_main)
                outputs["all_proper_nouns_observed_most_frequent"].update(observed_main)
                outputs["all_proper_nouns_priority_full_names"].update(priority_full_names_main)

        diagnostics.append(
            {
                "lemma": record.lemma,
                "lemma_stressed": record.canonical_lemma(),
                "noun_class": noun_class,
                "evidence_source": record.evidence_source,
                "observed_count": record.observed_count,
                "surface_form_count": len(record.surface_forms),
                "lemma_variants": dict(record.lemma_variants),
                "conflicts": conflict_entries,
            }
        )

    return outputs, diagnostics


def process_dump(xml_path: Path, max_pages: Optional[int], progress_every: int) -> Tuple[Dict[str, Dict[str, str]], dict]:
    records: Dict[Tuple[str, str], LemmaRecord] = {}
    stats = Counter()

    for page_index, (title, ns, text, redirect) in enumerate(iter_pages(xml_path), start=1):
        if max_pages is not None and page_index > max_pages:
            break
        stats["pages_seen"] += 1
        if progress_every and page_index % progress_every == 0:
            print(f"Processed {page_index} pages...", file=sys.stderr)
        if ns != "0" or redirect or not text:
            stats["pages_skipped_ns_or_redirect"] += 1
            continue

        lead = get_lead_text(text)
        lead_clean = clean_wikitext(lead)
        categories = categories_from_text(text)
        templates = templates_from_text(text)
        noun_class = classify_page(strip_title_disambiguation(title), lead_clean, categories, templates)
        if not noun_class:
            stats["pages_skipped_not_proper_noun"] += 1
            continue

        canonical = extract_canonical_title_form(title, lead)
        person_name_form = extract_person_name_form(title, lead) if noun_class == "proper_noun_other" else None
        person_aliases: Dict[str, str] = {}
        if person_name_form:
            person_aliases = derive_person_aliases(*person_name_form)

        if not canonical and person_aliases:
            surname_candidates = [(surface, stressed_plus) for surface, stressed_plus in person_aliases.items() if " " not in surface]
            canonical = surname_candidates[-1] if surname_candidates else None

        if not canonical:
            stats["pages_skipped_no_stressed_title"] += 1
            continue

        lemma, lemma_plus = canonical
        if count_stresses(plus_to_stressed(lemma_plus)) != 1:
            stats["pages_skipped_multi_stress"] += 1
            continue

        key = (lemma, noun_class)
        record = records.get(key)
        if record is None:
            record = LemmaRecord(
                lemma=lemma,
                lemma_stressed=lemma_plus,
                noun_class=noun_class,
                evidence_source="lead_title_match",
            )
            records[key] = record

        record.add_lemma_variant(lemma_plus, "lead_title_match")
        for surface, stressed_plus in person_aliases.items():
            record.add_observed(surface, stressed_plus, "lead_title_match")

        expected_surfaces = set(generate_forms(lemma, lemma_plus, noun_class))
        expected_surfaces.add(lemma)
        expected_surfaces.update(surface for surface in person_aliases if " " not in surface)
        observed = extract_observed_forms(text, expected_surfaces)
        for surface, variants in observed.items():
            for stressed_plus, count in variants.items():
                for _ in range(count):
                    evidence = "full_text_match" if surface != lemma else "lead_title_match"
                    record.add_observed(surface, stressed_plus, evidence)
        stats[f"accepted_{noun_class}"] += 1

    outputs, diagnostics = build_outputs(records)
    summary = {
        "stats": dict(stats),
        "diagnostics": diagnostics,
    }
    return outputs, summary


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract stressed proper nouns from a Russian Wikipedia XML dump.")
    parser.add_argument("xml_path", type=Path, help="Path to ruwiki-latest-pages-articles.xml")
    parser.add_argument("--output-dir", type=Path, default=Path("stress_output"), help="Directory for generated files")
    parser.add_argument("--max-pages", type=int, default=None, help="Optional page limit for test runs")
    parser.add_argument("--progress-every", type=int, default=5000, help="Progress report interval")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    outputs, summary = process_dump(args.xml_path, args.max_pages, args.progress_every)

    write_python_dict(args.output_dir / "toponyms_observed.py", "toponyms_observed", outputs["toponyms_observed"])
    write_python_dict(
        args.output_dir / "toponyms_observed_generated.py",
        "toponyms_observed_generated",
        outputs["toponyms_observed_generated"],
    )
    write_python_dict(
        args.output_dir / "proper_nouns_observed.py",
        "proper_nouns_observed",
        outputs["proper_nouns_observed"],
    )
    write_python_dict(
        args.output_dir / "proper_nouns_observed_generated.py",
        "proper_nouns_observed_generated",
        outputs["proper_nouns_observed_generated"],
    )
    write_python_dict(
        args.output_dir / "proper_nouns_priority_full_names.py",
        "proper_nouns_priority_full_names",
        outputs["proper_nouns_priority_full_names"],
    )
    write_python_dict(
        args.output_dir / "all_proper_nouns_observed.py",
        "all_proper_nouns_observed",
        outputs["all_proper_nouns_observed"],
    )
    write_python_dict(
        args.output_dir / "all_proper_nouns_observed_generated.py",
        "all_proper_nouns_observed_generated",
        outputs["all_proper_nouns_observed_generated"],
    )
    write_python_dict(
        args.output_dir / "all_proper_nouns_observed_single_variant.py",
        "all_proper_nouns_observed_single_variant",
        outputs["all_proper_nouns_observed_single_variant"],
    )
    write_python_dict(
        args.output_dir / "all_proper_nouns_observed_most_frequent.py",
        "all_proper_nouns_observed_most_frequent",
        outputs["all_proper_nouns_observed_most_frequent"],
    )
    write_python_dict(
        args.output_dir / "all_proper_nouns_priority_full_names.py",
        "all_proper_nouns_priority_full_names",
        outputs["all_proper_nouns_priority_full_names"],
    )
    write_json(args.output_dir / "diagnostics.json", summary["diagnostics"])
    write_json(args.output_dir / "summary.json", summary["stats"])

    print(f"Wrote results to {args.output_dir}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
