"""Assistant page placeholder.

The chat itself already works on the Home page — this page is for a
future, more dedicated assistant workspace.
"""

from components.placeholder import render_placeholder


def render() -> None:
    render_placeholder(
        title="Assistant",
        description=(
            "A dedicated assistant workspace with saved conversations and "
            "deeper farm context will live here. You can already chat with "
            "KisanSense from the Home page."
        ),
        planned_note="Planned for Phase 5.",
    )
