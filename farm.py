"""Farm page placeholder."""

from components.placeholder import render_placeholder


def render() -> None:
    render_placeholder(
        title="Farm",
        description="Your farm profile — fields, crops, location and layout — will live here.",
        planned_note="Planned for Phase 2.",
    )
