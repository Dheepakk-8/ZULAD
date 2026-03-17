from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional



@dataclass
class FilterContext:
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    course_id: Optional[str] = None
    group_id: Optional[str] = None
    learner_id: Optional[str] = None
    completion_min: Optional[float] = None
    completion_max: Optional[float] = None
    inactive_days_threshold: int = 7


def _parse_date(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def build_filter_context(params: Dict[str, str]) -> FilterContext:
    completion_min = float(params["completion_min"]) if params.get("completion_min") else None
    completion_max = float(params["completion_max"]) if params.get("completion_max") else None
    return FilterContext(
        date_from=_parse_date(params.get("date_from")),
        date_to=_parse_date(params.get("date_to")),
        course_id=params.get("course_id") or None,
        group_id=params.get("group_id") or None,
        learner_id=params.get("learner_id") or None,
        completion_min=completion_min,
        completion_max=completion_max,
    )


def _within_dates(dt_value: Optional[str], ctx: FilterContext) -> bool:
    if not dt_value:
        return True
    dt = datetime.fromisoformat(dt_value.replace("Z", "+00:00"))
    if ctx.date_from and dt < ctx.date_from:
        return False
    if ctx.date_to and dt > ctx.date_to:
        return False
    return True


def _is_dropped(enrollment: Dict[str, Any], threshold_days: int) -> bool:
    progress = int(enrollment.get("progress", 0) or 0)
    if progress >= 100:
        return False
    last_active = enrollment.get("last_active_at") or enrollment.get("updated_at")
    if not last_active:
        return False
    return datetime.fromisoformat(last_active.replace("Z", "+00:00")) < datetime.now(timezone.utc) - timedelta(days=threshold_days)


def compute_dashboard(courses: List[Dict[str, Any]], enrollments_by_course: Dict[str, List[Dict[str, Any]]], people: List[Dict[str, Any]], groups: List[Dict[str, Any]], ctx: FilterContext) -> Dict[str, Any]:
    learner_group_map: Dict[str, set[str]] = defaultdict(set)
    for group in groups:
        for member_id in group.get("member_ids", []) or []:
            learner_group_map[str(member_id)].add(str(group.get("id") or group.get("group_id")))

    selected_courses = [c for c in courses if not ctx.course_id or str(c.get("id") or c.get("course_id")) == ctx.course_id]

    course_rows = []
    unique_learners = set()
    total_enrollments = total_completed = total_in_progress = total_dropped = 0

    for course in selected_courses:
        cid = str(course.get("id") or course.get("course_id"))
        enrollments = enrollments_by_course.get(cid, [])
        scoped = []
        for e in enrollments:
            learner_id = str(e.get("person_id") or e.get("learner_id"))
            if ctx.learner_id and learner_id != ctx.learner_id:
                continue
            if ctx.group_id and ctx.group_id not in learner_group_map.get(learner_id, set()):
                continue
            if not _within_dates(e.get("created_at"), ctx):
                continue
            scoped.append(e)

        enrolled = len(scoped)
        completed = sum(1 for e in scoped if int(e.get("progress", 0) or 0) == 100)
        in_progress = sum(1 for e in scoped if 0 < int(e.get("progress", 0) or 0) < 100)
        dropped = sum(1 for e in scoped if _is_dropped(e, ctx.inactive_days_threshold))
        learners = {str(e.get("person_id") or e.get("learner_id")) for e in scoped}

        completion_pct = round((completed / len(learners) * 100), 2) if learners else 0
        if ctx.completion_min is not None and completion_pct < ctx.completion_min:
            continue
        if ctx.completion_max is not None and completion_pct > ctx.completion_max:
            continue

        unique_learners.update(learners)
        total_enrollments += enrolled
        total_completed += completed
        total_in_progress += in_progress
        total_dropped += dropped

        course_rows.append(
            {
                "course_id": cid,
                "course_name": course.get("name", "Unknown Course"),
                "enrollments": enrolled,
                "completed": completed,
                "in_progress": in_progress,
                "completion_percentage": completion_pct,
                "drop_rate": round((dropped / enrolled * 100), 2) if enrolled else 0,
            }
        )

    completion_percentage = round((total_completed / len(unique_learners) * 100), 2) if unique_learners else 0
    drop_rate = round((total_dropped / total_enrollments * 100), 2) if total_enrollments else 0

    kpis = {
        "courses_taken": len([r for r in course_rows if r["enrollments"] > 0]),
        "users_enrolled": total_enrollments,
        "users_completed": total_completed,
        "users_in_progress": total_in_progress,
        "users_dropped": total_dropped,
        "completion_percentage": completion_percentage,
        "drop_rate": drop_rate,
        "unique_learners": len(unique_learners),
    }

    insights = []
    low_completion_courses = [r for r in course_rows if r["completion_percentage"] < 40 and r["enrollments"] > 0]
    high_drop_courses = [r for r in course_rows if r["drop_rate"] > 30 and r["enrollments"] > 0]
    if low_completion_courses:
        insights.append(
            f"{len(low_completion_courses)} course(s) have completion rates below 40%, indicating potential content or engagement gaps."
        )
    if high_drop_courses:
        insights.append(
            f"{len(high_drop_courses)} course(s) exceed a 30% drop rate threshold and should be reviewed for friction points."
        )
    if not insights:
        insights.append("No critical rule-based risk signals detected for the selected filters.")

    return {
        "kpis": kpis,
        "courses": sorted(course_rows, key=lambda r: r["completion_percentage"]),
        "insights": insights,
        "people_count": len(people),
    }
