"""Arena PLM API client with session authentication."""

import httpx
from typing import Any


class ArenaClient:
    """Client for Arena PLM REST API."""

    BASE_URL = "https://api.arenasolutions.com/v1"

    def __init__(self) -> None:
        self._session_id: str | None = None
        self._workspace_id: int | None = None
        self._http = httpx.Client(timeout=30.0)

    @property
    def is_authenticated(self) -> bool:
        return self._session_id is not None

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._session_id:
            headers["arena_session_id"] = self._session_id
        return headers

    def login(self, email: str, password: str, workspace_id: int | None = None) -> dict[str, Any]:
        """Authenticate with Arena API and establish session.

        Args:
            email: User email address
            password: User password
            workspace_id: Optional workspace ID to use

        Returns:
            Login response with session info

        Raises:
            httpx.HTTPStatusError: If login fails
        """
        payload: dict[str, Any] = {"email": email, "password": password}
        if workspace_id:
            payload["workspaceId"] = workspace_id

        response = self._http.post(
            f"{self.BASE_URL}/login",
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()

        data = response.json()
        self._session_id = data["arenaSessionId"]
        self._workspace_id = data.get("workspaceId")
        return data

    def logout(self) -> None:
        """End the current session."""
        if self._session_id:
            self._http.put(f"{self.BASE_URL}/logout", headers=self._headers())
            self._session_id = None
            self._workspace_id = None

    def _ensure_authenticated(self) -> None:
        """Raise if not authenticated."""
        if not self.is_authenticated:
            raise RuntimeError("Not authenticated. Call login() first.")

    @staticmethod
    def _wrap_wildcard(value: str | None) -> str | None:
        """Wrap value with wildcards for partial matching if not already wildcarded."""
        if value is None:
            return None
        if "*" in value:
            return value
        return f"*{value}*"

    def search_items(
        self,
        name: str | None = None,
        number: str | None = None,
        description: str | None = None,
        category_guid: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Search for items in Arena.

        Args:
            name: Filter by item name (partial match, wildcards added automatically)
            number: Filter by item number (partial match, wildcards added automatically)
            description: Filter by description (partial match, wildcards added automatically)
            category_guid: Filter by category GUID (exact match)
            limit: Max results to return (default 20, max 400)
            offset: Starting position in results

        Returns:
            Search results with count and items array

        Raises:
            RuntimeError: If not authenticated
            httpx.HTTPStatusError: If request fails
        """
        self._ensure_authenticated()

        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if name:
            params["name"] = self._wrap_wildcard(name)
        if number:
            params["number"] = self._wrap_wildcard(number)
        if description:
            params["description"] = self._wrap_wildcard(description)
        if category_guid:
            params["category.guid"] = category_guid

        response = self._http.get(
            f"{self.BASE_URL}/items",
            params=params,
            headers=self._headers(),
        )
        response.raise_for_status()
        return response.json()

    def get_item(
        self,
        guid: str,
        include_empty_attributes: bool = False,
    ) -> dict[str, Any]:
        """Get a single item by GUID.

        Args:
            guid: Item GUID
            include_empty_attributes: Include empty additional attributes in response

        Returns:
            Item object with full details

        Raises:
            RuntimeError: If not authenticated
            httpx.HTTPStatusError: If request fails
        """
        self._ensure_authenticated()

        params: dict[str, Any] = {}
        if include_empty_attributes:
            params["includeEmptyAdditionalAttributes"] = "true"

        response = self._http.get(
            f"{self.BASE_URL}/items/{guid}",
            params=params,
            headers=self._headers(),
        )
        response.raise_for_status()
        return response.json()

    def get_item_bom(
        self,
        guid: str,
        include_additional_attributes: bool = False,
    ) -> dict[str, Any]:
        """Get bill of materials for an item.

        Args:
            guid: Item GUID
            include_additional_attributes: Include BOM line additional attributes

        Returns:
            BOM with count and array of BOM line objects

        Raises:
            RuntimeError: If not authenticated
            httpx.HTTPStatusError: If request fails
        """
        self._ensure_authenticated()

        params: dict[str, Any] = {}
        if include_additional_attributes:
            params["includeAdditionalAttributes"] = "true"

        response = self._http.get(
            f"{self.BASE_URL}/items/{guid}/bom",
            params=params,
            headers=self._headers(),
        )
        response.raise_for_status()
        return response.json()

    def get_item_where_used(self, guid: str) -> dict[str, Any]:
        """Get assemblies where this item is used.

        Args:
            guid: Item GUID

        Returns:
            Where used results with count and array of assembly references

        Raises:
            RuntimeError: If not authenticated
            httpx.HTTPStatusError: If request fails
        """
        self._ensure_authenticated()

        response = self._http.get(
            f"{self.BASE_URL}/items/{guid}/whereused",
            headers=self._headers(),
        )
        response.raise_for_status()
        return response.json()

    def get_item_revisions(self, guid: str) -> dict[str, Any]:
        """Get all revisions for an item.

        Args:
            guid: Item GUID

        Returns:
            Revisions with count and array of revision objects.
            Status: 0=working, 1=effective, 2=superseded

        Raises:
            RuntimeError: If not authenticated
            httpx.HTTPStatusError: If request fails
        """
        self._ensure_authenticated()

        response = self._http.get(
            f"{self.BASE_URL}/items/{guid}/revisions",
            headers=self._headers(),
        )
        response.raise_for_status()
        return response.json()

    def get_item_files(self, guid: str) -> dict[str, Any]:
        """Get files associated with an item.

        Args:
            guid: Item GUID

        Returns:
            Files with count and array of file association objects

        Raises:
            RuntimeError: If not authenticated
            httpx.HTTPStatusError: If request fails
        """
        self._ensure_authenticated()

        response = self._http.get(
            f"{self.BASE_URL}/items/{guid}/files",
            headers=self._headers(),
        )
        response.raise_for_status()
        return response.json()

    def get_item_sourcing(
        self,
        guid: str,
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Get sourcing/supplier relationships for an item.

        Args:
            guid: Item GUID
            limit: Max results to return (default 20, max 400)
            offset: Starting position in results

        Returns:
            Sourcing with count and array of source relationship objects

        Raises:
            RuntimeError: If not authenticated
            httpx.HTTPStatusError: If request fails
        """
        self._ensure_authenticated()

        params: dict[str, Any] = {"limit": limit, "offset": offset}

        response = self._http.get(
            f"{self.BASE_URL}/items/{guid}/sourcing",
            params=params,
            headers=self._headers(),
        )
        response.raise_for_status()
        return response.json()

    def get_categories(self, path: str | None = None) -> dict[str, Any]:
        """Get item categories.

        Args:
            path: Filter categories by path (e.g., "item\\Assembly")

        Returns:
            Categories with count and array of category objects

        Raises:
            RuntimeError: If not authenticated
            httpx.HTTPStatusError: If request fails
        """
        self._ensure_authenticated()

        params: dict[str, Any] = {}
        if path:
            params["path"] = path

        response = self._http.get(
            f"{self.BASE_URL}/settings/items/categories",
            params=params,
            headers=self._headers(),
        )
        response.raise_for_status()
        return response.json()

    def close(self) -> None:
        """Close the HTTP client."""
        self._http.close()
