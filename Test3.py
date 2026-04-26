import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, Input, Output, dash_table, dcc, html

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"


def read_data(filename, usecols=None):
    return pd.read_csv(DATA_DIR / filename, usecols=usecols)


transactions_1997 = read_data(
    "MavenMarket_Transactions_1997.csv",
    usecols=["transaction_date", "product_id", "customer_id", "store_id", "quantity"],
)

transactions_1998 = read_data(
    "MavenMarket_Transactions_1998.csv",
    usecols=["transaction_date", "product_id", "customer_id", "store_id", "quantity"],
)

customers = read_data(
    "MavenMarket_Customers.csv",
    usecols=["customer_id", "gender", "education", "occupation", "member_card"],
)

products = read_data(
    "MavenMarket_Products.csv",
    usecols=["product_id", "product_name", "product_brand", "product_retail_price", "product_cost"],
)

stores = read_data(
    "MavenMarket_Stores.csv",
    usecols=["store_id", "region_id", "store_name", "store_type"],
)

regions = read_data(
    "MavenMarket_Regions.csv",
    usecols=["region_id", "sales_region"],
)

transactions = pd.concat([transactions_1997, transactions_1998], ignore_index=True)
del transactions_1997, transactions_1998

transactions["transaction_date"] = pd.to_datetime(transactions["transaction_date"], errors="coerce")
transactions["year"] = transactions["transaction_date"].dt.year.astype("int16")
transactions["month"] = transactions["transaction_date"].dt.month.astype("int8")
transactions["month_name"] = transactions["transaction_date"].dt.strftime("%b")
transactions["weekday_short"] = transactions["transaction_date"].dt.strftime("%a")
transactions["weekday_name"] = transactions["transaction_date"].dt.day_name()
transactions["week_start"] = transactions["transaction_date"] - pd.to_timedelta(
    transactions["transaction_date"].dt.weekday, unit="D"
)

for frame, columns in [
    (transactions, ["product_id", "customer_id", "store_id"]),
    (customers, ["customer_id"]),
    (products, ["product_id"]),
    (stores, ["store_id", "region_id"]),
    (regions, ["region_id"]),
]:
    for column in columns:
        frame[column] = frame[column].astype(str).str.strip()

stores = stores.merge(regions, on="region_id", how="left")
del regions

df = transactions.merge(customers, on="customer_id", how="left")
df = df.merge(products, on="product_id", how="left")
df = df.merge(stores, on="store_id", how="left")
del transactions, customers, products, stores

df["sales"] = (df["quantity"] * df["product_retail_price"]).astype("float32")
df["cost"] = (df["quantity"] * df["product_cost"]).astype("float32")
df["profit"] = (df["sales"] - df["cost"]).astype("float32")

category_columns = [
    "sales_region",
    "gender",
    "education",
    "occupation",
    "member_card",
    "product_name",
    "product_brand",
    "store_name",
    "store_type",
    "month_name",
    "weekday_short",
    "weekday_name",
]

for column in category_columns:
    df[column] = df[column].fillna("Unknown").astype(str).str.strip().astype("category")

print("Running Test2.py", flush=True)
print("Rows loaded:", len(df), flush=True)
print("Total sales:", round(float(df["sales"].sum()), 2), flush=True)

app = Dash(__name__, suppress_callback_exceptions=True)
server = app.server
app.title = "Maven Market Dashboard"

DEFAULT_GRAPH_CONFIG = {"displayModeBar": True, "displaylogo": False, "responsive": True}
CHART_COLORS = ["#0f766e", "#f97316", "#0891b2", "#7c3aed", "#dc2626", "#65a30d"]


def themed_figure(fig, height=410):
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#f8fafc",
        colorway=CHART_COLORS,
        font={"family": "Plus Jakarta Sans, Segoe UI, sans-serif", "color": "#0f172a"},
        title={"x": 0.02, "xanchor": "left", "font": {"size": 19}},
        margin={"l": 44, "r": 22, "t": 68, "b": 54},
        height=height,
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
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
        font={"size": 15, "color": "#475569"},
    )
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    fig.update_layout(showlegend=False, title=title)
    return themed_figure(fig)


def graph(graph_id, title):
    return dcc.Graph(
        id=graph_id,
        figure=empty_figure(title),
        config=DEFAULT_GRAPH_CONFIG,
        style={"height": "420px"},
    )


def dropdown_options(series):
    return [{"label": str(value), "value": str(value)} for value in sorted(series.dropna().astype(str).unique())]


years = sorted(df["year"].dropna().astype(int).unique().tolist())

app.layout = html.Div(
    [
        html.Div(
            [
                html.P("Retail Intelligence", className="eyebrow"),
                html.H1("Maven Market Performance Dashboard"),
                html.P(
                    "Explore sales, profit, customer mix, and store performance across the Maven Market business.",
                    className="hero-subtitle",
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
                            options=[{"label": str(year), "value": year} for year in years],
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
                            options=dropdown_options(df["sales_region"]),
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
                            options=dropdown_options(df["gender"]),
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
                            options=dropdown_options(df["education"]),
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
                            options=dropdown_options(df["occupation"]),
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
                html.Div(graph("calendar_heatmap_chart", "Daily Sales Calendar Heatmap"), className="chart-card chart-card-wide"),
                html.Div(graph("monthly_sales_trend_chart", "Monthly Sales Trend"), className="chart-card"),
                html.Div(graph("day_of_week_chart", "Average Daily Sales by Day of Week"), className="chart-card"),
                html.Div(graph("sales_by_region_chart", "Sales by Region"), className="chart-card"),
                html.Div(graph("profit_by_brand_chart", "Top 10 Brands by Profit"), className="chart-card"),
                html.Div(graph("member_card_chart", "Customers by Member Card"), className="chart-card"),
                html.Div(graph("sales_by_education_chart", "Sales by Education"), className="chart-card"),
                html.Div(graph("sales_by_occupation_chart", "Top 10 Occupations by Sales"), className="chart-card"),
                html.Div(graph("top_store_sales_chart", "Top 10 Stores by Sales"), className="chart-card"),
                html.Div(graph("sales_by_store_type_chart", "Sales by Store Type"), className="chart-card"),
                html.Div(graph("sales_per_customer_occupation_chart", "Sales per Active Customer by Occupation"), className="chart-card"),
                html.Div(graph("occupation_member_mix_chart", "Member Card Mix by Occupation"), className="chart-card"),
                html.Div(graph("occupation_region_heatmap_chart", "Occupation x Region Heatmap"), className="chart-card"),
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


def filter_data(year_values, region_values, gender_values, education_values, occupation_values):
    mask = pd.Series(True, index=df.index)

    if year_values:
        mask &= df["year"].isin([int(value) for value in year_values])
    if region_values:
        mask &= df["sales_region"].astype(str).isin([str(value) for value in region_values])
    if gender_values:
        mask &= df["gender"].astype(str).isin([str(value) for value in gender_values])
    if education_values:
        mask &= df["education"].astype(str).isin([str(value) for value in education_values])
    if occupation_values:
        mask &= df["occupation"].astype(str).isin([str(value) for value in occupation_values])

    return df.loc[mask]


@app.callback(
    Output("kpi_cards", "children"),
    Output("calendar_heatmap_chart", "figure"),
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
    filtered = filter_data(year_values, region_values, gender_values, education_values, occupation_values)

    print("Callback started", flush=True)
    print("Filters:", year_values, region_values, gender_values, education_values, occupation_values, flush=True)
    print("Filtered rows:", len(filtered), flush=True)
    print("Total sales:", round(float(filtered["sales"].sum()), 2) if not filtered.empty else 0, flush=True)

    if filtered.empty:
        no_data = empty_figure("No data for selected filters")
        empty_card = html.Div(
            [html.P("No Results", className="kpi-label"), html.H2("Adjust Filters", className="kpi-value")],
            className="kpi-card",
        )
        return [empty_card], no_data, no_data, no_data, no_data, no_data, no_data, no_data, no_data, no_data, no_data, no_data, no_data, no_data, [], []

    cards_data = {
        "Total Sales": f"${float(filtered['sales'].sum()):,.2f}",
        "Total Profit": f"${float(filtered['profit'].sum()):,.2f}",
        "Total Quantity": f"{int(filtered['quantity'].sum()):,}",
        "Active Customers": f"{filtered['customer_id'].nunique():,}",
        "Active Stores": f"{filtered['store_id'].nunique():,}",
    }

    cards = [
        html.Div([html.P(label, className="kpi-label"), html.H2(value, className="kpi-value")], className="kpi-card")
        for label, value in cards_data.items()
    ]

    month_order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    weekday_order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    weekday_full_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    daily = filtered.groupby(
        [filtered["transaction_date"].dt.normalize(), "weekday_short", "week_start"],
        observed=True,
    )["sales"].sum().reset_index()
    daily = daily.rename(columns={"transaction_date": "date"})

    calendar_matrix = (
        daily.pivot_table(
            index="weekday_short",
            columns="week_start",
            values="sales",
            aggfunc="sum",
            fill_value=0,
            observed=True,
        )
        .reindex(weekday_order)
        .fillna(0)
    )

    fig_calendar = go.Figure(
        data=go.Heatmap(
            z=calendar_matrix.values,
            x=calendar_matrix.columns,
            y=calendar_matrix.index,
            colorscale=[
                [0.0, "#f7fcf9"],
                [0.2, "#d1fae5"],
                [0.4, "#86efac"],
                [0.6, "#34d399"],
                [0.8, "#059669"],
                [1.0, "#064e3b"],
            ],
            colorbar={"title": "Sales"},
            hovertemplate="Week of %{x|%b %d, %Y}<br>Day: %{y}<br>Sales: $%{z:,.2f}<extra></extra>",
        )
    )
    fig_calendar = themed_figure(fig_calendar, height=440)
    fig_calendar.update_layout(title="Daily Sales Calendar Heatmap", xaxis_title="Week Starting", yaxis_title="")
    fig_calendar.update_xaxes(dtick="M1", tickformat="%b<br>%Y")
    fig_calendar.update_yaxes(categoryorder="array", categoryarray=weekday_order)

    monthly = filtered.groupby(["year", "month", "month_name"], observed=True, as_index=False)["sales"].sum()
    monthly = monthly.sort_values(["year", "month"])
    fig_monthly = themed_figure(
        px.line(
            monthly,
            x="month_name",
            y="sales",
            color="year",
            markers=True,
            category_orders={"month_name": month_order},
            title="Monthly Sales Trend",
            labels={"month_name": "Month", "sales": "Sales", "year": "Year"},
        )
    )
    fig_monthly.update_traces(line={"width": 4}, marker={"size": 8})

    weekday = (
        filtered.groupby(["weekday_name", filtered["transaction_date"].dt.normalize()], observed=True)["sales"]
        .sum()
        .reset_index()
        .rename(columns={"transaction_date": "date"})
    )
    weekday_summary = weekday.groupby("weekday_name", observed=True, as_index=False).agg(
        total_sales=("sales", "sum"),
        active_days=("date", "nunique"),
    )
    weekday_summary["avg_daily_sales"] = weekday_summary["total_sales"] / weekday_summary["active_days"]
    weekday_summary["weekday_name"] = pd.Categorical(
        weekday_summary["weekday_name"], categories=weekday_full_order, ordered=True
    )
    weekday_summary = weekday_summary.sort_values("weekday_name")

    fig_weekday = themed_figure(
        px.bar(
            weekday_summary,
            x="weekday_name",
            y="avg_daily_sales",
            title="Average Daily Sales by Day of Week",
            labels={"weekday_name": "Day of Week", "avg_daily_sales": "Average Daily Sales"},
            hover_data={"total_sales": ":.2f", "active_days": True, "avg_daily_sales": ":.2f"},
        )
    )
    fig_weekday.update_traces(marker_color="#0f766e", marker_line_color="#ffffff", marker_line_width=1.5)

    region_sales = (
        filtered.groupby("sales_region", observed=True, as_index=False)["sales"]
        .sum()
        .sort_values("sales", ascending=False)
    )
    fig_region = themed_figure(px.bar(region_sales, x="sales_region", y="sales", title="Sales by Region"))
    fig_region.update_traces(marker_line_color="#ffffff", marker_line_width=1.5)

    brand_profit = (
        filtered.groupby("product_brand", observed=True, as_index=False)["profit"]
        .sum()
        .sort_values("profit", ascending=False)
        .head(10)
    )
    fig_brand = themed_figure(px.bar(brand_profit, x="product_brand", y="profit", title="Top 10 Brands by Profit"))
    fig_brand.update_traces(marker_line_color="#ffffff", marker_line_width=1.5)
    fig_brand.update_xaxes(tickangle=-30)

    member = filtered.groupby("member_card", observed=True, as_index=False)["customer_id"].nunique()
    fig_member = px.pie(member, names="member_card", values="customer_id", title="Customers by Member Card")
    fig_member.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#f8fafc",
        colorway=CHART_COLORS,
        font={"family": "Plus Jakarta Sans, Segoe UI, sans-serif", "color": "#0f172a"},
        height=410,
        margin={"l": 24, "r": 24, "t": 78, "b": 24},
        legend={"orientation": "h", "yanchor": "bottom", "y": -0.12, "xanchor": "center", "x": 0.5},
    )

    education_sales = (
        filtered.groupby("education", observed=True, as_index=False)["sales"]
        .sum()
        .sort_values("sales", ascending=False)
    )
    fig_education = themed_figure(px.bar(education_sales, x="education", y="sales", title="Sales by Education"))
    fig_education.update_traces(marker_line_color="#ffffff", marker_line_width=1.5)
    fig_education.update_xaxes(tickangle=-25)

    occupation_sales = (
        filtered.groupby("occupation", observed=True, as_index=False)["sales"]
        .sum()
        .sort_values("sales", ascending=False)
        .head(10)
    )
    fig_occupation = themed_figure(
        px.bar(occupation_sales, x="occupation", y="sales", title="Top 10 Occupations by Sales")
    )
    fig_occupation.update_traces(marker_line_color="#ffffff", marker_line_width=1.5)
    fig_occupation.update_xaxes(tickangle=-30)

    store_sales = (
        filtered.groupby("store_name", observed=True, as_index=False)["sales"]
        .sum()
        .sort_values("sales", ascending=False)
        .head(10)
    )
    fig_store = themed_figure(px.bar(store_sales, x="store_name", y="sales", title="Top 10 Stores by Sales"))
    fig_store.update_traces(marker_line_color="#ffffff", marker_line_width=1.5)
    fig_store.update_xaxes(tickangle=-30)

    store_type_sales = (
        filtered.groupby("store_type", observed=True, as_index=False)["sales"]
        .sum()
        .sort_values("sales", ascending=False)
    )
    fig_store_type = themed_figure(
        px.bar(store_type_sales, x="store_type", y="sales", title="Sales by Store Type")
    )
    fig_store_type.update_traces(marker_line_color="#ffffff", marker_line_width=1.5)

    occupation_value = (
        filtered.groupby("occupation", observed=True, as_index=False)
        .agg(sales=("sales", "sum"), active_customers=("customer_id", "nunique"), transactions=("customer_id", "size"))
        .sort_values("sales", ascending=False)
        .head(12)
    )
    occupation_value["active_customers"] = occupation_value["active_customers"].replace(0, 1)
    occupation_value["sales_per_customer"] = occupation_value["sales"] / occupation_value["active_customers"]
    occupation_value["transactions_per_customer"] = occupation_value["transactions"] / occupation_value["active_customers"]
    occupation_value = occupation_value.sort_values("sales_per_customer", ascending=True)
    occupation_order = occupation_value["occupation"].astype(str).tolist()[::-1]

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

    occupation_member = filtered[filtered["occupation"].astype(str).isin(occupation_order)]
    member_mix = (
        occupation_member.groupby(["occupation", "member_card"], observed=True, as_index=False)["customer_id"]
        .nunique()
        .rename(columns={"customer_id": "customers"})
    )
    member_mix["share_pct"] = member_mix["customers"] / member_mix.groupby("occupation", observed=True)["customers"].transform("sum") * 100

    fig_member_mix = themed_figure(
        px.bar(
            member_mix,
            x="occupation",
            y="share_pct",
            color="member_card",
            category_orders={"occupation": occupation_order},
            title="Member Card Mix by Occupation",
            labels={"share_pct": "Customer Share (%)", "member_card": "Member Card"},
        )
    )
    fig_member_mix.update_layout(barmode="stack", xaxis_title="Occupation", yaxis_title="Customer Share (%)")
    fig_member_mix.update_xaxes(tickangle=-30)

    occupation_region = (
        occupation_member.groupby(["occupation", "sales_region"], observed=True, as_index=False)
        .agg(sales=("sales", "sum"), active_customers=("customer_id", "nunique"))
    )
    occupation_region["active_customers"] = occupation_region["active_customers"].replace(0, 1)
    occupation_region["sales_per_customer"] = occupation_region["sales"] / occupation_region["active_customers"]

    occupation_region_matrix = (
        occupation_region.pivot_table(
            index="occupation",
            columns="sales_region",
            values="sales_per_customer",
            aggfunc="sum",
            fill_value=0,
            observed=True,
        )
        .reindex(occupation_order)
        .fillna(0)
    )

    fig_region_heatmap = go.Figure(
        data=go.Heatmap(
            z=occupation_region_matrix.values,
            x=occupation_region_matrix.columns,
            y=occupation_region_matrix.index,
            colorscale="Blues",
            colorbar={"title": "Sales / Customer"},
            hovertemplate="Region: %{x}<br>Occupation: %{y}<br>Sales / Customer: $%{z:,.2f}<extra></extra>",
        )
    )
    fig_region_heatmap = themed_figure(fig_region_heatmap)
    fig_region_heatmap.update_layout(
        title="Occupation x Region Heatmap (Sales per Active Customer)",
        xaxis_title="Sales Region",
        yaxis_title="Occupation",
    )

    top_products = (
        filtered.groupby(["product_name", "product_brand"], observed=True, as_index=False)
        .agg(sales=("sales", "sum"), profit=("profit", "sum"), quantity=("quantity", "sum"))
        .sort_values("sales", ascending=False)
        .head(15)
    )
    top_products["sales"] = top_products["sales"].round(2)
    top_products["profit"] = top_products["profit"].round(2)
    table_data = top_products.to_dict("records")
    table_columns = [{"name": column.replace("_", " ").title(), "id": column} for column in top_products.columns]

    print("Returning figures", flush=True)

    return (
        cards,
        fig_calendar,
        fig_monthly,
        fig_weekday,
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
