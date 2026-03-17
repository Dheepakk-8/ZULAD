from dashboard.analytics import FilterContext, compute_dashboard


def test_compute_dashboard_basic_metrics():
    courses = [{"id": "1", "name": "Course A"}]
    enrollments_by_course = {
        "1": [
            {"person_id": "u1", "progress": 100, "created_at": "2025-01-10T00:00:00Z", "last_active_at": "2025-01-10T00:00:00Z"},
            {"person_id": "u2", "progress": 50, "created_at": "2025-01-11T00:00:00Z", "last_active_at": "2025-01-11T00:00:00Z"},
        ]
    }
    result = compute_dashboard(courses, enrollments_by_course, people=[{}, {}], groups=[], ctx=FilterContext())

    assert result["kpis"]["users_enrolled"] == 2
    assert result["kpis"]["users_completed"] == 1
    assert result["kpis"]["completion_percentage"] == 50.0
