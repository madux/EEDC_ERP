# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

def _date(s):
    # Accept YYYY-MM-DD, fallback to None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return None

class SalesRepDashboard(http.Controller):

    @http.route("/sales_rep_dashboard", type="http", auth="user", website=True)
    def sales_rep_dashboard_page(self, **kw):
        # Render QWeb page (Bootstrap + placeholders). Data is fetched via /data
        return request.render("sales_rep_dashboard.dashboard_page")

    @http.route("/sales_rep_dashboard/data", type="json", auth="user")
    def sales_rep_dashboard_data(self, **kw):
        """Return KPIs, series, and table for the current user, filtered by dates."""
        env = request.env
        uid = request.uid
        company = env.user.company_id
        currency_symbol = company.currency_id.symbol or "₦"


        # Filters
        today = date.today()
        date_from = _date(kw.get("date_from")) 
        date_to   = _date(kw.get("date_to"))   
        search_term = (kw.get("search") or "").strip()

        # Build domain common pieces
        base_domain = [("user_id", "=", uid)]
        # date filters
        if date_from:
            base_domain.append(("date_order", ">=", datetime.combine(date_from, datetime.min.time())))
        if date_to:
            base_domain.append(("date_order", "<=", datetime.combine(date_to, datetime.max.time())))
            
        # search filter
        if search_term:
            base_domain.append("|")
            base_domain.append(("name", "ilike", search_term))
            base_domain.append(("partner_id.name", "ilike", search_term))


        order = env["sale.order"]

        # Quotations (draft or sent)
        quotations_domain = base_domain + [("state", "in", ["draft", "sent"])]
        quotations_count = order.search_count(quotations_domain)

        # Won (confirmed / delivered)
        won_domain = base_domain + [("state", "in", ["sale", "done"])]
        sales_won_count = order.search_count(won_domain)

        # Total won amount
        won_sum = 0.0
        won_rg = order.read_group(won_domain, ["amount_total:sum"], [])
        if won_rg:
            won_sum = won_rg[0].get("amount_total", 0.0) or 0.0

        # Forecasted amount
        forecast_domain = [
            ("user_id", "=", uid),
            ("state", "in", ["draft", "sent"]),
            ("validity_date", "!=", False),
        ]

        # Apply date filters only if provided
        if date_from:
            forecast_domain.append(("validity_date", ">=", datetime.combine(date_from, datetime.min.time())))
        if date_to:
            forecast_domain.append(("validity_date", "<=", datetime.combine(date_to, datetime.max.time())))

        forecast_sum = 0.0
        forecast_rg = order.read_group(forecast_domain, ["amount_total:sum"], [])
        if forecast_rg:
            forecast_sum = forecast_rg[0].get("amount_total", 0.0) or 0.0

        # Customers under salesperson
        partner = env["res.partner"]
        customers_count = partner.search_count([
            ("user_id", "=", uid),
            ("customer_rank", ">", 0),
        ])

        # Charts -------------
        # 1) Pipeline by month: quotations vs won
        def month_key(d):
            return d.strftime("%Y-%m")

        # Build monthly buckets
        months = []
        # use safe defaults if dates not given
        start_anchor = date_from or (today - relativedelta(months=5))
        end_anchor = date_to or today
        cur = start_anchor.replace(day=1)
        end_anchor = end_anchor.replace(day=1)

        # Ensure at least 6 months of data
        while len(months) < 6 or cur <= end_anchor:
            months.append(cur.strftime("%Y-%m"))
            cur = (cur + relativedelta(months=1))


        def sum_rg(domain):
            """Return monthly totals for a given domain"""
            rg = order.read_group(
                domain,
                ["amount_total:sum", "date_order"],
                ["date_order"]
            )
            out = {m: 0.0 for m in months}

            for row in rg:
                d = row.get("date_order")
                if isinstance(d, tuple):
                    d = d[0]
                if isinstance(d, str):
                    try:
                        d = datetime.strptime(d, "%Y-%m-%d")
                    except Exception:
                        continue
                if isinstance(d, datetime):
                    key = d.strftime("%Y-%m")
                    if key in out:
                        out[key] += row.get("amount_total", 0.0) or 0.0
            return [out[m] for m in months]

        pipe_quotation = sum_rg(base_domain + [("state", "in", ["draft", "sent"])])
        pipe_won       = sum_rg(base_domain + [("state", "in", ["sale", "done"])])

        # 2) Top customers by won amount (top 5)
        top_rg = order.read_group(
            won_domain,
            ["amount_total:sum", "partner_id"],
            ["partner_id"],
            limit=5
        )
        top_rg.sort(key=lambda r: r.get("amount_total", 0.0) or 0.0, reverse=True)
        top_labels = [
            env["res.partner"].browse(r["partner_id"][0]).name if r.get("partner_id") else "—"
            for r in top_rg
        ]
        top_values = [r.get("amount_total", 0.0) or 0.0 for r in top_rg]

        # 3) Forecast curve next 3 months (based on validity_date)
        fstart = today.replace(day=1)
        fmonths = [fstart + relativedelta(months=i) for i in range(3)]
        f_labels = [m.strftime("%b %Y") for m in fmonths]
        f_values = []
        for m in fmonths:
            m_start = datetime.combine(m, datetime.min.time())
            m_end = datetime.combine((m + relativedelta(months=1)) - relativedelta(days=1), datetime.max.time())
            rg = order.read_group([
                ("user_id", "=", uid),
                ("state", "in", ["draft", "sent"]),
                ("validity_date", ">=", m_start),
                ("validity_date", "<=", m_end),
            ], ["amount_total:sum"], [])
            f_values.append(float(rg[0].get("amount_total") or 0.0) if rg else 0.0)



        # Table (paginated)
        page = int(kw.get("page", 1))
        page_size = int(kw.get("page_size", 20))
        offset = (page - 1) * page_size

        # We show both quotations and won (all mine in window)
        table_domain = base_domain
        total_rows = order.search_count(table_domain)

        rows = order.search(table_domain, order="date_order desc", limit=page_size, offset=offset)
        table = []
        for r in rows:
            table.append({
                "name": r.name,
                "partner": r.partner_id.name,
                "state": r.state,
                "date_order": r.date_order and r.date_order.strftime("%Y-%m-%d %H:%M") or "",
                "amount_untaxed": r.amount_untaxed,
                "amount_total": r.amount_total,
                "currency": r.currency_id.symbol or r.currency_id.name,
                "validity_date": r.validity_date and r.validity_date.strftime("%Y-%m-%d") or "",
                "id": r.id,
            })

        return {
            "kpis": {
                "quotations": quotations_count,
                "sales_won": sales_won_count,
                "customers": customers_count,
                "total_won": won_sum,
                "forecast": forecast_sum,
            },
            "pipeline": {
                "labels": months,
                "quotations": pipe_quotation,
                "won": pipe_won,
            },
            "top_customers": {
                "labels": top_labels,
                "values": top_values,
            },
            "forecast_curve": {
                "labels": f_labels,
                "values": f_values,
            },
            "table": {
                "total": total_rows,
                "page": page,
                "page_size": page_size,
                "rows": table,
            },
            "currency_symbol": currency_symbol,
        }
