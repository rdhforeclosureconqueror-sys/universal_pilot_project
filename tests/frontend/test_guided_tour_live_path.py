from pathlib import Path
import re

MAIN_JS = Path("frontend/main.js")


def _source() -> str:
    return MAIN_JS.read_text(encoding="utf-8")


def test_guided_tour_persistence_keys_exist():
    source = _source()
    assert 'const TOUR_COMPLETED_KEY = "guided_tour_completed_v1";' in source
    assert 'const TOUR_DISMISSED_KEY = "guided_tour_dismissed_v1";' in source


def test_dismissal_does_not_override_completed_state():
    source = _source()
    assert (
        'if (localStorage.getItem(TOUR_COMPLETED_KEY) === "true") {\n'
        '      return;\n'
        '    }\n'
        '    localStorage.setItem(TOUR_DISMISSED_KEY, "true");'
    ) in source


def test_auto_start_is_blocked_when_completed_or_dismissed():
    source = _source()
    assert 'const completed = localStorage.getItem(TOUR_COMPLETED_KEY) === "true";' in source
    assert 'const dismissed = localStorage.getItem(TOUR_DISMISSED_KEY) === "true";' in source
    assert 'return !completed && !dismissed;' in source


def test_take_tour_button_always_restarts_from_step_one():
    source = _source()
    assert 'document.getElementById("tour-replay").addEventListener("click", () => {' in source
    assert 'guidedTourController.restart();' in source
    assert 'const restart = async () => {' in source
    assert 'await start({ restart: true });' in source


def test_missing_target_steps_are_skipped_safely_without_crashing():
    source = _source()
    pattern = re.compile(
        r"if \(!target\) \{\n\s*if \(step\.skipIfMissing \|\| step\.optional\) \{\n\s*activateStep\(requestedIndex \+ 1\);\n\s*return;\n\s*\}\n\s*stop\(\{ markComplete: false \}\);",
        re.MULTILINE,
    )
    assert pattern.search(source), "Missing-target skip logic must be preserved"


def test_auto_start_only_runs_for_non_login_dashboard_routes_with_token():
    source = _source()
    assert 'const isNonLoginDashboardRoute = (page) =>' in source
    assert 'Boolean(page && page !== "login" && pages[page]);' in source
    assert 'if (!token || !isNonLoginDashboardRoute(currentPage)) {' in source


def test_tour_route_handoff_is_present_for_cross_page_steps():
    source = _source()
    assert 'window.location.hash = `#/${step.page}`;' in source
    assert 'setPageFn(step.page);' in source
