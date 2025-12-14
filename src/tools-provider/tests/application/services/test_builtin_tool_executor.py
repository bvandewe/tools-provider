"""Tests for BuiltinToolExecutor - file handling capabilities."""

import base64

import pytest

from application.services.builtin_tool_executor import BuiltinToolExecutor


@pytest.fixture
def executor():
    return BuiltinToolExecutor()


class TestFileWriter:
    """Tests for file_writer tool."""

    @pytest.mark.asyncio
    async def test_text_file_succeeds(self, executor):
        """Text files should be written successfully."""
        result = await executor.execute("file_writer", {"filename": "test.txt", "content": "hello world"})
        assert result.success is True
        assert result.result["filename"] == "test.txt"

    @pytest.mark.asyncio
    async def test_xlsx_without_is_binary_fails(self, executor):
        """Excel files without is_binary flag should fail with helpful message."""
        result = await executor.execute("file_writer", {"filename": "test.xlsx", "content": "hello"})
        assert result.success is False
        assert "spreadsheet_write" in result.error or "is_binary" in result.error

    @pytest.mark.asyncio
    async def test_xlsx_with_is_binary_succeeds(self, executor):
        """Excel files with is_binary=True and base64 content should succeed."""
        xlsx_content = base64.b64encode(b"fake xlsx content").decode()
        result = await executor.execute("file_writer", {"filename": "test.xlsx", "content": xlsx_content, "is_binary": True})
        assert result.success is True
        assert result.result["filename"] == "test.xlsx"
        assert result.result["is_binary"] is True

    @pytest.mark.asyncio
    async def test_pdf_with_is_binary_succeeds(self, executor):
        """PDF files with is_binary=True should succeed."""
        pdf_content = base64.b64encode(b"%PDF-1.4 fake pdf").decode()
        result = await executor.execute("file_writer", {"filename": "doc.pdf", "content": pdf_content, "is_binary": True})
        assert result.success is True

    @pytest.mark.asyncio
    async def test_disallowed_extension_fails(self, executor):
        """Extensions not in allowed list should fail."""
        result = await executor.execute("file_writer", {"filename": "test.exe", "content": "malware"})
        assert result.success is False
        assert "not allowed" in result.error


class TestFetchUrlSaveAsFile:
    """Tests for fetch_url save_as_file parameter."""

    @pytest.mark.asyncio
    async def test_save_as_file_validation(self, executor):
        """Path traversal in save_as_file should be rejected."""
        result = await executor.execute("fetch_url", {"url": "https://example.com/file.xlsx", "save_as_file": "../../../etc/passwd"})
        assert result.success is False
        assert "path traversal" in result.error.lower()


class TestToolDefinitions:
    """Tests for tool definitions."""

    def test_fetch_url_has_save_as_file(self):
        """fetch_url tool should have save_as_file parameter."""
        from application.services.builtin_source_adapter import get_builtin_tools

        tools = get_builtin_tools()
        fetch_tool = next(t for t in tools if t.name == "fetch_url")
        assert "save_as_file" in fetch_tool.input_schema["properties"]

    def test_file_writer_has_is_binary(self):
        """file_writer tool should have is_binary parameter."""
        from application.services.builtin_source_adapter import get_builtin_tools

        tools = get_builtin_tools()
        file_writer_tool = next(t for t in tools if t.name == "file_writer")
        assert "is_binary" in file_writer_tool.input_schema["properties"]
