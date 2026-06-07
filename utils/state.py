from __future__ import annotations

PENDING_ACTION_KEY = "pending_action"
PENDING_DATA_KEY = "pending_data"


def set_pending(context, action: str, **data) -> None:
    context.user_data[PENDING_ACTION_KEY] = action
    context.user_data[PENDING_DATA_KEY] = data


def get_pending(context) -> tuple[str | None, dict]:
    action = context.user_data.get(PENDING_ACTION_KEY)
    data = context.user_data.get(PENDING_DATA_KEY, {})
    return action, data


def clear_pending(context) -> None:
    context.user_data.pop(PENDING_ACTION_KEY, None)
    context.user_data.pop(PENDING_DATA_KEY, None)

