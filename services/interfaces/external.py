# services/interfaces/external.py
"""External service interface definitions."""

from typing import Protocol, Any, Optional


class IGristService(Protocol):
    """Interface for Grist spreadsheet operations."""

    async def load_table_data(
        self,
        table_name: str,
        filter_dict: Optional[dict] = None,
        sort: Optional[str] = None
    ) -> list[dict]:
        """Load data from table with optional filter and sort."""
        ...

    async def patch_table_data(self, table_name: str, records: list[dict]) -> bool:
        """Update existing records in table."""
        ...

    async def post_table_data(self, table_name: str, records: list[dict]) -> bool:
        """Insert new records into table."""
        ...

    async def fetch_table(
        self,
        table_name: str,
        filter_: Optional[dict] = None
    ) -> list[dict]:
        """Fetch table with optional filter."""
        ...


class IWebService(Protocol):
    """Interface for HTTP operations."""

    async def get(self, url: str, **kwargs) -> dict:
        """HTTP GET request."""
        ...

    async def post(self, url: str, data: Any = None, **kwargs) -> dict:
        """HTTP POST request."""
        ...

    async def get_json(self, url: str) -> Any:
        """GET request returning JSON."""
        ...
