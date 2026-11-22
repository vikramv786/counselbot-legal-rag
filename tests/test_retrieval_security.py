
from qdrant_client import models

from counselbot_legal_rag.demo_users import get_demo_user
from counselbot_legal_rag.retrieval import build_access_filter


def test_corporate_counsel_filter():
    user = get_demo_user("adv.rao")

    access_filter = build_access_filter(user)

    assert isinstance(access_filter, models.Filter)
    assert len(access_filter.must) == 2

    role_condition = access_filter.must[0]
    matter_filter = access_filter.must[1]

    assert role_condition.key == "access_roles"
    assert role_condition.match.value == "corporate_counsel"

    matter_conditions = matter_filter.min_should.conditions

    allowed_matters = {
        condition.match.value
        for condition in matter_conditions
    }

    assert allowed_matters == {"NONE", "MTR-017"}
    assert matter_filter.min_should.min_count == 1


def test_general_counsel_filter():
    user = get_demo_user("gc.sharma")

    access_filter = build_access_filter(user)

    assert isinstance(access_filter, models.Filter)
    assert len(access_filter.must) == 1

    role_condition = access_filter.must[0]

    assert role_condition.key == "access_roles"
    assert role_condition.match.value == "general_counsel"


from unittest.mock import MagicMock, patch

from counselbot_legal_rag.retrieval import hybrid_search


def test_hybrid_search_applies_access_filter_everywhere():
    user = get_demo_user("adv.rao")

    fake_dense_vector = [0.1, 0.2, 0.3]
    fake_sparse_vector = {
        "indices": [1, 5],
        "values": [0.8, 0.4],
    }

    fake_client = MagicMock()
    fake_client.query_points.return_value.points = []

    with (
        patch(
            "counselbot_legal_rag.retrieval.get_embedding_model"
        ),
        patch(
            "counselbot_legal_rag.retrieval.get_sparse_embedding_model"
        ),
        patch(
            "counselbot_legal_rag.retrieval.embed_texts",
            return_value=[fake_dense_vector],
        ),
        patch(
            "counselbot_legal_rag.retrieval.embed_sparse_texts",
            return_value=[fake_sparse_vector],
        ),
        patch(
            "counselbot_legal_rag.retrieval.get_qdrant_client",
            return_value=fake_client,
        ),
    ):
        hybrid_search(
            query="litigation case strategy",
            user=user,
            limit=5,
        )

    fake_client.query_points.assert_called_once()

    kwargs = fake_client.query_points.call_args.kwargs

    access_filter = build_access_filter(user)

    assert kwargs["query_filter"] == access_filter
    assert len(kwargs["prefetch"]) == 2

    for prefetch in kwargs["prefetch"]:
        assert prefetch.filter == access_filter

    fake_client.close.assert_called_once()
