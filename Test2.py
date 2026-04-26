import os
from pathlib import Path

import pandas as pd
import plotly.express as px
from dash import Dash, Input, Output, dash_table, dcc, html

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"


def read_csv(filename, usecols=None):
    return pd.read_csv(DATA_DIR / filename, usecols=usecols)


transactions_1997 = read_csv(
    "MavenMarket_Transactions_1997.csv",
    usecols=["transaction_date", "product_id", "customer_id", "store_id", "quantity"],
)
transactions_1998 = read_csv(
    "MavenMarket_Transactions_1998.csv",
    usecols=["transaction_date", "product_id", "customer_id", "store_id", "quantity"],
)

customers = read_csv(
    "MavenMarket_Customers.csv",
    usecols=["customer_id", "gender", "education", "occupation", "member_card"],
)

products = read_csv(
    "MavenMarket_Products.csv",
    usecols=["product_id", "product_name", "product_brand", "product_retail_price", "product_cost"],
)

stores = read_csv(
    "MavenMarket_Stores.csv",
    usecols=["store_id", "region_id", "store_name", "store_type"],
)

regions = read_csv(
    "MavenMarket_Regions.csv",
    usecols=["region_id", "sales_region"],
)

transactions = pd.concat([transactions_1997, transactions_1998], ignore_index=True)
del transactions_1997, transactions_1998

transactions["transaction_date"] = pd.to_datetime(transactions["transaction_date"], errors="coerce")
transactions["year"] = transactions["transaction_date"].dt.year.astype("int16")
transactions["month"] = transactions["transaction_date"].dt.month.astype("int8")
transactions["month_name"] = transactions["transaction_date"].dt.strftime("%b")

for frame, key_cols in [
    (transactions, ["product_id", "customer_id", "store_id"]),
    (customers, ["customer_id"]),
    (products, ["product_id"]),
    (stores, ["store_id", "region_id"]),
    (regions, ["region_id"]),
]:
    for col in key_cols:
        frame[col] = frame[col].astype(str).str.strip()

stores = stores.merge(regions, on="region_id", how="left")
del regions

df = transactions.merge(customers, on="customer_id", how="left")
df = df.merge(products, on="product_id", how="left")
df = df.merge(stores, on="store_id", how="left")
del transactions, customers, products, stores

df["sales"] = df["quantity"] * df["product_retail_price"]
df["cost"] = df["quantity"] * df["product_cost"]
df["profit"] = df["sales"] - df["cost"]

text_cols = [
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
]

for col in text_cols:
    df[col] = df[col].fillna("Unknown").astype("category")

print("Running Test2.py", flush=True)
print("Rows loaded:", len(df), flush=True)
print("Total sales:", round(df["sales"].sum(), 2), flush=True)

app = Dash(__name__, suppress_callback_exceptions=True)
server = app.server
app.title = "Maven Market Dashboard"

DEFAULT_GRAPH_CONFIG = {"displayModeBar": True, "displaylogo": False, "responsive": True}
CHART_COLORS = ["#0f766e", "#f97316", "#0891b2", "#7c3aed", "#dc2626", "#65a30d"]


def themed_figure(fig, height=390):
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
    fig = px.scatter(title=title)
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
    return themed_figure(fig)


def graph(graph_id, title):
    return dcc.Graph(
        id=graph_id,
        figure=empty_figure(title),
        config=DEFAULT_GRAPH_CONFIG,
        style={"height": "400px"},
    )


def dropdown_options(series):
    return [{"label": str(x), "value": str(x)} for x in sorted(series.dropna().astype(str).unique())]


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
                html.Div(graph("monthly_sales_trend_chart", "Monthly Sales Trend"), className="chart-card chart-card-wide"),
                html.Div(graph("sales_by_region_chart", "Sales by Region"), className="chart-card"),
                html.Div(graph("top_products_chart", "Top 15 Products by Sales"), className="chart-card"),
                html.Div(graph("profit_by_brand_chart", "Top 10 Brands by Profit"), className="chart-card"),
                html.Div(graph("sales_by_store_type_chart", "Sales by Store Type"), className="chart-card"),
                html.Div(graph("sales_by_education_chart", "Sales by Education"), className="chart-card"),
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
        mask &= df["year"].isin([int(y) for y in year_values])
    if region_values:
        mask &= df["sales_region"].astype(str).isin([str(x) for x in region_values])
    if gender_values:
        mask &= df["gender"].astype(str).isin([str(x) for x in gender_values])
    if education_values:
        mask &= df["education"].astype(str).isin([str(x) for x in education_values])
    if occupation_values:
        mask &= df["occupation"].astype(str).isin([str(x) for x in occupation_values])

    return df.loc[mask]


@app.callback(
    Output("kpi_cards", "children"),
    Output("monthly_sales_trend_chart", "figure"),
    Output("sales_by_region_chart", "figure"),
    Output("top_products_chart", "figure"),
    Output("profit_by_brand_chart", "figure"),
    Output("sales_by_store_type_chart", "figure"),
    Output("sales_by_education_chart", "figure"),
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
    print("Total sales:", round(filtered["sales"].sum(), 2) if not filtered.empty else 0, flush=True)

    if filtered.empty:
        no_data = empty_figure("No data for selected filters")
        empty_card = html.Div(
            [html.P("No Results", className="kpi-label"), html.H2("Adjust Filters", className="kpi-value")],
            className="kpi-card",
        )
        return [empty_card], no_data, no_data, no_data, no_data, no_data, no_data, [], []

    cards_data = {
        "Total Sales": f"${filtered['sales'].sum():,.2f}",
        "Total Profit": f"${filtered['profit'].sum():,.2f}",
        "Total Quantity": f"{filtered['quantity'].sum():,.0f}",
        "Active Customers": f"{filtered['customer_id'].nunique():,}",
        "Active Stores": f"{filtered['store_id'].nunique():,}",
    }

    cards = [
        html.Div([html.P(label, className="kpi-label"), html.H2(value, className="kpi-value")], className="kpi-card")
        for label, value in cards_data.items()
    ]

    month_order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

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
        ),
        height=420,
    )
    fig_monthly.update_traces(line={"width": 4}, marker={"size": 8})

    region_sales = (
        filtered.groupby("sales_region", observed=True, as_index=False)["sales"]
        .sum()
        .sort_values("sales", ascending=False)
    )
    fig_region = themed_figure(px.bar(region_sales, x="sales_region", y="sales", title="Sales by Region"))

    top_products = (
        filtered.groupby(["product_name", "product_brand"], observed=True, as_index=False)
        .agg(sales=("sales", "sum"), profit=("profit", "sum"), quantity=("quantity", "sum"))
        .sort_values("sales", ascending=False)
        .head(15)
    )
    fig_products = themed_figure(px.bar(top_products, x="product_name", y="sales", title="Top 15 Products by Sales"))
    fig_products.update_xaxes(tickangle=-35)

    brand_profit = (
        filtered.groupby("product_brand", observed=True, as_index=False)["profit"]
        .sum()
        .sort_values("profit", ascending=False)
        .head(10)
    )
    fig_brand = themed_figure(px.bar(brand_profit, x="product_brand", y="profit", title="Top 10 Brands by Profit"))
    fig_brand.update_xaxes(tickangle=-35)

    store_type = (
        filtered.groupby("store_type", observed=True, as_index=False)["sales"]
        .sum()
        .sort_values("sales", ascending=False)
    )
    fig_store_type = themed_figure(px.bar(store_type, x="store_type", y="sales", title="Sales by Store Type"))

    education = (
        filtered.groupby("education", observed=True, as_index=False)["sales"]
        .sum()
        .sort_values("sales", ascending=False)
    )
    fig_education = themed_figure(px.bar(education, x="education", y="sales", title="Sales by Education"))
    fig_education.update_xaxes(tickangle=-25)

    table_df = top_products.copy()
    table_df["sales"] = table_df["sales"].round(2)
    table_df["profit"] = table_df["profit"].round(2)
    table_data = table_df.to_dict("records")
    table_columns = [{"name": col.replace("_", " ").title(), "id": col} for col in table_df.columns]

    print("Returning figures", flush=True)

    return (
        cards,
        fig_monthly,
        fig_region,
        fig_products,
        fig_brand,
        fig_store_type,
        fig_education,
        table_data,
        table_columns,
    )


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=int(os.environ.get("PORT", 8050)))
