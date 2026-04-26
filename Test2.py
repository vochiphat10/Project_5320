import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, Input, Output, dash_table, dcc, html


# ============================================================
# Maven Market Dash App - Render Ready Version
# Start command on Render: gunicorn Test:server
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"


def read_csv_file(filename):
    path = DATA_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Missing required data file: {path}")
    return pd.read_csv(path)


def clean_columns(dataframe):
    dataframe = dataframe.copy()
    dataframe.columns = (
        dataframe.columns.str.strip()
        .str.lower()
        .str.replace(" ", "_")
        .str.replace(r"[^\w]", "", regex=True)
    )
    return dataframe


# -----------------------------
# Load datasets
# -----------------------------
customers = clean_columns(read_csv_file("MavenMarket_Customers.csv"))
products = clean_columns(read_csv_file("MavenMarket_Products.csv"))
regions = clean_columns(read_csv_file("MavenMarket_Regions.csv"))
stores = clean_columns(read_csv_file("MavenMarket_Stores.csv"))
calendar = clean_columns(read_csv_file("MavenMarket_Calendar.csv"))
trans_1997 = clean_columns(read_csv_file("MavenMarket_Transactions_1997.csv"))
trans_1998 = clean_columns(read_csv_file("MavenMarket_Transactions_1998.csv"))
returns = clean_columns(read_csv_file("MavenMarket_Returns_1997-1998.csv"))


# -----------------------------
# Preprocess dates
# -----------------------------
transactions = pd.concat([trans_1997, trans_1998], ignore_index=True)

calendar["date"] = pd.to_datetime(calendar["date"], errors="coerce")
calendar["year"] = calendar["date"].dt.year
calendar["month"] = calendar["date"].dt.month
calendar["month_name"] = calendar["date"].dt.strftime("%b")
calendar["weekday_name"] = calendar["date"].dt.strftime("%a")
calendar["week_start"] = calendar["date"] - pd.to_timedelta(calendar["date"].dt.weekday, unit="D")

transactions["transaction_date"] = pd.to_datetime(transactions["transaction_date"], errors="coerce")
transactions["year"] = transactions["transaction_date"].dt.year
transactions["month"] = transactions["transaction_date"].dt.month
transactions["month_name"] = transactions["transaction_date"].dt.strftime("%b")
transactions["quarter"] = transactions["transaction_date"].dt.quarter

returns["return_date"] = pd.to_datetime(returns["return_date"], errors="coerce")
returns["year"] = returns["return_date"].dt.year
returns["month"] = returns["return_date"].dt.month
returns["month_name"] = returns["return_date"].dt.strftime("%b")


# -----------------------------
# Normalize key columns for joins
# -----------------------------
for df_obj, col in [
    (customers, "customer_id"),
    (products, "product_id"),
    (regions, "region_id"),
    (stores, "store_id"),
    (stores, "region_id"),
    (transactions, "customer_id"),
    (transactions, "product_id"),
    (transactions, "store_id"),
    (returns, "product_id"),
    (returns, "store_id"),
]:
    if col in df_obj.columns:
        df_obj[col] = df_obj[col].astype(str).str.strip()


# -----------------------------
# Join datasets
# -----------------------------
stores_regions = stores.merge(regions, on="region_id", how="left")

df = transactions.merge(customers, on="customer_id", how="left")
df = df.merge(products, on="product_id", how="left")
df = df.merge(stores_regions, on="store_id", how="left")

# Main calculated metrics
df["sales"] = df["quantity"] * df["product_retail_price"]
df["cost"] = df["quantity"] * df["product_cost"]
df["profit"] = df["sales"] - df["cost"]

# Make sure important text columns do not have NaN
for col in [
    "sales_region",
    "gender",
    "education",
    "occupation",
    "product_name",
    "product_brand",
    "member_card",
    "store_name",
    "store_type",
]:
    if col in df.columns:
        df[col] = df[col].fillna("Unknown").astype(str).str.strip()


# -----------------------------
# Helper functions
# -----------------------------
def apply_filters(dataframe, years=None, regions=None, genders=None, educations=None, occupations=None):
    filtered = dataframe.copy()

    if years:
        years = [int(y) for y in years]
        filtered = filtered[filtered["year"].astype(int).isin(years)]

    if regions:
        regions = [str(r).strip() for r in regions]
        filtered = filtered[filtered["sales_region"].astype(str).str.strip().isin(regions)]

    if genders:
        genders = [str(g).strip() for g in genders]
        filtered = filtered[filtered["gender"].astype(str).str.strip().isin(genders)]

    if educations:
        educations = [str(e).strip() for e in educations]
        filtered = filtered[filtered["education"].astype(str).str.strip().isin(educations)]

    if occupations:
        occupations = [str(o).strip() for o in occupations]
        filtered = filtered[filtered["occupation"].astype(str).str.strip().isin(occupations)]

    return filtered


def kpi_summary(dataframe):
    return {
        "Total Sales": f"${dataframe['sales'].sum():,.2f}",
        "Total Profit": f"${dataframe['profit'].sum():,.2f}",
        "Total Quantity": f"{dataframe['quantity'].sum():,.0f}",
        "Active Customers": f"{dataframe['customer_id'].nunique():,}",
        "Active Stores": f"{dataframe['store_id'].nunique():,}",
    }


def top_products_table(dataframe):
    result = (
        dataframe.groupby(["product_name", "product_brand"], as_index=False)[["sales", "profit", "quantity"]]
        .sum()
        .sort_values("sales", ascending=False)
        .head(15)
    )
    result["sales"] = result["sales"].round(2)
    result["profit"] = result["profit"].round(2)
    return result


# -----------------------------
# Dash app
# -----------------------------
app = Dash(__name__, suppress_callback_exceptions=True)
server = app.server
app.title = "Maven Market Dashboard"

CHART_COLORS = ["#0f766e", "#f97316", "#0891b2", "#7c3aed", "#dc2626", "#65a30d"]

DEFAULT_GRAPH_CONFIG = {
    "displayModeBar": True,
    "displaylogo": False,
    "responsive": True,
}


def themed_figure(fig):
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#f8fafc",
        colorway=CHART_COLORS,
        font={"family": "Plus Jakarta Sans, Segoe UI, sans-serif", "color": "#0f172a"},
        title={"x": 0.02, "xanchor": "left", "font": {"size": 20}},
        margin={"l": 40, "r": 24, "t": 72, "b": 44},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
        height=420,
    )
    fig.update_xaxes(showgrid=False, zeroline=False, linecolor="#cbd5e1")
    fig.update_yaxes(gridcolor="rgba(148,163,184,0.20)", zeroline=False)
    return fig


def empty_figure(title="No data"):
    fig = go.Figure()
    fig.add_annotation(
        text="No data available. Try widening the filters.",
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        showarrow=False,
        font={"size": 16, "color": "#475569"},
    )
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    fig.update_layout(showlegend=False)
    return themed_figure(fig).update_layout(title=title)


def graph_component(graph_id, title):
    return dcc.Graph(
        id=graph_id,
        figure=empty_figure(title),
        config=DEFAULT_GRAPH_CONFIG,
        style={"height": "420px"},
    )


years = sorted(df["year"].dropna().astype(int).unique().tolist())
regions_list = sorted(df["sales_region"].dropna().astype(str).unique().tolist())
genders = sorted(df["gender"].dropna().astype(str).unique().tolist())
educations = sorted(df["education"].dropna().astype(str).unique().tolist())
occupations = sorted(df["occupation"].dropna().astype(str).unique().tolist())


app.layout = html.Div(
    [
        html.Div(
            [
                html.Div(
                    [
                        html.P("Retail Intelligence", className="eyebrow"),
                        html.H1("Maven Market Performance Dashboard"),
                        html.P(
                            "Explore sales, profit, customer mix, and store performance across the Maven Market business.",
                            className="hero-subtitle",
                        ),
                    ]
                ),
            ],
            className="hero-section",
        ),
        html.Div(
            [
                html.Div(
                    [
                        html.Label("Year"),
                        dcc.Dropdown(
                            id="year_filter",
                            options=[{"label": str(y), "value": y} for y in years],
                            value=years,
                            multi=True,
                            placeholder="Select year",
                        ),
                    ],
                    className="filter-field",
                ),
                html.Div(
                    [
                        html.Label("Region"),
                        dcc.Dropdown(
                            id="region_filter",
                            options=[{"label": r, "value": r} for r in regions_list],
                            value=[],
                            multi=True,
                            placeholder="Select region",
                        ),
                    ],
                    className="filter-field",
                ),
                html.Div(
                    [
                        html.Label("Gender"),
                        dcc.Dropdown(
                            id="gender_filter",
                            options=[{"label": g, "value": g} for g in genders],
                            value=[],
                            multi=True,
                            placeholder="Select gender",
                        ),
                    ],
                    className="filter-field",
                ),
                html.Div(
                    [
                        html.Label("Education"),
                        dcc.Dropdown(
                            id="education_filter",
                            options=[{"label": e, "value": e} for e in educations],
                            value=[],
                            multi=True,
                            placeholder="Select education",
                        ),
                    ],
                    className="filter-field",
                ),
                html.Div(
                    [
                        html.Label("Occupation"),
                        dcc.Dropdown(
                            id="occupation_filter",
                            options=[{"label": o, "value": o} for o in occupations],
                            value=[],
                            multi=True,
                            placeholder="Select occupation",
                        ),
                    ],
                    className="filter-field",
                ),
            ],
            className="filter-panel",
        ),
        html.Div(id="kpi_cards", className="kpi-grid"),
        html.Div(
            [
                html.Div(graph_component("monthly_sales_chart", "Daily Sales Calendar Heatmap"), className="chart-card chart-card-wide"),
                html.Div(graph_component("monthly_sales_trend_chart", "Monthly Sales Trend"), className="chart-card"),
                html.Div(graph_component("day_of_week_chart", "Average Daily Sales by Day of Week"), className="chart-card"),
                html.Div(graph_component("sales_by_region_chart", "Sales by Region"), className="chart-card"),
                html.Div(graph_component("profit_by_brand_chart", "Top 10 Brands by Profit"), className="chart-card"),
                html.Div(graph_component("member_card_chart", "Customers by Member Card"), className="chart-card"),
                html.Div(graph_component("sales_by_education_chart", "Sales by Education"), className="chart-card"),
                html.Div(graph_component("sales_by_occupation_chart", "Top 10 Occupations by Sales"), className="chart-card"),
                html.Div(graph_component("top_store_sales_chart", "Top 10 Stores by Sales"), className="chart-card"),
                html.Div(graph_component("sales_by_store_type_chart", "Sales by Store Type"), className="chart-card"),
                html.Div(graph_component("sales_per_customer_occupation_chart", "Sales per Active Customer by Occupation"), className="chart-card"),
                html.Div(graph_component("occupation_member_mix_chart", "Member Card Mix by Occupation"), className="chart-card"),
                html.Div(graph_component("occupation_region_heatmap_chart", "Occupation x Region Heatmap"), className="chart-card"),
            ],
            className="charts-grid",
        ),
        html.Div(
            [
                html.Div(
                    [
                        html.P("Top Products", className="section-label"),
                        html.H3("Top 15 Products by Sales"),
                    ],
                    className="section-heading",
                ),
                dash_table.DataTable(
                    id="top_products_table",
                    page_size=15,
                    sort_action="native",
                    style_as_list_view=True,
                    style_table={"overflowX": "auto"},
                    style_header={
                        "backgroundColor": "#e2e8f0",
                        "border": "none",
                        "color": "#0f172a",
                        "fontWeight": "700",
                        "padding": "14px",
                    },
                    style_cell={
                        "backgroundColor": "rgba(255,255,255,0.92)",
                        "border": "none",
                        "color": "#334155",
                        "fontFamily": "Plus Jakarta Sans, Segoe UI, sans-serif",
                        "padding": "12px",
                        "textAlign": "left",
                    },
                    style_data_conditional=[
                        {"if": {"row_index": "odd"}, "backgroundColor": "#f8fafc"},
                        {"if": {"state": "active"}, "backgroundColor": "#ecfeff", "border": "1px solid #14b8a6"},
                    ],
                ),
            ],
            className="table-card",
        ),
    ],
    className="app-shell",
)


# -----------------------------
# Callback
# -----------------------------
@app.callback(
    Output("kpi_cards", "children"),
    Output("monthly_sales_chart", "figure"),
    Output("monthly_sales_trend_chart", "figure"),
    Output("day_of_week_chart", "figure"),
    Output("sales_by_region_chart", "figure"),
    Output("profit_by_brand_chart", "figure"),
    Output("member_card_chart", "figure"),
    Output("sales_by_education_chart", "figure"),
    Output("sales_by_occupation_chart", "figure"),
    Output("top_store_sales_chart", "figure"),
    Output("sales_by_store_type_chart", "figure"),
    Output("sales_per_customer_occupation_chart", "figure"),
    Output("occupation_member_mix_chart", "figure"),
    Output("occupation_region_heatmap_chart", "figure"),
    Output("top_products_table", "data"),
    Output("top_products_table", "columns"),
    Input("year_filter", "value"),
    Input("region_filter", "value"),
    Input("gender_filter", "value"),
    Input("education_filter", "value"),
    Input("occupation_filter", "value"),
    prevent_initial_call=False,
)
def update_dashboard(year_values, region_values, gender_values, education_values, occupation_values):
    filtered = apply_filters(
        df,
        years=year_values,
        regions=region_values,
        genders=gender_values,
        educations=education_values,
        occupations=occupation_values,
    )

    print("CALLBACK STARTED", flush=True)
    print("Filters:", year_values, region_values, gender_values, education_values, occupation_values, flush=True)
    print("Filtered rows:", len(filtered), flush=True)
    print("Total sales:", filtered["sales"].sum() if not filtered.empty else 0, flush=True)

    if filtered.empty:
        empty_card = html.Div(
            [
                html.P("No Results", className="kpi-label"),
                html.H2("Adjust Filters", className="kpi-value"),
            ],
            className="kpi-card",
        )
        no_data = empty_figure("No data for selected filters")
        return (
            [empty_card],
            no_data,
            no_data,
            no_data,
            no_data,
            no_data,
            no_data,
            no_data,
            no_data,
            no_data,
            no_data,
            no_data,
            no_data,
            no_data,
            [],
            [],
        )

    # KPI cards
    kpis = kpi_summary(filtered)
    cards = [
        html.Div(
            [
                html.P(k, className="kpi-label"),
                html.H2(v, className="kpi-value"),
            ],
            className="kpi-card",
        )
        for k, v in kpis.items()
    ]

    weekday_order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    weekday_full_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    month_order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    # Daily sales calendar heatmap
    daily_sales = filtered.copy()
    daily_sales["date"] = daily_sales["transaction_date"].dt.normalize()
    daily_sales = daily_sales.groupby("date", as_index=False)["sales"].sum()

    calendar_view = calendar.copy()
    if year_values:
        calendar_view = calendar_view[calendar_view["year"].astype(int).isin([int(y) for y in year_values])]

    calendar_view = calendar_view.merge(daily_sales, on="date", how="left")
    calendar_view["sales"] = calendar_view["sales"].fillna(0)

    calendar_heatmap = (
        calendar_view.pivot_table(
            index="weekday_name",
            columns="week_start",
            values="sales",
            aggfunc="sum",
            fill_value=0,
        )
        .reindex(weekday_order)
        .fillna(0)
    )

    fig_monthly = go.Figure(
        data=go.Heatmap(
            z=calendar_heatmap.values,
            x=calendar_heatmap.columns,
            y=calendar_heatmap.index,
            colorscale=[
                [0.0, "#f7fcf9"],
                [0.2, "#d1fae5"],
                [0.4, "#86efac"],
                [0.6, "#34d399"],
                [0.8, "#059669"],
                [1.0, "#064e3b"],
            ],
            colorbar={"title": "Sales"},
            hovertemplate=(
                "Week of %{x|%b %d, %Y}<br>"
                "Day: %{y}<br>"
                "Sales: $%{z:,.2f}<extra></extra>"
            ),
        )
    )
    fig_monthly = themed_figure(fig_monthly)
    fig_monthly.update_layout(title="Daily Sales Calendar Heatmap", xaxis_title="Week Starting", yaxis_title="")
    fig_monthly.update_xaxes(dtick="M1", tickformat="%b<br>%Y")
    fig_monthly.update_yaxes(categoryorder="array", categoryarray=weekday_order)

    # Monthly sales trend
    monthly_trend = filtered.groupby(["year", "month_name"], as_index=False)["sales"].sum()
    monthly_trend["month_name"] = pd.Categorical(monthly_trend["month_name"], categories=month_order, ordered=True)
    monthly_trend = monthly_trend.sort_values(["year", "month_name"])

    fig_monthly_trend = themed_figure(
        px.line(
            monthly_trend,
            x="month_name",
            y="sales",
            color="year",
            markers=True,
            title="Monthly Sales Trend",
            labels={"month_name": "Month", "sales": "Sales", "year": "Year"},
        )
    )
    fig_monthly_trend.update_traces(line={"width": 4}, marker={"size": 8})

    # Average daily sales by day of week
    day_of_week = filtered.copy()
    day_of_week["weekday_name"] = day_of_week["transaction_date"].dt.day_name()
    day_of_week["date"] = day_of_week["transaction_date"].dt.normalize()

    weekday_summary = (
        day_of_week.groupby("weekday_name", as_index=False)
        .agg(
            total_sales=("sales", "sum"),
            active_days=("date", "nunique"),
            transactions=("sales", "size"),
        )
    )
    weekday_summary["avg_daily_sales"] = weekday_summary["total_sales"] / weekday_summary["active_days"]
    weekday_summary["weekday_name"] = pd.Categorical(
        weekday_summary["weekday_name"],
        categories=weekday_full_order,
        ordered=True,
    )
    weekday_summary = weekday_summary.sort_values("weekday_name")

    fig_day_of_week = themed_figure(
        px.bar(
            weekday_summary,
            x="weekday_name",
            y="avg_daily_sales",
            title="Average Daily Sales by Day of Week",
            labels={"weekday_name": "Day of Week", "avg_daily_sales": "Average Daily Sales"},
            hover_data={
                "total_sales": ":.2f",
                "active_days": True,
                "transactions": True,
                "avg_daily_sales": ":.2f",
            },
        )
    )
    fig_day_of_week.update_traces(marker_color="#0f766e", marker_line_color="#ffffff", marker_line_width=1.5)

    # Sales by region
    by_region = filtered.groupby("sales_region", as_index=False)["sales"].sum().sort_values("sales", ascending=False)
    fig_region = themed_figure(px.bar(by_region, x="sales_region", y="sales", title="Sales by Region"))
    fig_region.update_traces(marker_line_color="#ffffff", marker_line_width=1.5)

    # Profit by brand
    by_brand = (
        filtered.groupby("product_brand", as_index=False)["profit"]
        .sum()
        .sort_values("profit", ascending=False)
        .head(10)
    )
    fig_brand = themed_figure(px.bar(by_brand, x="product_brand", y="profit", title="Top 10 Brands by Profit"))
    fig_brand.update_traces(marker_line_color="#ffffff", marker_line_width=1.5)
    fig_brand.update_xaxes(tickangle=-28)

    # Customers by member card
    member = filtered.groupby("member_card", as_index=False)["customer_id"].nunique()
    fig_member = px.pie(member, names="member_card", values="customer_id", title="Customers by Member Card")
    fig_member.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#f8fafc",
        font={"family": "Plus Jakarta Sans, Segoe UI, sans-serif", "color": "#0f172a"},
        colorway=CHART_COLORS,
        height=420,
        margin={"l": 24, "r": 24, "t": 80, "b": 24},
        legend={"orientation": "h", "yanchor": "bottom", "y": -0.12, "xanchor": "center", "x": 0.5},
    )

    # Sales by education
    by_education = filtered.groupby("education", as_index=False)["sales"].sum().sort_values("sales", ascending=False)
    fig_education = themed_figure(px.bar(by_education, x="education", y="sales", title="Sales by Education"))
    fig_education.update_traces(marker_line_color="#ffffff", marker_line_width=1.5)
    fig_education.update_xaxes(tickangle=-28)

    # Top occupations
    by_occupation = (
        filtered.groupby("occupation", as_index=False)["sales"]
        .sum()
        .sort_values("sales", ascending=False)
        .head(10)
    )
    fig_occupation = themed_figure(px.bar(by_occupation, x="occupation", y="sales", title="Top 10 Occupations by Sales"))
    fig_occupation.update_traces(marker_line_color="#ffffff", marker_line_width=1.5)
    fig_occupation.update_xaxes(tickangle=-28)

    # Top stores
    by_store = (
        filtered.groupby("store_name", as_index=False)["sales"]
        .sum()
        .sort_values("sales", ascending=False)
        .head(10)
    )
    fig_store = themed_figure(px.bar(by_store, x="store_name", y="sales", title="Top 10 Stores by Sales"))
    fig_store.update_traces(marker_line_color="#ffffff", marker_line_width=1.5)
    fig_store.update_xaxes(tickangle=-28)

    # Sales by store type
    by_store_type = (
        filtered.groupby("store_type", as_index=False)["sales"]
        .sum()
        .sort_values("sales", ascending=False)
    )
    fig_store_type = themed_figure(px.bar(by_store_type, x="store_type", y="sales", title="Sales by Store Type"))
    fig_store_type.update_traces(marker_line_color="#ffffff", marker_line_width=1.5)

    # Sales per customer by occupation
    occupation_value = (
        filtered.groupby("occupation", as_index=False)
        .agg(
            sales=("sales", "sum"),
            active_customers=("customer_id", "nunique"),
            transactions=("customer_id", "size"),
        )
        .sort_values("sales", ascending=False)
    )
    occupation_value["active_customers"] = occupation_value["active_customers"].replace(0, 1)
    occupation_value["sales_per_customer"] = occupation_value["sales"] / occupation_value["active_customers"]
    occupation_value["transactions_per_customer"] = occupation_value["transactions"] / occupation_value["active_customers"]
    occupation_value = occupation_value.sort_values("sales_per_customer", ascending=True)
    occupation_order = occupation_value["occupation"].tolist()[::-1]

    fig_sales_per_customer = themed_figure(
        px.bar(
            occupation_value,
            x="sales_per_customer",
            y="occupation",
            orientation="h",
            title="Sales per Active Customer by Occupation",
            hover_data={
                "sales": ":.2f",
                "active_customers": True,
                "transactions_per_customer": ":.2f",
                "sales_per_customer": ":.2f",
            },
        )
    )
    fig_sales_per_customer.update_layout(xaxis_title="Sales per Active Customer", yaxis_title="Occupation")

    # Member card mix by occupation
    occupation_member_mix = (
        filtered.groupby(["occupation", "member_card"], as_index=False)["customer_id"]
        .nunique()
        .rename(columns={"customer_id": "customers"})
    )
    occupation_member_mix["share_pct"] = (
        occupation_member_mix["customers"]
        / occupation_member_mix.groupby("occupation")["customers"].transform("sum")
        * 100
    )

    fig_member_mix = themed_figure(
        px.bar(
            occupation_member_mix,
            x="occupation",
            y="share_pct",
            color="member_card",
            category_orders={"occupation": occupation_order},
            title="Member Card Mix by Occupation",
            labels={"share_pct": "Customer Share (%)", "member_card": "Member Card"},
        )
    )
    fig_member_mix.update_layout(barmode="stack", xaxis_title="Occupation", yaxis_title="Customer Share (%)")
    fig_member_mix.update_xaxes(tickangle=-28)

    # Occupation x region heatmap using graph_objects instead of px.imshow for Render stability
    occupation_region = (
        filtered.groupby(["occupation", "sales_region"], as_index=False)
        .agg(
            sales=("sales", "sum"),
            active_customers=("customer_id", "nunique"),
        )
    )
    occupation_region["active_customers"] = occupation_region["active_customers"].replace(0, 1)
    occupation_region["sales_per_customer"] = occupation_region["sales"] / occupation_region["active_customers"]

    occupation_region_heatmap = (
        occupation_region.pivot_table(
            index="occupation",
            columns="sales_region",
            values="sales_per_customer",
            aggfunc="sum",
            fill_value=0,
        )
        .reindex(occupation_order)
        .fillna(0)
    )

    fig_region_heatmap = go.Figure(
        data=go.Heatmap(
            z=occupation_region_heatmap.values,
            x=occupation_region_heatmap.columns,
            y=occupation_region_heatmap.index,
            colorscale="Blues",
            colorbar={"title": "Sales / Customer"},
            hovertemplate=(
                "Region: %{x}<br>"
                "Occupation: %{y}<br>"
                "Sales / Customer: $%{z:,.2f}<extra></extra>"
            ),
        )
    )
    fig_region_heatmap = themed_figure(fig_region_heatmap)
    fig_region_heatmap.update_layout(
        title="Occupation x Region Heatmap (Sales per Active Customer)",
        xaxis_title="Sales Region",
        yaxis_title="Occupation",
    )

    # Top products table
    table_df = top_products_table(filtered)
    table_data = table_df.to_dict("records")
    table_columns = [{"name": col.replace("_", " ").title(), "id": col} for col in table_df.columns]

    print("ABOUT TO RETURN FIGURES", flush=True)

    return (
        cards,
        fig_monthly,
        fig_monthly_trend,
        fig_day_of_week,
        fig_region,
        fig_brand,
        fig_member,
        fig_education,
        fig_occupation,
        fig_store,
        fig_store_type,
        fig_sales_per_customer,
        fig_member_mix,
        fig_region_heatmap,
        table_data,
        table_columns,
    )


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=int(os.environ.get("PORT", 8050)))
