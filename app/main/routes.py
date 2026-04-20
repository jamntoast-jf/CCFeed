import calendar as _cal
import math
import re
from collections import Counter
from datetime import date, datetime
from urllib.parse import unquote
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from flask import render_template, request, current_app
from app.main import bp
from app.db import fetch_notes

PER_PAGE = 10
PER_PAGE_MOBILE = 5

_MOBILE_UA = re.compile(r'(?i)(android|iphone|ipad|ipod|mobile|windows phone)')


def _per_page():
    ua = request.headers.get("User-Agent", "")
    return PER_PAGE_MOBILE if _MOBILE_UA.search(ua) else PER_PAGE


_COST_RE = re.compile(r"\[in:\d+ out:\d+ ~\$(\d+\.\d+)\]")


def _local_date(note, tz):
    dt = datetime.fromisoformat(note["createdAt"].replace("Z", "+00:00"))
    return dt.astimezone(tz).date()


def _parse_cost(text):
    m = _COST_RE.search(text or "")
    return float(m.group(1)) if m else None


def _compute_stats(all_notes, tz):
    if not all_notes:
        return None

    dates = []
    costs = []
    for note in all_notes:
        try:
            dates.append(_local_date(note, tz))
        except Exception:
            pass
        c = _parse_cost(note.get("text", ""))
        if c is not None:
            costs.append((c, note))

    if not dates:
        return None

    total = len(all_notes)
    first_date = min(dates)
    today_local = datetime.now(tz).date()
    days_active = (today_local - first_date).days + 1
    avg_per_day = round(total / days_active, 1)
    top_days = Counter(dates).most_common(5)

    stats = {
        "total": total,
        "avg_per_day": avg_per_day,
        "top_days": top_days,
        "first_date": first_date,
        "cost": None,
    }

    if costs:
        avg_cost = sum(c for c, _ in costs) / len(costs)
        top_cost, top_note = max(costs, key=lambda x: x[0])
        top_text = top_note.get("text", "")
        top_text_clean = _COST_RE.sub("", top_text).strip()
        short = top_text_clean if len(top_text_clean) <= 60 else top_text_clean[:57] + "..."
        stats["cost"] = {
            "avg": round(avg_cost, 4),
            "top": round(top_cost, 4),
            "top_text": short,
            "top_text_full": top_text_clean,
            "top_date": top_note.get("createdAt", "")[:10],
            "top_rkey": top_note.get("rkey", ""),
            "n": len(costs),
        }

    return stats


def _build_calendar(all_notes, month_str, tz):
    today = datetime.now(tz).date()
    if month_str:
        try:
            month_date = date.fromisoformat(month_str + "-01")
        except Exception:
            month_date = today.replace(day=1)
    else:
        month_date = today.replace(day=1)

    day_counts = Counter()
    for note in all_notes:
        try:
            day_counts[_local_date(note, tz)] += 1
        except Exception:
            pass

    c = _cal.Calendar(firstweekday=6)
    weeks = c.monthdatescalendar(month_date.year, month_date.month)

    y, m = month_date.year, month_date.month
    prev_month = date(y - 1 if m == 1 else y, 12 if m == 1 else m - 1, 1).strftime("%Y-%m")
    next_month = date(y + 1 if m == 12 else y, 1 if m == 12 else m + 1, 1).strftime("%Y-%m")

    return month_date, weeks, day_counts, prev_month, next_month


@bp.route("/")
def index():
    page = request.args.get("page", 1, type=int)
    month_str = request.args.get("month", "")
    day_str = request.args.get("day", "")
    highlight = request.args.get("note", "")

    try:
        tz = ZoneInfo(unquote(request.cookies.get("tz", "UTC")))
    except (ZoneInfoNotFoundError, KeyError):
        tz = ZoneInfo("UTC")

    try:
        all_notes = fetch_notes(current_app.config["DB_PATH"])
        stats = _compute_stats(all_notes, tz)
        cal_month, cal_weeks, day_counts, cal_prev, cal_next = _build_calendar(
            all_notes, month_str, tz
        )

        if day_str and not month_str:
            month_str = day_str[:7]
            cal_month, cal_weeks, day_counts, cal_prev, cal_next = _build_calendar(
                all_notes, month_str, tz
            )

        if day_str:
            try:
                sel_day = date.fromisoformat(day_str)
                filtered = [n for n in all_notes if _local_date(n, tz) == sel_day]
            except Exception:
                filtered = all_notes
        else:
            filtered = all_notes

        total_filtered = len(filtered)
        per_page = _per_page()
        total_pages = max(1, math.ceil(total_filtered / per_page))

        if highlight:
            for i, n in enumerate(filtered):
                if n.get("rkey") == highlight:
                    page = (i // per_page) + 1
                    break

        page = max(1, min(page, total_pages))
        offset = (page - 1) * per_page
        notes = filtered[offset:offset + per_page]
        error = None

    except Exception as e:
        notes, stats, total_pages, total_filtered, error = [], None, 1, 0, str(e)
        page = 1
        highlight = ""
        cal_month = date.today().replace(day=1)
        cal_weeks, day_counts = [], {}
        cal_prev = cal_next = ""

    return render_template(
        "index.html",
        notes=notes,
        page=page,
        total_pages=total_pages,
        total_filtered=total_filtered,
        month_str=month_str,
        day_str=day_str,
        cal_month=cal_month,
        cal_weeks=cal_weeks,
        day_counts=day_counts,
        cal_prev=cal_prev,
        cal_next=cal_next,
        highlight=highlight,
        stats=stats,
        error=error,
        feed_title=current_app.config["FEED_TITLE"],
    )
