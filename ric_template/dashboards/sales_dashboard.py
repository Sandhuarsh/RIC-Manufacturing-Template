"""Sales dashboard data (revenue, bookings, receivables, backlog, quotes, team).

Ported from the Supreme Equipments Server Script APIs "sales_dashboard_data" and
"sales_dashboard_daily".
"""

import frappe

STALLED_QUOTE_DAYS = 15
OPEN_ORDER_STATUSES = ["To Deliver and Bill", "To Bill", "To Deliver"]
QUOTE_WON = ["Ordered", "Partially Ordered"]
QUOTE_LOST = ["Lost", "Expired"]
AGING_LABELS = ["Not yet due", "1-30 days", "31-60 days", "61-90 days", "90+ days"]


def flt(value):
    return frappe.utils.flt(value)


def pct_change(current, previous):
    if not previous:
        return None
    return round(((current - previous) / abs(previous)) * 100, 1)


def safe_pct(numerator, denominator):
    if not denominator:
        return None
    return round((numerator / denominator) * 100, 1)


def in_range(date_str, start_str, end_str):
    return date_str >= start_str and date_str <= end_str


def parse_args():
    today_date = frappe.utils.getdate(frappe.utils.today())
    fy_rows = frappe.get_all(
        "Fiscal Year",
        filters={"year_start_date": ["<=", today_date], "year_end_date": [">=", today_date]},
        fields=["name", "year_start_date", "year_end_date"],
        limit_page_length=1
    )
    fy_name = ""
    fy_start = str(frappe.utils.add_months(today_date, -6))
    fy_end = str(today_date)
    if fy_rows:
        fy_name = fy_rows[0].name
        fy_start = str(fy_rows[0].year_start_date)
        fy_end = str(fy_rows[0].year_end_date)

    to_date = frappe.utils.getdate(frappe.form_dict.get("to_date") or today_date)
    from_date = frappe.utils.getdate(frappe.form_dict.get("from_date") or fy_start)
    if from_date > to_date:
        holder = from_date
        from_date = to_date
        to_date = holder

    return {
        "today": str(today_date),
        "from_date": str(from_date),
        "to_date": str(to_date),
        "company": frappe.form_dict.get("company") or None,
        "sales_person": frappe.form_dict.get("sales_person") or None,
        "territory": frappe.form_dict.get("territory") or None,
        "fy_name": fy_name,
        "fy_start": fy_start,
        "fy_end": fy_end
    }


def previous_period(from_str, to_str):
    period_days = frappe.utils.date_diff(to_str, from_str) + 1
    prev_to = frappe.utils.add_days(from_str, -1)
    prev_from = frappe.utils.add_days(prev_to, -(period_days - 1))
    return {"from_date": str(prev_from), "to_date": str(prev_to)}


def month_keys(base_date, offset_months):
    keys = []
    for i in range(11, -1, -1):
        keys.append(str(frappe.utils.add_months(base_date, -(i + offset_months)))[:7])
    return keys


def fetch_invoices(start_str, end_str, company):
    filters = {"docstatus": 1, "posting_date": ["between", [start_str, end_str]]}
    if company:
        filters["company"] = company
    return frappe.get_all(
        "Sales Invoice", filters=filters,
        fields=["name", "posting_date", "customer", "customer_name", "base_net_total",
                "outstanding_amount", "due_date", "is_return"],
        limit_page_length=0
    )


def fetch_receivable_rows(company):
    filters = {"docstatus": 1, "outstanding_amount": [">", 0]}
    if company:
        filters["company"] = company
    return frappe.get_all(
        "Sales Invoice", filters=filters,
        fields=["name", "posting_date", "customer", "customer_name", "base_net_total",
                "outstanding_amount", "due_date", "is_return"],
        limit_page_length=0
    )


def fetch_orders(start_str, end_str, company):
    filters = {"docstatus": 1, "transaction_date": ["between", [start_str, end_str]]}
    if company:
        filters["company"] = company
    return frappe.get_all(
        "Sales Order", filters=filters,
        fields=["name", "transaction_date", "customer", "customer_name", "base_net_total",
                "status", "per_delivered", "per_billed", "delivery_date"],
        limit_page_length=0
    )


def fetch_open_orders(company):
    filters = {"docstatus": 1, "status": ["in", OPEN_ORDER_STATUSES]}
    if company:
        filters["company"] = company
    return frappe.get_all(
        "Sales Order", filters=filters,
        fields=["name", "transaction_date", "customer", "customer_name", "base_net_total",
                "status", "per_delivered", "per_billed", "delivery_date"],
        limit_page_length=0
    )


def fetch_quotes(start_str, end_str, company):
    filters = {"docstatus": 1, "transaction_date": ["between", [start_str, end_str]]}
    if company:
        filters["company"] = company
    return frappe.get_all(
        "Quotation", filters=filters,
        fields=["name", "transaction_date", "party_name", "customer_name", "base_net_total", "status"],
        limit_page_length=0
    )


def fetch_open_quotes(company):
    filters = {"docstatus": 1, "status": "Open"}
    if company:
        filters["company"] = company
    return frappe.get_all(
        "Quotation", filters=filters,
        fields=["name", "transaction_date", "party_name", "customer_name", "base_net_total", "status"],
        limit_page_length=0
    )


def fetch_alloc(parent_doctype, names):
    result = {}
    if not names:
        return result
    rows = frappe.get_all(
        "Sales Team",
        filters={"parenttype": parent_doctype, "parent": ["in", names]},
        fields=["parent", "sales_person", "allocated_amount"],
        limit_page_length=0
    )
    for r in rows:
        if r.parent not in result:
            result[r.parent] = []
        result[r.parent].append(r)
    return result


def build_maps(customer_ids):
    territory_map = {}
    group_map = {}
    if customer_ids:
        rows = frappe.get_all(
            "Customer", filters={"name": ["in", customer_ids]},
            fields=["name", "territory", "customer_group"], limit_page_length=0
        )
        for r in rows:
            territory_map[r.name] = r.territory
            group_map[r.name] = r.customer_group
    return {"territory": territory_map, "group": group_map}


def prepare_docs(rows, date_field, cust_field, sales_person, territory, terr_map, group_map, alloc_map):
    out = []
    for r in rows:
        cust = r.get(cust_field)
        terr = terr_map.get(cust) or "Unassigned"
        if terr == "All Territories":
            terr = "Unassigned"
        if territory and terr != territory:
            continue

        people = alloc_map.get(r.name) or []
        net = flt(r.base_net_total)
        value = net
        ratio = 1
        if sales_person:
            has_person = False
            matched = 0
            for p in people:
                if p.sales_person == sales_person:
                    has_person = True
                    matched = matched + flt(p.allocated_amount)
            if not has_person:
                continue
            value = matched
            ratio = (matched / net) if net else 0

        due_value = r.get("due_date")
        out.append({
            "name": r.name,
            "date": str(r.get(date_field))[:10],
            "customer": cust,
            "customer_name": r.get("customer_name") or cust,
            "value": value,
            "ratio": ratio,
            "territory": terr,
            "segment": group_map.get(cust) or "Unassigned",
            "people": people,
            "due": str(due_value)[:10] if due_value else "",
            "row": r
        })
    return out


def period_sum(items, start_str, end_str, skip_returns):
    total = 0
    for it in items:
        if in_range(it["date"], start_str, end_str):
            if skip_returns and it["row"].get("is_return"):
                continue
            total = total + it["value"]
    return total


def period_count(items, start_str, end_str, skip_returns):
    total = 0
    for it in items:
        if in_range(it["date"], start_str, end_str):
            if skip_returns and it["row"].get("is_return"):
                continue
            total = total + 1
    return total


def month_totals(items):
    totals = {}
    for it in items:
        key = it["date"][:7]
        if key not in totals:
            totals[key] = 0
        totals[key] = totals[key] + it["value"]
    return totals


def series_for(keys, totals):
    series = []
    for k in keys:
        series.append(round(totals.get(k) or 0, 2))
    return series


def top_with_others(totals, limit):
    rows = []
    for k in totals.keys():
        rows.append({"label": k, "value": round(totals[k], 2)})
    rows = sorted(rows, key=lambda x: x["value"], reverse=True)
    grand = 0
    for r in rows:
        grand = grand + r["value"]
    out = []
    others = 0
    for i in range(len(rows)):
        if i < limit:
            out.append({"label": rows[i]["label"], "value": rows[i]["value"], "pct": safe_pct(rows[i]["value"], grand)})
        else:
            others = others + rows[i]["value"]
    if others:
        out.append({"label": "Others", "value": round(others, 2), "pct": safe_pct(others, grand)})
    return out


def compute_aging(ar_items, today_str):
    buckets = []
    for label in AGING_LABELS:
        buckets.append({"label": label, "amount": 0, "count": 0})

    overdue_total = 0
    over60_total = 0
    outstanding_total = 0
    by_customer = {}
    outstanding_by_customer = {}

    for it in ar_items:
        amount = flt(it["row"].outstanding_amount) * it["ratio"]
        outstanding_total = outstanding_total + amount
        cust_key = it["customer_name"]
        if cust_key not in outstanding_by_customer:
            outstanding_by_customer[cust_key] = 0
        outstanding_by_customer[cust_key] = outstanding_by_customer[cust_key] + amount

        days = 0
        if it["due"] and it["due"] < today_str:
            days = frappe.utils.date_diff(today_str, it["due"])

        idx = 0
        if days > 90:
            idx = 4
        elif days > 60:
            idx = 3
        elif days > 30:
            idx = 2
        elif days > 0:
            idx = 1

        buckets[idx]["amount"] = buckets[idx]["amount"] + amount
        buckets[idx]["count"] = buckets[idx]["count"] + 1

        if days > 0:
            overdue_total = overdue_total + amount
            if days > 60:
                over60_total = over60_total + amount
            if cust_key not in by_customer:
                by_customer[cust_key] = {"name": cust_key, "amount": 0, "days": 0}
            by_customer[cust_key]["amount"] = by_customer[cust_key]["amount"] + amount
            if days > by_customer[cust_key]["days"]:
                by_customer[cust_key]["days"] = days

    overdue_accounts = sorted(by_customer.values(), key=lambda x: x["amount"], reverse=True)

    for b in buckets:
        b["amount"] = round(b["amount"], 2)

    return {
        "buckets": buckets,
        "outstanding_total": round(outstanding_total, 2),
        "overdue_total": round(overdue_total, 2),
        "over60_total": round(over60_total, 2),
        "overdue_accounts": overdue_accounts[:5],
        "outstanding_by_customer": outstanding_by_customer
    }


def compute_target(fy_name, fy_start, fy_end, to_str, sales_person, inv_items):
    result = {"available": False, "target": 0, "achieved": 0, "pct": None, "expected_pct": None, "by_person": {}}
    if not fy_name:
        return result
    try:
        filters = {"parenttype": "Sales Person", "fiscal_year": fy_name}
        if sales_person:
            filters["parent"] = sales_person
        rows = frappe.get_all("Target Detail", filters=filters, fields=["parent", "target_amount"], limit_page_length=0)
    except Exception:
        return result

    total = 0
    by_person = {}
    for r in rows:
        amt = flt(r.target_amount)
        total = total + amt
        if r.parent not in by_person:
            by_person[r.parent] = 0
        by_person[r.parent] = by_person[r.parent] + amt

    if not total:
        return result

    achieved = period_sum(inv_items, fy_start, to_str, False)
    elapsed = frappe.utils.date_diff(to_str, fy_start) + 1
    span = frappe.utils.date_diff(fy_end, fy_start) + 1
    result["available"] = True
    result["target"] = round(total, 2)
    result["achieved"] = round(achieved, 2)
    result["pct"] = safe_pct(achieved, total)
    result["expected_pct"] = safe_pct(elapsed, span)
    result["by_person"] = by_person
    return result


@frappe.whitelist()
def sales_dashboard_data():
    """Return all KPI cards and chart data for the Sales Dashboard block."""
    try:
        args = parse_args()
        today_str = args["today"]
        from_str = args["from_date"]
        to_str = args["to_date"]
        company = args["company"]
        sales_person = args["sales_person"]
        territory = args["territory"]

        prev = previous_period(from_str, to_str)
        prev_from = prev["from_date"]
        prev_to = prev["to_date"]

        base = frappe.utils.getdate(to_str[:7] + "-01")
        keys = month_keys(base, 0)
        prior_keys = month_keys(base, 12)

        window_start = str(frappe.utils.add_months(base, -23))[:10]
        if prev_from < window_start:
            window_start = prev_from
        if from_str < window_start:
            window_start = from_str

        inv_rows = fetch_invoices(window_start, to_str, company)
        ar_rows = fetch_receivable_rows(company)
        so_rows = fetch_orders(window_start, to_str, company)
        open_so_rows = fetch_open_orders(company)
        qt_rows = fetch_quotes(window_start, to_str, company)
        open_qt_rows = fetch_open_quotes(company)

        customer_seen = {}
        inv_names = {}
        so_names = {}
        qt_names = {}
        for r in inv_rows:
            customer_seen[r.customer] = 1
            inv_names[r.name] = 1
        for r in ar_rows:
            customer_seen[r.customer] = 1
            inv_names[r.name] = 1
        for r in so_rows:
            customer_seen[r.customer] = 1
            so_names[r.name] = 1
        for r in open_so_rows:
            customer_seen[r.customer] = 1
            so_names[r.name] = 1
        for r in qt_rows:
            customer_seen[r.party_name] = 1
            qt_names[r.name] = 1
        for r in open_qt_rows:
            customer_seen[r.party_name] = 1
            qt_names[r.name] = 1

        maps = build_maps(list(customer_seen.keys()))
        terr_map = maps["territory"]
        group_map = maps["group"]
        alloc_inv = fetch_alloc("Sales Invoice", list(inv_names.keys()))
        alloc_so = fetch_alloc("Sales Order", list(so_names.keys()))
        alloc_qt = fetch_alloc("Quotation", list(qt_names.keys()))

        inv = prepare_docs(inv_rows, "posting_date", "customer", sales_person, territory, terr_map, group_map, alloc_inv)
        ar = prepare_docs(ar_rows, "posting_date", "customer", sales_person, territory, terr_map, group_map, alloc_inv)
        so = prepare_docs(so_rows, "transaction_date", "customer", sales_person, territory, terr_map, group_map, alloc_so)
        open_so = prepare_docs(open_so_rows, "transaction_date", "customer", sales_person, territory, terr_map, group_map, alloc_so)
        qt = prepare_docs(qt_rows, "transaction_date", "party_name", sales_person, territory, terr_map, group_map, alloc_qt)
        open_qt = prepare_docs(open_qt_rows, "transaction_date", "party_name", sales_person, territory, terr_map, group_map, alloc_qt)

        revenue = period_sum(inv, from_str, to_str, False)
        revenue_prev = period_sum(inv, prev_from, prev_to, False)
        invoice_count = period_count(inv, from_str, to_str, True)

        booked = period_sum(so, from_str, to_str, False)
        booked_prev = period_sum(so, prev_from, prev_to, False)
        order_count = period_count(so, from_str, to_str, False)

        aging = compute_aging(ar, today_str)

        backlog_value = 0
        backlog_count = 0
        late_orders = []
        for it in open_so:
            pending = it["value"] * ((100 - flt(it["row"].per_delivered)) / 100)
            backlog_value = backlog_value + pending
            backlog_count = backlog_count + 1
            delivery = it["row"].get("delivery_date")
            if delivery and str(delivery)[:10] < today_str and flt(it["row"].per_delivered) < 100:
                late_orders.append({
                    "customer": it["customer_name"],
                    "order": it["name"],
                    "days": frappe.utils.date_diff(today_str, str(delivery)[:10]),
                    "value": round(pending, 2)
                })
        late_orders = sorted(late_orders, key=lambda x: x["value"], reverse=True)

        open_quote_value = 0
        stalled_quotes = []
        for it in open_qt:
            open_quote_value = open_quote_value + it["value"]
            age = frappe.utils.date_diff(today_str, it["date"])
            if age >= STALLED_QUOTE_DAYS:
                stalled_quotes.append({
                    "customer": it["customer_name"],
                    "quote": it["name"],
                    "days": age,
                    "value": round(it["value"], 2)
                })
        stalled_quotes = sorted(stalled_quotes, key=lambda x: x["value"], reverse=True)

        q_won = 0
        q_lost = 0
        q_open = 0
        q_won_value = 0
        q_total_value = 0
        for it in qt:
            if in_range(it["date"], from_str, to_str):
                q_total_value = q_total_value + it["value"]
                status = it["row"].status
                if status in QUOTE_WON:
                    q_won = q_won + 1
                    q_won_value = q_won_value + it["value"]
                elif status in QUOTE_LOST:
                    q_lost = q_lost + 1
                else:
                    q_open = q_open + 1
        quote_count = q_won + q_lost + q_open

        target = compute_target(args["fy_name"], args["fy_start"], args["fy_end"], to_str, sales_person, inv)

        inv_month = month_totals(inv)
        so_month = month_totals(so)
        revenue_trend = {
            "months": keys,
            "current": series_for(keys, inv_month),
            "previous": series_for(prior_keys, inv_month)
        }
        flow = {
            "months": keys,
            "booked": series_for(keys, so_month),
            "invoiced": series_for(keys, inv_month)
        }

        period_names = []
        ratio_by_name = {}
        for it in inv:
            if in_range(it["date"], from_str, to_str):
                period_names.append(it["name"])
                ratio_by_name[it["name"]] = it["ratio"]

        group_totals = {}
        if period_names:
            item_rows = frappe.get_all(
                "Sales Invoice Item",
                filters={"parent": ["in", period_names]},
                fields=["parent", "item_group", "base_net_amount"],
                limit_page_length=0
            )
            for r in item_rows:
                group = r.item_group or "Uncategorised"
                if group not in group_totals:
                    group_totals[group] = 0
                group_totals[group] = group_totals[group] + (flt(r.base_net_amount) * (ratio_by_name.get(r.parent) or 0))
        category_mix = top_with_others(group_totals, 6)

        region_totals = {}
        segment_totals = {}
        for it in inv:
            if in_range(it["date"], from_str, to_str):
                rkey = it["territory"]
                if rkey not in region_totals:
                    region_totals[rkey] = 0
                region_totals[rkey] = region_totals[rkey] + it["value"]
                skey = it["segment"]
                if skey not in segment_totals:
                    segment_totals[skey] = 0
                segment_totals[skey] = segment_totals[skey] + it["value"]
        regions = top_with_others(region_totals, 8)
        segments = top_with_others(segment_totals, 7)

        lead_filters = {"creation": ["between", [from_str, to_str + " 23:59:59"]]}
        opp_filters = {"creation": ["between", [from_str, to_str + " 23:59:59"]]}
        if company:
            lead_filters["company"] = company
            opp_filters["company"] = company
        if territory:
            lead_filters["territory"] = territory
            opp_filters["territory"] = territory
        lead_count = frappe.db.count("Lead", lead_filters)
        opp_rows = frappe.get_all("Opportunity", filters=opp_filters, fields=["opportunity_amount"], limit_page_length=0)
        opp_value = 0
        for r in opp_rows:
            opp_value = opp_value + flt(r.opportunity_amount)

        funnel = [
            {"label": "Leads", "count": lead_count, "value": None},
            {"label": "Opportunities", "count": len(opp_rows), "value": round(opp_value, 2) if opp_value else None},
            {"label": "Quotations", "count": quote_count, "value": round(q_total_value, 2)},
            {"label": "Sales Orders", "count": order_count, "value": round(booked, 2)},
            {"label": "Invoiced", "count": invoice_count, "value": round(revenue, 2)}
        ]

        cust_now = {}
        cust_prev = {}
        for it in inv:
            if in_range(it["date"], from_str, to_str):
                key = it["customer_name"]
                if key not in cust_now:
                    cust_now[key] = {"name": key, "segment": it["segment"], "revenue": 0}
                cust_now[key]["revenue"] = cust_now[key]["revenue"] + it["value"]
            elif in_range(it["date"], prev_from, prev_to):
                key2 = it["customer_name"]
                if key2 not in cust_prev:
                    cust_prev[key2] = 0
                cust_prev[key2] = cust_prev[key2] + it["value"]

        top_customers = []
        ranked = sorted(cust_now.values(), key=lambda x: x["revenue"], reverse=True)
        for c in ranked[:8]:
            previous_value = cust_prev.get(c["name"]) or 0
            change = pct_change(c["revenue"], previous_value)
            status = "steady"
            if not previous_value:
                status = "new"
            elif change is not None and change >= 10:
                status = "growing"
            elif change is not None and change <= -10:
                status = "review"
            top_customers.append({
                "name": c["name"],
                "segment": c["segment"],
                "revenue": round(c["revenue"], 2),
                "share_pct": safe_pct(c["revenue"], revenue),
                "change_pct": change,
                "status": status,
                "outstanding": round(aging["outstanding_by_customer"].get(c["name"]) or 0, 2)
            })

        reps = {}
        for it in inv:
            if in_range(it["date"], from_str, to_str):
                for p in it["people"]:
                    if sales_person and p.sales_person != sales_person:
                        continue
                    if p.sales_person not in reps:
                        reps[p.sales_person] = {"name": p.sales_person, "revenue": 0, "invoices": 0, "orders": 0, "booked": 0}
                    reps[p.sales_person]["revenue"] = reps[p.sales_person]["revenue"] + flt(p.allocated_amount)
                    reps[p.sales_person]["invoices"] = reps[p.sales_person]["invoices"] + 1
        for it in so:
            if in_range(it["date"], from_str, to_str):
                for p in it["people"]:
                    if sales_person and p.sales_person != sales_person:
                        continue
                    if p.sales_person not in reps:
                        reps[p.sales_person] = {"name": p.sales_person, "revenue": 0, "invoices": 0, "orders": 0, "booked": 0}
                    reps[p.sales_person]["orders"] = reps[p.sales_person]["orders"] + 1
                    reps[p.sales_person]["booked"] = reps[p.sales_person]["booked"] + flt(p.allocated_amount)

        sales_team = []
        rep_total = 0
        rep_list = sorted(reps.values(), key=lambda x: x["revenue"], reverse=True)
        for rep in rep_list:
            rep_total = rep_total + rep["revenue"]
            rep_target = target["by_person"].get(rep["name"]) or 0
            sales_team.append({
                "name": rep["name"],
                "revenue": round(rep["revenue"], 2),
                "invoices": rep["invoices"],
                "orders": rep["orders"],
                "booked": round(rep["booked"], 2),
                "share_pct": safe_pct(rep["revenue"], revenue),
                "target": round(rep_target, 2),
                "target_pct": safe_pct(rep["revenue"], rep_target) if rep_target else None
            })
        unallocated = 0
        if not sales_person:
            unallocated = round(revenue - rep_total, 2)

        attention = []
        if aging["overdue_total"] > 0:
            attention.append({
                "kind": "overdue",
                "severity": "critical" if aging["over60_total"] > 0 else "warn",
                "total": aging["overdue_total"],
                "over60": aging["over60_total"],
                "rows": aging["overdue_accounts"][:3]
            })
        if stalled_quotes:
            attention.append({
                "kind": "stalled_quotes",
                "severity": "warn",
                "count": len(stalled_quotes),
                "threshold": STALLED_QUOTE_DAYS,
                "rows": stalled_quotes[:3]
            })
        if late_orders:
            attention.append({
                "kind": "late_deliveries",
                "severity": "warn",
                "count": len(late_orders),
                "rows": late_orders[:3]
            })
        if target["available"]:
            if target["pct"] is not None and target["expected_pct"] is not None and target["pct"] < target["expected_pct"]:
                attention.append({
                    "kind": "pace",
                    "severity": "warn",
                    "pct": target["pct"],
                    "expected": target["expected_pct"]
                })
        else:
            attention.append({"kind": "no_target", "severity": "info"})

        real_regions = 0
        for rg in regions:
            if rg["label"] != "Unassigned":
                real_regions = real_regions + 1

        return {
            "success": True,
            "generated_at": str(frappe.utils.now()),
            "filters": {
                "from_date": from_str, "to_date": to_str, "prev_from": prev_from, "prev_to": prev_to,
                "company": company, "sales_person": sales_person, "territory": territory,
                "fiscal_year": args["fy_name"]
            },
            "kpis": {
                "revenue": {"value": round(revenue, 2), "previous": round(revenue_prev, 2),
                            "change_pct": pct_change(revenue, revenue_prev), "invoices": invoice_count,
                            "avg_invoice": round(revenue / invoice_count, 2) if invoice_count else None},
                "booked": {"value": round(booked, 2), "previous": round(booked_prev, 2),
                           "change_pct": pct_change(booked, booked_prev), "orders": order_count,
                           "avg_order": round(booked / order_count, 2) if order_count else None},
                "receivables": {"outstanding": aging["outstanding_total"], "overdue": aging["overdue_total"],
                                "over60": aging["over60_total"]},
                "backlog": {"value": round(backlog_value, 2), "orders": backlog_count, "late": len(late_orders)},
                "quotes": {"open_value": round(open_quote_value, 2), "open_count": len(open_qt),
                           "won": q_won, "lost": q_lost, "in_period": quote_count,
                           "conversion_pct": safe_pct(q_won, quote_count),
                           "won_value": round(q_won_value, 2)},
                "customers": {"active": len(cust_now), "previous": len(cust_prev),
                              "change": len(cust_now) - len(cust_prev)},
                "target": target
            },
            "charts": {
                "revenue_trend": revenue_trend,
                "flow": flow,
                "category_mix": category_mix,
                "regions": regions,
                "regions_meaningful": real_regions > 0,
                "segments": segments,
                "funnel": funnel,
                "aging": aging["buckets"],
                "top_customers": top_customers,
                "sales_team": sales_team,
                "team_unallocated": unallocated
            },
            "attention": attention
        }

    except Exception as e:
        error_message = str(e)
        frappe.log_error(title="Sales Dashboard Data Failed", message=error_message)
        return {"success": False, "error": error_message}


def daily_totals(doctype, date_field, to_str, start_str, company, sales_person):
    filters = {"docstatus": 1, date_field: ["between", [start_str, to_str]]}
    if company:
        filters["company"] = company
    rows = frappe.get_all(doctype, filters=filters, fields=["name", date_field, "base_net_total"], limit_page_length=0)

    alloc = {}
    if sales_person and rows:
        names = []
        for r in rows:
            names.append(r.name)
        team = frappe.get_all(
            "Sales Team",
            filters={"parenttype": doctype, "parent": ["in", names], "sales_person": sales_person},
            fields=["parent", "allocated_amount"], limit_page_length=0
        )
        for t in team:
            if t.parent not in alloc:
                alloc[t.parent] = 0
            alloc[t.parent] = alloc[t.parent] + frappe.utils.flt(t.allocated_amount)

    totals = {}
    for r in rows:
        value = frappe.utils.flt(r.base_net_total)
        if sales_person:
            value = alloc.get(r.name) or 0
        key = str(r.get(date_field))[:10]
        if key not in totals:
            totals[key] = 0
        totals[key] = totals[key] + value
    return totals


@frappe.whitelist()
def sales_dashboard_daily():
    """Return the last 30 days of invoiced and booked totals."""
    try:
        to_date = frappe.utils.getdate(frappe.form_dict.get("to_date") or frappe.utils.today())
        company = frappe.form_dict.get("company") or None
        sales_person = frappe.form_dict.get("sales_person") or None
        start_str = str(frappe.utils.add_days(to_date, -29))
        to_str = str(to_date)

        inv_totals = daily_totals("Sales Invoice", "posting_date", to_str, start_str, company, sales_person)
        so_totals = daily_totals("Sales Order", "transaction_date", to_str, start_str, company, sales_person)

        days = []
        invoiced = []
        booked = []
        for i in range(29, -1, -1):
            key = str(frappe.utils.add_days(to_date, -i))
            days.append(key)
            invoiced.append(round(inv_totals.get(key) or 0, 2))
            booked.append(round(so_totals.get(key) or 0, 2))

        return {"success": True, "days": days, "invoiced": invoiced, "booked": booked}
    except Exception as e:
        frappe.log_error(title="Sales Dashboard Daily Failed", message=str(e))
        return {"success": False, "error": str(e)}
