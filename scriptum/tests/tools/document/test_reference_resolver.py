"""Tests for the reference resolver (LLM structuring + CrossRef enrichment)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from tools.document.models import Reference
from tools.document.reference_resolver import (
    _crossref_lookup,
    resolve_references,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ref(raw_text: str = "", **kwargs) -> Reference:
    return Reference(raw_text=raw_text, **kwargs)


def _llm_response_json(entries: list[dict]) -> MagicMock:
    """Create a mock LLMResponse whose .text is a JSON array."""
    resp = MagicMock()
    resp.text = json.dumps(entries)
    return resp


# ---------------------------------------------------------------------------
# resolve_references — top-level
# ---------------------------------------------------------------------------


class TestResolveReferences:
    async def test_empty_list_returns_empty(self):
        result = await resolve_references([])
        assert result == []

    async def test_none_phases_when_both_disabled(self):
        refs = [_make_ref("Smith et al. 2020")]
        result = await resolve_references(refs, use_llm=False, use_apis=False)
        assert len(result) == 1
        assert not result[0].resolved

    async def test_llm_phase_called_when_use_llm_true(self):
        refs = [_make_ref("Smith et al. 2020")]
        with patch(
            "tools.document.reference_resolver._llm_structure_references",
            new_callable=AsyncMock,
            return_value=refs,
        ) as mock_llm:
            await resolve_references(refs, use_llm=True, use_apis=False)
            mock_llm.assert_awaited_once_with(refs)

    async def test_api_phase_called_when_use_apis_true(self):
        refs = [_make_ref("Smith et al. 2020")]
        with (
            patch(
                "tools.document.reference_resolver._llm_structure_references",
                new_callable=AsyncMock,
                return_value=refs,
            ),
            patch(
                "tools.document.reference_resolver._api_enrich_references",
                new_callable=AsyncMock,
                return_value=refs,
            ) as mock_api,
        ):
            await resolve_references(refs, use_llm=True, use_apis=True)
            mock_api.assert_awaited_once_with(refs)


# ---------------------------------------------------------------------------
# Phase A: LLM structuring
# ---------------------------------------------------------------------------


class TestLLMStructuring:
    async def test_structures_raw_references(self):
        refs = [
            _make_ref("Vaswani et al. Attention Is All You Need. NeurIPS 2017."),
            _make_ref("Devlin et al. BERT: Pre-training. NAACL 2019."),
        ]

        llm_result = [
            {
                "title": "Attention Is All You Need",
                "authors": ["Vaswani"],
                "year": "2017",
                "venue": "NeurIPS",
            },
            {
                "title": "BERT: Pre-training",
                "authors": ["Devlin"],
                "year": "2019",
                "venue": "NAACL",
            },
        ]

        mock_client = AsyncMock()
        mock_client.complete = AsyncMock(return_value=_llm_response_json(llm_result))

        with patch("backend.core.llm.LLMClient", return_value=mock_client):
            result = await resolve_references(refs, use_llm=True, use_apis=False)

        assert result[0].title == "Attention Is All You Need"
        assert result[0].year == "2017"
        assert result[0].venue == "NeurIPS"
        assert result[0].resolved is True
        assert result[1].title == "BERT: Pre-training"
        assert result[1].resolved is True

    async def test_skips_already_resolved_refs(self):
        refs = [
            _make_ref("Vaswani et al.", resolved=True, title="Already Done"),
            _make_ref("Devlin et al. BERT 2019."),
        ]

        llm_result = [
            {"title": "BERT", "authors": ["Devlin"], "year": "2019", "venue": "NAACL"},
        ]

        mock_client = AsyncMock()
        mock_client.complete = AsyncMock(return_value=_llm_response_json(llm_result))

        with patch("backend.core.llm.LLMClient", return_value=mock_client):
            result = await resolve_references(refs, use_llm=True, use_apis=False)

        # First ref should be unchanged
        assert result[0].title == "Already Done"
        # Second ref should be enriched
        assert result[1].title == "BERT"
        assert result[1].resolved is True

    async def test_handles_invalid_json_from_llm(self):
        refs = [_make_ref("Some ref")]

        mock_resp = MagicMock()
        mock_resp.text = "not valid json {"

        mock_client = AsyncMock()
        mock_client.complete = AsyncMock(return_value=mock_resp)

        with patch("backend.core.llm.LLMClient", return_value=mock_client):
            result = await resolve_references(refs, use_llm=True, use_apis=False)

        # Should not crash, ref stays unresolved
        assert not result[0].resolved

    async def test_handles_llm_returning_non_array(self):
        refs = [_make_ref("Some ref")]

        mock_resp = MagicMock()
        mock_resp.text = json.dumps({"error": "unexpected"})

        mock_client = AsyncMock()
        mock_client.complete = AsyncMock(return_value=mock_resp)

        with patch("backend.core.llm.LLMClient", return_value=mock_client):
            result = await resolve_references(refs, use_llm=True, use_apis=False)

        assert not result[0].resolved

    async def test_handles_llm_exception_gracefully(self):
        """If LLM client raises during complete(), refs stay unresolved."""
        refs = [_make_ref("Some ref")]

        mock_client = AsyncMock()
        mock_client.complete = AsyncMock(side_effect=RuntimeError("LLM down"))

        with patch("backend.core.llm.LLMClient", return_value=mock_client):
            result = await resolve_references(refs, use_llm=True, use_apis=False)

        assert not result[0].resolved

    async def test_skips_refs_without_raw_text(self):
        refs = [_make_ref(""), _make_ref("Has text")]

        llm_result = [
            {"title": "Parsed", "authors": [], "year": "2020", "venue": "ICML"},
        ]

        mock_client = AsyncMock()
        mock_client.complete = AsyncMock(return_value=_llm_response_json(llm_result))

        with patch("backend.core.llm.LLMClient", return_value=mock_client):
            result = await resolve_references(refs, use_llm=True, use_apis=False)

        # First ref (empty raw_text) should be unresolved
        assert not result[0].resolved
        # Second ref should be resolved
        assert result[1].title == "Parsed"
        assert result[1].resolved is True


# ---------------------------------------------------------------------------
# Phase B: CrossRef DOI lookup
# ---------------------------------------------------------------------------


class TestCrossRefEnrichment:
    async def test_resolves_doi_from_crossref(self):
        ref = _make_ref("", title="Attention Is All You Need", authors=["Vaswani"])

        crossref_response = {
            "message": {
                "items": [
                    {
                        "DOI": "10.5555/3295222.3295349",
                        "title": ["Attention Is All You Need"],
                        "container-title": ["NeurIPS"],
                        "issued": {"date-parts": [[2017]]},
                    }
                ]
            }
        }

        mock_response = httpx.Response(200, json=crossref_response)

        with patch("tools.document.reference_resolver.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            result = await resolve_references([ref], use_llm=False, use_apis=True)

        assert result[0].doi == "10.5555/3295222.3295349"
        assert result[0].venue == "NeurIPS"
        assert result[0].year == "2017"
        assert result[0].resolved is True

    async def test_skips_refs_without_title(self):
        ref = _make_ref("raw text only, no title")

        with patch("tools.document.reference_resolver.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            result = await resolve_references([ref], use_llm=False, use_apis=True)

        # No title = no CrossRef lookup attempted
        assert not result[0].doi
        mock_client.get.assert_not_awaited()

    async def test_skips_refs_that_already_have_doi(self):
        ref = _make_ref("", title="Some Paper", doi="10.1234/existing")

        with patch("tools.document.reference_resolver.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client

            result = await resolve_references([ref], use_llm=False, use_apis=True)

        assert result[0].doi == "10.1234/existing"
        mock_client.get.assert_not_awaited()

    async def test_rejects_title_mismatch(self):
        """CrossRef result with a completely different title should be ignored."""
        ref = _make_ref("", title="Attention Is All You Need")

        crossref_response = {
            "message": {
                "items": [
                    {
                        "DOI": "10.9999/wrong",
                        "title": ["Completely Unrelated Paper About Cats"],
                        "container-title": ["Cat Journal"],
                    }
                ]
            }
        }

        mock_response = httpx.Response(200, json=crossref_response)
        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_response)

        await _crossref_lookup(mock_client_instance, ref)

        # Should NOT have set the DOI since titles don't match
        assert ref.doi == ""

    async def test_handles_crossref_http_error(self):
        ref = _make_ref("", title="Some Paper")

        mock_response = httpx.Response(500)
        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_response)

        await _crossref_lookup(mock_client_instance, ref)

        assert ref.doi == ""
        assert not ref.resolved

    async def test_handles_crossref_empty_results(self):
        ref = _make_ref("", title="Obscure Paper Nobody Indexed")

        crossref_response = {"message": {"items": []}}
        mock_response = httpx.Response(200, json=crossref_response)
        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_response)

        await _crossref_lookup(mock_client_instance, ref)

        assert ref.doi == ""
        assert not ref.resolved
