"""Tests for the file upload API endpoints."""

import io
from uuid import uuid4

import pytest

pytestmark = pytest.mark.asyncio


class TestUploadFiles:
    """Tests for POST /api/v1/files/upload."""

    async def test_upload_single_pdf(self, client):
        """Upload a single PDF file."""
        pdf_content = b"%PDF-1.4 test content"
        files = [("files", ("paper.pdf", io.BytesIO(pdf_content), "application/pdf"))]
        resp = await client.post("/api/v1/files/upload", files=files)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["filename"] == "paper.pdf"
        assert data[0]["file_type"] == "pdf"
        assert data[0]["size_bytes"] == len(pdf_content)
        assert data[0]["status"] == "accepted"
        assert "file_id" in data[0]

    async def test_upload_multiple_files(self, client):
        """Upload PDF + LaTeX + BibTeX files."""
        files = [
            ("files", ("paper.pdf", io.BytesIO(b"%PDF content"), "application/pdf")),
            ("files", ("paper.tex", io.BytesIO(b"\\documentclass{article}"), "text/plain")),
            ("files", ("refs.bib", io.BytesIO(b"@article{key,}"), "text/plain")),
        ]
        resp = await client.post("/api/v1/files/upload", files=files)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3
        types = {d["file_type"] for d in data}
        assert types == {"pdf", "latex", "bibtex"}

    async def test_upload_invalid_extension(self, client):
        """Reject files with disallowed extensions."""
        files = [("files", ("image.png", io.BytesIO(b"PNG data"), "image/png"))]
        resp = await client.post("/api/v1/files/upload", files=files)
        assert resp.status_code == 400
        assert "not allowed" in resp.json()["detail"]

    async def test_upload_empty_file(self, client):
        """Reject empty files."""
        files = [("files", ("paper.pdf", io.BytesIO(b""), "application/pdf"))]
        resp = await client.post("/api/v1/files/upload", files=files)
        assert resp.status_code == 400
        assert "empty" in resp.json()["detail"].lower()

    async def test_upload_file_too_large(self, client, monkeypatch):
        """Reject files that exceed the size limit."""
        import backend.api.v1.files as files_mod

        monkeypatch.setattr(files_mod, "MAX_FILE_SIZE_BYTES", 100)
        content = b"x" * 200
        files = [("files", ("paper.pdf", io.BytesIO(content), "application/pdf"))]
        resp = await client.post("/api/v1/files/upload", files=files)
        assert resp.status_code == 400
        assert "exceeds" in resp.json()["detail"].lower()

    async def test_upload_stores_on_disk(self, client, tmp_upload_dir):
        """Uploaded files are stored on disk."""
        content = b"%PDF-1.4 stored content"
        files = [("files", ("paper.pdf", io.BytesIO(content), "application/pdf"))]
        resp = await client.post("/api/v1/files/upload", files=files)
        assert resp.status_code == 200
        file_id = resp.json()[0]["file_id"]

        stored_dir = tmp_upload_dir / file_id
        assert stored_dir.exists()
        stored_files = list(stored_dir.iterdir())
        assert len(stored_files) == 1
        assert stored_files[0].read_bytes() == content

    async def test_upload_no_filename(self, client):
        """Reject files without a filename."""
        files = [("files", ("", io.BytesIO(b"content"), "application/pdf"))]
        resp = await client.post("/api/v1/files/upload", files=files)
        assert resp.status_code in (400, 422)


class TestGetFileInfo:
    """Tests for GET /api/v1/files/{file_id}."""

    async def test_get_uploaded_file_from_disk(self, client, tmp_upload_dir):
        """Get info for a file that's on disk but not yet in DB."""
        content = b"%PDF-1.4 test"
        files = [("files", ("paper.pdf", io.BytesIO(content), "application/pdf"))]
        resp = await client.post("/api/v1/files/upload", files=files)
        file_id = resp.json()[0]["file_id"]

        resp2 = await client.get(f"/api/v1/files/{file_id}")
        assert resp2.status_code == 200
        data = resp2.json()
        assert data["filename"] == "paper.pdf"
        assert data["file_type"] == "pdf"
        assert data["size_bytes"] == len(content)
        assert data["review_id"] is None

    async def test_get_nonexistent_file(self, client):
        """Return 404 for a file ID that doesn't exist."""
        resp = await client.get(f"/api/v1/files/{uuid4()}")
        assert resp.status_code == 404


class TestDeleteFile:
    """Tests for DELETE /api/v1/files/{file_id}."""

    async def test_delete_uploaded_file(self, client, tmp_upload_dir):
        """Delete an uploaded file that's not linked to a review."""
        content = b"%PDF-1.4 delete me"
        files = [("files", ("paper.pdf", io.BytesIO(content), "application/pdf"))]
        resp = await client.post("/api/v1/files/upload", files=files)
        file_id = resp.json()[0]["file_id"]

        resp2 = await client.delete(f"/api/v1/files/{file_id}")
        assert resp2.status_code == 200
        assert resp2.json()["status"] == "deleted"

        # Verify removed from disk
        assert not (tmp_upload_dir / file_id).exists()

    async def test_delete_nonexistent_file(self, client):
        """Return 404 for a non-existent file."""
        resp = await client.delete(f"/api/v1/files/{uuid4()}")
        assert resp.status_code == 404
