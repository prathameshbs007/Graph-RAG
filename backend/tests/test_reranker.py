from unittest.mock import MagicMock, patch

from services.reranker import Reranker


def test_rerank_empty_documents_returns_empty_list():
    reranker = Reranker()
    assert reranker.rerank("query", []) == []


@patch("services.reranker.TextCrossEncoder")
def test_rerank_orders_by_score_descending(mock_cross_encoder_cls):
    mock_model = MagicMock()
    mock_model.rerank.return_value = [0.1, 0.9, 0.5]
    mock_cross_encoder_cls.return_value = mock_model

    reranker = Reranker()
    result = reranker.rerank("query", ["doc0", "doc1", "doc2"], top_n=3)

    assert result == [1, 2, 0]


@patch("services.reranker.TextCrossEncoder")
def test_rerank_respects_top_n(mock_cross_encoder_cls):
    mock_model = MagicMock()
    mock_model.rerank.return_value = [0.1, 0.9, 0.5]
    mock_cross_encoder_cls.return_value = mock_model

    reranker = Reranker()
    result = reranker.rerank("query", ["doc0", "doc1", "doc2"], top_n=1)

    assert result == [1]


@patch("services.reranker.TextCrossEncoder")
def test_rerank_falls_back_to_identity_order_on_error(mock_cross_encoder_cls):
    mock_cross_encoder_cls.side_effect = RuntimeError("model load failed")

    reranker = Reranker()
    result = reranker.rerank("query", ["doc0", "doc1", "doc2"], top_n=2)

    assert result == [0, 1]
