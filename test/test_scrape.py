"""
Tests for scrape.py YieldDataFetcher
"""

import os
from unittest.mock import MagicMock, patch

import orjson
import pytest

from src.scrape import YieldDataFetcher


@pytest.fixture
def mock_api_response():
    """Mock API response data"""
    return {
        "status": "success",
        "data": [
            {
                "chain": "Hedera",
                "project": "saucerswap",
                "symbol": "USDC",
                "tvlUsd": 1500000,
                "apyBase": 8.5,
                "stablecoin": True,
            },
            {
                "chain": "Hedera",
                "project": "pangolin",
                "symbol": "HBAR",
                "tvlUsd": 2000000,
                "apyBase": 12.3,
                "stablecoin": False,
            },
            {
                "chain": "Hedera",
                "project": "test-protocol",
                "symbol": "USDC-HBAR",
                "tvlUsd": 500000,
                "apyBase": 15.0,
                "stablecoin": False,
            },
            {
                "chain": "Ethereum",
                "project": "aave",
                "symbol": "USDC",
                "tvlUsd": 10000000,
                "apyBase": 5.5,
                "stablecoin": True,
            },
            {
                "chain": "Hedera",
                "project": "another-protocol",
                "symbol": "DAI",
                "tvlUsd": 800000,
                "apyBase": None,
                "stablecoin": True,
            },
            {
                "chain": "Hedera",
                "project": "zero-apy",
                "symbol": "USDT",
                "tvlUsd": 600000,
                "apyBase": 0,
                "stablecoin": True,
            },
        ],
    }


def test_fetch_data_success(mock_api_response):
    """Test successful data fetching"""
    fetcher = YieldDataFetcher("https://api.example.com/yields")

    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = orjson.dumps(mock_api_response)
        mock_get.return_value = mock_response

        fetcher.fetch_data()

        assert fetcher.data is not None
        assert fetcher.data["status"] == "success"
        assert len(fetcher.data["data"]) == 6


def test_fetch_data_failure():
    """Test failed data fetching"""
    fetcher = YieldDataFetcher("https://api.example.com/yields")

    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        with pytest.raises(Exception, match="Failed to fetch data"):
            fetcher.fetch_data()


def test_filter_data(mock_api_response):
    """Test data filtering logic"""
    fetcher = YieldDataFetcher("https://api.example.com/yields")
    fetcher.data = mock_api_response

    fetcher.filter_data()

    assert fetcher.filtered_data is not None
    assert len(fetcher.filtered_data) == 2

    # Check that only Hedera chain items with valid APY and no hyphen in symbol are included
    for item in fetcher.filtered_data:
        assert item["chain"] == "Hedera"
        assert item["apyBase"] is not None
        assert item["apyBase"] != 0
        assert "-" not in item["symbol"]

    # Verify the correct items were filtered
    symbols = [item["symbol"] for item in fetcher.filtered_data]
    assert "USDC" in symbols
    assert "HBAR" in symbols
    assert "USDC-HBAR" not in symbols  # Has hyphen
    assert "DAI" not in symbols  # apyBase is None
    assert "USDT" not in symbols  # apyBase is 0


def test_filter_data_without_fetch():
    """Test that filter_data raises error if data not fetched"""
    fetcher = YieldDataFetcher("https://api.example.com/yields")

    with pytest.raises(ValueError, match="Data is not fetched yet"):
        fetcher.filter_data()


def test_save_data(mock_api_response, tmp_path):
    """Test saving filtered data to file"""
    fetcher = YieldDataFetcher("https://api.example.com/yields")
    fetcher.data = mock_api_response
    fetcher.filter_data()

    output_file = tmp_path / "test_output.json"
    fetcher.save_data(str(output_file))

    assert output_file.exists()

    with open(output_file, "rb") as f:
        saved_data = orjson.loads(f.read())

    assert len(saved_data) == 2
    assert saved_data[0]["chain"] == "Hedera"


def test_save_data_without_filter():
    """Test that save_data raises error if data not filtered"""
    fetcher = YieldDataFetcher("https://api.example.com/yields")

    with pytest.raises(ValueError, match="Data is not filtered yet"):
        fetcher.save_data("output.json")


def test_full_workflow(mock_api_response, tmp_path):
    """Test complete workflow from fetch to save"""
    fetcher = YieldDataFetcher("https://api.example.com/yields")
    output_file = tmp_path / "workflow_test.json"

    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = orjson.dumps(mock_api_response)
        mock_get.return_value = mock_response

        fetcher.fetch_data()
        fetcher.filter_data()
        fetcher.save_data(str(output_file))

    assert output_file.exists()

    with open(output_file, "rb") as f:
        result = orjson.loads(f.read())

    assert len(result) == 2
    assert all(item["chain"] == "Hedera" for item in result)


@pytest.mark.integration
def test_real_api_call():
    """Integration test with real API call"""
    api_url = os.getenv("DEFILLAMA_API")
    if not api_url:
        pytest.skip("DEFILLAMA_API environment variable not set")

    fetcher = YieldDataFetcher(api_url)

    try:
        fetcher.fetch_data()
        assert fetcher.data is not None

        fetcher.filter_data()
        assert fetcher.filtered_data is not None
        assert isinstance(fetcher.filtered_data, list)

        fetcher.save_data("test/test_scrape.json")
        print("\n✓ Data saved to test.json")
        print(f"✓ Found {len(fetcher.filtered_data)} Hedera protocols")

        # Display sample data
        if fetcher.filtered_data:
            print("\nSample data:")
            for item in fetcher.filtered_data[:3]:
                print(f"  - {item['project']}: {item['symbol']} ({item['apyBase']:.2f}% APY)")

    except Exception as e:
        pytest.fail(f"Real API call failed: {e}")
