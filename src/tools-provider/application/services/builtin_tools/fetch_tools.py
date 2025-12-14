"""URL fetching and web search tools.

Tools for fetching web content and performing searches:
- fetch_url: Fetch content from URLs (HTML, JSON, binary)
- web_search: Search the web using DuckDuckGo
- wikipedia_query: Query Wikipedia for information
- browser_navigate: Navigate with headless browser (requires Playwright)
"""

import html
import logging
import os
import re
from typing import Any
from urllib.parse import quote, unquote

import httpx

from .base import (
    FETCH_TIMEOUT,
    MAX_CONTENT_SIZE,
    BuiltinToolResult,
    UserContext,
    cleanup_old_files,
    extract_filename,
    get_workspace_dir,
    is_json_content,
    is_text_content,
)

logger = logging.getLogger(__name__)


async def execute_fetch_url(arguments: dict[str, Any], user_context: UserContext | None = None) -> BuiltinToolResult:
    """Execute the fetch_url tool."""
    url = arguments.get("url", "")
    extract_text = arguments.get("extract_text", True)
    save_as_file = arguments.get("save_as_file")

    if not url:
        return BuiltinToolResult(success=False, error="URL is required")

    if not url.startswith(("http://", "https://")):
        return BuiltinToolResult(success=False, error="URL must start with http:// or https://")

    if save_as_file and (".." in save_as_file or save_as_file.startswith("/")):
        return BuiltinToolResult(success=False, error="Invalid filename: path traversal not allowed")

    logger.info(f"Fetching URL: {url}")

    try:
        async with httpx.AsyncClient(timeout=FETCH_TIMEOUT, follow_redirects=True, max_redirects=5) as client:
            try:
                head_response = await client.head(url)
                content_length = head_response.headers.get("content-length")
                if content_length and int(content_length) > MAX_CONTENT_SIZE:
                    return BuiltinToolResult(
                        success=False,
                        error=f"Content too large: {int(content_length)} bytes (max: {MAX_CONTENT_SIZE})",
                    )
            except Exception:  # nosec B110 - HEAD request failure is non-critical, continue to GET
                pass

            response = await client.get(url)
            response.raise_for_status()

            content_type = response.headers.get("content-type", "").lower()
            content_length = len(response.content)

            if content_length > MAX_CONTENT_SIZE:
                return BuiltinToolResult(
                    success=False,
                    error=f"Content too large: {content_length} bytes (max: {MAX_CONTENT_SIZE})",
                )

            if is_text_content(content_type):
                content = response.text
                if extract_text and "html" in content_type:
                    content = _extract_text_from_html(content)

                return BuiltinToolResult(
                    success=True,
                    result=content,
                    metadata={
                        "url": str(response.url),
                        "status_code": response.status_code,
                        "content_length": content_length,
                        "content_type": content_type.split(";")[0].strip(),
                    },
                )

            elif is_json_content(content_type):
                try:
                    json_content = response.json()
                    return BuiltinToolResult(
                        success=True,
                        result=json_content,
                        metadata={
                            "url": str(response.url),
                            "status_code": response.status_code,
                            "content_length": content_length,
                            "content_type": "application/json",
                        },
                    )
                except Exception:
                    return BuiltinToolResult(
                        success=True,
                        result=response.text,
                        metadata={
                            "url": str(response.url),
                            "status_code": response.status_code,
                            "content_length": content_length,
                            "content_type": content_type.split(";")[0].strip(),
                        },
                    )

            else:
                # Binary content
                filename = save_as_file or extract_filename(response, url)
                workspace_dir = get_workspace_dir(user_context)
                cleanup_old_files(workspace_dir)
                file_path = os.path.join(workspace_dir, filename)

                os.makedirs(os.path.dirname(file_path) if os.path.dirname(file_path) else workspace_dir, exist_ok=True)

                with open(file_path, "wb") as f:
                    f.write(response.content)

                logger.info(f"Auto-saved binary file: {filename} ({content_length} bytes)")

                return BuiltinToolResult(
                    success=True,
                    result={
                        "message": f"Binary file saved to workspace: {filename}",
                        "filename": filename,
                        "path": file_path,
                        "size_bytes": content_length,
                        "content_type": content_type.split(";")[0].strip(),
                    },
                    metadata={
                        "url": str(response.url),
                        "status_code": response.status_code,
                        "content_length": content_length,
                        "filename": filename,
                        "is_binary": True,
                        "saved_to_workspace": True,
                        "content_type": content_type.split(";")[0].strip(),
                    },
                )

    except httpx.TimeoutException:
        return BuiltinToolResult(success=False, error=f"Request timed out after {FETCH_TIMEOUT} seconds")
    except httpx.HTTPStatusError as e:
        return BuiltinToolResult(
            success=False,
            error=f"HTTP error {e.response.status_code}: {e.response.reason_phrase}",
            metadata={"status_code": e.response.status_code},
        )
    except httpx.RequestError as e:
        return BuiltinToolResult(success=False, error=f"Request failed: {str(e)}")


async def execute_web_search(arguments: dict[str, Any], user_context: UserContext | None = None) -> BuiltinToolResult:
    """Execute the web_search tool using DuckDuckGo."""
    query = arguments.get("query", "")
    max_results = min(arguments.get("max_results", 5), 10)
    region = arguments.get("region", "wt-wt")

    if not query:
        return BuiltinToolResult(success=False, error="Query is required")

    logger.info(f"Web search: {query}")

    try:
        async with httpx.AsyncClient(timeout=FETCH_TIMEOUT) as client:
            response = await client.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query, "kl": region},
                headers={"User-Agent": "Mozilla/5.0 (compatible; MCPToolsProvider/1.0)"},
            )
            response.raise_for_status()

            results = _parse_ddg_results(response.text, max_results)

            return BuiltinToolResult(
                success=True,
                result={"query": query, "results": results, "result_count": len(results)},
            )

    except Exception as e:
        logger.exception(f"Web search failed: {e}")
        return BuiltinToolResult(success=False, error=f"Search failed: {str(e)}")


async def execute_wikipedia_query(arguments: dict[str, Any], user_context: UserContext | None = None) -> BuiltinToolResult:
    """Execute the wikipedia_query tool."""
    query = arguments.get("query", "")
    language = arguments.get("language", "en")
    sentences = min(arguments.get("sentences", 5), 10)

    if not query:
        return BuiltinToolResult(success=False, error="Query is required")

    logger.info(f"Wikipedia query: {query}")

    try:
        async with httpx.AsyncClient(timeout=FETCH_TIMEOUT) as client:
            search_url = f"https://{language}.wikipedia.org/api/rest_v1/page/summary/{quote(query)}"
            response = await client.get(
                search_url,
                headers={"User-Agent": "MCPToolsProvider/1.0 (https://github.com/tools-provider)"},
            )

            if response.status_code == 404:
                search_api = f"https://{language}.wikipedia.org/w/api.php"
                search_response = await client.get(
                    search_api,
                    params={"action": "opensearch", "search": query, "limit": 1, "format": "json"},
                )
                search_data = search_response.json()

                if len(search_data) >= 4 and search_data[1]:
                    actual_title = search_data[1][0]
                    response = await client.get(
                        f"https://{language}.wikipedia.org/api/rest_v1/page/summary/{quote(actual_title)}",
                        headers={"User-Agent": "MCPToolsProvider/1.0"},
                    )
                else:
                    return BuiltinToolResult(success=False, error=f"No Wikipedia article found for: {query}")

            response.raise_for_status()
            data = response.json()

            extract = data.get("extract", "")
            if sentences < 10 and extract:
                sentence_list = re.split(r"(?<=[.!?])\s+", extract)
                extract = " ".join(sentence_list[:sentences])

            return BuiltinToolResult(
                success=True,
                result={
                    "title": data.get("title", ""),
                    "summary": extract,
                    "description": data.get("description", ""),
                    "url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
                    "thumbnail": data.get("thumbnail", {}).get("source", ""),
                },
            )

    except Exception as e:
        logger.exception(f"Wikipedia query failed: {e}")
        return BuiltinToolResult(success=False, error=f"Wikipedia query failed: {str(e)}")


async def execute_browser_navigate(arguments: dict[str, Any], user_context: UserContext | None = None) -> BuiltinToolResult:
    """Execute the browser_navigate tool using Playwright."""
    url = arguments.get("url", "")
    wait_for = arguments.get("wait_for")
    timeout = min(arguments.get("timeout", 30), 60) * 1000
    extract_text = arguments.get("extract_text", True)

    if not url:
        return BuiltinToolResult(success=False, error="URL is required")

    if not url.startswith(("http://", "https://")):
        return BuiltinToolResult(success=False, error="URL must start with http:// or https://")

    logger.info(f"Browser navigate: {url}")

    try:
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return BuiltinToolResult(
                success=False,
                error="Browser navigation requires Playwright. Install with: pip install playwright && playwright install chromium",
            )

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                await page.goto(url, timeout=timeout, wait_until="networkidle")

                if wait_for:
                    await page.wait_for_selector(wait_for, timeout=timeout)

                if extract_text:
                    content = await page.inner_text("body")
                else:
                    content = await page.content()

                title = await page.title()
                final_url = page.url

            finally:
                await browser.close()

            return BuiltinToolResult(
                success=True,
                result=content,
                metadata={"url": final_url, "title": title, "content_length": len(content)},
            )

    except Exception as e:
        logger.exception(f"Browser navigation failed: {e}")
        return BuiltinToolResult(success=False, error=f"Navigation failed: {str(e)}")


def _extract_text_from_html(html_content: str) -> str:
    """Extract plain text from HTML content."""
    text = re.sub(r"<script[^>]*>.*?</script>", "", html_content, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _parse_ddg_results(html_content: str, max_results: int) -> list[dict]:
    """Parse DuckDuckGo HTML search results."""
    results = []

    link_pattern = r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>([^<]*)</a>'
    snippet_pattern = r'<a[^>]*class="result__snippet"[^>]*>([^<]*(?:<[^>]*>[^<]*)*)</a>'

    links = re.findall(link_pattern, html_content)
    snippets = re.findall(snippet_pattern, html_content)

    for i, (url, title) in enumerate(links[:max_results]):
        snippet = snippets[i] if i < len(snippets) else ""
        snippet = re.sub(r"<[^>]*>", "", snippet)
        snippet = html.unescape(snippet).strip()

        if "uddg=" in url:
            url_match = re.search(r"uddg=([^&]+)", url)
            if url_match:
                url = unquote(url_match.group(1))

        results.append({"title": html.unescape(title).strip(), "url": url, "snippet": snippet})

    return results
