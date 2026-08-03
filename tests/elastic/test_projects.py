from unittest.mock import MagicMock, patch

import pytest

from logpyre.elastic.projects import delete_project


def test_delete_project_rejects_reserved_slugs():
    with pytest.raises(ValueError, match="reserved"):
        delete_project("formats")
    with pytest.raises(ValueError, match="reserved"):
        delete_project("projects")


def test_delete_project_returns_zero_when_no_matching_indices():
    client = MagicMock()
    client.cat.indices.return_value = []
    with patch("logpyre.elastic.client.get_client", return_value=client):
        assert delete_project("ghost") == 0
    client.indices.delete.assert_not_called()


def test_delete_project_deletes_matching_indices():
    client = MagicMock()
    client.cat.indices.return_value = [
        {"index": "logpyre-frontend-nginx_combined-2024.01.01"},
        {"index": "logpyre-frontend-nginx_combined-2024.01.02"},
    ]
    with patch("logpyre.elastic.client.get_client", return_value=client):
        assert delete_project("frontend") == 2
    client.indices.delete.assert_called_once_with(
        index="logpyre-frontend-nginx_combined-2024.01.01,logpyre-frontend-nginx_combined-2024.01.02",
        ignore_unavailable=True,
    )
