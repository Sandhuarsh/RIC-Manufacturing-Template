"""CRM KPI dashboard data (leads, opportunities, win rate, pipeline, geography).

Ported from the Supreme Equipments Server Script API "crm_kpi_dashboard_data".
"""

import frappe

WON_STATUS = "Converted"
LOST_STATUS = "Lost"
NOT_OPEN_STATUSES = ["Converted", "Lost", "Closed"]

SALES_STAGE_ORDER = [
    "Prospecting",
    "Qualification",
    "Needs Analysis",
    "Value Proposition",
    "Identifying Decision Makers",
    "Perception Analysis",
    "Proposal/Price Quote",
    "Negotiation/Review"
]


def attach_amounts(rows):
    names = [r.name for r in rows]
    quote_map = {}
    if names:
        quotes = frappe.get_all(
            "Quotation",
            filters={"opportunity": ["in", names], "docstatus": 1},
            fields=["opportunity", "base_grand_total", "status"],
            limit_page_length=0
        )
        for q in quotes:
            if q.status in ["Lost", "Cancelled"]:
                continue
            value = frappe.utils.flt(q.base_grand_total)
            if value > quote_map.get(q.opportunity, 0):
                quote_map[q.opportunity] = value
    for r in rows:
        amount = frappe.utils.flt(r.opportunity_amount)
        if not amount:
            amount = quote_map.get(r.name, 0)
        r["opportunity_amount"] = amount
    return rows


INDIA_STATES = [
    "Andaman and Nicobar Islands", "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar",
    "Chandigarh", "Chhattisgarh", "Dadra and Nagar Haveli and Daman and Diu", "Delhi", "Goa",
    "Gujarat", "Haryana", "Himachal Pradesh", "Jammu and Kashmir", "Jharkhand", "Karnataka",
    "Kerala", "Ladakh", "Lakshadweep Islands", "Madhya Pradesh", "Maharashtra", "Manipur",
    "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Puducherry", "Punjab", "Rajasthan", "Sikkim",
    "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal"
]

# Misspellings, old names and cities that people type into the State / City boxes.
INDIA_STATE_ALIASES = {
    "maharashatra": "Maharashtra", "maharastra": "Maharashtra", "maharshtra": "Maharashtra",
    "pune": "Maharashtra", "mumbai": "Maharashtra", "thane": "Maharashtra", "nashik": "Maharashtra",
    "nagpur": "Maharashtra", "ahilyanagar": "Maharashtra", "ahmednagar": "Maharashtra",
    "sangamner": "Maharashtra", "kolhapur": "Maharashtra", "sambhajinagar": "Maharashtra",
    "aurangabad": "Maharashtra", "solapur": "Maharashtra", "satara": "Maharashtra",
    "gujrat": "Gujarat", "ahmedabad": "Gujarat", "surat": "Gujarat", "vadodara": "Gujarat",
    "rajkot": "Gujarat", "kheda": "Gujarat",
    "chattisgarh": "Chhattisgarh", "chhatisgarh": "Chhattisgarh", "gariyaband": "Chhattisgarh",
    "raipur": "Chhattisgarh",
    "andhrapradesh": "Andhra Pradesh", "andra pradesh": "Andhra Pradesh", "eluru": "Andhra Pradesh",
    "vijayawada": "Andhra Pradesh", "visakhapatnam": "Andhra Pradesh",
    "hyderabad": "Telangana", "sangareddy": "Telangana", "warangal": "Telangana",
    "peddapalli": "Telangana", "telengana": "Telangana",
    "lucknow": "Uttar Pradesh", "barabanki": "Uttar Pradesh", "kanpur": "Uttar Pradesh",
    "noida": "Uttar Pradesh",
    "orissa": "Odisha", "uttaranchal": "Uttarakhand", "pondicherry": "Puducherry",
    "new delhi": "Delhi", "jammu & kashmir": "Jammu and Kashmir", "kolkata": "West Bengal",
    "bengaluru": "Karnataka", "bangalore": "Karnataka", "chennai": "Tamil Nadu",
    "jaipur": "Rajasthan", "ludhiana": "Punjab"
}

STATE_LOOKUP = {}
for state_name in INDIA_STATES:
    STATE_LOOKUP[state_name.lower()] = state_name
for alias_name in INDIA_STATE_ALIASES:
    STATE_LOOKUP[alias_name] = INDIA_STATE_ALIASES[alias_name]
STATE_SUBSTRING_KEYS = sorted([k for k in STATE_LOOKUP.keys() if len(k) >= 5], key=lambda x: -len(x))


def canonical_state(raw):
    if not raw:
        return None
    text = str(raw).strip().lower()
    if not text:
        return None
    if text in STATE_LOOKUP:
        return STATE_LOOKUP[text]
    for key in STATE_SUBSTRING_KEYS:
        if key in text:
            return STATE_LOOKUP[key]
    return None


def geo_territory_key(territory, country):
    # A real territory (e.g. "India", "Nashik") wins; the root "All Territories" and the
    # catch-all "Rest Of The World" are too vague for a map, so the record's country is
    # used instead when it has one.
    territory_text = (territory or "").strip()
    country_text = (country or "").strip()
    if territory_text and territory_text not in ["All Territories", "Rest Of The World"]:
        return territory_text
    if country_text:
        return country_text
    if territory_text and territory_text != "All Territories":
        return territory_text
    return "Not Set"


def geo_state_key(state, city, country):
    country_text = (country or "").strip().lower()
    if country_text and country_text != "india":
        return None
    canonical = canonical_state(state) or canonical_state(city)
    if canonical:
        return canonical
    if country_text == "india":
        return "Not Set"
    return None


def add_geo(bucket_map, label_field, key, metric, amount):
    if key not in bucket_map:
        bucket_map[key] = {label_field: key, "leads": 0, "opportunities": 0, "won": 0, "pipeline_value": 0}
    bucket_map[key][metric] = bucket_map[key][metric] + amount


def collect_geo(from_date, to_date, company, sales_person):
    leads = frappe.get_all(
        "Lead",
        filters=build_lead_filters(from_date, to_date, company, sales_person, None),
        fields=["territory", "country", "state", "city"],
        limit_page_length=0
    )
    opps = frappe.get_all(
        "Opportunity",
        filters=build_opportunity_filters(from_date, to_date, company, sales_person, None),
        fields=["name", "territory", "country", "state", "city", "status", "opportunity_amount"],
        limit_page_length=0
    )
    opps = attach_amounts(opps)

    territories = {}
    states = {}

    for l in leads:
        add_geo(territories, "territory", geo_territory_key(l.territory, l.country), "leads", 1)
        state_key = geo_state_key(l.state, l.city, l.country)
        if state_key:
            add_geo(states, "state", state_key, "leads", 1)

    for o in opps:
        territory_key = geo_territory_key(o.territory, o.country)
        state_key = geo_state_key(o.state, o.city, o.country)
        add_geo(territories, "territory", territory_key, "opportunities", 1)
        if state_key:
            add_geo(states, "state", state_key, "opportunities", 1)
        if o.status == WON_STATUS:
            add_geo(territories, "territory", territory_key, "won", 1)
            if state_key:
                add_geo(states, "state", state_key, "won", 1)
        if o.status not in NOT_OPEN_STATUSES:
            amount = frappe.utils.flt(o.opportunity_amount)
            add_geo(territories, "territory", territory_key, "pipeline_value", amount)
            if state_key:
                add_geo(states, "state", state_key, "pipeline_value", amount)

    return {"territories": territories, "states": states}


def geo_rows_with_previous(current_map, previous_map):
    rows = []
    for key in current_map:
        row = current_map[key]
        before = previous_map.get(key)
        if before:
            row["previous"] = {
                "leads": before["leads"],
                "opportunities": before["opportunities"],
                "won": before["won"],
                "pipeline_value": before["pipeline_value"]
            }
        else:
            row["previous"] = {"leads": 0, "opportunities": 0, "won": 0, "pipeline_value": 0}
        rows.append(row)
    rows.sort(key=lambda x: (x["leads"] + x["opportunities"]), reverse=True)
    return rows


def safe_div(numerator, denominator):
    if not denominator:
        return None
    return (numerator / denominator) * 100


def safe_avg(values):
    clean = [v for v in values if v is not None]
    if not clean:
        return None
    return sum(clean) / len(clean)


def parse_args():
    to_date = frappe.utils.getdate(frappe.form_dict.get("to_date") or frappe.utils.today())
    from_date = frappe.utils.getdate(
        frappe.form_dict.get("from_date") or frappe.utils.add_months(to_date, -3)
    )
    if from_date > to_date:
        swap_holder = from_date
        from_date = to_date
        to_date = swap_holder

    return {
        "from_date": from_date,
        "to_date": to_date,
        "company": frappe.form_dict.get("company") or None,
        "sales_person": frappe.form_dict.get("sales_person") or None,
        "territory": frappe.form_dict.get("territory") or None
    }


def previous_period(from_date, to_date):
    period_days = (to_date - from_date).days + 1
    prev_to = frappe.utils.add_days(from_date, -1)
    prev_from = frappe.utils.add_days(prev_to, -(period_days - 1))
    return {"from_date": prev_from, "to_date": prev_to}


def build_lead_filters(from_date, to_date, company, sales_person, territory):
    filters = {
        "creation": ["between", [
            frappe.utils.get_datetime(from_date),
            frappe.utils.add_to_date(frappe.utils.get_datetime(to_date), days=1, seconds=-1)
        ]]
    }
    if company:
        filters["company"] = company
    if sales_person:
        filters["lead_owner"] = sales_person
    if territory:
        filters["territory"] = territory
    return filters


def build_opportunity_filters(from_date, to_date, company, sales_person, territory):
    filters = {
        "creation": ["between", [
            frappe.utils.get_datetime(from_date),
            frappe.utils.add_to_date(frappe.utils.get_datetime(to_date), days=1, seconds=-1)
        ]]
    }
    if company:
        filters["company"] = company
    if sales_person:
        filters["opportunity_owner"] = sales_person
    if territory:
        filters["territory"] = territory
    return filters


def get_lead_conversion(from_date, to_date, company, sales_person, territory):
    filters = build_lead_filters(from_date, to_date, company, sales_person, territory)
    total = frappe.db.count("Lead", filters)

    converted_filters = dict(filters)
    converted_filters["status"] = "Converted"
    converted = frappe.db.count("Lead", converted_filters)

    rate = safe_div(converted, total)

    prev_period = previous_period(from_date, to_date)
    prev_filters = build_lead_filters(prev_period["from_date"], prev_period["to_date"], company, sales_person, territory)
    prev_total = frappe.db.count("Lead", prev_filters)
    prev_converted_filters = dict(prev_filters)
    prev_converted_filters["status"] = "Converted"
    prev_converted = frappe.db.count("Lead", prev_converted_filters)
    prev_rate = safe_div(prev_converted, prev_total)

    delta = None
    if rate is not None and prev_rate is not None:
        delta = round(rate - prev_rate, 1)

    return {
        "total_leads": total,
        "converted_leads": converted,
        "rate": round(rate, 1) if rate is not None else None,
        "previous_rate": round(prev_rate, 1) if prev_rate is not None else None,
        "delta": delta
    }


def get_win_rate(from_date, to_date, company, sales_person, territory):
    filters = build_opportunity_filters(from_date, to_date, company, sales_person, territory)

    won_filters = dict(filters)
    won_filters["status"] = WON_STATUS
    won = frappe.db.count("Opportunity", won_filters)

    lost_filters = dict(filters)
    lost_filters["status"] = LOST_STATUS
    lost = frappe.db.count("Opportunity", lost_filters)

    closed = won + lost
    rate = safe_div(won, closed)

    return {
        "won": won,
        "lost": lost,
        "closed": closed,
        "rate": round(rate, 1) if rate is not None else None
    }


def get_first_response_time(from_date, to_date, company, sales_person, territory):
    filters = build_opportunity_filters(from_date, to_date, company, sales_person, territory)
    filters["first_response_time"] = [">", 0]

    rows = frappe.get_all(
        "Opportunity",
        filters=filters,
        fields=["first_response_time"],
        limit_page_length=0
    )

    seconds_list = [frappe.utils.flt(r.first_response_time) for r in rows if r.first_response_time]
    avg_seconds = safe_avg(seconds_list)

    total_in_range = frappe.db.count("Opportunity", build_opportunity_filters(
        from_date, to_date, company, sales_person, territory
    ))

    result = {
        "avg_seconds": avg_seconds,
        "sample_size": len(seconds_list),
        "total_opportunities_in_range": total_in_range,
        "avg_hours": None,
        "avg_minutes": None
    }

    if avg_seconds is not None:
        total_minutes = int(round(avg_seconds / 60))
        result["avg_hours"] = total_minutes // 60
        result["avg_minutes"] = total_minutes % 60

    return result


def get_pipeline_value(from_date, to_date, company, sales_person, territory):
    filters = build_opportunity_filters(from_date, to_date, company, sales_person, territory)
    filters["status"] = ["not in", NOT_OPEN_STATUSES]

    rows = frappe.get_all(
        "Opportunity",
        filters=filters,
        fields=["name", "opportunity_amount", "sales_stage", "territory", "opportunity_owner", "creation"],
        limit_page_length=0
    )
    rows = attach_amounts(rows)

    total_value = sum(frappe.utils.flt(r.opportunity_amount) for r in rows)

    return {
        "total_value": total_value,
        "count": len(rows),
        "rows": rows
    }


def get_sales_cycle(from_date, to_date, company, sales_person, territory):
    filters = build_opportunity_filters(from_date, to_date, company, sales_person, territory)
    filters["status"] = WON_STATUS

    rows = frappe.get_all(
        "Opportunity",
        filters=filters,
        fields=["creation", "modified"],
        limit_page_length=0
    )

    days_list = []
    for r in rows:
        if not r.creation or not r.modified:
            continue
        days = (frappe.utils.get_datetime(r.modified) - frappe.utils.get_datetime(r.creation)).total_seconds() / 86400.0
        if days >= 0:
            days_list.append(days)

    avg_days = safe_avg(days_list)

    return {
        "avg_days": round(avg_days, 1) if avg_days is not None else None,
        "sample_size": len(days_list),
        "note": "Close date is approximated using the record's last-modified timestamp, since Opportunity has no dedicated close-date field in this installation."
    }


def get_lead_to_customer_time(from_date, to_date, company, sales_person, territory):
    customer_filters = {
        "lead_name": ["is", "set"],
        "creation": ["between", [
            frappe.utils.get_datetime(from_date),
            frappe.utils.add_to_date(frappe.utils.get_datetime(to_date), days=1, seconds=-1)
        ]]
    }

    customers = frappe.get_all(
        "Customer",
        filters=customer_filters,
        fields=["name", "lead_name", "creation"],
        limit_page_length=0
    )

    days_list = []
    excluded = 0

    for c in customers:
        lead = frappe.db.get_value(
            "Lead", c.lead_name, ["creation", "lead_owner", "territory", "company"], as_dict=True
        )
        if not lead or not lead.creation:
            excluded += 1
            continue
        if sales_person and lead.lead_owner != sales_person:
            continue
        if territory and lead.territory != territory:
            continue
        if company and lead.company != company:
            continue

        days = (frappe.utils.get_datetime(c.creation) - frappe.utils.get_datetime(lead.creation)).total_seconds() / 86400.0
        if days >= 0:
            days_list.append(days)
        else:
            excluded += 1

    avg_days = safe_avg(days_list)

    return {
        "avg_days": round(avg_days, 1) if avg_days is not None else None,
        "sample_size": len(days_list),
        "excluded_unreliable": excluded
    }


def get_lead_conversion_trend(from_date, to_date, company, sales_person, territory):
    filters = build_lead_filters(from_date, to_date, company, sales_person, territory)
    rows = frappe.get_all(
        "Lead",
        filters=filters,
        fields=["creation", "status"],
        limit_page_length=0
    )

    buckets = {}
    for r in rows:
        key = frappe.utils.formatdate(r.creation, "MM-yyyy")
        if key not in buckets:
            buckets[key] = {
                "month": key,
                "sort_key": str(frappe.utils.getdate(r.creation))[:7],
                "leads": 0,
                "converted": 0
            }
        buckets[key]["leads"] = buckets[key]["leads"] + 1
        if r.status == "Converted":
            buckets[key]["converted"] = buckets[key]["converted"] + 1

    result = sorted(buckets.values(), key=lambda x: x["sort_key"])
    for b in result:
        b["rate"] = round(safe_div(b["converted"], b["leads"]), 1) if b["leads"] else 0

    return result


def get_opportunity_funnel(from_date, to_date, company, sales_person, territory):
    filters = build_opportunity_filters(from_date, to_date, company, sales_person, territory)
    rows = frappe.get_all(
        "Opportunity",
        filters=filters,
        fields=["name", "sales_stage", "opportunity_amount"],
        limit_page_length=0
    )
    rows = attach_amounts(rows)

    stage_map = {}
    for r in rows:
        stage = r.sales_stage or "Not Set"
        if stage not in stage_map:
            stage_map[stage] = {"stage": stage, "count": 0, "amount": 0}
        stage_map[stage]["count"] = stage_map[stage]["count"] + 1
        stage_map[stage]["amount"] = stage_map[stage]["amount"] + frappe.utils.flt(r.opportunity_amount)

    ordered = []
    for stage in SALES_STAGE_ORDER:
        if stage in stage_map:
            ordered.append(stage_map.pop(stage))
    for remaining in stage_map.values():
        ordered.append(remaining)

    return ordered


def get_pipeline_by_stage(pipeline_rows):
    stage_map = {}
    for r in pipeline_rows:
        stage = r.sales_stage or "Not Set"
        if stage not in stage_map:
            stage_map[stage] = {"stage": stage, "count": 0, "amount": 0}
        stage_map[stage]["count"] = stage_map[stage]["count"] + 1
        stage_map[stage]["amount"] = stage_map[stage]["amount"] + frappe.utils.flt(r.opportunity_amount)

    ordered = []
    for stage in SALES_STAGE_ORDER:
        if stage in stage_map:
            ordered.append(stage_map.pop(stage))
    for remaining in stage_map.values():
        ordered.append(remaining)

    return ordered


def get_win_loss(from_date, to_date, company, sales_person, territory):
    filters = build_opportunity_filters(from_date, to_date, company, sales_person, territory)

    won_filters = dict(filters)
    won_filters["status"] = WON_STATUS
    won_rows = attach_amounts(frappe.get_all("Opportunity", filters=won_filters, fields=["name", "opportunity_amount"], limit_page_length=0))

    lost_filters = dict(filters)
    lost_filters["status"] = LOST_STATUS
    lost_rows = attach_amounts(frappe.get_all("Opportunity", filters=lost_filters, fields=["name", "opportunity_amount"], limit_page_length=0))

    return {
        "won_count": len(won_rows),
        "won_amount": sum(frappe.utils.flt(r.opportunity_amount) for r in won_rows),
        "lost_count": len(lost_rows),
        "lost_amount": sum(frappe.utils.flt(r.opportunity_amount) for r in lost_rows)
    }


def get_pipeline_trend(pipeline_rows):
    buckets = {}
    for r in pipeline_rows:
        key = frappe.utils.formatdate(r.creation, "MM-yyyy")
        sort_key = str(frappe.utils.getdate(r.creation))[:7]
        if key not in buckets:
            buckets[key] = {"month": key, "sort_key": sort_key, "value": 0, "count": 0}
        buckets[key]["value"] = buckets[key]["value"] + frappe.utils.flt(r.opportunity_amount)
        buckets[key]["count"] = buckets[key]["count"] + 1

    result = sorted(buckets.values(), key=lambda x: x["sort_key"])
    return result


def get_sales_person_performance(from_date, to_date, company, territory):
    lead_filters = build_lead_filters(from_date, to_date, company, None, territory)
    leads = frappe.get_all("Lead", filters=lead_filters, fields=["lead_owner", "status"], limit_page_length=0)

    opp_filters = build_opportunity_filters(from_date, to_date, company, None, territory)
    opps = frappe.get_all(
        "Opportunity", filters=opp_filters,
        fields=["name", "opportunity_owner", "status", "opportunity_amount"],
        limit_page_length=0
    )
    opps = attach_amounts(opps)

    people = {}

    for l in leads:
        owner_key = l.lead_owner or "Unassigned"
        if owner_key not in people:
            people[owner_key] = {
                "sales_person": owner_key, "leads": 0, "opportunities": 0,
                "won": 0, "lost": 0, "pipeline_value": 0
            }
        people[owner_key]["leads"] = people[owner_key]["leads"] + 1

    for o in opps:
        owner_key = o.opportunity_owner or "Unassigned"
        if owner_key not in people:
            people[owner_key] = {
                "sales_person": owner_key, "leads": 0, "opportunities": 0,
                "won": 0, "lost": 0, "pipeline_value": 0
            }
        bucket = people[owner_key]
        bucket["opportunities"] = bucket["opportunities"] + 1
        if o.status == WON_STATUS:
            bucket["won"] = bucket["won"] + 1
        elif o.status == LOST_STATUS:
            bucket["lost"] = bucket["lost"] + 1
        if o.status not in NOT_OPEN_STATUSES:
            bucket["pipeline_value"] = bucket["pipeline_value"] + frappe.utils.flt(o.opportunity_amount)

    result = []
    for p in people.values():
        closed = p["won"] + p["lost"]
        p["win_rate"] = round(safe_div(p["won"], closed), 1) if closed else None
        result.append(p)

    owner_ids = [p["sales_person"] for p in result if p["sales_person"] != "Unassigned"]
    full_names = {}
    if owner_ids:
        for u in frappe.get_all("User", filters={"name": ["in", owner_ids]}, fields=["name", "full_name"], limit_page_length=0):
            full_names[u.name] = u.full_name
    for p in result:
        p["full_name"] = full_names.get(p["sales_person"]) or p["sales_person"]

    result.sort(key=lambda x: (x["opportunities"] + x["leads"]), reverse=True)
    return result


def get_lead_source_performance(from_date, to_date, company, sales_person, territory):
    filters = build_lead_filters(from_date, to_date, company, sales_person, territory)
    rows = frappe.get_all("Lead", filters=filters, fields=["utm_source", "status"], limit_page_length=0)

    sources = {}
    for r in rows:
        key = r.utm_source or "Unknown"
        if key not in sources:
            sources[key] = {"source": key, "leads": 0, "converted": 0}
        sources[key]["leads"] = sources[key]["leads"] + 1
        if r.status == "Converted":
            sources[key]["converted"] = sources[key]["converted"] + 1

    result = list(sources.values())
    for s in result:
        s["rate"] = round(safe_div(s["converted"], s["leads"]), 1) if s["leads"] else 0
    result.sort(key=lambda x: x["leads"], reverse=True)
    return result


@frappe.whitelist()
def crm_kpi_dashboard_data():
    """Return all KPI cards and chart data for the CRM KPI Dashboard block."""
    try:
        args = parse_args()
        from_date = args["from_date"]
        to_date = args["to_date"]
        company = args["company"]
        sales_person = args["sales_person"]
        territory = args["territory"]

        lead_conversion = get_lead_conversion(from_date, to_date, company, sales_person, territory)
        win_rate = get_win_rate(from_date, to_date, company, sales_person, territory)
        first_response = get_first_response_time(from_date, to_date, company, sales_person, territory)
        pipeline = get_pipeline_value(from_date, to_date, company, sales_person, territory)
        sales_cycle = get_sales_cycle(from_date, to_date, company, sales_person, territory)
        lead_to_customer = get_lead_to_customer_time(from_date, to_date, company, sales_person, territory)

        lead_conversion_trend = get_lead_conversion_trend(from_date, to_date, company, sales_person, territory)
        opportunity_funnel = get_opportunity_funnel(from_date, to_date, company, sales_person, territory)
        win_loss = get_win_loss(from_date, to_date, company, sales_person, territory)
        pipeline_by_stage = get_pipeline_by_stage(pipeline["rows"])
        pipeline_trend = get_pipeline_trend(pipeline["rows"])
        sales_person_performance = get_sales_person_performance(from_date, to_date, company, territory)
        lead_source_performance = get_lead_source_performance(from_date, to_date, company, sales_person, territory)
        previous = previous_period(from_date, to_date)
        geo_now = collect_geo(from_date, to_date, company, sales_person)
        geo_before = collect_geo(previous["from_date"], previous["to_date"], company, sales_person)
        territory_performance = geo_rows_with_previous(geo_now["territories"], geo_before["territories"])
        state_performance = geo_rows_with_previous(geo_now["states"], geo_before["states"])

        return {
            "success": True,
            "generated_at": str(frappe.utils.now()),
            "filters": {
                "from_date": str(from_date),
                "to_date": str(to_date),
                "company": company,
                "sales_person": sales_person,
                "territory": territory,
                "previous_from_date": str(previous["from_date"]),
                "previous_to_date": str(previous["to_date"])
            },
            "kpis": {
                "lead_conversion": lead_conversion,
                "win_rate": win_rate,
                "first_response": first_response,
                "pipeline": {"total_value": pipeline["total_value"], "count": pipeline["count"]},
                "sales_cycle": sales_cycle,
                "lead_to_customer": lead_to_customer
            },
            "charts": {
                "lead_conversion_trend": lead_conversion_trend,
                "opportunity_funnel": opportunity_funnel,
                "win_loss": win_loss,
                "pipeline_by_stage": pipeline_by_stage,
                "pipeline_trend": pipeline_trend,
                "sales_person_performance": sales_person_performance,
                "lead_source_performance": lead_source_performance,
                "territory_performance": territory_performance,
                "state_performance": state_performance
            }
        }

    except Exception as e:
        error_message = str(e)
        frappe.log_error(title="CRM KPI Dashboard Data Failed", message=error_message)
        return {
            "success": False,
            "error": error_message
        }
