"""Auth abstraction layer for analytics endpoints.

Single point of change when real authentication is added.
Currently returns a hardcoded dev user ID.

Rule: No analytics endpoint may reference a user_id except via get_current_user_id().
"""

from fastapi import Request


def get_current_user_id(request: Request) -> str:
    """Resolve the current user ID from the request.

    Currently returns a hardcoded dev placeholder.
    When real auth is added, read from session token/JWT here.

    Returns:
        str: The authenticated user's ID.
    """
    # PLACEHOLDER: hardcoded dev user
    return "dev_user_001"