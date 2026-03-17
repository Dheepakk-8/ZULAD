from __future__ import annotations

import csv
import io
import os
from datetime import datetime, timezone
from typing import Dict, List

from flask import Flask, jsonify, render_template, request, send_file
from openpyxl import Workbook

from dashboard.analytics import build_filter_context, compute_dashboard
from dashboard.northpass_client import NorthpassClient


app = Flask(__name__)
client = NorthpassClient()


_cache: Dict[str, tuple[datetime, dict]] = {}
CACHE_SECONDS = int(os.getenv("CACHE_SECONDS", "300"))


def _load_data(force_refresh: bool = False) -> dict:
    key = "northpass_snapshot"
    now = datetime.now(timezone.utc)
    if not force_refresh and key in _cache:
        created_at, payload = _cache[key]
        if (now - created_at).total_seconds() < CACHE_SECONDS:
            return payload

    courses = client.get_courses()
    people = client.get_people()
    groups = client.get_groups()

    enrollments_by_course: Dict[str, List[dict]] = {}
    for course in courses:
        cid = str(course.get("id") or course.get("course_id"))
        enrollments_by_course[cid] = client.get_course_enrollments(cid)

    payload = {
        "courses": courses,
        "people": people,
        "groups": groups,
        "enrollments_by_course": enrollments_by_course,
    }
    _cache[key] = (now, payload)
    return payload


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/filters")
def filters():
    data = _load_data(request.args.get("refresh") == "true")
    return jsonify(
        {
            "courses": [
                {"id": str(c.get("id") or c.get("course_id")), "name": c.get("name", "Untitled")}
                for c in data["courses"]
            ],
            "groups": [
                {"id": str(g.get("id") or g.get("group_id")), "name": g.get("name") or g.get("group_name", "Unnamed")}
                for g in data["groups"]
            ],
            "learners": [
                {
                    "id": str(p.get("id") or p.get("learner_id")),
                    "name": p.get("name") or p.get("full_name") or "Unknown",
                    "email": p.get("email", ""),
                }
                for p in data["people"]
            ],
        }
    )


@app.get("/api/dashboard")
def dashboard():
    data = _load_data(request.args.get("refresh") == "true")
    ctx = build_filter_context(request.args)
    result = compute_dashboard(
        courses=data["courses"],
        enrollments_by_course=data["enrollments_by_course"],
        people=data["people"],
        groups=data["groups"],
        ctx=ctx,
    )
    return jsonify(result)


@app.get("/api/export")
def export_dashboard():
    fmt = request.args.get("format", "csv")
    data = _load_data(request.args.get("refresh") == "true")
    ctx = build_filter_context(request.args)
    result = compute_dashboard(
        courses=data["courses"],
        enrollments_by_course=data["enrollments_by_course"],
        people=data["people"],
        groups=data["groups"],
        ctx=ctx,
    )

    rows = result["courses"]
    if fmt == "xlsx":
        wb = Workbook()
        ws = wb.active
        ws.title = "Course Analytics"
        headers = ["Course Name", "Enrollments", "Completed", "In Progress", "Completion %", "Drop Rate %"]
        ws.append(headers)
        for row in rows:
            ws.append(
                [
                    row["course_name"],
                    row["enrollments"],
                    row["completed"],
                    row["in_progress"],
                    row["completion_percentage"],
                    row["drop_rate"],
                ]
            )

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return send_file(
            output,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name="dashboard_export.xlsx",
        )

    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=["course_name", "enrollments", "completed", "in_progress", "completion_percentage", "drop_rate"],
    )
    writer.writeheader()
    writer.writerows(rows)

    mem = io.BytesIO(output.getvalue().encode("utf-8"))
    return send_file(mem, mimetype="text/csv", as_attachment=True, download_name="dashboard_export.csv")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
