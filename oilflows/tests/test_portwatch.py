import pandas as pd

from oilflows.portwatch import normalize_daily_rows


def test_normalize_daily_rows_filters_before_start_date():
    frame = pd.DataFrame(
        [
            {"date": "2025-06-21", "portid": "P1"},
            {"date": "2025-06-22", "portid": "P1"},
            {"date": "2025-06-23", "portid": "P1"},
        ]
    )

    result = normalize_daily_rows(frame, "2025-06-22")

    assert [str(value) for value in result["date"]] == ["2025-06-22", "2025-06-23"]
