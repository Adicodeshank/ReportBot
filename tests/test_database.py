"""
tests/test_database.py
----------------------
Unit tests for the database layer (app/database.py).

KEY CONCEPT - WHY WE MOCK THE DATABASE:
  A unit test must be:
    1. Fast        - no waiting for network or disk
    2. Isolated    - works even without a real PostgreSQL server
    3. Repeatable  - same result every single run

  If we connected to a real DB in tests, the test would fail if:
    - The DB is down
    - The data changed
    - Someone is running on a machine without PostgreSQL

  Instead we use unittest.mock.patch to replace the real
  SQLAlchemy engine with a fake one that returns data we control.
  The code under test never knows the difference.

RUN:
  pytest tests/test_database.py -v
"""

import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from datetime import date

from app.database import fetch_daily_summary, get_summary_dict


# == Shared test data ==========================================================

FAKE_DF = pd.DataFrame([{
    "report_date":      date(2026, 4, 20),
    "new_users":        3,
    "total_orders":     4,
    "total_revenue":    175.50,
    "avg_order_value":  103.88,
    "max_order_value":  200.00,
    "completed_orders": 2,
    "pending_orders":   1,
    "cancelled_orders": 1,
}])

EMPTY_DF = pd.DataFrame(columns=[
    "report_date", "new_users", "total_orders", "total_revenue",
    "avg_order_value", "max_order_value",
    "completed_orders", "pending_orders", "cancelled_orders"
])


# == Tests for fetch_daily_summary() ===========================================

class TestFetchDailySummary:

    @patch("app.database.pd.read_sql") # it is the address where the code will go to mock the data
    # =>>>>>>>>> pd.read_sql: This is the specific tool inside database.py that we want to replace. 
    @patch("app.database._engine")
    def test_returns_dataframe(self, mock_engine, mock_read_sql):
        """
        WHAT:  fetch_daily_summary() should return a DataFrame.
        WHY:   The calling code expects a DataFrame object.
               If this returns None or a dict everything downstream breaks.

        HOW THE MOCK WORKS:
          @patch replaces pd.read_sql inside the database module
          with a MagicMock. We set return_value = FAKE_DF so when
          the code calls pd.read_sql(...) it gets FAKE_DF back
          instead of actually hitting PostgreSQL.
        """

        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_engine.connect.return_value.__exit__  = MagicMock(return_value=False)
        # enter and exit are beacuse of the with block in fetch faily summary in app/database.py
        mock_read_sql.return_value = FAKE_DF 

        result = fetch_daily_summary() # when this function calls goes it gets the mocked data due to enter and exit system 

        assert isinstance(result, pd.DataFrame)

    @patch("app.database.pd.read_sql")
    @patch("app.database._engine")
    def test_returns_correct_columns(self, mock_engine, mock_read_sql):
        """
        WHAT:  The DataFrame must have all 9 expected columns.
        WHY:   report.py accesses specific keys. A missing column
               causes a KeyError at 8 AM with no one watching.
        """
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_engine.connect.return_value.__exit__  = MagicMock(return_value=False)
        mock_read_sql.return_value = FAKE_DF

        result = fetch_daily_summary()

        expected_columns = [
            "report_date", "new_users", "total_orders", "total_revenue",
            "avg_order_value", "max_order_value",
            "completed_orders", "pending_orders", "cancelled_orders"
        ]
        for col in expected_columns:
            assert col in result.columns, f"Column '{col}' missing"

    @patch("app.database.pd.read_sql")
    @patch("app.database._engine")
    def test_handles_empty_result(self, mock_engine, mock_read_sql):
        """
        WHAT:  fetch_daily_summary() should NOT crash on empty result.
        WHY:   On holidays there may be zero orders. The bot should
               send a zero report, not crash with an IndexError.
        """
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_engine.connect.return_value.__exit__  = MagicMock(return_value=False)
        mock_read_sql.return_value = EMPTY_DF

        result = fetch_daily_summary()

        assert isinstance(result, pd.DataFrame)


# == Tests for get_summary_dict() ==============================================

class TestGetSummaryDict:

    def test_returns_dict(self):
        """
        WHAT:  get_summary_dict() must return a plain Python dict.
        WHY:   .py accesses vareportlues with dict keys like s["new_users"].
               No mocking needed - pure data transformation, no DB calls.
        """
        result = get_summary_dict(FAKE_DF)
        assert isinstance(result, dict)

    def test_correct_values(self):
        """
        WHAT:  Dict values must exactly match the DataFrame row.
        WHY:   Silent data corruption is the worst kind of bug.
               If revenue shows 0 instead of 175.50 the manager
               gets a wrong report with no error raised.
        """
        result = get_summary_dict(FAKE_DF)

        assert result["new_users"]        == 3
        assert result["total_orders"]     == 4
        assert result["total_revenue"]    == 175.50
        assert result["completed_orders"] == 2
        assert result["pending_orders"]   == 1
        assert result["cancelled_orders"] == 1

    def test_correct_types(self):
        """
        WHAT:  Integer fields must be int, float fields must be float.
        WHY:   fpdf2 crashes if you pass numpy.int64 where it expects
               a plain Python int. Type safety prevents this entirely.
        """
        result = get_summary_dict(FAKE_DF)

        assert isinstance(result["new_users"],        int)
        assert isinstance(result["total_orders"],     int)
        assert isinstance(result["total_revenue"],    float)
        assert isinstance(result["avg_order_value"],  float)
        assert isinstance(result["completed_orders"], int)

    def test_empty_dataframe_returns_zeros(self):
        """
        WHAT:  Empty DataFrame must return a dict of zeros, not crash.
        WHY:   Holiday / outage scenario. The report should show zeros
               cleanly, not blow up with an IndexError at 8 AM.
        """
        result = get_summary_dict(EMPTY_DF)

        assert result["new_users"]        == 0
        assert result["total_orders"]     == 0
        assert result["total_revenue"]    == 0.0
        assert result["completed_orders"] == 0
        assert result["pending_orders"]   == 0
        assert result["cancelled_orders"] == 0

    def test_all_required_keys_present(self):
        """
        WHAT:  All 9 keys that report.py expects must exist.
        WHY:   One missing key = KeyError at runtime. This test
               catches that at test time instead of 8 AM.
        """
        result = get_summary_dict(FAKE_DF)

        required_keys = [
            "report_date", "new_users", "total_orders", "total_revenue",
            "avg_order_value", "max_order_value",
            "completed_orders", "pending_orders", "cancelled_orders"
        ]
        for key in required_keys:
            assert key in result, f"Key '{key}' missing from result"