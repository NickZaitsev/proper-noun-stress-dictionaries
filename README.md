# Словари ударений для имён собственных из русской Википедии

Этот репозиторий содержит уже готовую опубликованную сборку словарей ударений для имён собственных, извлечённых из дампа русской Википедии, а также скрипты, которыми эти словари были собраны и преобразованы.

Ударение кодируется знаком `+` перед ударной гласной:

- `М+изес`
- `Тар+ас`
- `Шевч+енко`

## Что лежит в репозитории

```text
.
├── PyDictionaries/
├── DemagogDictionaries/
├── extract_proper_noun_stress.py
├── normalize_stress_dictionary.py
├── make_unique_proper_noun_layers.py
├── export_python_dicts_to_dic.py
└── test_extract_proper_noun_stress.py
```

- `PyDictionaries/`
  Основная опубликованная сборка в формате Python-словарей `{'слово': 'сл+ово'}`.

- `DemagogDictionaries/`
  Те же словари в формате `key=value`, удобном для Demagog и похожих движков.

- `extract_proper_noun_stress.py`
  Главный скрипт извлечения из XML-дампа Википедии.

- `normalize_stress_dictionary.py`
  Нормализация готовых `*.py` словарей.

- `make_unique_proper_noun_layers.py`
  Построение `*_unique` слоёв без пересечений.

- `export_python_dicts_to_dic.py`
  Конвертация папки с Python-словарями в `.dic`-файлы.

- `test_extract_proper_noun_stress.py`
  Небольшой набор регрессионных тестов.

## С чего начинать

Если нужен просто готовый словарь без долгого разбора, обычно стоит смотреть в таком порядке:

1. `PyDictionaries/all_proper_nouns_priority_full_names.py`
2. `PyDictionaries/all_proper_nouns_observed_single_variant.py`
3. `PyDictionaries/all_proper_nouns_observed_most_frequent.py`
4. `PyDictionaries/all_proper_nouns_observed_generated.py`

То же самое есть в формате `.dic` в папке `DemagogDictionaries/`.

Если нужен максимально осторожный каскад, можно остановиться на первых трёх файлах и не использовать `generated`.

## Как читать названия словарей

Имена файлов состоят из понятных частей.

### По типу сущностей

- `toponyms_*` — только топонимы.
- `proper_nouns_*` — прочие имена собственные: люди, фамилии, персонажи и т. п.
- `all_proper_nouns_*` — объединение всего.

### По типу данных

- `observed` — только реально замеченные в Википедии формы.
- `generated` — наблюдённые формы плюс автоматически достроенные словоформы.
- `priority_full_names` — полные имена людей, которые желательно применять раньше общих словарей.
- `single_variant` — написания слов, для которых нашёлся ровно один вариант ударения.
- `most_frequent` — для каждого написания слова выбран самый частый наблюдённый вариант.
- `unique` — слой без пересечений с более приоритетными словарями.

## Форматы данных

### Python

Файлы из `PyDictionaries/` содержат обычные Python-словари:

```python
all_proper_nouns_observed = {
    'Августовка': 'Август+овка',
    'Авербух': 'Аверб+ух',
    'Авнер': '+Авнер',
}
```

### `.dic`

Файлы из `DemagogDictionaries/` содержат по одной паре на строку:

```text
Августовка=Август+овка
Авербух=Аверб+ух
Авнер=+Авнер
```

## Что именно опубликовано

В опубликованной сборке лежат:

- `14` Python-словарей в `PyDictionaries/`
- `14` `.dic`-словарей в `DemagogDictionaries/`
- `summary.json` с краткой статистикой прогона
- `diagnostics.json` с более подробной диагностикой

Краткая статистика текущей сборки:

- просмотрено страниц: `6,310,533`
- принято топонимов: `81,211`
- принято прочих имён собственных: `138,195`
- пропущено страниц без ударения в заголовке: `930,939`
- пропущено как не-имена собственные: `891,018`

## Какие файлы чаще всего нужны

- `PyDictionaries/all_proper_nouns_observed_single_variant.py`
  Один из самых надёжных общих словарей.

- `PyDictionaries/all_proper_nouns_observed_most_frequent.py`
  Хороший широкий словарь, если нужен практичный дефолт.

- `PyDictionaries/all_proper_nouns_priority_full_names.py`
  Полезно применять раньше общих словарей, чтобы корректнее обрабатывать полные имена.

- `DemagogDictionaries/all_proper_nouns_observed_most_frequent.dic`
  Удобный стартовый файл для систем, которым нужен формат `key=value`.

## Как пересобрать словари

### 1. Извлечь словари из дампа

```bash
python extract_proper_noun_stress.py ruwiki-latest-pages-articles.xml --output-dir PyDictionaries
```

Для пробного прогона:

```bash
python extract_proper_noun_stress.py ruwiki-latest-pages-articles.xml --max-pages 5000 --output-dir stress_output_sample
```

### 2. Построить `unique`-слои

```bash
python make_unique_proper_noun_layers.py PyDictionaries
```

### 3. При необходимости нормализовать конкретный словарь

```bash
python normalize_stress_dictionary.py PyDictionaries/all_proper_nouns_observed.py
```

### 4. Выгрузить `.dic`-версии

```bash
python export_python_dicts_to_dic.py PyDictionaries --output-dir DemagogDictionaries
```

## Зависимости

Основные скрипты используют стандартную библиотеку Python.

`pymorphy3` опционален и нужен для части морфологической генерации. Если его нет, базовая логика проекта всё равно остаётся рабочей, но покрытие `generated`-словарей может быть хуже.

## Лицензия

В репозитории используется раздельное лицензирование:

- код и скрипты: `MIT`, см. `LICENSE-MIT`
- словари и производные данные в `PyDictionaries/` и `DemagogDictionaries/`: `CC BY-SA 4.0`, см. `LICENSE-DATA`

Это сделано потому, что словари являются производными данными из текста Википедии, а для такого материала важны атрибуция и share-alike.

## Ограничения

Проект не угадывает ударение “из головы”. Он опирается на:

- уже проставленные ударения в статьях Википедии
- эвристики классификации страниц
- морфологическую генерацию словоформ
- перенос ударения по позиции ударной гласной

Поэтому:

- `observed` обычно надёжнее `generated`
- полные имена лучше применять раньше голых фамилий
- для спорных случаев лучше начинать с `single_variant`, а затем переходить к `most_frequent`
