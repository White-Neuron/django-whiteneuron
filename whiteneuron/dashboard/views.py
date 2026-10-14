from django.shortcuts import render
from django.utils.translation import gettext as _
from django.contrib import messages
from django.template.loader import render_to_string
from django.utils.html import format_html
from django.utils.safestring import mark_safe
import random
import json
from django.views.generic import RedirectView

class HomeView(RedirectView):
    pattern_name = "admin:index"


from whiteneuron.base.models import UserActivity, AnonymousActivity
import datetime
# timezones
from django.utils import timezone
from django.core.cache import cache
from django.db.models import Count, Q
from django.db.models.functions import TruncDay

_STATS_CACHE_TIMEOUT = 60  # seconds


def _period_ranges(time, today):
    """Half-open [start, end) ranges (local dates) for the period and the previous one."""
    if time == "today":
        start, end = today, today + datetime.timedelta(days=1)
        start_last = start - datetime.timedelta(days=1)
    elif time == "7days":
        start, end = today - datetime.timedelta(days=6), today + datetime.timedelta(days=1)
        start_last = start - datetime.timedelta(days=7)
    elif time == "week":
        start = today - datetime.timedelta(days=today.weekday())
        end = start + datetime.timedelta(days=7)
        start_last = start - datetime.timedelta(days=7)
    elif time == "month":
        start = today.replace(day=1)
        end = (start + datetime.timedelta(days=32)).replace(day=1)
        start_last = (start - datetime.timedelta(days=1)).replace(day=1)
    elif time == "year":
        start = today.replace(month=1, day=1)
        end = start.replace(year=start.year + 1)
        start_last = start.replace(year=start.year - 1)
    else:
        return None
    return start, end, start_last


def _aware(day):
    return timezone.make_aware(datetime.datetime.combine(day, datetime.time.min))


def _dashboard_stats(time):
    """KPI + 28-day chart numbers: 4 aggregate queries, cached briefly."""
    today = timezone.localdate()
    ranges = _period_ranges(time, today)
    if ranges is None:
        return None
    cache_key = f"wn:dashboard:{time}:{today.isoformat()}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    start, end, start_last = (_aware(d) for d in ranges)
    ok = Q(status_code__lt=400)

    def kpi(model):
        # current period, its successes, previous period — in one query
        current = Q(timestamp__gte=start, timestamp__lt=end)
        row = model.objects.filter(timestamp__gte=start_last, timestamp__lt=end).aggregate(
            total=Count("id", filter=current),
            success=Count("id", filter=current & ok),
            last=Count("id", filter=Q(timestamp__lt=start)),
        )
        return row["total"], row["success"], row["last"]

    days = [today - datetime.timedelta(days=n) for n in range(27, -1, -1)]  # oldest -> today
    tz = timezone.get_current_timezone()

    def per_day(model):
        rows = (model.objects.filter(timestamp__gte=_aware(days[0]))
                .annotate(day=TruncDay("timestamp", tzinfo=tz)).values("day")
                .annotate(success=Count("id", filter=ok), error=Count("id", filter=~ok | Q(status_code__isnull=True))))
        by_day = {row["day"].date() if hasattr(row["day"], "date") else row["day"]: row for row in rows}
        success = [by_day.get(d, {}).get("success", 0) for d in days]
        error = [by_day.get(d, {}).get("error", 0) for d in days]
        return success, error

    user_success, user_error = per_day(UserActivity)
    anon_success, anon_error = per_day(AnonymousActivity)
    stats = {
        "kpi": kpi(UserActivity) + kpi(AnonymousActivity),
        "chart": {
            "success": user_success,
            "error": user_error,
            "anonymous_success": anon_success,
            "anonymous_error": anon_error,
            "average": [(a + b) / 2 for a, b in zip(user_success, user_error)],
            "anonymous_average": [(a + b) / 2 for a, b in zip(anon_success, anon_error)],
        },
        "weekdays": [d.weekday() for d in days],
    }
    cache.set(cache_key, stats, timeout=_STATS_CACHE_TIMEOUT)
    return stats


def dashboard_callback(request, context):
    # messages.info(request, render_to_string("CCMS/service.html"))

    time= request.GET.get("time", "week")
    if time not in ("today", "7days", "week", "month", "year"):
        time = "week"
    
    MAPTIME = {
        'today': _('today'),
        '7days': _('7 days'),
        'week': _('week'),
        'month': _('month'),
        'year': _('year'),
    }

    WEEKDAYS = [
        "Mon",
        "Tue",
        "Wed",
        "Thu",
        "Fri",
        "Sat",
        "Sun",
    ]

    stats = _dashboard_stats(time)  # `time` is validated above
    (total_activities, total_activities_success, total_activities_last,
     total_anonymous_activities, total_anonymous_activities_success,
     total_anonymous_activities_last) = stats["kpi"]
    user_activities_28_days = stats["chart"]
    _28_days = [_(WEEKDAYS[d]) for d in stats["weekdays"]]

    def render_kpi(label, object_name, value, last_value, time, success=None):
        # Whole translatable sentences with named placeholders (word order differs per
        # language; makemessages can't see _() inside f-strings)
        diff = value - last_value
        diff_percent = diff / last_value * 100 if last_value else 0
        period = MAPTIME[time] if time != "today" else _("day")
        footer = format_html(
            '<strong class="{} font-medium">{}{} ({}%)</strong>&nbsp;{} - {}',
            "text-green-600" if diff >= 0 else "text-red-600",
            "+" if diff >= 0 else "-", abs(diff), f"{diff_percent:.2f}",
            _("progress from last"), period,
        )
        rate = round(success / value * 100, 1) if value and success else None
        return {
            "label": label,
            "title": _("%(object)s in %(period)s") % {"object": object_name, "period": MAPTIME[time]},
            "metric_total": value,
            "metric_success": (
                _("%(count)s successful (%(rate)s%%)") % {"count": success, "rate": rate}
                if rate is not None else None
            ),
            "footer": footer,
        }


    # positive = [[1, random.randrange(8, 28)] for i in range(1, 28)]
    # negative = [[-1, -random.randrange(8, 28)] for i in range(1, 28)]
    # average = [r[1] - random.randint(3, 5) for r in positive]
    # performance_positive = [[1, random.randrange(8, 28)] for i in range(1, 28)]
    # performance_negative = [[-1, -random.randrange(8, 28)] for i in range(1, 28)]

    context.update(
        {
            "navigation": [
                {"title": _("Dashboard"), "link": "", "active": True},
                {"title": _("Analytics"), "link": "analytics"},
                {"title": _("Settings"), "link": "settings"},
            ],
            "filters": [
                {
                    "title": _("Today"),
                    "link": "?time=today",
                    "active": False if time != "today" else True,
                },
                {
                    "title": _("7 days"),
                    "link": "?time=7days",
                    "active": False if time != "7days" else True,
                },
                {
                    "title": _("Week"), 
                    "link": "?time=week",
                    "active": False if time != "week" else True,
            },
                {
                    "title": _("Month"),
                    "link": "?time=month",
                    "active": False if time != "month" else True,
                },
                {
                    "title": _("Year"),
                    "link": "?time=year",
                    "active": False if time != "year" else True,
                },
            ],
            "kpi": [
                render_kpi(_("User"), _("Activities"), total_activities, total_activities_last, time, success=total_activities_success),
                render_kpi(_("Anonymous"), _("Visits"), total_anonymous_activities, total_anonymous_activities_last, time, success=total_anonymous_activities_success),
                # render_kpi("Activity", "ICD-10 activities", total_activities_icd10, total_activities_last_icd10, time),
                # {
                #     "title": "Product A Performance",
                #     "metric": "$1,234.56",
                #     "footer": mark_safe(
                #         '<strong class="text-green-600 font-medium">+3.14%</strong>&nbsp;{_("progress from last")} week'
                #     ),
                #     "chart": json.dumps(
                #         {
                #             "labels": [WEEKDAYS[day % 7] for day in range(1, 28)],
                #             "datasets": [{"data": average, "borderColor": "#9333ea"}],
                #         }
                #     ),
                # },
            ],
            # "progress": [
            #     {
            #         "title": "Social marketing e-book",
            #         "description": " $1,234.56",
            #         "value": random.randint(10, 90),
            #     },
            #     {
            #         "title": "Freelancing tasks",
            #         "description": " $1,234.56",
            #         "value": random.randint(10, 90),
            #     },
            #     {
            #         "title": "Development coaching",
            #         "description": " $1,234.56",
            #         "value": random.randint(10, 90),
            #     },
            #     {
            #         "title": "Product consulting",
            #         "description": " $1,234.56",
            #         "value": random.randint(10, 90),
            #     },
            #     {
            #         "title": "Other income",
            #         "description": " $1,234.56",
            #         "value": random.randint(10, 90),
            #     },
            # ],
            # colors are CSS variables: unfold (>= 0.105) resolves them, so the chart follows the admin theme
            "chart": json.dumps(
                {
                    "labels": _28_days,
                    "datasets": [
                        {
                            "label": _("User average"),
                            "type": "line",
                            "data": user_activities_28_days['average'],
                            "backgroundColor": "var(--color-primary-300)",
                            "borderColor": "var(--color-primary-300)",
                        },
                        {
                            "label": _("Anonymous average"),
                            "type": "line",
                            "data": user_activities_28_days['anonymous_average'],
                            "backgroundColor": "var(--color-secondary)",
                            "borderColor": "var(--color-secondary)",
                        },
                        {
                            "label": _("User success"),
                            "data": user_activities_28_days['success'],
                            "backgroundColor": "var(--color-primary-600)",
                        },
                        {
                            "label": _("Anonymous success"),
                            "data": user_activities_28_days['anonymous_success'],
                            "backgroundColor": "var(--color-accent)",
                        },
                        {
                            "label": _("User error"),
                            "data": user_activities_28_days['error'],
                            "backgroundColor": "var(--color-error)",
                        },
                        {
                            "label": _("Anonymous error"),
                            "data": user_activities_28_days['anonymous_error'],
                            "backgroundColor": "var(--color-warning)",
                        },
                    ],
                }
            ),
            # "performance": [
            #     {
            #         "title": _("Last week revenue"),
            #         "metric": "$1,234.56",
            #         "footer": mark_safe(
            #             '<strong class="text-green-600 font-medium">+3.14%</strong>&nbsp;{_("progress from last")} week'
            #         ),
            #         "chart": json.dumps(
            #             {
            #                 "labels": [WEEKDAYS[day % 7] for day in range(1, 28)],
            #                 "datasets": [
            #                     {"data": performance_positive, "borderColor": "#9333ea"}
            #                 ],
            #             }
            #         ),
            #     },
            #     {
            #         "title": _("Last week expenses"),
            #         "metric": "$1,234.56",
            #         "footer": mark_safe(
            #             '<strong class="text-green-600 font-medium">+3.14%</strong>&nbsp;{_("progress from last")} week'
            #         ),
            #         "chart": json.dumps(
            #             {
            #                 "labels": [WEEKDAYS[day % 7] for day in range(1, 28)],
            #                 "datasets": [
            #                     {"data": performance_negative, "borderColor": "#f43f5e"}
            #                 ],
            #             }
            #         ),
            #     },
            # ],
        },
    )

    return context