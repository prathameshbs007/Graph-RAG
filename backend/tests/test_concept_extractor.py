import json
from unittest.mock import MagicMock, patch

from services.concept_extractor import extract_concepts


def _mock_completion(content: str):
    completion = MagicMock()
    completion.choices = [MagicMock(message=MagicMock(content=content))]
    return completion


def test_extract_concepts_empty_text_returns_empty_without_calling_groq():
    result = extract_concepts("   ")
    assert result == {"concepts": [], "cited_titles": []}


@patch("services.concept_extractor._get_client")
def test_extract_concepts_parses_valid_json(mock_get_client):
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _mock_completion(
        json.dumps({"concepts": ["Transformers", " Self-Attention "], "cited_titles": ["Some Paper"]})
    )
    mock_get_client.return_value = mock_client

    result = extract_concepts("Some paper text about transformers.")

    assert result == {"concepts": ["Transformers", "Self-Attention"], "cited_titles": ["Some Paper"]}


@patch("services.concept_extractor._get_client")
def test_extract_concepts_malformed_json_fails_gracefully(mock_get_client):
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _mock_completion("not valid json")
    mock_get_client.return_value = mock_client

    result = extract_concepts("some text")

    assert result == {"concepts": [], "cited_titles": []}


@patch("services.concept_extractor._get_client")
def test_extract_concepts_non_list_fields_default_to_empty(mock_get_client):
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _mock_completion(
        json.dumps({"concepts": "not a list", "cited_titles": None})
    )
    mock_get_client.return_value = mock_client

    result = extract_concepts("some text")

    assert result == {"concepts": [], "cited_titles": []}


@patch("services.concept_extractor._get_client")
def test_extract_concepts_groq_exception_fails_gracefully(mock_get_client):
    mock_get_client.side_effect = RuntimeError("groq is down")

    result = extract_concepts("some text")

    assert result == {"concepts": [], "cited_titles": []}
