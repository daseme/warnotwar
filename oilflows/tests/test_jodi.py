import pandas as pd

from oilflows.jodi import primary_year_urls, select_gulf_crude_exports


def test_primary_year_urls_support_both_jodi_filename_conventions():
    urls = primary_year_urls(2026)
    assert urls[0].endswith("/primaryyear2026.csv")
    assert urls[1].endswith("/2026.csv")


def test_select_gulf_crude_exports_filters_to_crude_export_kbd():
    frame = pd.DataFrame(
        [
            {
                "REF_AREA": "SA",
                "TIME_PERIOD": "2026-01",
                "ENERGY_PRODUCT": "CRUDEOIL",
                "FLOW_BREAKDOWN": "TOTEXPSB",
                "UNIT_MEASURE": "KBD",
                "OBS_VALUE": "6500",
                "ASSESSMENT_CODE": "1",
                "SOURCE_YEAR_FILE": 2026,
            },
            {
                "REF_AREA": "SA",
                "TIME_PERIOD": "2026-01",
                "ENERGY_PRODUCT": "CRUDEOIL",
                "FLOW_BREAKDOWN": "INDPROD",
                "UNIT_MEASURE": "KBD",
                "OBS_VALUE": "9000",
                "ASSESSMENT_CODE": "1",
                "SOURCE_YEAR_FILE": 2026,
            },
            {
                "REF_AREA": "US",
                "TIME_PERIOD": "2026-01",
                "ENERGY_PRODUCT": "CRUDEOIL",
                "FLOW_BREAKDOWN": "TOTEXPSB",
                "UNIT_MEASURE": "KBD",
                "OBS_VALUE": "4000",
                "ASSESSMENT_CODE": "1",
                "SOURCE_YEAR_FILE": 2026,
            },
        ]
    )

    result = select_gulf_crude_exports(frame)

    assert len(result) == 1
    assert result.iloc[0]["country_code"] == "SA"
    assert result.iloc[0]["crude_exports_kbd"] == 6500
