"""
Tests for filters.py module.
"""

import pytest
import pandas as pd
from datetime import datetime

# Add parent directory to path for imports
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestAplicarFiltros:
    """Tests for aplicar_filtros function."""

    @pytest.fixture
    def sample_dataframe(self):
        """Create a sample dataframe for testing."""
        return pd.DataFrame(
            {
                "TAGS": [["TAG1"], ["TAG2"], ["TAG1", "TAG2"], ["TAG3"]],
                "STATUS": ["ABERTO", "FECHADO", "ABERTO", "FECHADO"],
                "MODELO": ["HELIX", "VISTA", "HELIX", "CENTURY"],
                "CLIENTE": ["Cliente A", "Cliente B", "Cliente C", "Cliente D"],
                "CHASSI": ["123456", "234567", "345678", "456789"],
                "INÍCIO": pd.to_datetime(
                    ["2024-01-01", "2024-01-15", "2024-02-01", "2024-02-15"]
                ),
                "FIM": pd.to_datetime(
                    ["2024-01-10", "2024-01-20", None, "2024-02-20"]
                ),
            }
        )

    def test_search_filter_returns_correct_rows(self, sample_dataframe):
        """BUG-001: Verify text search filter returns only matching rows."""
        # Import here to avoid cache issues
        from filters import aplicar_filtros, _aplicar_filtros_cached

        # Clear cache before test
        _aplicar_filtros_cached.clear()

        # Search for "HELIX" - should return 2 rows
        result = aplicar_filtros(
            sample_dataframe,
            tags_selecionadas=[],
            selecoes={},
            termo_pesquisa="HELIX",
            status_selecionado="GERAL",
            data_inicio=None,
            data_fim=None,
        )

        assert len(result) == 2, f"Expected 2 rows with HELIX, got {len(result)}"
        assert all(
            result["MODELO"] == "HELIX"
        ), "All returned rows should have MODELO=HELIX"

    def test_search_filter_case_insensitive(self, sample_dataframe):
        """Verify search is case-insensitive."""
        from filters import aplicar_filtros, _aplicar_filtros_cached

        _aplicar_filtros_cached.clear()

        # Search for lowercase "helix"
        result = aplicar_filtros(
            sample_dataframe,
            tags_selecionadas=[],
            selecoes={},
            termo_pesquisa="helix",
            status_selecionado="GERAL",
            data_inicio=None,
            data_fim=None,
        )

        assert len(result) == 2, f"Expected 2 rows with helix (case-insensitive), got {len(result)}"

    def test_search_filter_partial_match(self, sample_dataframe):
        """Verify search finds partial matches."""
        from filters import aplicar_filtros, _aplicar_filtros_cached

        _aplicar_filtros_cached.clear()

        # Search for "Cliente" - should match all 4 rows
        result = aplicar_filtros(
            sample_dataframe,
            tags_selecionadas=[],
            selecoes={},
            termo_pesquisa="Cliente",
            status_selecionado="GERAL",
            data_inicio=None,
            data_fim=None,
        )

        assert len(result) == 4, f"Expected 4 rows with 'Cliente', got {len(result)}"

    def test_search_filter_no_match(self, sample_dataframe):
        """Verify search returns empty when no match."""
        from filters import aplicar_filtros, _aplicar_filtros_cached

        _aplicar_filtros_cached.clear()

        # Search for non-existent term
        result = aplicar_filtros(
            sample_dataframe,
            tags_selecionadas=[],
            selecoes={},
            termo_pesquisa="NONEXISTENT_TERM_XYZ123",
            status_selecionado="GERAL",
            data_inicio=None,
            data_fim=None,
        )

        assert len(result) == 0, f"Expected 0 rows for non-existent term, got {len(result)}"

    def test_search_filter_searches_all_columns(self, sample_dataframe):
        """Verify search looks in all columns."""
        from filters import aplicar_filtros, _aplicar_filtros_cached

        _aplicar_filtros_cached.clear()

        # Search for chassis number - should find 1 row
        result = aplicar_filtros(
            sample_dataframe,
            tags_selecionadas=[],
            selecoes={},
            termo_pesquisa="345678",
            status_selecionado="GERAL",
            data_inicio=None,
            data_fim=None,
        )

        assert len(result) == 1, f"Expected 1 row with chassis 345678, got {len(result)}"
        assert result.iloc[0]["CHASSI"] == "345678"

    def test_search_empty_string_returns_all(self, sample_dataframe):
        """Verify empty search returns all rows."""
        from filters import aplicar_filtros, _aplicar_filtros_cached

        _aplicar_filtros_cached.clear()

        result = aplicar_filtros(
            sample_dataframe,
            tags_selecionadas=[],
            selecoes={},
            termo_pesquisa="",
            status_selecionado="GERAL",
            data_inicio=None,
            data_fim=None,
        )

        assert len(result) == len(sample_dataframe), "Empty search should return all rows"


class TestCacheIntegrity:
    """Tests for BUG-002: Cache collision with mutable parameters."""

    @pytest.fixture
    def sample_dataframe(self):
        """Create a sample dataframe for testing."""
        return pd.DataFrame(
            {
                "TAGS": [["TAG1"], ["TAG2"], ["TAG1", "TAG2"], ["TAG3"]],
                "STATUS": ["ABERTO", "FECHADO", "ABERTO", "FECHADO"],
                "MODELO": ["HELIX", "VISTA", "HELIX", "CENTURY"],
                "CLIENTE": ["Cliente A", "Cliente B", "Cliente C", "Cliente D"],
                "CHASSI": ["123456", "234567", "345678", "456789"],
                "INÍCIO": pd.to_datetime(
                    ["2024-01-01", "2024-01-15", "2024-02-01", "2024-02-15"]
                ),
                "FIM": pd.to_datetime(
                    ["2024-01-10", "2024-01-20", None, "2024-02-20"]
                ),
            }
        )

    def test_different_dicts_return_different_results(self, sample_dataframe):
        """BUG-002: Different dict selections should return different results."""
        from filters import aplicar_filtros, _aplicar_filtros_cached

        _aplicar_filtros_cached.clear()

        # First call with HELIX filter
        result1 = aplicar_filtros(
            sample_dataframe,
            tags_selecionadas=[],
            selecoes={"MODELO": ["HELIX"]},
            termo_pesquisa="",
            status_selecionado="GERAL",
        )

        # Second call with VISTA filter
        result2 = aplicar_filtros(
            sample_dataframe,
            tags_selecionadas=[],
            selecoes={"MODELO": ["VISTA"]},
            termo_pesquisa="",
            status_selecionado="GERAL",
        )

        assert len(result1) == 2, "HELIX filter should return 2 rows"
        assert len(result2) == 1, "VISTA filter should return 1 row"
        assert len(result1) != len(result2), "Different filters must return different results"

    def test_same_filters_return_cached_result(self, sample_dataframe):
        """Verify same filters return identical results (cached)."""
        from filters import aplicar_filtros, _aplicar_filtros_cached

        _aplicar_filtros_cached.clear()

        # First call
        result1 = aplicar_filtros(
            sample_dataframe,
            tags_selecionadas=[],
            selecoes={"MODELO": ["HELIX"]},
            termo_pesquisa="",
            status_selecionado="GERAL",
        )

        # Second call with same parameters
        result2 = aplicar_filtros(
            sample_dataframe,
            tags_selecionadas=[],
            selecoes={"MODELO": ["HELIX"]},
            termo_pesquisa="",
            status_selecionado="GERAL",
        )

        assert len(result1) == len(result2), "Same filters should return same row count"
        assert result1.equals(result2), "Same filters should return identical results"

    def test_hashable_conversion_preserves_filter_logic(self, sample_dataframe):
        """Verify hashable conversion doesn't break filter logic."""
        from filters import _convert_to_hashable

        # Test dict conversion
        selecoes = {"MODELO": ["HELIX", "VISTA"], "STATUS": ["ABERTO"]}
        hashable = _convert_to_hashable(selecoes)

        # Verify it's a tuple
        assert isinstance(hashable, tuple), "Result should be a tuple"

        # Verify contents are preserved
        converted_back = {k: list(v) for k, v in hashable}
        assert set(converted_back.keys()) == set(selecoes.keys())
        assert set(converted_back["MODELO"]) == set(selecoes["MODELO"])
        assert set(converted_back["STATUS"]) == set(selecoes["STATUS"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
