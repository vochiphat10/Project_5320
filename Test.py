%pip install dash plotly pandas
%pip install -U nbformat ipykernel plotly

#import packages
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html, dash_table, Input, Output

#import datasets
customers = pd.read_csv("data/MavenMarket_Customers.csv")
products = pd.read_csv("data/MavenMarket_Products.csv")
regions = pd.read_csv("data/MavenMarket_Regions.csv")
stores = pd.read_csv("data/MavenMarket_Stores.csv")
calendar = pd.read_csv("data/MavenMarket_Calendar.csv")
trans_1997 = pd.read_csv("data/MavenMarket_Transactions_1997.csv")
trans_1998 = pd.read_csv("data/MavenMarket_Transactions_1998.csv")
returns = pd.read_csv("data/MavenMarket_Returns_1997-1998.csv")

#data preprocessing
def clean_columns(df):
    df = df.copy()
    df.columns = (
        df.columns.str.strip()
        .str.lower()
        .str.replace(" ", "_")
        .str.replace(r"[^\w]", "", regex=True)
    )
    return df

customers = clean_columns(customers)
products = clean_columns(products)
regions = clean_columns(regions)
stores = clean_columns(stores)
calendar = clean_columns(calendar)
trans_1997 = clean_columns(trans_1997)
trans_1998 = clean_columns(trans_1998)
returns = clean_columns(returns)

#data transformation and aggregation
transactions = pd.concat([trans_1997, trans_1998], ignore_index=True)

calendar["date"] = pd.to_datetime(calendar["date"], errors="coerce")
calendar["year"] = calendar["date"].dt.year
calendar["month"] = calendar["date"].dt.month
calendar["month_name"] = calendar["date"].dt.strftime("%b")
calendar["weekday_name"] = calendar["date"].dt.strftime("%a")
calendar["week_start"] = calendar["date"] - pd.to_timedelta(calendar["date"].dt.weekday, unit="D")

transactions["transaction_date"] = pd.to_datetime(
    transactions["transaction_date"], errors="coerce"
)

transactions["year"] = transactions["transaction_date"].dt.year
transactions["month"] = transactions["transaction_date"].dt.month
transactions["month_name"] = transactions["transaction_date"].dt.strftime("%b")
transactions["quarter"] = transactions["transaction_date"].dt.quarter

returns["return_date"] = pd.to_datetime(returns["return_date"], errors="coerce")
returns["year"] = returns["return_date"].dt.year
returns["month"] = returns["return_date"].dt.month
returns["month_name"] = returns["return_date"].dt.strftime("%b")

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
        df_obj[col] = df_obj[col].astype(str)

#joining dataset on keys 
stores_regions = stores.merge(regions, on="region_id", how="left")

df = transactions.merge(customers, on="customer_id", how="left")
df = df.merge(products, on="product_id", how="left")
df = df.merge(stores_regions, on="store_id", how="left")

returns_df = returns.merge(products, on="product_id", how="left")
returns_df = returns_df.merge(stores_regions, on="store_id", how="left")
returns_df = returns_df.rename(columns={"quantity": "return_quantity"})

#define main metrics
df["sales"] = df["quantity"] * df["product_retail_price"]
df["cost"] = df["quantity"] * df["product_cost"]
df["profit"] = df["sales"] - df["cost"]

#define filters attributes
def apply_filters(df, years=None, regions=None, genders=None, educations=None, occupations=None):
    filtered = df.copy()

    if years:
        filtered = filtered[filtered["year"].isin(years)]

    if regions and "sales_region" in filtered.columns:
        filtered = filtered[filtered["sales_region"].isin(regions)]

    if genders and "gender" in filtered.columns:
        filtered = filtered[filtered["gender"].isin(genders)]

    if educations and "education" in filtered.columns:
        filtered = filtered[filtered["education"].isin(educations)]

    if occupations and "occupation" in filtered.columns:
        filtered = filtered[filtered["occupation"].isin(occupations)]

    return filtered

#kpi cards
def kpi_summary(df):
    return {
        "Total Sales": f"${df['sales'].sum():,.2f}",
        "Total Profit": f"${df['profit'].sum():,.2f}",
        "Total Quantity": f"{df['quantity'].sum():,.0f}",
        "Active Customers": f"{df['customer_id'].nunique():,}",
        "Active Stores": f"{df['store_id'].nunique():,}",
    }

#top product table
def top_products_table(df):
    result = (
        df.groupby(["product_name", "product_brand"], as_index=False)[["sales", "profit", "quantity"]]
        .sum()
        .sort_values("sales", ascending=False)
        .head(15)
    )
    result["sales"] = result["sales"].round(2)
    result["profit"] = result["profit"].round(2)
    return result

#create dashapp
app = Dash(__name__)
app.title = "Maven Market Dashboard"

CHART_COLORS = ["#0f766e", "#f97316", "#0891b2", "#7c3aed", "#dc2626", "#65a30d"]
DEFAULT_GRAPH_CONFIG = {
    "displayModeBar": True,
    "displaylogo": True,
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
    )
    fig.update_xaxes(showgrid=False, zeroline=False, linecolor="#cbd5e1")
    fig.update_yaxes(gridcolor="rgba(148,163,184,0.20)", zeroline=False)
    return fig

years = sorted(df["year"].dropna().astype(int).unique().tolist())
regions_list = sorted(df["sales_region"].dropna().astype(str).unique().tolist()) if "sales_region" in df.columns else []
genders = sorted(df["gender"].dropna().astype(str).unique().tolist()) if "gender" in df.columns else []
educations = sorted(df["education"].dropna().astype(str).unique().tolist()) if "education" in df.columns else []
occupations = sorted(df["occupation"].dropna().astype(str).unique().tolist()) if "occupation" in df.columns else []

app.layout = html.Div([
    html.Div([
        html.Div([
            html.P("Retail Intelligence", className="eyebrow"),
            html.H1("Maven Market Performance Dashboard"),
            html.P(
                "Explore sales, profit, customer mix, and store performance across the Maven Market business.",
                className="hero-subtitle",
            ),
        ]),
    ], className="hero-section"),

    html.Div([
        html.Div([
            html.Label("Year"),
            dcc.Dropdown(
                id="year_filter",
                options=[{"label": str(y), "value": y} for y in years],
                value=years,
                multi=True,
                placeholder="Select year",
            ),
        ], className="filter-field"),
        html.Div([
            html.Label("Region"),
            dcc.Dropdown(
                id="region_filter",
                options=[{"label": r, "value": r} for r in regions_list],
                value=[],
                multi=True,
                placeholder="Select region",
            ),
        ], className="filter-field"),
        html.Div([
            html.Label("Gender"),
            dcc.Dropdown(
                id="gender_filter",
                options=[{"label": g, "value": g} for g in genders],
                value=[],
                multi=True,
                placeholder="Select gender",
            ),
        ], className="filter-field"),
        html.Div([
            html.Label("Education"),
            dcc.Dropdown(
                id="education_filter",
                options=[{"label": e, "value": e} for e in educations],
                value=[],
                multi=True,
                placeholder="Select education",
            ),
        ], className="filter-field"),
        html.Div([
            html.Label("Occupation"),
            dcc.Dropdown(
                id="occupation_filter",
                options=[{"label": o, "value": o} for o in occupations],
                value=[],
                multi=True,
                placeholder="Select occupation",
            ),
        ], className="filter-field"),
    ], className="filter-panel"),

    html.Div(id="kpi_cards", className="kpi-grid"),

    html.Div([
        html.Div(dcc.Graph(id="monthly_sales_chart", config=DEFAULT_GRAPH_CONFIG), className="chart-card chart-card-wide"),
        html.Div(dcc.Graph(id="monthly_sales_trend_chart", config=DEFAULT_GRAPH_CONFIG), className="chart-card"),
        html.Div(dcc.Graph(id="day_of_week_chart", config=DEFAULT_GRAPH_CONFIG), className="chart-card"),
        html.Div(dcc.Graph(id="sales_by_region_chart", config=DEFAULT_GRAPH_CONFIG), className="chart-card"),
        html.Div(dcc.Graph(id="profit_by_brand_chart", config=DEFAULT_GRAPH_CONFIG), className="chart-card"),
        html.Div(dcc.Graph(id="member_card_chart", config=DEFAULT_GRAPH_CONFIG), className="chart-card"),
        html.Div(dcc.Graph(id="sales_by_education_chart", config=DEFAULT_GRAPH_CONFIG), className="chart-card"),
        html.Div(dcc.Graph(id="sales_by_occupation_chart", config=DEFAULT_GRAPH_CONFIG), className="chart-card"),
        html.Div(dcc.Graph(id="top_store_sales_chart", config=DEFAULT_GRAPH_CONFIG), className="chart-card"),
        html.Div(dcc.Graph(id="sales_by_store_type_chart", config=DEFAULT_GRAPH_CONFIG), className="chart-card"),
        html.Div(dcc.Graph(id="sales_per_customer_occupation_chart", config=DEFAULT_GRAPH_CONFIG), className="chart-card"),
        html.Div(dcc.Graph(id="occupation_member_mix_chart", config=DEFAULT_GRAPH_CONFIG), className="chart-card"),
        html.Div(dcc.Graph(id="occupation_region_heatmap_chart", config=DEFAULT_GRAPH_CONFIG), className="chart-card"),
    ], className="charts-grid"),

    html.Div([
        html.Div([
            html.P("Top Products", className="section-label"),
            html.H3("Top 15 Products by Sales"),
        ], className="section-heading"),
        dash_table.DataTable(
            id="top_products_table",
            page_size=15,
            sort_action="native",
            style_as_list_view=True,
            style_table={"overflowX": "auto"},
            style_header={"backgroundColor": "#e2e8f0", "border": "none", "color": "#0f172a", "fontWeight": "700", "padding": "14px"},
            style_cell={"backgroundColor": "rgba(255,255,255,0.92)", "border": "none", "color": "#334155", "fontFamily": "Plus Jakarta Sans, Segoe UI, sans-serif", "padding": "12px", "textAlign": "left"},
            style_data_conditional=[
                {"if": {"row_index": "odd"}, "backgroundColor": "#f8fafc"},
                {"if": {"state": "active"}, "backgroundColor": "#ecfeff", "border": "1px solid #14b8a6"},
            ],
        ),
    ], className="table-card"),
], className="app-shell")


#define callback layout
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

    if filtered.empty:
        empty_card = html.Div([
            html.P("No Results", className="kpi-label"),
            html.H2("Adjust Filters", className="kpi-value"),
        ], className="kpi-card")
        empty_fig = themed_figure(px.scatter(title="No data for selected filters"))
        empty_fig.add_annotation(
            text="Try widening the filters to bring the dashboard back to life.",
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            showarrow=False,
            font={"size": 16, "color": "#475569"},
        )
        empty_fig.update_xaxes(visible=False)
        empty_fig.update_yaxes(visible=False)
        empty_fig.update_layout(showlegend=False)
        return (
            [empty_card],
            empty_fig,
            empty_fig,
            empty_fig,
            empty_fig,
            empty_fig,
            empty_fig,
            empty_fig,
            empty_fig,
            empty_fig,
            empty_fig,
            empty_fig,
            empty_fig,
            empty_fig,
            [],
            [],
        )

    kpis = kpi_summary(filtered)
    cards = [
        html.Div([
            html.P(k, className="kpi-label"),
            html.H2(v, className="kpi-value"),
        ], className="kpi-card")
        for k, v in kpis.items()
    ]

    weekday_order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    month_order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    daily_sales = filtered.copy()
    daily_sales["date"] = daily_sales["transaction_date"].dt.normalize()
    daily_sales = daily_sales.groupby("date", as_index=False)["sales"].sum()

    calendar_view = calendar.copy()
    if year_values:
        calendar_view = calendar_view[calendar_view["year"].isin(year_values)]

    calendar_view = calendar_view.merge(daily_sales, on="date", how="left")
    calendar_view["sales"] = calendar_view["sales"].fillna(0)
    heatmap_data = (
        calendar_view.pivot_table(index="weekday_name", columns="week_start", values="sales", aggfunc="sum", fill_value=0)
        .reindex(weekday_order)
    )
    fig_monthly = go.Figure(
        data=go.Heatmap(
            z=heatmap_data.values,
            x=heatmap_data.columns,
            y=heatmap_data.index,
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
    fig_monthly = themed_figure(fig_monthly)
    fig_monthly.update_layout(title="Daily Sales Calendar Heatmap", xaxis_title="Week Starting", yaxis_title="")
    fig_monthly.update_xaxes(dtick="M1", tickformat="%b\n%Y")
    fig_monthly.update_yaxes(categoryorder="array", categoryarray=weekday_order)

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

    day_of_week = filtered.copy()
    day_of_week["weekday_name"] = day_of_week["transaction_date"].dt.day_name()
    day_of_week["date"] = day_of_week["transaction_date"].dt.normalize()
    weekday_full_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    weekday_summary = (
        day_of_week.groupby("weekday_name", as_index=False)
        .agg(
            total_sales=("sales", "sum"),
            active_days=("date", "nunique"),
            transactions=("sales", "size"),
        )
    )
    weekday_summary["avg_daily_sales"] = weekday_summary["total_sales"] / weekday_summary["active_days"]
    weekday_summary["weekday_name"] = pd.Categorical(weekday_summary["weekday_name"], categories=weekday_full_order, ordered=True)
    weekday_summary = weekday_summary.sort_values("weekday_name")
    fig_day_of_week = themed_figure(
        px.bar(
            weekday_summary,
            x="weekday_name",
            y="avg_daily_sales",
            title="Average Daily Sales by Day of Week",
            labels={"weekday_name": "Day of Week", "avg_daily_sales": "Average Daily Sales"},
            hover_data={"total_sales": ":.2f", "active_days": True, "transactions": True, "avg_daily_sales": ":.2f"},
        )
    )
    fig_day_of_week.update_traces(marker_color="#0f766e", marker_line_color="#ffffff", marker_line_width=1.5)

    by_region = filtered.groupby("sales_region", as_index=False)["sales"].sum()
    fig_region = themed_figure(px.bar(by_region, x="sales_region", y="sales", title="Sales by Region"))
    fig_region.update_traces(marker_line_color="#ffffff", marker_line_width=1.5)

    by_brand = (
        filtered.groupby("product_brand", as_index=False)["profit"]
        .sum()
        .sort_values("profit", ascending=False)
        .head(10)
    )
    fig_brand = themed_figure(px.bar(by_brand, x="product_brand", y="profit", title="Top 10 Brands by Profit"))
    fig_brand.update_traces(marker_line_color="#ffffff", marker_line_width=1.5)
    fig_brand.update_xaxes(tickangle=-28)

    member = filtered.groupby("member_card", as_index=False)["customer_id"].nunique()
    fig_member = px.pie(member, names="member_card", values="customer_id", title="Customers by Member Card")
    fig_member.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#f8fafc",
        font={"family": "Plus Jakarta Sans, Segoe UI, sans-serif", "color": "#0f172a"},
        colorway=CHART_COLORS,
        height=350,
        margin={"l": 24, "r": 24, "t": 80, "b": 24},
        legend={"orientation": "h", "yanchor": "bottom", "y": -0.12, "xanchor": "center", "x": 0.5},
    )

    by_education = (
        filtered.groupby("education", as_index=False)["sales"]
        .sum()
        .sort_values("sales", ascending=False)
    )
    fig_education = themed_figure(px.bar(by_education, x="education", y="sales", title="Sales by Education"))
    fig_education.update_traces(marker_line_color="#ffffff", marker_line_width=1.5)
    fig_education.update_xaxes(tickangle=-28)

    by_occupation = (
        filtered.groupby("occupation", as_index=False)["sales"]
        .sum()
        .sort_values("sales", ascending=False)
        .head(10)
    )
    fig_occupation = themed_figure(px.bar(by_occupation, x="occupation", y="sales", title="Top 10 Occupations by Sales"))
    fig_occupation.update_traces(marker_line_color="#ffffff", marker_line_width=1.5)
    fig_occupation.update_xaxes(tickangle=-28)

    by_store = (
        filtered.groupby("store_name", as_index=False)["sales"]
        .sum()
        .sort_values("sales", ascending=False)
        .head(10)
    )
    fig_store = themed_figure(px.bar(by_store, x="store_name", y="sales", title="Top 10 Stores by Sales"))
    fig_store.update_traces(marker_line_color="#ffffff", marker_line_width=1.5)
    fig_store.update_xaxes(tickangle=-28)

    by_store_type = (
        filtered.groupby("store_type", as_index=False)["sales"]
        .sum()
        .sort_values("sales", ascending=False)
    )
    fig_store_type = themed_figure(px.bar(by_store_type, x="store_type", y="sales", title="Sales by Store Type"))
    fig_store_type.update_traces(marker_line_color="#ffffff", marker_line_width=1.5)

    occupation_value = (
        filtered.groupby("occupation", as_index=False)
        .agg(
            sales=("sales", "sum"),
            active_customers=("customer_id", "nunique"),
            transactions=("customer_id", "size"),
        )
        .sort_values("sales", ascending=False)
    )
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

    occupation_region = (
        filtered.groupby(["occupation", "sales_region"], as_index=False)
        .agg(
            sales=("sales", "sum"),
            active_customers=("customer_id", "nunique"),
        )
    )
    occupation_region["sales_per_customer"] = occupation_region["sales"] / occupation_region["active_customers"]
    heatmap_data = (
        occupation_region.pivot(index="occupation", columns="sales_region", values="sales_per_customer")
        .fillna(0)
        .reindex(occupation_order)
    )
    fig_region_heatmap = themed_figure(
        px.imshow(
            heatmap_data,
            aspect="auto",
            color_continuous_scale="Blues",
            title="Occupation x Region Heatmap (Sales per Active Customer)",
            labels={"x": "Sales Region", "y": "Occupation", "color": "Sales / Customer"},
        )
    )
    fig_region_heatmap.update_layout(xaxis_title="Sales Region", yaxis_title="Occupation")

    table_df = top_products_table(filtered)
    table_data = table_df.to_dict("records")
    table_columns = [{"name": c.replace("_", " ").title(), "id": c} for c in table_df.columns]

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

#run dashapp on web browser
import webbrowser
from threading import Timer

def open_browser():
    webbrowser.open_new("http://127.0.0.1:8060/")

if __name__ == "__main__":
    Timer(1, open_browser).start()
    app.run(debug=True, port=8060)