"""
Tests for data_loader.py module.
"""

import pytest
import pandas as pd

# Add parent directory to path for imports
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestDataValidation:
    """Tests for ENH-002: Data validation layer."""

    def test_validate_dataframe_with_required_columns(self):
        """Test validation passes when required columns exist."""
        from data_loader import validate_dataframe

        df = pd.DataFrame({"A": [1, 2], "B": [3, 4], "C": [5, 6]})
        result = validate_dataframe(df, ["A", "B"], "TestDF")
        assert result is True

    def test_validate_dataframe_missing_columns_raises(self):
        """Test validation raises error when columns missing."""
        from data_loader import validate_dataframe, DataValidationError

        df = pd.DataFrame({"A": [1, 2]})

        with pytest.raises(DataValidationError) as exc_info:
            validate_dataframe(df, ["A", "B", "C"], "TestDF")

        assert "missing required columns" in str(exc_info.value)
        assert "B" in str(exc_info.value)
        assert "C" in str(exc_info.value)

    def test_validate_dataframe_empty_df_returns_true(self):
        """Test validation returns True for empty DataFrame with warning."""
        from data_loader import validate_dataframe

        df = pd.DataFrame()
        result = validate_dataframe(df, ["A", "B"], "TestDF")
        assert result is True

    def test_validate_chamados_df_valid(self):
        """Test chamados validation with valid data."""
        from data_loader import validate_chamados_df

        df = pd.DataFrame({
            "SS": ["SS001"],
            "Tarefa": ["T001"],
            "Status": ["ABERTO"],
            "Chassi": ["123456"]
        })
        result = validate_chamados_df(df)
        assert result is True

    def test_validate_chamados_df_missing_columns(self):
        """Test chamados validation fails with missing columns."""
        from data_loader import validate_chamados_df, DataValidationError

        df = pd.DataFrame({"SS": ["SS001"]})  # Missing other required columns

        with pytest.raises(DataValidationError):
            validate_chamados_df(df)

    def test_validate_o2c_df_valid(self):
        """Test O2C validation with valid data."""
        from data_loader import validate_o2c_df

        df = pd.DataFrame({
            "NUM_SERIAL": ["123456"],
            "GARANTIA": [365]
        })
        result = validate_o2c_df(df)
        assert result is True

    def test_validate_rtm_errors_df_valid(self):
        """Test RTM errors validation with valid data."""
        from data_loader import validate_rtm_errors_df

        df = pd.DataFrame({"SS": ["SS001", "SS002"]})
        result = validate_rtm_errors_df(df)
        assert result is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
