"""
Tests for business_logic.py module.
"""

import pytest
import pandas as pd
import numpy as np

# Add parent directory to path for imports
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestCreateDuracaoGarantiaColumn:
    """Tests for BUG-003: Integer conversion edge cases in create_duracao_garantia_column."""

    def test_valid_warranty_periods(self):
        """Test valid warranty period values are correctly mapped."""
        from business_logic import create_duracao_garantia_column

        series = pd.Series([183, 365, 548, 730, 1095])
        result = create_duracao_garantia_column(series)

        assert result.iloc[0] == "6 meses (183 dias)"
        assert result.iloc[1] == "12 meses (365 dias)"
        assert result.iloc[2] == "18 meses (548 dias)"
        assert result.iloc[3] == "24 meses (730 dias)"
        assert result.iloc[4] == "36 meses (1095 dias)"

    def test_nan_values_return_nao_informado(self):
        """Test NaN values return 'Não informado'."""
        from business_logic import create_duracao_garantia_column

        series = pd.Series([np.nan, None, float("nan")])
        result = create_duracao_garantia_column(series)

        assert all(result == "Não informado")

    def test_zero_returns_nao_informado(self):
        """Test zero value returns 'Não informado'."""
        from business_logic import create_duracao_garantia_column

        series = pd.Series([0, 0.0, "0"])
        result = create_duracao_garantia_column(series)

        # 0 should return "Não informado", "0" as string should also be handled
        assert result.iloc[0] == "Não informado"
        assert result.iloc[1] == "Não informado"

    def test_empty_string_returns_nao_informado(self):
        """Test empty string returns 'Não informado'."""
        from business_logic import create_duracao_garantia_column

        series = pd.Series([""])
        result = create_duracao_garantia_column(series)

        assert result.iloc[0] == "Não informado"

    def test_inf_returns_outros(self):
        """BUG-003: Test infinity values return 'Outros' instead of crashing."""
        from business_logic import create_duracao_garantia_column

        series = pd.Series([float("inf"), float("-inf")])
        result = create_duracao_garantia_column(series)

        assert result.iloc[0] == "Outros", "Positive infinity should return 'Outros'"
        assert result.iloc[1] == "Outros", "Negative infinity should return 'Outros'"

    def test_negative_values_return_outros(self):
        """BUG-003: Test negative values return 'Outros'."""
        from business_logic import create_duracao_garantia_column

        series = pd.Series([-1, -100, -365])
        result = create_duracao_garantia_column(series)

        assert all(result == "Outros"), "Negative values should return 'Outros'"

    def test_very_large_values_return_outros(self):
        """BUG-003: Test unreasonably large values return 'Outros'."""
        from business_logic import create_duracao_garantia_column

        series = pd.Series([10000, 100000, 1e10])
        result = create_duracao_garantia_column(series)

        assert all(result == "Outros"), "Very large values should return 'Outros'"

    def test_string_numbers_work(self):
        """Test string representations of numbers work correctly."""
        from business_logic import create_duracao_garantia_column

        series = pd.Series(["365", "730", "183"])
        result = create_duracao_garantia_column(series)

        assert result.iloc[0] == "12 meses (365 dias)"
        assert result.iloc[1] == "24 meses (730 dias)"
        assert result.iloc[2] == "6 meses (183 dias)"

    def test_invalid_strings_return_outros(self):
        """Test invalid string values return 'Outros'."""
        from business_logic import create_duracao_garantia_column

        series = pd.Series(["abc", "not a number", "12x"])
        result = create_duracao_garantia_column(series)

        assert all(result == "Outros"), "Invalid strings should return 'Outros'"

    def test_unrecognized_valid_numbers_return_outros(self):
        """Test valid numbers that don't match warranty periods return 'Outros'."""
        from business_logic import create_duracao_garantia_column

        series = pd.Series([100, 200, 500, 800])
        result = create_duracao_garantia_column(series)

        assert all(result == "Outros"), "Unrecognized periods should return 'Outros'"


class TestCalculateGarantiaDistribution:
    """Tests for calculate_garantia_distribution function."""

    def test_empty_dataframe_returns_zeros(self):
        """Test empty dataframe returns all zeros."""
        from business_logic import calculate_garantia_distribution

        df = pd.DataFrame({"GARANTIA": []})
        result = calculate_garantia_distribution(df)

        assert result["pct_6m"] == 0.0
        assert result["pct_12m"] == 0.0
        assert result["pct_18m"] == 0.0
        assert result["pct_24m"] == 0.0
        assert result["pct_36m"] == 0.0

    def test_missing_garantia_column_returns_zeros(self):
        """Test missing GARANTIA column returns all zeros."""
        from business_logic import calculate_garantia_distribution

        df = pd.DataFrame({"OTHER_COL": [1, 2, 3]})
        result = calculate_garantia_distribution(df)

        assert all(v == 0.0 for v in result.values())

    def test_correct_distribution_calculation(self):
        """Test correct percentage calculation."""
        from business_logic import calculate_garantia_distribution

        # 2 units at 12 months, 2 at 24 months = 50% each
        df = pd.DataFrame({"GARANTIA": [365, 365, 730, 730]})
        result = calculate_garantia_distribution(df)

        assert result["pct_12m"] == 50.0
        assert result["pct_24m"] == 50.0
        assert result["pct_6m"] == 0.0


class TestCalculateRtmAnalysisByYear:
    """Tests for calculate_rtm_analysis_by_year function - Total row consistency."""

    def test_total_units_equals_sum_of_yearly_units(self):
        """
        Total Units Sales must equal sum of per-year Units Sales.

        When a chassis appears in multiple years (e.g., partial shipments),
        it's counted in each year it appears, and Total = sum of all years.
        """
        from business_logic import calculate_rtm_analysis_by_year

        # Create O2C data with chassis appearing in multiple years (partial shipments)
        # Chassis "A" appears in 2022 and 2023 - counted in both years
        o2c_df = pd.DataFrame({
            "NUM_SERIAL": ["A", "A", "B", "C", "D", "E"],
            "RTM": ["SIM", "SIM", "SIM", "SIM", "SIM", "SIM"],
            "DT_NUM_NF": pd.to_datetime([
                "2022-01-15",  # A first shipment in 2022
                "2023-06-01",  # A second shipment in 2023 (valid partial shipment)
                "2022-03-20",  # B in 2022
                "2023-02-10",  # C in 2023
                "2023-08-05",  # D in 2023
                "2024-01-20",  # E in 2024
            ]),
            "ANO_NF": [2022, 2023, 2022, 2023, 2023, 2024],
            "STATUS_GARANTIA": ["DENTRO", "DENTRO", "FORA", "DENTRO", "FORA", "DENTRO"],
            "GARANTIA": [365, 365, 365, 730, 730, 1095],
        })

        # Create minimal chamados and erros_rtm dataframes
        chamados_df = pd.DataFrame({
            "SS": ["SS001"],
            "CHASSI": ["A"],
            "SERVIÇO": ["MANUTENÇÃO"],
            "SUMÁRIO": ["Test call"],
        })
        erros_rtm_df = pd.DataFrame({"SS": pd.Series([], dtype=str)})

        result = calculate_rtm_analysis_by_year(o2c_df, chamados_df, erros_rtm_df, "SIM")

        # Extract yearly and total units
        yearly_rows = result[result["Ano"] != "Total"]
        total_row = result[result["Ano"] == "Total"]

        sum_of_years = yearly_rows["Units Sales"].sum()
        total_units = total_row["Units Sales"].iloc[0]

        # Total Units Sales = sum of per-year Units Sales
        assert total_units == sum_of_years, (
            f"Total ({total_units}) should equal sum of years ({sum_of_years})"
        )

        # Verify correct counts:
        # 2022: A, B = 2 unique chassis
        # 2023: A, C, D = 3 unique chassis (A counted again - partial shipment)
        # 2024: E = 1 unique chassis
        # Sum of years = 6 = Total
        assert sum_of_years == 6, f"Expected sum of years = 6, got {sum_of_years}"
        assert total_units == 6, f"Expected Total = 6, got {total_units}"

    def test_empty_o2c_returns_empty_dataframe(self):
        """Test empty O2C data returns empty dataframe."""
        from business_logic import calculate_rtm_analysis_by_year

        o2c_df = pd.DataFrame({
            "NUM_SERIAL": pd.Series([], dtype=str),
            "RTM": pd.Series([], dtype=str),
            "DT_NUM_NF": pd.Series([], dtype="datetime64[ns]"),
            "STATUS_GARANTIA": pd.Series([], dtype=str),
        })
        chamados_df = pd.DataFrame({
            "SS": pd.Series([], dtype=str),
            "CHASSI": pd.Series([], dtype=str),
            "SERVIÇO": pd.Series([], dtype=str),
            "SUMÁRIO": pd.Series([], dtype=str),
        })
        erros_rtm_df = pd.DataFrame({"SS": pd.Series([], dtype=str)})

        result = calculate_rtm_analysis_by_year(o2c_df, chamados_df, erros_rtm_df, "SIM")

        assert len(result) == 0

    def test_general_warranty_gte_electronic_warranty(self):
        """
        BUG-010: General warranty % must be >= electronic warranty %.

        Since minimum warranty is 12 months and electronic warranty is also 12 months,
        any unit under electronic warranty should also be under general warranty.
        If STATUS_GARANTIA is missing but unit is within 12 months, count as under warranty.
        """
        from business_logic import calculate_rtm_analysis_by_year

        # Create data with some units missing STATUS_GARANTIA but within 12 months
        hoje = pd.Timestamp.now().normalize()
        o2c_df = pd.DataFrame({
            "NUM_SERIAL": ["A", "B", "C"],
            "RTM": ["SIM", "SIM", "SIM"],
            "DT_NUM_NF": [
                hoje - pd.Timedelta(days=100),  # A: within 12 months
                hoje - pd.Timedelta(days=100),  # B: within 12 months
                hoje - pd.Timedelta(days=500),  # C: outside 12 months
            ],
            "ANO_NF": [hoje.year, hoje.year, hoje.year - 1],
            "STATUS_GARANTIA": ["DENTRO", "", "FORA"],  # B has missing status
            "GARANTIA": [365, np.nan, 365],  # B has missing warranty period
        })

        # Create chamados with proper string dtypes to avoid accessor issues
        chamados_df = pd.DataFrame({
            "SS": pd.Series([], dtype=str),
            "CHASSI": pd.Series([], dtype=str),
            "SERVIÇO": pd.Series([], dtype=str),
            "SUMÁRIO": pd.Series([], dtype=str),
        })
        erros_rtm_df = pd.DataFrame({"SS": pd.Series([], dtype=str)})

        result = calculate_rtm_analysis_by_year(o2c_df, chamados_df, erros_rtm_df, "SIM")

        # Check each row: general warranty % should be >= electronic warranty %
        for _, row in result.iterrows():
            general_pct = row["% Chassis Under Warranty"]
            electronic_pct = row["% Chassis Under Electronic Warranty"]
            assert general_pct >= electronic_pct, (
                f"Year {row['Ano']}: General warranty ({general_pct:.1f}%) should be >= "
                f"electronic warranty ({electronic_pct:.1f}%)"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
