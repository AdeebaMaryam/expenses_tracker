# expense_tracker_streamlit.py
# Expense tracker converted to match the income tracker UI & visuals.
from typing import Any, Dict
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# ------------------------------------------------------------
st.set_page_config(page_title="Expense Dashboard — Income-style", layout="wide")
st.sidebar.header("📂 Upload & Filters")

# Small user input requested earlier
thora_input = st.sidebar.text_input("Thora input (optional) — a short note or label:")

uploaded_file = st.sidebar.file_uploader("Upload expenses CSV or XLSX", type=["csv", "xlsx"])
if uploaded_file is None:
    st.sidebar.info("Upload a CSV/XLSX file (expenses data) to begin.")
    st.warning("⚠ Please upload a CSV/XLSX file from the sidebar to continue.")
    st.stop()

@st.cache_data
def load_data(file) -> pd.DataFrame:
    name = getattr(file, "name", "").lower()
    if name.endswith(".xlsx"):
        return pd.read_excel(file)
    else:
        # CSV
        try:
            file.seek(0)
        except Exception:
            pass
        return pd.read_csv(file)

# Load
try:
    df = load_data(uploaded_file)
except Exception as e:
    st.error(f"❌ Failed to read file: {e}")
    st.stop()

st.sidebar.markdown(f"**Loaded file:** `{getattr(uploaded_file, 'name', 'uploaded_file')}`")
st.write("🎯 Loaded CSV Successfully")
st.write("Rows:", df.shape[0], "Columns:", df.shape[1])

# Expected columns for expense dataset
expected_cols = ["date", "user_id", "expense_type", "vendor", "amount"]

missing = [c for c in expected_cols if c not in df.columns]
if missing:
    st.warning("⚠ The following recommended columns are missing from your file: " + ", ".join(missing))
    st.info("The app will continue with available columns, but some visuals/KPIs may not show as expected.")

# Date parsing
if "date" in df.columns:
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
else:
    st.error("❌ `date` column is required for time-based analysis. Please include it in the CSV.")
    st.stop()

# numeric conversions
if "amount" in df.columns:
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
else:
    st.error("❌ `amount` column is required. Please include it in the CSV.")
    st.stop()

# optional numeric columns
if "orders" in df.columns:
    df["orders"] = pd.to_numeric(df["orders"], errors="coerce")

df = df.sort_values("date").reset_index(drop=True)

# derived columns
df["weekday"] = df["date"].dt.day_name()
df["week"] = df["date"].dt.isocalendar().week
df["month"] = df["date"].dt.month_name()

# Sidebar filters: date range, expense_type, user
min_date = df["date"].min()
max_date = df["date"].max()
date_input_value: Any = st.sidebar.date_input("Select date range", [min_date.date(), max_date.date()])

try:
    if isinstance(date_input_value, (list, tuple)):
        if len(date_input_value) >= 2:
            start_date = pd.to_datetime(date_input_value[0])
            end_date = pd.to_datetime(date_input_value[1])
        elif len(date_input_value) == 1:
            start_date = pd.to_datetime(date_input_value[0])
            end_date = start_date
        else:
            start_date = pd.to_datetime(min_date)
            end_date = pd.to_datetime(max_date)
    else:
        start_date = pd.to_datetime(date_input_value)
        end_date = start_date
except Exception:
    start_date = pd.to_datetime(min_date)
    end_date = pd.to_datetime(max_date)

# expense_type filter
expense_types = df["expense_type"].dropna().unique().tolist() if "expense_type" in df.columns else []
selected_types = st.sidebar.multiselect("Expense type (select one or more)", options=expense_types, default=expense_types)

# user filter
user_search = None
if "user_id" in df.columns:
    user_list = df["user_id"].dropna().unique().tolist()
    user_search = st.sidebar.selectbox("Filter by user (optional)", options=["All"] + user_list)
else:
    st.sidebar.info("No `user_id` column found; skipping user filter.")

# Apply filters
df_filtered = df.copy()
try:
    df_filtered = df_filtered[(df_filtered["date"] >= start_date) & (df_filtered["date"] <= end_date)]
except Exception:
    st.error("Invalid date range selected. Showing full range.")
    df_filtered = df.copy()

if expense_types and selected_types:
    df_filtered = df_filtered[df_filtered["expense_type"].isin(selected_types)]

if user_search and user_search != "All":
    df_filtered = df_filtered[df_filtered["user_id"] == user_search]

if df_filtered.empty:
    st.warning("No data after applying filters. Try changing the filters.")
    st.stop()

# ---------------------------
# KPIs (Income-style)
# ---------------------------
st.markdown("---")
st.header("Key Performance Indicators")

total_spend = df_filtered["amount"].sum()
daily_group = df_filtered.groupby("date")["amount"].sum()
avg_daily = daily_group.mean() if not daily_group.empty else 0
if not daily_group.empty:
    best_day = daily_group.idxmax()
    best_day_amt = daily_group.max()
else:
    best_day = None
    best_day_amt = 0

st.markdown(f"""
<div style="display:flex;gap:20px;margin:20px 0;">
    <div style="padding:12px;background:#2E86C1;color:white;border-radius:8px;">
        <h3>Total Spend</h3><h2>₹{total_spend:,.0f}</h2>
    </div>
    <div style="padding:12px;background:#1ABC9C;color:white;border-radius:8px;">
        <h3>Average Daily</h3><h2>₹{avg_daily:,.0f}</h2>
    </div>
    <div style="padding:12px;background:#F39C12;color:white;border-radius:8px;">
        <h3>Max Day</h3><h2>{pd.Timestamp(best_day).date() if best_day is not None else 'N/A'} → ₹{best_day_amt:,.0f}</h2>
    </div>
</div>
""", unsafe_allow_html=True)

# ---------------------------
# Daily trend + 7-day moving average
# ---------------------------
st.markdown("---")
st.subheader("📅 Daily Spend + Moving Average")
daily = df_filtered.groupby("date")["amount"].sum().reset_index().sort_values("date")
daily["7d_avg"] = daily["amount"].rolling(7, min_periods=1).mean()

fig = go.Figure()
fig.add_trace(go.Scatter(x=daily["date"], y=daily["amount"], mode="lines+markers", name="Daily Spend", line=dict(color="#3498DB")))
fig.add_trace(go.Scatter(x=daily["date"], y=daily["7d_avg"], mode="lines", name="7-Day Avg", line=dict(color="#E74C3C", width=3)))
fig.update_layout(xaxis_title="Date", yaxis_title="Amount (₹)", legend=dict(orientation="h"))
st.plotly_chart(fig, use_container_width=True)

# ---------------------------
# Expense-type-wise trend (like platform-wise)
# ---------------------------
if "expense_type" in df_filtered.columns:
    st.markdown("---")
    st.subheader("📂 Expense-type-wise Trend")
    et_daily = df_filtered.groupby(["date", "expense_type"])["amount"].sum().reset_index()
    fig = px.line(et_daily, x="date", y="amount", color="expense_type", markers=True, title="Expense-type-wise Trend")
    fig.update_layout(xaxis_title="Date", yaxis_title="Amount (₹)")
    st.plotly_chart(fig, use_container_width=True)

# ---------------------------
# Heatmap: Weekday × Month
# ---------------------------
st.markdown("---")
st.subheader("🔥 Heatmap: Weekday × Month Spend")
heatmap = df_filtered.pivot_table(index="weekday", columns="month", values="amount", aggfunc="sum").reindex(index=["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"])
if heatmap.isnull().all().all():
    st.info("No data available to build heatmap (missing weekday/month values).")
else:
    fig = px.imshow(heatmap.fillna(0), aspect="auto", title="Heatmap: Weekday × Month Spend")
    fig.update_layout(xaxis_title="Month", yaxis_title="Day")
    st.plotly_chart(fig, use_container_width=True)

# ---------------------------
# Distribution & Boxplot
# ---------------------------
st.markdown("---")
st.subheader("📊 Distribution of Expenses")
fig_hist = px.histogram(df_filtered, x="amount", nbins=30, title="Distribution of Expenses")
st.plotly_chart(fig_hist, use_container_width=True)

fig_box = px.box(df_filtered, y="amount", points="all", title="📦 Expense Outlier Boxplot")
st.plotly_chart(fig_box, use_container_width=True)

# ---------------------------
# Outlier detection (Z-score)
# ---------------------------
st.markdown("---")
st.subheader("⚠ Outlier Detection (Z ≥ 2)")
daily2 = daily.copy()
daily2["z"] = (daily2["amount"] - daily2["amount"].mean()) / (daily2["amount"].std(ddof=0) if daily2["amount"].std(ddof=0) != 0 else np.nan)
outliers = daily2[daily2["z"] >= 2]

fig_out = px.scatter(daily2, x="date", y="amount", color=(daily2["z"] >= 2), labels={"color": "Outlier"}, title="Outlier Detection (Z ≥ 2)")
st.plotly_chart(fig_out, use_container_width=True)

st.write("⚠ Outlier Days:")
if outliers.empty:
    st.write("No outlier days found with Z ≥ 2.")
else:
    st.dataframe(outliers[["date", "amount", "z"]].reset_index(drop=True))

# ---------------------------
# Category contribution (pie)
# ---------------------------
st.markdown("---")
st.subheader("🍕 Expense-type Contribution")
if "expense_type" in df_filtered.columns:
    summary = df_filtered.groupby("expense_type")["amount"].sum().reset_index()
    fig = px.pie(summary, names="expense_type", values="amount", title="Expense-type Contribution", hole=0.45)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("`expense_type` column not found; skipping category contribution pie chart.")

# ---------------------------
# User-wise table (like user-wise earnings)
# ---------------------------
st.markdown("---")
st.subheader("👤 User-wise Expense Summary")
if "user_id" in df_filtered.columns:
    user_sum = df_filtered.groupby("user_id")["amount"].sum().reset_index().sort_values("amount", ascending=False)
    fig_table = go.Figure(data=[go.Table(
        header=dict(values=["User","Total Spend"], fill_color="#2E86C1", font=dict(color="white")),
        cells=dict(values=[user_sum["user_id"], user_sum["amount"]], fill_color="#D6EAF8")
    )])
    fig_table.update_layout(title="User-wise Expense Summary")
    st.plotly_chart(fig_table, use_container_width=True)
else:
    st.info("`user_id` column not found; skipping user-wise table.")

# ---------------------------
# Footer / Export
# ---------------------------
st.markdown("---")
st.subheader("Download filtered data")
csv = df_filtered.to_csv(index=False)
st.download_button("⬇️ Download filtered CSV", csv, file_name="filtered_expenses.csv", mime="text/csv")

st.caption("Built with ❤️ — Upload different CSVs to analyze other datasets.")
