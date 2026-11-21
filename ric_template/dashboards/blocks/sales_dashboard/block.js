(async function () {
    const root = (root_element && root_element[0]) ? root_element[0] : root_element;
    if (!root) { console.error("Sales Dashboard root not found."); return; }

    const NS = "http://www.w3.org/2000/svg";
    const PALETTE = ["#5B84B1", "#D9A441", "#3E9B6E", "#B8842A", "#8FA39B", "#7FA8C9", "#C9CFC5"];
    const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

    function find(sel) { return root.querySelector(sel); }
    function role(name) { return find('[data-role="' + name + '"]'); }
    function setText(name, text) { const e = role(name); if (e) { e.textContent = text; } }
    function el(tag, cls, text) {
        const e = document.createElement(tag);
        if (cls) { e.className = cls; }
        if (text !== undefined && text !== null) { e.textContent = text; }
        return e;
    }
    function svgEl(tag, attrs) {
        const e = document.createElementNS(NS, tag);
        Object.keys(attrs || {}).forEach(function (k) { e.setAttribute(k, attrs[k]); });
        return e;
    }
    function clear(name) { const e = role(name); if (e) { e.replaceChildren(); } return e; }
    function empty(container, message) { container.appendChild(el("div", "sd-empty", message)); }
    function setPanelSub(name, text) {
        const p = role(name).closest(".sd-panel");
        const s = p ? p.querySelector(".sd-panel-sub") : null;
        if (s) { s.textContent = text; }
    }

    const intFmt = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 });
    function fmtInt(v) { return intFmt.format(Number(v || 0)); }
    function fmtINR(v) {
        const n = Number(v || 0), a = Math.abs(n), s = n < 0 ? "-" : "";
        if (a >= 1e7) { return s + "₹" + (a / 1e7).toFixed(2) + " Cr"; }
        if (a >= 1e5) { return s + "₹" + (a / 1e5).toFixed(1) + "L"; }
        return s + "₹" + intFmt.format(a);
    }
    function fmtAxis(v) {
        const a = Math.abs(v);
        if (a >= 1e7) { return "₹" + +(a / 1e7).toFixed(1) + "Cr"; }
        if (a >= 1e5) { return "₹" + +(a / 1e5).toFixed(1) + "L"; }
        if (a >= 1e3) { return "₹" + +(a / 1e3).toFixed(0) + "K"; }
        return "₹" + a;
    }
    function pad2(n) { return n < 10 ? "0" + n : String(n); }
    function dstr(d) { return d.getFullYear() + "-" + pad2(d.getMonth() + 1) + "-" + pad2(d.getDate()); }
    function monthLabel(key) {
        const p = key.split("-");
        return MONTHS[parseInt(p[1], 10) - 1] + " " + p[0].slice(2);
    }
    function dayLabel(key) {
        const p = key.split("-");
        return parseInt(p[2], 10) + " " + MONTHS[parseInt(p[1], 10) - 1];
    }
    function niceMax(v) {
        if (v <= 0) { return 1; }
        const pow = Math.pow(10, Math.floor(Math.log10(v)));
        const n = v / pow;
        return (n <= 1 ? 1 : n <= 2 ? 2 : n <= 5 ? 5 : 10) * pow;
    }

    // ---------- Charts ----------
    function barChart(container, labels, series, opts) {
        const o = opts || {};
        const axisLabel = o.label || monthLabel;
        const every = o.every || 1;
        container.replaceChildren();
        const W = 640, H = 250, L = 56, R = 8, T = 14, B = 28;
        let max = 0;
        series.forEach(function (s) { s.values.forEach(function (v) { if (v > max) { max = v; } }); });
        if (!max) { empty(container, "No activity in this period."); return; }
        const top = niceMax(max), ph = H - T - B;
        const svg = svgEl("svg", { viewBox: "0 0 " + W + " " + H, class: "sd-svg", role: "img" });
        for (let i = 0; i <= 4; i++) {
            const y = T + ph * (1 - i / 4);
            svg.appendChild(svgEl("line", { x1: L, x2: W - R, y1: y, y2: y, stroke: "var(--border-color)", "stroke-width": 1 }));
            const t = svgEl("text", { x: L - 8, y: y + 3, "text-anchor": "end", "font-size": 10, fill: "var(--text-muted)" });
            t.textContent = fmtAxis(top * i / 4);
            svg.appendChild(t);
        }
        const gw = (W - L - R) / labels.length;
        const bw = Math.min(30, (gw * 0.7) / series.length);
        labels.forEach(function (lab, gi) {
            const gx = L + gi * gw + (gw - (bw * series.length + 3 * (series.length - 1))) / 2;
            series.forEach(function (s, si) {
                const v = s.values[gi] || 0;
                const h = Math.max(v ? 2 : 0, (v / top) * ph);
                const x = gx + si * (bw + 3);
                const r = svgEl("rect", { x: x, y: T + ph - h, width: bw, height: h, rx: Math.min(3, bw / 2), fill: s.color });
                const tt = svgEl("title", {});
                tt.textContent = axisLabel(lab) + " - " + s.name + ": " + fmtINR(v);
                r.appendChild(tt);
                svg.appendChild(r);
                if (v && gw > 60) {
                    const vt = svgEl("text", { x: x + bw / 2, y: T + ph - h - 4, "text-anchor": "middle", "font-size": 9, fill: "var(--text-muted)" });
                    vt.textContent = fmtAxis(v);
                    svg.appendChild(vt);
                }
            });
            if (gi % every === 0) {
                const xt = svgEl("text", { x: L + gi * gw + gw / 2, y: H - 9, "text-anchor": "middle", "font-size": 10, fill: "var(--text-muted)" });
                xt.textContent = axisLabel(lab);
                svg.appendChild(xt);
            }
        });
        container.appendChild(svg);
    }

    function legend(name, items) {
        const c = clear(name);
        items.forEach(function (it) {
            const s = el("span");
            const i = el("i"); i.style.background = it.color;
            s.appendChild(i); s.appendChild(document.createTextNode(it.label));
            c.appendChild(s);
        });
    }

    function trimStart(series, length) {
        let first = length;
        series.forEach(function (vals) {
            for (let i = 0; i < length; i++) { if (vals[i] && i < first) { first = i; break; } }
        });
        if (first === length) { return Math.max(0, length - 4); }
        return Math.min(Math.max(0, first - 1), length - 4);
    }

    function activeMonths(series, length) {
        let count = 0;
        for (let i = 0; i < length; i++) {
            let any = false;
            series.forEach(function (vals) { if (vals[i]) { any = true; } });
            if (any) { count++; }
        }
        return count;
    }

    function hBars(containerName, rows, opts) {
        const c = clear(containerName);
        if (!rows || !rows.length) { empty(c, opts.emptyText); return; }
        let max = 0;
        rows.forEach(function (r) { if (opts.value(r) > max) { max = opts.value(r); } });
        if (!max) { empty(c, opts.emptyText); return; }
        rows.forEach(function (r, i) {
            const row = el("div", "sd-bar-row");
            row.appendChild(el("div", "sd-bar-label", opts.label(r)));
            const track = el("div", "sd-bar-track");
            const fill = el("div", "sd-bar-fill");
            fill.style.width = Math.max(2, (opts.value(r) / max) * 100) + "%";
            fill.style.background = opts.color(r, i);
            track.appendChild(fill);
            row.appendChild(track);
            const val = el("div", "sd-bar-value", opts.text(r));
            if (opts.sub) { val.appendChild(el("div", "sd-bar-sub", opts.sub(r))); }
            row.appendChild(val);
            c.appendChild(row);
        });
    }

    function donut(containerName, rows, centerTop, centerBottom) {
        const c = clear(containerName);
        if (!rows || !rows.length) { empty(c, "No invoiced revenue in this period."); return; }
        const wrap = el("div", "sd-donut");
        const svg = svgEl("svg", { viewBox: "0 0 42 42" });
        svg.appendChild(svgEl("circle", { cx: 21, cy: 21, r: 15.915, fill: "none", stroke: "var(--control-bg)", "stroke-width": 6 }));
        let acc = 0;
        rows.forEach(function (r, i) {
            const pct = r.pct || 0;
            const seg = svgEl("circle", {
                cx: 21, cy: 21, r: 15.915, fill: "none", stroke: PALETTE[i % PALETTE.length], "stroke-width": 6,
                "stroke-dasharray": pct + " " + (100 - pct), "stroke-dashoffset": 25 - acc
            });
            const tt = svgEl("title", {});
            tt.textContent = r.label + ": " + fmtINR(r.value) + " (" + pct + "%)";
            seg.appendChild(tt);
            svg.appendChild(seg);
            acc += pct;
        });
        const t1 = svgEl("text", { x: 21, y: 20.5, "text-anchor": "middle", "font-size": 4.6, "font-weight": 700, fill: "var(--text-color)" });
        t1.textContent = centerTop;
        const t2 = svgEl("text", { x: 21, y: 25.5, "text-anchor": "middle", "font-size": 2.6, fill: "var(--text-muted)" });
        t2.textContent = centerBottom;
        svg.appendChild(t1); svg.appendChild(t2);
        wrap.appendChild(svg);
        const lg = el("div", "sd-donut-legend");
        rows.forEach(function (r, i) {
            const row = el("div", "sd-donut-row");
            const sw = el("i"); sw.style.background = PALETTE[i % PALETTE.length];
            row.appendChild(sw);
            row.appendChild(el("span", "n", r.label));
            row.appendChild(el("span", "p", (r.pct === null || r.pct === undefined ? "-" : r.pct + "%")));
            lg.appendChild(row);
        });
        wrap.appendChild(lg);
        c.appendChild(wrap);
    }

    // ---------- KPIs ----------
    function deltaSpec(change, suffix) {
        if (change === null || change === undefined) { return { text: "No prior-period data", cls: "" }; }
        if (change > 0) { return { text: "▲ " + change + "% " + suffix, cls: "up" }; }
        if (change < 0) { return { text: "▼ " + Math.abs(change) + "% " + suffix, cls: "down" }; }
        return { text: "No change " + suffix, cls: "" };
    }

    function renderKpis(k) {
        const c = clear("sd-kpis");
        const rev = k.revenue, bk = k.booked, rc = k.receivables, bl = k.backlog, q = k.quotes, cu = k.customers, tg = k.target;
        const cards = [
            { label: "Revenue (invoiced)", value: fmtINR(rev.value), tone: "good", delta: deltaSpec(rev.change_pct, "vs previous period"),
              note: fmtInt(rev.invoices) + " invoices" + (rev.avg_invoice ? " · avg " + fmtINR(rev.avg_invoice) : "") },
            { label: "Orders Booked", value: fmtINR(bk.value), tone: "", delta: deltaSpec(bk.change_pct, "vs previous period"),
              note: fmtInt(bk.orders) + " sales orders" },
            { label: "Average Order Value", value: bk.avg_order ? fmtINR(bk.avg_order) : "-", tone: "gold", delta: { text: "", cls: "" },
              note: "Booked value ÷ orders in period" },
            { label: "Outstanding Receivables", value: fmtINR(rc.outstanding), tone: rc.overdue > 0 ? "flag" : "good",
              delta: { text: rc.overdue > 0 ? fmtINR(rc.overdue) + " overdue" : "Nothing overdue", cls: rc.overdue > 0 ? "down" : "up" },
              note: rc.over60 > 0 ? fmtINR(rc.over60) + " overdue more than 60 days" : "None overdue beyond 60 days" },
            { label: "Order Backlog", value: fmtINR(bl.value), tone: bl.late > 0 ? "flag" : "",
              delta: { text: bl.late > 0 ? fmtInt(bl.late) + " past delivery date" : "All on schedule", cls: bl.late > 0 ? "down" : "up" },
              note: fmtInt(bl.orders) + " open orders, value still to deliver" },
            { label: "Open Quotations", value: fmtINR(q.open_value), tone: "gold", delta: { text: "", cls: "" },
              note: fmtInt(q.open_count) + " quotations awaiting a decision" },
            { label: "Quotation Conversion", value: q.conversion_pct === null ? "-" : q.conversion_pct + "%", tone: "good", delta: { text: "", cls: "" },
              note: fmtInt(q.won) + " of " + fmtInt(q.in_period) + " quotations became orders (" + fmtINR(q.won_value) + ")" },
            { label: "Active Customers", value: fmtInt(cu.active), tone: "", delta: cu.previous ? { text: (cu.change >= 0 ? "▲ " : "▼ ") + Math.abs(cu.change) + " vs previous period", cls: cu.change >= 0 ? "up" : "down" } : { text: "No prior-period data", cls: "" },
              note: "Customers invoiced in the period" }
        ];
        if (tg && tg.available) {
            cards.push({ label: "FY Target Progress", value: (tg.pct === null ? "-" : tg.pct + "%"),
                tone: tg.pct !== null && tg.expected_pct !== null && tg.pct < tg.expected_pct ? "flag" : "good",
                delta: { text: tg.expected_pct !== null ? "Time elapsed: " + tg.expected_pct + "%" : "", cls: "" },
                note: fmtINR(tg.achieved) + " of " + fmtINR(tg.target) + " target" });
        }
        cards.forEach(function (s) {
            const card = el("div", "sd-kpi" + (s.tone ? " " + s.tone : ""));
            card.appendChild(el("div", "sd-kpi-label", s.label));
            card.appendChild(el("div", "sd-kpi-value", s.value));
            if (s.delta.text) { card.appendChild(el("div", "sd-kpi-delta " + s.delta.cls, s.delta.text)); }
            card.appendChild(el("div", "sd-kpi-note", s.note));
            c.appendChild(card);
        });
    }

    // ---------- Attention ----------
    function richLine(parts) {
        const d = el("div", "sd-attn-detail");
        parts.forEach(function (p) {
            if (typeof p === "string") { d.appendChild(document.createTextNode(p)); } else { d.appendChild(el("b", null, p.b)); }
        });
        return d;
    }
    function attnItem(sev, title, tag, parts) {
        const item = el("div", "sd-attn-item " + sev);
        const t = el("div", "sd-attn-title");
        t.appendChild(el("span", null, title));
        t.appendChild(el("span", "sd-tag", tag));
        item.appendChild(t);
        item.appendChild(richLine(parts));
        return item;
    }
    function joinRows(rows, build) {
        const parts = [];
        rows.forEach(function (r, i) {
            if (i > 0) { parts.push("; "); }
            build(r).forEach(function (p) { parts.push(p); });
        });
        return parts;
    }

    function renderAttention(items) {
        const c = clear("sd-attn");
        let real = 0;
        items.forEach(function (a) {
            if (a.kind !== "no_target") { real++; }
            if (a.kind === "overdue") {
                let parts = [fmtINR(a.total) + " overdue. "];
                if (a.over60 > 0) { parts.push("Of which " + fmtINR(a.over60) + " is over 60 days. "); }
                parts = parts.concat(joinRows(a.rows, function (r) { return [{ b: r.name.trim() }, " " + fmtINR(r.amount) + " (" + r.days + " days)"]; }));
                c.appendChild(attnItem(a.severity, "Overdue receivables", a.severity === "critical" ? "CRITICAL" : "FOLLOW UP", parts));
            } else if (a.kind === "stalled_quotes") {
                const parts = [fmtInt(a.count) + " open quotations older than " + a.threshold + " days. Largest: "]
                    .concat(joinRows(a.rows, function (r) { return [{ b: r.customer }, " " + fmtINR(r.value) + " (" + r.days + " days)"]; }));
                c.appendChild(attnItem("warn", "Stalled quotations", "FOLLOW UP", parts));
            } else if (a.kind === "late_deliveries") {
                const parts = [fmtInt(a.count) + " orders are past their delivery date. Largest: "]
                    .concat(joinRows(a.rows, function (r) { return [{ b: r.customer }, " " + fmtINR(r.value) + " (" + r.days + " days late)"]; }));
                c.appendChild(attnItem("warn", "Delayed deliveries", "FOLLOW UP", parts));
            } else if (a.kind === "pace") {
                c.appendChild(attnItem("warn", "Behind target pace", "WATCH",
                    ["Target achieved is ", { b: a.pct + "%" }, " while ", { b: a.expected + "%" }, " of the year has elapsed."]));
            } else if (a.kind === "no_target") {
                c.appendChild(attnItem("info", "Sales targets not set", "SETUP",
                    ["No targets are defined for the fiscal year. Add targets on ", { b: "Sales Person" }, " to enable target-progress tracking."]));
            }
        });
        if (!real) {
            c.insertBefore(attnItem("ok", "All clear", "GOOD", ["No overdue receivables, stalled quotations or delayed deliveries right now."]), c.firstChild);
        }
        setText("sd-attn-sub", real + " item" + (real === 1 ? "" : "s") + " flagged today");
    }

    // ---------- Tables / team ----------
    function renderCustomers(rows, hasPrev) {
        const c = clear("sd-customers");
        if (!rows.length) { empty(c, "No invoiced customers in this period."); return; }
        const table = el("table", "sd-table");
        const head = el("tr");
        ["Customer", "Revenue", "Share", "Outstanding"].concat(hasPrev ? ["Change", "Status"] : []).forEach(function (h) { head.appendChild(el("th", null, h)); });
        const thead = el("thead"); thead.appendChild(head); table.appendChild(thead);
        const body = el("tbody");
        rows.forEach(function (r) {
            const tr = el("tr");
            const td = el("td");
            td.appendChild(el("div", "sd-cust", r.name.trim()));
            td.appendChild(el("div", "sd-cust-sub", r.segment));
            tr.appendChild(td);
            tr.appendChild(el("td", null, fmtINR(r.revenue)));
            tr.appendChild(el("td", null, r.share_pct === null ? "-" : r.share_pct + "%"));
            tr.appendChild(el("td", null, r.outstanding ? fmtINR(r.outstanding) : "-"));
            if (hasPrev) {
                const ch = el("td", null, r.change_pct === null ? "-" : (r.change_pct > 0 ? "+" : "") + r.change_pct + "%");
                tr.appendChild(ch);
                const st = el("td");
                st.appendChild(el("span", "sd-status " + r.status, r.status.charAt(0).toUpperCase() + r.status.slice(1)));
                tr.appendChild(st);
            }
            body.appendChild(tr);
        });
        table.appendChild(body);
        c.appendChild(table);
    }

    function renderTeam(rows, unallocated, hasTarget) {
        const c = clear("sd-team");
        if (!rows.length) { empty(c, "No sales-person allocated revenue in this period."); return; }
        let max = 0;
        rows.forEach(function (r) { if (r.revenue > max) { max = r.revenue; } });
        rows.forEach(function (r, i) {
            const rep = el("div", "sd-rep");
            const top = el("div", "sd-rep-top");
            top.appendChild(el("span", "sd-rep-name", r.name));
            let val = fmtINR(r.revenue) + (r.share_pct !== null ? " · " + r.share_pct + "%" : "");
            if (hasTarget && r.target) { val = fmtINR(r.revenue) + " / " + fmtINR(r.target) + " · " + r.target_pct + "%"; }
            top.appendChild(el("span", "sd-rep-val", val));
            rep.appendChild(top);
            const track = el("div", "sd-rep-track");
            const fill = el("div", "sd-rep-fill" + (i === 0 ? " top" : ""));
            const base = hasTarget && r.target ? Math.min(100, r.target_pct || 0) : (max ? (r.revenue / max) * 100 : 0);
            fill.style.width = Math.max(2, base) + "%";
            track.appendChild(fill);
            rep.appendChild(track);
            rep.appendChild(el("div", "sd-rep-sub", fmtInt(r.invoices) + " invoices · " + fmtInt(r.orders) + " orders booked (" + fmtINR(r.booked) + ")"));
            c.appendChild(rep);
        });
        if (unallocated > 1) {
            const rep = el("div", "sd-rep");
            const top = el("div", "sd-rep-top");
            top.appendChild(el("span", "sd-rep-name", "Not allocated to a sales person"));
            top.appendChild(el("span", "sd-rep-val", fmtINR(unallocated)));
            rep.appendChild(top);
            const track = el("div", "sd-rep-track");
            const fill = el("div", "sd-rep-fill low");
            fill.style.width = Math.max(2, max ? (unallocated / max) * 100 : 0) + "%";
            track.appendChild(fill);
            rep.appendChild(track);
            c.appendChild(rep);
        }
    }

    // ---------- Quick links ----------
    const LINKS = [
        { label: "Sales Orders", color: "#5B84B1", go: function () { frappe.set_route("List", "Sales Order"); } },
        { label: "Quotations", color: "#D9A441", go: function () { frappe.set_route("List", "Quotation"); } },
        { label: "Sales Invoices", color: "#3E9B6E", go: function () { frappe.set_route("List", "Sales Invoice"); } },
        { label: "Customers", color: "#7FA8C9", go: function () { frappe.set_route("List", "Customer"); } },
        { label: "Accounts Receivable", color: "#D0573B", go: function () { frappe.set_route("query-report", "Accounts Receivable"); } },
        { label: "Sales Register", color: "#B8842A", go: function () { frappe.set_route("query-report", "Sales Register"); } }
    ];
    function renderLinks() {
        const c = clear("sd-links");
        LINKS.forEach(function (l) {
            const chip = el("div", "sd-link");
            chip.setAttribute("role", "link");
            chip.setAttribute("tabindex", "0");
            const dot = el("i"); dot.style.background = l.color;
            chip.appendChild(dot);
            chip.appendChild(document.createTextNode(l.label));
            chip.addEventListener("click", l.go);
            chip.addEventListener("keydown", function (e) { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); l.go(); } });
            c.appendChild(chip);
        });
    }

    // ---------- Filters ----------
    function fillSelect(name, options, placeholder) {
        const s = role(name);
        const current = s.value;
        s.replaceChildren();
        const p = document.createElement("option");
        p.value = ""; p.textContent = placeholder;
        s.appendChild(p);
        options.forEach(function (o) {
            const opt = document.createElement("option");
            opt.value = o.value; opt.textContent = o.label;
            s.appendChild(opt);
        });
        s.value = options.some(function (o) { return o.value === current; }) ? current : "";
    }
    async function loadOptions() {
        try {
            const res = await Promise.all([
                frappe.call({ method: "frappe.client.get_list", args: { doctype: "Company", fields: ["name"], limit_page_length: 0 }, freeze: false }),
                frappe.call({ method: "frappe.client.get_list", args: { doctype: "Sales Person", fields: ["name"], filters: { is_group: 0, enabled: 1 }, order_by: "name asc", limit_page_length: 0 }, freeze: false }),
                frappe.call({ method: "frappe.client.get_list", args: { doctype: "Territory", fields: ["name"], filters: { is_group: 0 }, order_by: "name asc", limit_page_length: 0 }, freeze: false })
            ]);
            fillSelect("sd-company", (res[0].message || []).map(function (r) { return { value: r.name, label: r.name }; }), "All Companies");
            fillSelect("sd-person", (res[1].message || []).map(function (r) { return { value: r.name, label: r.name }; }), "All Sales Persons");
            fillSelect("sd-territory", (res[2].message || []).map(function (r) { return { value: r.name, label: r.name }; }), "All Territories");
        } catch (e) { console.error("Sales Dashboard: filter options failed", e); }
    }
    function filters() {
        return {
            from_date: role("sd-from").value, to_date: role("sd-to").value,
            company: role("sd-company").value, sales_person: role("sd-person").value, territory: role("sd-territory").value
        };
    }
    function defaultRange() {
        const now = new Date();
        const fyYear = now.getMonth() >= 3 ? now.getFullYear() : now.getFullYear() - 1;
        return { from: fyYear + "-04-01", to: dstr(now) };
    }

    // ---------- Trend rendering (monthly, or daily while history is short) ----------
    async function renderTrends(ch, f) {
        const n = ch.revenue_trend.months.length;
        const all = [ch.revenue_trend.current, ch.revenue_trend.previous, ch.flow.booked, ch.flow.invoiced];
        let daily = null;
        if (activeMonths(all, n) <= 2 && !f.territory) {
            try {
                const dr = await frappe.call({ method: "ric_template.dashboards.sales_dashboard.sales_dashboard_daily", args: { to_date: f.to_date, company: f.company, sales_person: f.sales_person }, freeze: false });
                if (dr.message && dr.message.success) { daily = dr.message; }
            } catch (e) { console.error("Sales Dashboard: daily series failed", e); }
        }

        if (daily) {
            const dopts = { label: dayLabel, every: 5 };
            barChart(clear("sd-trend"), daily.days, [{ name: "Invoiced revenue", color: "#5B84B1", values: daily.invoiced }], dopts);
            legend("sd-trend-legend", [{ label: "Invoiced revenue (daily)", color: "#5B84B1" }]);
            setPanelSub("sd-trend", "Invoiced net revenue by day, last 30 days (switches to monthly as history builds)");
            barChart(clear("sd-flow"), daily.days, [
                { name: "Orders booked", color: "#5B84B1", values: daily.booked },
                { name: "Invoiced", color: "#D9A441", values: daily.invoiced }
            ], dopts);
            legend("sd-flow-legend", [{ label: "Orders booked", color: "#5B84B1" }, { label: "Invoiced", color: "#D9A441" }]);
            setPanelSub("sd-flow", "Sales orders confirmed against invoices raised, by day, last 30 days");
            return;
        }

        const s1 = trimStart(all, n);
        const months = ch.revenue_trend.months.slice(s1);
        const cur = ch.revenue_trend.current.slice(s1);
        const prev = ch.revenue_trend.previous.slice(s1);
        const hasPrev = prev.some(function (v) { return v > 0; });
        const trendSeries = [{ name: "This period", color: "#5B84B1", values: cur }];
        const lg = [{ label: "Selected months", color: "#5B84B1" }];
        if (hasPrev) { trendSeries.unshift({ name: "Same month last year", color: "#C6CCD3", values: prev }); lg.push({ label: "Same month last year", color: "#C6CCD3" }); }
        barChart(clear("sd-trend"), months, trendSeries);
        legend("sd-trend-legend", lg);
        setPanelSub("sd-trend", "Invoiced net revenue by month");

        barChart(clear("sd-flow"), months, [
            { name: "Orders booked", color: "#5B84B1", values: ch.flow.booked.slice(s1) },
            { name: "Invoiced", color: "#D9A441", values: ch.flow.invoiced.slice(s1) }
        ]);
        legend("sd-flow-legend", [{ label: "Orders booked", color: "#5B84B1" }, { label: "Invoiced", color: "#D9A441" }]);
        setPanelSub("sd-flow", "Sales orders confirmed against invoices raised, by month");
    }

    // ---------- Load ----------
    async function load() {
        const err = role("sd-error"); err.hidden = true;
        setText("sd-meta", "Loading live sales data...");
        try {
            const f = filters();
            const resp = await frappe.call({ method: "ric_template.dashboards.sales_dashboard.sales_dashboard_data", args: f, freeze: false });
            const d = resp.message || {};
            if (!d.success) { throw new Error(d.error || "Sales data could not be loaded."); }
            const ch = d.charts, k = d.kpis;

            renderKpis(k);
            renderAttention(d.attention || []);
            await renderTrends(ch, f);

            const agingColors = ["#3E9B6E", "#D9A441", "#E58A3A", "#D0573B", "#A63A24"];
            hBars("sd-aging", ch.aging, {
                emptyText: "No outstanding receivables.",
                label: function (r) { return r.label; }, value: function (r) { return r.amount; },
                color: function (r, i) { return agingColors[i]; },
                text: function (r) { return fmtINR(r.amount); }, sub: function (r) { return fmtInt(r.count) + " invoice" + (r.count === 1 ? "" : "s"); }
            });

            const totalMix = ch.category_mix.reduce(function (a, r) { return a + r.value; }, 0);
            donut("sd-mix", ch.category_mix, fmtINR(totalMix), "total revenue");

            hBars("sd-segments", ch.segments, {
                emptyText: "No invoiced revenue in this period.",
                label: function (r) { return r.label; }, value: function (r) { return r.value; },
                color: function (r, i) { return PALETTE[i % PALETTE.length]; },
                text: function (r) { return fmtINR(r.value); }, sub: function (r) { return (r.pct === null ? "-" : r.pct + "%") + " of revenue"; }
            });

            role("sd-region-panel").hidden = !ch.regions_meaningful;
            role("sd-territory-field").hidden = !ch.regions_meaningful;
            if (ch.regions_meaningful) {
                hBars("sd-regions", ch.regions, {
                    emptyText: "No regional data.",
                    label: function (r) { return r.label; }, value: function (r) { return r.value; },
                    color: function (r, i) { return PALETTE[i % PALETTE.length]; },
                    text: function (r) { return fmtINR(r.value); }, sub: function (r) { return (r.pct === null ? "-" : r.pct + "%") + " of revenue"; }
                });
            }

            const funnelColors = ["#7FA8C9", "#5B84B1", "#D9A441", "#B8842A", "#3E9B6E"];
            hBars("sd-funnel", ch.funnel, {
                emptyText: "No sales activity in this period.",
                label: function (r) { return r.label; }, value: function (r) { return r.count; },
                color: function (r, i) { return funnelColors[i]; },
                text: function (r) { return fmtInt(r.count); }, sub: function (r) { return r.value ? fmtINR(r.value) : ""; }
            });
            const fn = role("sd-funnel-note");
            fn.hidden = false;
            fn.textContent = f.sales_person
                ? "Lead and opportunity counts are not sales-person specific. Stages are documents created in the period, not a strict cohort funnel."
                : "Stages are documents created in the period, not a strict cohort funnel (an order can exist without a quotation).";

            renderCustomers(ch.top_customers, k.revenue.previous > 0);
            renderTeam(ch.sales_team, ch.team_unallocated, k.target && k.target.available);
            setText("sd-team-sub", k.target && k.target.available ? "Revenue vs individual target" : "Invoiced revenue allocated via Sales Team");

            const range = d.filters.from_date + " to " + d.filters.to_date;
            const pill = role("sd-period");
            pill.replaceChildren();
            pill.appendChild(document.createTextNode((d.filters.fiscal_year ? "FY " + d.filters.fiscal_year + " · " : "")));
            pill.appendChild(el("strong", null, range));
            const gen = (frappe.datetime && frappe.datetime.str_to_user) ? frappe.datetime.str_to_user(d.generated_at) : d.generated_at;
            setText("sd-meta", "Live from ERPNext · updated " + gen);
        } catch (e) {
            console.error("Sales Dashboard:", e);
            setText("sd-meta", "Unable to load sales data");
            err.hidden = false;
            err.textContent = e.message || "The dashboard could not be loaded.";
        }
    }

    // ---------- Init ----------
    const now = new Date();
    const hr = now.getHours();
    const hello = hr < 12 ? "Good morning" : hr < 17 ? "Good afternoon" : "Good evening";
    const who = (frappe.session && frappe.session.user_fullname) ? ", " + frappe.session.user_fullname : "";
    setText("sd-greeting", hello + who);
    setText("sd-date", now.toLocaleDateString("en-IN", { weekday: "long", year: "numeric", month: "long", day: "numeric" }));

    const dr = defaultRange();
    role("sd-from").value = dr.from;
    role("sd-to").value = dr.to;
    renderLinks();

    role("sd-apply").addEventListener("click", load);
    role("sd-print").addEventListener("click", function () { window.print(); });
    role("sd-reset").addEventListener("click", function () {
        const r = defaultRange();
        role("sd-from").value = r.from; role("sd-to").value = r.to;
        role("sd-company").value = ""; role("sd-person").value = ""; role("sd-territory").value = "";
        load();
    });

    await Promise.all([loadOptions(), load()]);
})();