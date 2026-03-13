#!/usr/bin/env python
"""Setup script for mcp-context-keeper package."""

from setuptools import find_packages, setup

with open("README.md", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="mcp-context-keeper",
    version="0.1.0",
    description="MCP (Model Context Protocol) server for managing and persisting context across conversations",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Hannibal",
    author_email="",
    url="https://github.com/annibale-x/context-keeper-mcp-server",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "pydantic>=2.0.0",
        "networkx>=3.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "ruff>=0.1.0",
            "mypy>=1.0.0",
        ],
        "server": [
            "fastapi>=0.104.0",
            "uvicorn[standard]>=0.24.0",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Communications :: Chat",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    keywords=[
        "mcp",
        "model-context-protocol",
        "context",
        "memory",
        "ai",
        "chat",
        "zed",
    ],
    project_urls={
        "Homepage": "https://github.com/annibale-x/context-keeper-mcp-server",
        "Documentation": "https://github.com/annibale-x/context-keeper-mcp-server#readme",
        "Repository": "https://github.com/annibale-x/context-keeper-mcp-server",
        "Issues": "https://github.com/annibale-x/context-keeper-mcp-server/issues",
    },
)
