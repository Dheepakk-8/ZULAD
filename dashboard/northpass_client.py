import os
from typing import Any, Dict, List, Optional

import requests


class NorthpassClient:
    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.northpass.com") -> None:
        self.api_key = api_key or os.getenv("NORTHPASS_API_KEY", "")
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()

    def _headers(self) -> Dict[str, str]:
        return {
            "X-Api-Key": self.api_key,
            "Accept": "application/json",
        }

    def _extract_items(self, payload: Any) -> List[Dict[str, Any]]:
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            for key in ["data", "items", "courses", "enrollments", "people", "groups", "activities"]:
                if isinstance(payload.get(key), list):
                    return payload[key]
        return []

    def _next_url(self, response: requests.Response, payload: Any) -> Optional[str]:
        link_header = response.headers.get("Link", "")
        for part in link_header.split(","):
            if 'rel="next"' in part:
                return part.split(";")[0].strip().strip("<>")

        if isinstance(payload, dict):
            for key in ["next", "next_page", "nextPage"]:
                value = payload.get(key)
                if value:
                    return value
            pagination = payload.get("pagination") or {}
            for key in ["next", "next_page", "nextPage"]:
                if pagination.get(key):
                    return pagination[key]
        return None

    def _paginate(self, path: str) -> List[Dict[str, Any]]:
        if not self.api_key:
            raise ValueError("NORTHPASS_API_KEY is required")

        url = f"{self.base_url}{path}" if path.startswith("/") else path
        records: List[Dict[str, Any]] = []

        while url:
            response = self.session.get(url, headers=self._headers(), timeout=30)
            response.raise_for_status()
            payload = response.json()
            records.extend(self._extract_items(payload))
            url = self._next_url(response, payload)

        return records

    def get_courses(self) -> List[Dict[str, Any]]:
        return self._paginate("/v2/courses")

    def get_course_enrollments(self, course_id: str) -> List[Dict[str, Any]]:
        return self._paginate(f"/v2/courses/{course_id}/enrollments")

    def get_people(self) -> List[Dict[str, Any]]:
        return self._paginate("/v2/people")

    def get_groups(self) -> List[Dict[str, Any]]:
        return self._paginate("/v2/groups")

    def get_course_activities(self, course_id: str) -> List[Dict[str, Any]]:
        return self._paginate(f"/v2/courses/{course_id}/activities")
