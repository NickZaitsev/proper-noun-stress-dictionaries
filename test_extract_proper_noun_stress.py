import tempfile
import textwrap
import unittest
from pathlib import Path

from extract_proper_noun_stress import (
    ACCENT,
    MORPH,
    classify_page,
    clean_wikitext,
    derive_person_aliases,
    extract_canonical_title_form,
    extract_person_name_form,
    generate_forms,
    generate_forms_pymorphy3,
    generate_forms_rule_based,
    load_python_dict,
    normalize_stress_mapping,
    process_dump,
    stressed_to_plus,
    templates_from_text,
    write_python_dict,
)


SAMPLE_XML = textwrap.dedent(
    """\
    <mediawiki xmlns="http://www.mediawiki.org/xml/export-0.11/">
      <page>
        <title>Варшава</title>
        <ns>0</ns>
        <id>1</id>
        <revision>
          <text xml:space="preserve">'''Варша́ва''' — город в Польше.
    Жители Варша́вы любят Варша́ву и рассказывают о Варша́ве.
    [[Категория:Города Польши]]</text>
        </revision>
      </page>
      <page>
        <title>Зайнутдин</title>
        <ns>0</ns>
        <id>2</id>
        <revision>
          <text xml:space="preserve">'''Зайнутди́н''' — фамилия.
    Семья Зайнутди́на и разговор с Зайнутди́ну.
    [[Категория:Фамилии]]</text>
        </revision>
      </page>
      <page>
        <title>Арда</title>
        <ns>0</ns>
        <id>3</id>
        <revision>
          <text xml:space="preserve">'''А{{ударение}}рда''' — вымышленный мир.
    В А{{ударение}}рде живут герои.
    [[Категория:Литературные персонажи]]</text>
        </revision>
      </page>
    </mediawiki>
    """
)


class ExtractProperNounStressTests(unittest.TestCase):
    def test_extract_canonical_title_form_handles_combining_and_template_stress(self) -> None:
        self.assertEqual(
            extract_canonical_title_form("Варшава", "'''Варша́ва''' — город."),
            ("Варшава", "Варш+ава"),
        )
        self.assertEqual(
            extract_canonical_title_form("Арда", "'''А{{ударение}}рда''' — мир."),
            ("Арда", "+Арда"),
        )

    def test_classify_page_prefers_toponyms(self) -> None:
        self.assertEqual(
            classify_page("Варшава", "Варшава — город в Польше.", ["Города Польши"], []),
            "toponym",
        )
        self.assertEqual(
            classify_page("Зайнутдин", "Зайнутдин — фамилия.", ["Фамилии"], []),
            "proper_noun_other",
        )
        self.assertEqual(
            classify_page("Мизес, Людвиг фон", "Людвиг фон Мизес — экономист.", [], []),
            "proper_noun_other",
        )
        self.assertEqual(
            classify_page("Мизес, Людвиг фон", "Людвиг фон Мизес.", [], ["учёный"]),
            "proper_noun_other",
        )

    def test_templates_from_text_extracts_infobox_names(self) -> None:
        self.assertEqual(
            templates_from_text("{{Учёный| имя = Тест }}\n{{Либертарианство}}\ntext"),
            ["учёный", "либертарианство"],
        )

    def test_clean_wikitext_normalizes_nbsp(self) -> None:
        self.assertEqual(clean_wikitext("А.\u00a0Х.\u00a0Таммсааре"), "А. Х. Таммсааре")
        self.assertEqual(
            clean_wikitext(
                "Тарас Григорьевич{{ref+|текст [http://example.com 23 октября 1840 г.] <s>foo</s>|group=\"К\"}} Шевченко"
            ),
            "Тарас Григорьевич Шевченко",
        )

    def test_generate_forms_for_regular_patterns(self) -> None:
        generated = generate_forms("Варшава", "Варш+ава", "toponym")
        self.assertEqual(generated["Варшава"], "Варш+ава")
        self.assertEqual(generated["Варшавы"], "Варш+авы")
        self.assertEqual(generated["Варшаве"], "Варш+аве")

        generated = generate_forms("Зайнутдин", "Зайнутд+ин", "proper_noun_other")
        self.assertEqual(generated["Зайнутдин"], "Зайнутд+ин")
        self.assertEqual(generated["Зайнутдина"], "Зайнутд+ина")
        self.assertEqual(generated["Зайнутдину"], "Зайнутд+ину")

    def test_generate_forms_rule_based_still_available(self) -> None:
        generated = generate_forms_rule_based("Мизес", "М+изес")
        self.assertEqual(generated["Мизеса"], "М+изеса")
        self.assertEqual(generated["Мизесу"], "М+изесу")

    def test_generate_forms_pymorphy3_when_available(self) -> None:
        if MORPH is None:
            self.skipTest("pymorphy3 is not installed")
        generated = generate_forms_pymorphy3("Хайек", "Х+айек")
        self.assertEqual(generated, {"Хайек": "Х+айек"})

    def test_process_dump_builds_expected_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            xml_path = Path(tmp_dir) / "sample.xml"
            xml_path.write_text(SAMPLE_XML, encoding="utf-8")
            outputs, summary = process_dump(xml_path, max_pages=None, progress_every=0)

        self.assertEqual(outputs["toponyms_observed"]["Варшава"], "Варш+ава")
        self.assertEqual(outputs["toponyms_observed"]["Варшавы"], "Варш+авы")
        self.assertEqual(outputs["proper_nouns_observed"]["Зайнутдин"], "Зайнутд+ин")
        self.assertEqual(outputs["proper_nouns_observed"]["Арда"], "+Арда")
        self.assertEqual(outputs["all_proper_nouns_observed_generated"]["Варшаве"], "Варш+аве")
        self.assertGreaterEqual(summary["stats"]["accepted_toponym"], 1)

    def test_stressed_to_plus_rejects_multiple_stresses(self) -> None:
        self.assertIsNone(stressed_to_plus(f"бо{ACCENT}льша{ACCENT}я"))

    def test_extract_person_name_form_and_aliases_for_comma_title(self) -> None:
        lead = "'''Людвиг фон Ми\u0301зес''' — экономист."
        self.assertEqual(
            extract_person_name_form("Мизес, Людвиг фон", lead),
            ("Людвиг фон Мизес", "Людвиг фон М+изес"),
        )
        self.assertEqual(
            derive_person_aliases("Рихард Мартин эдлер фон Мизес", "Р+ихард Мартин эдлер фон М+изес"),
            {
                "Рихард Мартин эдлер фон Мизес": "Р+ихард Мартин эдлер фон М+изес",
                "Рихард": "Р+ихард",
                "Мизес": "М+изес",
                "Рихард Мизес": "Р+ихард М+изес",
                "Мизес Рихард": "М+изес Р+ихард",
            },
        )

    def test_normalize_stress_mapping_cleans_spaces_quotes_and_empty_parens(self) -> None:
        normalized = normalize_stress_mapping(
            {
                " Ястребов () ": " +Ястребов () ",
                "«Аль-Джазира»": "«Аль-Джаз+ира»",
                '"Бригантина"': '"Бригант+ина"',
                "(Муоткавара)": "(М+уоткавара)",
                ".Дмитрий Денисович Космович": ".Дм+итрий Ден+исович Косм+ович",
                'Тарас Григорьевич{{ref+|текст [http://example.com 23 октября 1840 г.] <s>foo</s>|group="К"}} Шевченко': 'Тар+ас Григ+орьевич{{ref+|текст [http://example.com 23 октября 1840 г.] <s>foo</s>|group="К"}} Шевч+енко',
                "А.\u00a0Х.\u00a0Таммсааре": "А.\u00a0Х.\u00a0Т+аммсааре",
                "Ярослав I": "Яросл+ав I",
            }
        )
        self.assertEqual(normalized["Ястребов"], "+Ястребов")
        self.assertEqual(normalized["Аль-Джазира"], "Аль-Джаз+ира")
        self.assertEqual(normalized["Бригантина"], "Бригант+ина")
        self.assertEqual(normalized["Муоткавара"], "М+уоткавара")
        self.assertEqual(normalized["Дмитрий Денисович Космович"], "Дм+итрий Ден+исович Косм+ович")
        self.assertEqual(normalized["Тарас Григорьевич Шевченко"], "Тар+ас Григ+орьевич Шевч+енко")
        self.assertEqual(normalized["А. Х. Таммсааре"], "А. Х. Т+аммсааре")
        self.assertEqual(normalized["Ярослав I"], "Яросл+ав I")

    def test_write_and_load_python_dict_preserve_variable_name_and_normalize(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "sample_dict.py"
            write_python_dict(
                path,
                "sample_dict",
                {
                    " «Аль-Каида» ": " «Аль-К+аида» ",
                    "Ястребов ()": "+Ястребов ()",
                    "«Рубин»": "«Руб+ин»",
                    "Рубин": "Р+убин",
                },
            )
            variable_name, payload = load_python_dict(path)

        self.assertEqual(variable_name, "sample_dict")
        self.assertEqual(payload["Аль-Каида"], "Аль-К+аида")
        self.assertEqual(payload["Ястребов"], "+Ястребов")
        self.assertIn("Рубин", payload)
        self.assertNotIn("«Рубин»", payload)

    def test_process_dump_extracts_person_surname_and_full_name_priority(self) -> None:
        sample_xml = textwrap.dedent(
            """\
            <mediawiki xmlns="http://www.mediawiki.org/xml/export-0.11/">
              <page>
                <title>Мизес, Людвиг фон</title>
                <ns>0</ns>
                <id>10</id>
                <revision>
                  <text xml:space="preserve">'''Людвиг фон Ми́зес''' — экономист.
            Работы Мизе́са и Людвига фон Ми́зеса оказали влияние.
            [[Категория:Экономисты Австрии]]</text>
                </revision>
              </page>
            </mediawiki>
            """
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            xml_path = Path(tmp_dir) / "sample.xml"
            xml_path.write_text(sample_xml, encoding="utf-8")
            outputs, summary = process_dump(xml_path, max_pages=None, progress_every=0)

        self.assertEqual(outputs["proper_nouns_observed"]["Мизес"], "М+изес")
        self.assertEqual(outputs["all_proper_nouns_observed"]["Мизес"], "М+изес")
        self.assertEqual(outputs["proper_nouns_priority_full_names"]["Людвиг фон Мизес"], "Людвиг фон М+изес")
        self.assertEqual(
            outputs["all_proper_nouns_observed_single_variant"]["Людвиг фон Мизес"],
            "Людвиг фон М+изес",
        )
        self.assertGreaterEqual(summary["stats"]["accepted_proper_noun_other"], 1)

    def test_process_dump_accepts_long_person_lead_with_profession_after_dates(self) -> None:
        sample_xml = textwrap.dedent(
            """\
            <mediawiki xmlns="http://www.mediawiki.org/xml/export-0.11/">
              <page>
                <title>Мизес, Рихард фон</title>
                <ns>0</ns>
                <id>11</id>
                <revision>
                  <text xml:space="preserve">'''Ри́хард Мартин эдлер фон Ми́зес''' (нем. Richard Edler von Mises, 19 апреля 1883, Лемберг, Австро-Венгрия (ныне Львов, Украина) — 14 июля 1953, Бостон, США) — математик и механик австрийского происхождения.
            [[Категория:Математики Австрии]]</text>
                </revision>
              </page>
            </mediawiki>
            """
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            xml_path = Path(tmp_dir) / "sample.xml"
            xml_path.write_text(sample_xml, encoding="utf-8")
            outputs, summary = process_dump(xml_path, max_pages=None, progress_every=0)

        self.assertEqual(outputs["all_proper_nouns_observed"]["Мизес"], "М+изес")
        self.assertEqual(outputs["all_proper_nouns_priority_full_names"]["Рихард Мартин эдлер фон Мизес"], "Р+ихард Мартин эдлер фон М+изес")
        self.assertGreaterEqual(summary["stats"]["accepted_proper_noun_other"], 1)


if __name__ == "__main__":
    unittest.main()
