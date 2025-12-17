#!/usr/bin/env python3
"""
File Tools for AI Agents.

Provides tools for reading, writing, and searching files.
Returns actual file contents and performs real file operations.

Example:
    User: "What's in the config.json file?"
    Agent uses: read_file("config.json")
    Returns: Actual file contents
"""

import os
from typing import Optional
from langchain_core.tools import tool
from pydantic import BaseModel, Field


# ============================================================================
# Pydantic Schemas
# ============================================================================

class ReadFileInput(BaseModel):
    """Input for reading a file."""
    path: str = Field(description="Path to the file to read")
    encoding: str = Field(default="utf-8", description="File encoding")
    max_size: int = Field(default=100000, description="Max bytes to read")


class WriteFileInput(BaseModel):
    """Input for writing a file."""
    path: str = Field(description="Path to the file to write")
    content: str = Field(description="Content to write")
    encoding: str = Field(default="utf-8", description="File encoding")
    mode: str = Field(default="w", description="Write mode: 'w' (overwrite) or 'a' (append)")


class SearchFilesInput(BaseModel):
    """Input for searching files."""
    directory: str = Field(description="Directory to search in")
    pattern: str = Field(description="Glob pattern to match (e.g., '*.py', '**/*.json')")
    recursive: bool = Field(default=True, description="Search recursively")


# ============================================================================
# File Reading Tools
# ============================================================================

@tool(args_schema=ReadFileInput)
def read_file(path: str, encoding: str = "utf-8", max_size: int = 100000) -> dict:
    """Read the contents of a file.

    Use this tool when you need to read file contents.
    Examples:
    - Reading configuration files
    - Loading data files
    - Checking log files

    Args:
        path: Path to the file
        encoding: File encoding (default: utf-8)
        max_size: Maximum bytes to read (default: 100KB)

    Returns:
        File contents or error
    """
    try:
        # Security check - prevent path traversal
        abs_path = os.path.abspath(path)

        if not os.path.exists(abs_path):
            return {"success": False, "error": f"File not found: {path}"}

        if not os.path.isfile(abs_path):
            return {"success": False, "error": f"Not a file: {path}"}

        # Check file size
        file_size = os.path.getsize(abs_path)
        if file_size > max_size:
            return {
                "success": False,
                "error": f"File too large ({file_size} bytes). Max: {max_size} bytes"
            }

        with open(abs_path, "r", encoding=encoding) as f:
            content = f.read()

        return {
            "success": True,
            "path": abs_path,
            "content": content,
            "size": file_size,
            "encoding": encoding
        }

    except UnicodeDecodeError:
        return {"success": False, "error": f"Cannot decode file with {encoding} encoding"}
    except PermissionError:
        return {"success": False, "error": "Permission denied"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def read_file_lines(
    path: str,
    start_line: int = 1,
    num_lines: int = 100,
    encoding: str = "utf-8"
) -> dict:
    """Read specific lines from a file.

    Use this tool when you need to read a portion of a large file.

    Args:
        path: Path to the file
        start_line: Line number to start from (1-based)
        num_lines: Number of lines to read
        encoding: File encoding

    Returns:
        Selected lines from the file
    """
    try:
        abs_path = os.path.abspath(path)

        if not os.path.exists(abs_path):
            return {"success": False, "error": f"File not found: {path}"}

        lines = []
        with open(abs_path, "r", encoding=encoding) as f:
            for i, line in enumerate(f, 1):
                if i >= start_line and i < start_line + num_lines:
                    lines.append({"line_num": i, "content": line.rstrip()})
                if i >= start_line + num_lines:
                    break

        return {
            "success": True,
            "path": abs_path,
            "start_line": start_line,
            "lines": lines,
            "count": len(lines)
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================================
# File Writing Tools
# ============================================================================

@tool(args_schema=WriteFileInput)
def write_file(
    path: str,
    content: str,
    encoding: str = "utf-8",
    mode: str = "w"
) -> dict:
    """Write content to a file.

    Use this tool when you need to save data to a file.
    Examples:
    - Saving generated content
    - Creating configuration files
    - Writing logs

    Args:
        path: Path to the file
        content: Content to write
        encoding: File encoding
        mode: 'w' to overwrite, 'a' to append

    Returns:
        Write result with bytes written
    """
    if mode not in ["w", "a"]:
        return {"success": False, "error": "Mode must be 'w' (overwrite) or 'a' (append)"}

    try:
        abs_path = os.path.abspath(path)

        # Create directory if needed
        directory = os.path.dirname(abs_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

        with open(abs_path, mode, encoding=encoding) as f:
            bytes_written = f.write(content)

        return {
            "success": True,
            "path": abs_path,
            "bytes_written": bytes_written,
            "mode": "overwrite" if mode == "w" else "append"
        }

    except PermissionError:
        return {"success": False, "error": "Permission denied"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================================
# File Search Tools
# ============================================================================

@tool(args_schema=SearchFilesInput)
def search_files(
    directory: str,
    pattern: str,
    recursive: bool = True
) -> dict:
    """Search for files matching a pattern.

    Use this tool when you need to find files by name or extension.
    Examples:
    - Find all Python files: pattern="*.py"
    - Find all JSON configs: pattern="**/config*.json"

    Args:
        directory: Directory to search in
        pattern: Glob pattern (e.g., "*.py", "**/*.json")
        recursive: Whether to search subdirectories

    Returns:
        List of matching file paths
    """
    import glob

    try:
        abs_dir = os.path.abspath(directory)

        if not os.path.exists(abs_dir):
            return {"success": False, "error": f"Directory not found: {directory}"}

        if not os.path.isdir(abs_dir):
            return {"success": False, "error": f"Not a directory: {directory}"}

        search_pattern = os.path.join(abs_dir, pattern)
        matches = glob.glob(search_pattern, recursive=recursive)

        files = []
        for match in matches[:100]:  # Limit results
            if os.path.isfile(match):
                files.append({
                    "path": match,
                    "name": os.path.basename(match),
                    "size": os.path.getsize(match)
                })

        return {
            "success": True,
            "directory": abs_dir,
            "pattern": pattern,
            "files": files,
            "count": len(files)
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def search_in_files(
    directory: str,
    search_text: str,
    file_pattern: str = "*",
    max_results: int = 50
) -> dict:
    """Search for text within files.

    Use this tool when you need to find files containing specific text.

    Args:
        directory: Directory to search in
        search_text: Text to search for
        file_pattern: File pattern to filter (e.g., "*.py")
        max_results: Maximum number of matches to return

    Returns:
        Files and lines containing the search text
    """
    import glob

    try:
        abs_dir = os.path.abspath(directory)

        if not os.path.exists(abs_dir):
            return {"success": False, "error": f"Directory not found: {directory}"}

        search_pattern = os.path.join(abs_dir, "**", file_pattern)
        files = glob.glob(search_pattern, recursive=True)

        results = []

        for file_path in files:
            if not os.path.isfile(file_path):
                continue

            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    for line_num, line in enumerate(f, 1):
                        if search_text in line:
                            results.append({
                                "file": file_path,
                                "line_num": line_num,
                                "line": line.strip()[:200]  # Limit line length
                            })

                            if len(results) >= max_results:
                                return {
                                    "success": True,
                                    "results": results,
                                    "count": len(results),
                                    "truncated": True
                                }
            except:
                continue  # Skip files that can't be read

        return {
            "success": True,
            "results": results,
            "count": len(results),
            "truncated": False
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================================
# File Parsing Tools
# ============================================================================

@tool
def parse_csv(path: str, limit: int = 1000) -> dict:
    """Parse a CSV file into records.

    Use this tool when you need to read structured CSV data.

    Args:
        path: Path to the CSV file
        limit: Maximum rows to return

    Returns:
        List of records as dictionaries
    """
    import csv

    try:
        abs_path = os.path.abspath(path)

        if not os.path.exists(abs_path):
            return {"success": False, "error": f"File not found: {path}"}

        records = []
        with open(abs_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                if i >= limit:
                    break
                records.append(dict(row))

        return {
            "success": True,
            "path": abs_path,
            "records": records,
            "count": len(records),
            "columns": list(records[0].keys()) if records else []
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def parse_json(path: str) -> dict:
    """Parse a JSON file.

    Use this tool when you need to read JSON data.

    Args:
        path: Path to the JSON file

    Returns:
        Parsed JSON data
    """
    import json

    try:
        abs_path = os.path.abspath(path)

        if not os.path.exists(abs_path):
            return {"success": False, "error": f"File not found: {path}"}

        with open(abs_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return {
            "success": True,
            "path": abs_path,
            "data": data
        }

    except json.JSONDecodeError as e:
        return {"success": False, "error": f"Invalid JSON: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def file_info(path: str) -> dict:
    """Get information about a file.

    Use this tool to check file existence, size, and metadata.

    Args:
        path: Path to the file

    Returns:
        File metadata
    """
    from datetime import datetime

    try:
        abs_path = os.path.abspath(path)

        if not os.path.exists(abs_path):
            return {"success": False, "error": f"File not found: {path}", "exists": False}

        stat = os.stat(abs_path)

        return {
            "success": True,
            "exists": True,
            "path": abs_path,
            "name": os.path.basename(abs_path),
            "is_file": os.path.isfile(abs_path),
            "is_directory": os.path.isdir(abs_path),
            "size": stat.st_size,
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "extension": os.path.splitext(abs_path)[1]
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================================
# Export all tools
# ============================================================================

FILE_TOOLS = [
    read_file,
    read_file_lines,
    write_file,
    search_files,
    search_in_files,
    parse_csv,
    parse_json,
    file_info
]
