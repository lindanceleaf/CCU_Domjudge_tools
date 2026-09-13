"""Small HTTP helpers for DOMjudge import endpoints."""

from pathlib import Path

import requests


def upload_multipart(session, base_url, endpoint, field_name, file_path):
    path = Path(file_path)
    url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
    content_type = "application/json" if path.suffix.lower() == ".json" else "application/octet-stream"

    with path.open("rb") as source:
        try:
            response = session.post(
                url,
                files={field_name: (path.name, source, content_type)},
                timeout=30,
            )
        except requests.RequestException as error:
            raise requests.RequestException(f"{url}: {error}") from error

    try:
        response.raise_for_status()
    except requests.HTTPError as error:
        summary = " ".join(response.text.split())
        if len(summary) > 500:
            summary = summary[:500] + "..."
        raise requests.HTTPError(
            f"{url}: HTTP {response.status_code}; response: {summary or '(empty response)'}",
            response=response,
            request=error.request,
        ) from error

    return response

