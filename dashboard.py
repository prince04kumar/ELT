import streamlit as st
import pandas as pd
import awswrangler as wr
import plotly.express as px

# Set up page configurations
st.set_page_config(page_title="Streaming Platform Analytics", layout="wide")
st.title("🎬 Streaming Platform Analytics Dashboard (ELT Pipeline)")

# ⚠️ REPLACE WITH YOUR EXACT ATHENA RESULTS BUCKET NAME FROM STEP 2
ATHENA_OUTPUT_BUCKET = "s3://my-elt-athena-results-uniqueid/"


@st.cache_data(ttl=60)  # Refreshes the data cache every 60 seconds
def run_elt_transformations():
    """
    Executes the 'Transform' step using AWS Athena's compute engine
    and returns a clean, aggregated Pandas DataFrame.
    """
    # This SQL query cleans, filters out noise (<10s), and aggregates raw data on the fly
    elt_query = """
    WITH cleaned_logs AS (
        SELECT 
            user_id,
            video_id,
            watch_time_seconds,
            device,
            CAST(from_iso8601_timestamp(timestamp) AS TIMESTAMP) AS event_timestamp
        FROM default.raw_watch_logs
        WHERE watch_time_seconds >= 10  -- T Step: Filter out accidental clicks/bounces
    )
    SELECT 
        user_id,
        device,
        COUNT(video_id) AS total_videos_watched,
        ROUND(SUM(watch_time_seconds) / 60.0, 2) AS total_watch_minutes,
        MAX(event_timestamp) AS last_active
    FROM cleaned_logs
    GROUP BY user_id, device
    """

    # Run the SQL transformation on Athena and pull the aggregated dataset back to local python
    df = wr.athena.read_sql_query(
        sql=elt_query, database="default", s3_output=ATHENA_OUTPUT_BUCKET
    )
    return df


# Run the transformation pipeline
try:
    with st.spinner("Executing Athena ELT Transformations..."):
        clean_df = run_elt_transformations()

    # ---- DASHBOARD LAYOUT ----
    # 1. High-Level Metrics Row
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Unique Viewers", clean_df["user_id"].nunique())
    m2.metric(
        "Total Watch Time (Mins)", round(clean_df["total_watch_minutes"].sum(), 1)
    )
    m3.metric(
        "Avg Watch Time per User (Mins)",
        round(clean_df["total_watch_minutes"].mean(), 1),
    )

    st.markdown("---")

    # 2. Charts Row
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("📱 Watch Time Distribution by Device")
        device_fig = px.pie(
            clean_df,
            values="total_watch_minutes",
            names="device",
            hole=0.4,
            color_discrete_sequence=px.colors.sequential.RdBu,
        )
        st.plotly_chart(device_fig, use_container_width=True)

    with c2:
        st.subheader("🏆 Top Engaged Users (Minutes Watched)")
        top_users = (
            clean_df.groupby("user_id")["total_watch_minutes"].sum().reset_index()
        )
        top_users = top_users.sort_values(
            by="total_watch_minutes", ascending=False
        ).head(10)
        bar_fig = px.bar(
            top_users,
            x="user_id",
            y="total_watch_minutes",
            labels={"user_id": "User", "total_watch_minutes": "Minutes Played"},
            color="total_watch_minutes",
        )
        st.plotly_chart(bar_fig, use_container_width=True)

    # 3. Raw Cleaned Data Inspection Table
    st.subheader("📋 Transformed Production-Ready Schema (Fact Table)")
    st.dataframe(clean_df, use_container_width=True)

except Exception as e:
    st.error(
        f"Failed to fetch data from AWS Athena. Please verify your S3 path bucket permissions. Details: {e}"
    )
