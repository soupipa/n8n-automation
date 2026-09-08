
import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).parent

STRUCTURED_JSON = (
    BASE_DIR / "uploads" / "guide_2026_tp.json"
)

DICTIONARY_JSON = (
    BASE_DIR / "uploads" / "merged_dictionnaries.json"
)

OUTPUT_JSON = (
    BASE_DIR / "uploads" / "guide_2026_trilingual.json"
)

MISSING_TRANSLATIONS_JSON = (
    BASE_DIR / "uploads" / "missing_translations.json"
)

# ============================================================
# LOAD JSON
# ============================================================

def load_json(path):
    """
    Load a JSON file using UTF-8 encoding.
    """

    print(f"Loading: {path}")

    if not path.exists():
        raise FileNotFoundError(
            f"File not found: {path}"
        )

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ============================================================
# NORMALIZATION
# ============================================================

def normalize(text):
    """
    Normalize Arabic strings so that small formatting
    differences can still be matched.

    Examples:

        "كلية العلوم الإنسانية\nوالإجتماعية"

    and

        "كلية العلوم الإنسانية والإجتماعية"

    are normalized mainly by removing unnecessary
    whitespace/newlines.
    """

    if not isinstance(text, str):
        return text

    # Remove zero-width characters
    text = text.replace("\u200b", "")
    text = text.replace("\ufeff", "")

    # Convert all whitespace/newlines to one space
    text = re.sub(r"\s+", " ", text)

    return text.strip()


# ============================================================
# BUILD TRANSLATION DICTIONARY
# ============================================================

def build_translation_dictionary(dictionary_data):
    """
    Extract the masterDict from the dictionary JSON.

    Expected structure:

    {
        "masterDict": {
            "آداب": {
                "en": "Humanities",
                "fr": "Lettres"
            }
        }
    }

    Also supports:

    [
        {
            "masterDict": {
                ...
            }
        }
    ]
    """

    if isinstance(dictionary_data, dict):

        if "masterDict" in dictionary_data:
            master_dict = dictionary_data["masterDict"]
        else:
            # Allow the dictionary itself to be the master dictionary
            master_dict = dictionary_data

    elif isinstance(dictionary_data, list):

        if (
            len(dictionary_data) == 1
            and isinstance(dictionary_data[0], dict)
            and "masterDict" in dictionary_data[0]
        ):
            master_dict = dictionary_data[0]["masterDict"]

        else:
            raise ValueError(
                "Could not find masterDict in dictionary JSON."
            )

    else:

        raise ValueError(
            "Unsupported dictionary JSON structure."
        )

    if not isinstance(master_dict, dict):
        raise ValueError(
            "masterDict must be a JSON object/dictionary."
        )

    # --------------------------------------------------------
    # Create normalized dictionary
    # --------------------------------------------------------

    normalized_dict = {}

    for arabic_text, translations in master_dict.items():

        key = normalize(arabic_text)

        normalized_dict[key] = translations

    return master_dict, normalized_dict


# ============================================================
# TRANSLATE ONE VALUE
# ============================================================

def translate(
    value,
    language,
    master_dict,
    normalized_dict
):
    """
    Translate a single Arabic value.

    Matching order:

    1. Exact match
    2. Normalized match
    3. No translation -> None
    """

    if value is None:
        return None

    if not isinstance(value, str):
        return value

    # --------------------------------------------------------
    # 1. Exact match
    # --------------------------------------------------------

    if value in master_dict:

        translations = master_dict[value]

        if isinstance(translations, dict):
            return translations.get(language)

        return None

    # --------------------------------------------------------
    # 2. Normalized match
    # --------------------------------------------------------

    normalized_value = normalize(value)

    if normalized_value in normalized_dict:

        translations = normalized_dict[normalized_value]

        if isinstance(translations, dict):
            return translations.get(language)

        return None

    # --------------------------------------------------------
    # 3. No translation
    # --------------------------------------------------------

    return None


# ============================================================
# TRANSLATE SPECIALIZATIONS
# ============================================================

def translate_specializations(
    specializations,
    language,
    master_dict,
    normalized_dict
):
    """
    Translate every specialization in the list.
    """

    if not specializations:
        return []

    result = []

    for specialization in specializations:

        translation = translate(
            specialization,
            language,
            master_dict,
            normalized_dict
        )

        result.append(translation)

    return result


# ============================================================
# TRANSLATE ADMISSION OPTIONS
# ============================================================

def translate_admission_options(
    admission_options,
    master_dict,
    normalized_dict
):
    """
    Translate bac_type while keeping the other admission
    information unchanged.
    """

    if not admission_options:
        return []

    result = []

    for admission in admission_options:

        if not isinstance(admission, dict):
            continue

        bac_type = admission.get("bac_type")

        result.append(
            {
                # Arabic
                "bac_type": bac_type,

                # English
                "bac_type_en": translate(
                    bac_type,
                    "en",
                    master_dict,
                    normalized_dict
                ),

                # French
                "bac_type_fr": translate(
                    bac_type,
                    "fr",
                    master_dict,
                    normalized_dict
                ),

                # Keep these exactly as they are
                "score_formula": admission.get(
                    "score_formula"
                ),

                "capacity": admission.get(
                    "capacity"
                ),

                "last_admitted_score_2025": admission.get(
                    "last_admitted_score_2025"
                )
            }
        )

    return result


# ============================================================
# TRANSFORM ONE RECORD
# ============================================================

def transform_record(
    record,
    master_dict,
    normalized_dict
):
    """
    Transform one Arabic record into the trilingual format.
    """

    result = {

        # ----------------------------------------------------
        # CODE
        # ----------------------------------------------------

        "code": record.get("code"),

        # ----------------------------------------------------
        # DOMAIN
        # ----------------------------------------------------

        "domain": record.get("domain"),

        "domain_en": translate(
            record.get("domain"),
            "en",
            master_dict,
            normalized_dict
        ),

        "domain_fr": translate(
            record.get("domain"),
            "fr",
            master_dict,
            normalized_dict
        ),

        # ----------------------------------------------------
        # DEGREE TRACK
        # ----------------------------------------------------

        "degree_track": record.get("degree_track"),

        "degree_track_en": translate(
            record.get("degree_track"),
            "en",
            master_dict,
            normalized_dict
        ),

        "degree_track_fr": translate(
            record.get("degree_track"),
            "fr",
            master_dict,
            normalized_dict
        ),

        # ----------------------------------------------------
        # INSTITUTION
        # ----------------------------------------------------

        "institution": record.get("institution"),

        "institution_en": translate(
            record.get("institution"),
            "en",
            master_dict,
            normalized_dict
        ),

        "institution_fr": translate(
            record.get("institution"),
            "fr",
            master_dict,
            normalized_dict
        ),

        # ----------------------------------------------------
        # SPECIALIZATIONS
        # ----------------------------------------------------

        "specializations": record.get(
            "specializations",
            []
        ),

        "specializations_en": translate_specializations(
            record.get(
                "specializations",
                []
            ),
            "en",
            master_dict,
            normalized_dict
        ),

        "specializations_fr": translate_specializations(
            record.get(
                "specializations",
                []
            ),
            "fr",
            master_dict,
            normalized_dict
        ),

        # ----------------------------------------------------
        # ADMISSION OPTIONS
        # ----------------------------------------------------

        "admission_options": translate_admission_options(
            record.get(
                "admission_options",
                []
            ),
            master_dict,
            normalized_dict
        ),

        # ----------------------------------------------------
        # SOURCE PAGES
        # ----------------------------------------------------

        "source_pages": record.get(
            "source_pages",
            []
        )
    }

    return result


# ============================================================
# CHECK MISSING TRANSLATIONS
# ============================================================

def check_missing_translations(
    record,
    result,
    record_index,
    missing_translations
):
    """
    Check all translated fields and record missing
    translations.
    """

    # --------------------------------------------------------
    # Main fields
    # --------------------------------------------------------

    fields_to_check = [

        (
            "domain_en",
            record.get("domain")
        ),

        (
            "domain_fr",
            record.get("domain")
        ),

        (
            "degree_track_en",
            record.get("degree_track")
        ),

        (
            "degree_track_fr",
            record.get("degree_track")
        ),

        (
            "institution_en",
            record.get("institution")
        ),

        (
            "institution_fr",
            record.get("institution")
        )
    ]

    for field, original in fields_to_check:

        if (
            original is not None
            and result.get(field) is None
        ):

            missing_translations.append(
                {
                    "record_index": record_index,
                    "code": record.get("code"),
                    "field": field,
                    "arabic": original
                }
            )

    # --------------------------------------------------------
    # Specializations
    # --------------------------------------------------------

    original_specializations = record.get(
        "specializations",
        []
    )

    translated_en = result.get(
        "specializations_en",
        []
    )

    translated_fr = result.get(
        "specializations_fr",
        []
    )

    for i, specialization in enumerate(
        original_specializations
    ):

        # English
        if (
            i < len(translated_en)
            and translated_en[i] is None
        ):

            missing_translations.append(
                {
                    "record_index": record_index,
                    "code": record.get("code"),
                    "field": "specializations_en",
                    "index": i,
                    "arabic": specialization
                }
            )

        # French
        if (
            i < len(translated_fr)
            and translated_fr[i] is None
        ):

            missing_translations.append(
                {
                    "record_index": record_index,
                    "code": record.get("code"),
                    "field": "specializations_fr",
                    "index": i,
                    "arabic": specialization
                }
            )

    # --------------------------------------------------------
    # BAC type translations
    # --------------------------------------------------------

    for admission in result.get(
        "admission_options",
        []
    ):

        bac_type = admission.get("bac_type")

        if (
            bac_type is not None
            and admission.get("bac_type_en") is None
        ):

            missing_translations.append(
                {
                    "record_index": record_index,
                    "code": record.get("code"),
                    "field": "bac_type_en",
                    "arabic": bac_type
                }
            )

        if (
            bac_type is not None
            and admission.get("bac_type_fr") is None
        ):

            missing_translations.append(
                {
                    "record_index": record_index,
                    "code": record.get("code"),
                    "field": "bac_type_fr",
                    "arabic": bac_type
                }
            )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("TRILINGUAL JSON BUILDER")
    print("=" * 60)

    print()
    print("Configuration:")
    print(f"  Structured JSON : {STRUCTURED_JSON}")
    print(f"  Dictionary JSON : {DICTIONARY_JSON}")
    print(f"  Output JSON     : {OUTPUT_JSON}")
    print()

    # --------------------------------------------------------
    # Verify input files
    # --------------------------------------------------------

    if not STRUCTURED_JSON.exists():

        raise FileNotFoundError(
            f"Structured JSON not found:\n"
            f"{STRUCTURED_JSON}"
        )

    if not DICTIONARY_JSON.exists():

        raise FileNotFoundError(
            f"Dictionary JSON not found:\n"
            f"{DICTIONARY_JSON}"
        )

    # --------------------------------------------------------
    # Load original structured JSON
    # --------------------------------------------------------

    records = load_json(
        STRUCTURED_JSON
    )

    if not isinstance(records, list):

        raise ValueError(
            "guide_2026_structured.json "
            "must contain a JSON array."
        )

    print(
        f"Found {len(records)} records."
    )

    # --------------------------------------------------------
    # Load translation dictionary
    # --------------------------------------------------------

    dictionary_data = load_json(
        DICTIONARY_JSON
    )

    master_dict, normalized_dict = (
        build_translation_dictionary(
            dictionary_data
        )
    )

    print(
        f"Loaded {len(master_dict)} "
        f"translation entries."
    )

    # --------------------------------------------------------
    # Transform all records
    # --------------------------------------------------------

    output = []

    missing_translations = []

    for index, record in enumerate(records):

        if not isinstance(record, dict):

            print(
                f"WARNING: Record {index} "
                f"is not a JSON object. Skipping."
            )

            continue

        result = transform_record(
            record,
            master_dict,
            normalized_dict
        )

        output.append(result)

        # ----------------------------------------------------
        # Check missing translations
        # ----------------------------------------------------

        check_missing_translations(
            record,
            result,
            index,
            missing_translations
        )

    # --------------------------------------------------------
    # Make sure output directory exists
    # --------------------------------------------------------

    OUTPUT_JSON.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------------
    # Save final trilingual JSON
    # --------------------------------------------------------

    with open(
        OUTPUT_JSON,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            output,
            f,
            ensure_ascii=False,
            indent=2
        )

    # --------------------------------------------------------
    # Print statistics
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print("DONE")
    print("=" * 60)

    print(
        f"Records processed: {len(output)}"
    )

    print(
        f"Missing translations: "
        f"{len(missing_translations)}"
    )

    print(
        f"Output: {OUTPUT_JSON}"
    )

    # --------------------------------------------------------
    # Save missing translations
    # --------------------------------------------------------

    if missing_translations:

        print()
        print(
            "WARNING: Missing translations"
        )

        print("-" * 60)

        for missing in missing_translations[:50]:

            print(
                f"[{missing['code']}] "
                f"{missing['field']}: "
                f"{missing['arabic']}"
            )

        with open(
            MISSING_TRANSLATIONS_JSON,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                missing_translations,
                f,
                ensure_ascii=False,
                indent=2
            )

        print()
        print(
            f"Missing translations saved to: "
            f"{MISSING_TRANSLATIONS_JSON}"
        )

    else:

        # Remove an old missing-translations file if
        # there are no missing translations this time.

        if MISSING_TRANSLATIONS_JSON.exists():
            MISSING_TRANSLATIONS_JSON.unlink()

        print()
        print(
            "All checked translations were found."
        )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
