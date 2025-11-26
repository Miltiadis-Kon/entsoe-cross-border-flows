import streamlit as st
import pandas as pd
import json
import os
import plotly.express as px

st.set_page_config(page_title="Balkan Energy Flows", layout="wide")

st.title("Balkan Cross-Border Electricity Flows")

# Load countries
@st.cache_data
def load_countries():
    with open('countries.json', 'r') as f:
        return json.load(f)

countries = load_countries()
country_map = {c['name']: c['code'] for c in countries}
code_map = {c['code']: c['name'] for c in countries}

# Sidebar controls
st.sidebar.header("Navigation")
view_mode = st.sidebar.radio("View Mode", ["Single Flow", "Country Total", "Missing Data Analysis"])

# --- SHARED FUNCTIONS ---
def get_flow_data(code_from, code_to):
    filename = f"data/flow_{code_from}_{code_to}.json"
    if os.path.exists(filename):
        try:
            df = pd.read_json(filename)
            if not df.empty and 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.set_index('timestamp', inplace=True)
                return df
        except Exception as e:
            st.error(f"Error reading {filename}: {e}")
    return None

# --- VIEW: SINGLE FLOW ---
if view_mode == "Single Flow":
    st.sidebar.header("Configuration")
    from_country_name = st.sidebar.selectbox("From Country", list(country_map.keys()))
    from_country_code = country_map[from_country_name]

    # Filter neighbors based on selection
    selected_country_data = next(c for c in countries if c['code'] == from_country_code)
    neighbors = selected_country_data['neighbors']
    neighbor_options = [code_map.get(n, n) for n in neighbors]
    to_country_name = st.sidebar.selectbox("To Country", neighbor_options)
    to_country_code = next((k for k, v in code_map.items() if v == to_country_name), to_country_name)

    df = get_flow_data(from_country_code, to_country_code)

    if df is not None:
        # Date Range Filter
        min_date = df.index.min().date()
        max_date = df.index.max().date()
        
        start_date, end_date = st.sidebar.date_input(
            "Date Range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )

        # Filter data
        mask = (df.index.date >= start_date) & (df.index.date <= end_date)
        filtered_df = df.loc[mask]

        # Metrics
        total_flow = filtered_df['flow'].sum()
        avg_flow = filtered_df['flow'].mean()
        max_flow = filtered_df['flow'].max()

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Flow (MWh)", f"{total_flow:,.2f}")
        col2.metric("Average Flow (MW)", f"{avg_flow:,.2f}")
        col3.metric("Max Flow (MW)", f"{max_flow:,.2f}")

        # Charts
        st.subheader("Flow Over Time")
        fig = px.line(filtered_df, y='flow', title=f"Flow from {from_country_name} to {to_country_name}")
        st.plotly_chart(fig, use_container_width=True)

        # Hourly Profile
        st.subheader("Average Hourly Profile")
        # Group by hour (0-23) and calculate mean
        hourly_profile = filtered_df.groupby(filtered_df.index.hour)['flow'].mean()
        
        fig_hourly = px.line(
            x=hourly_profile.index, 
            y=hourly_profile.values, 
            title=f"Average Hourly Flow (00:00 - 23:00) - {start_date} to {end_date}",
            labels={'x': 'Hour of Day', 'y': 'Average Flow (MW)'}
        )
        # Ensure x-axis shows all hours
        fig_hourly.update_layout(xaxis=dict(tickmode='linear', tick0=0, dtick=1))
        st.plotly_chart(fig_hourly, use_container_width=True)

        # Aggregations
        st.subheader("Aggregations")
        agg_type = st.selectbox("Aggregation Period", ["Daily", "Monthly", "Yearly"])
        
        if agg_type == "Daily":
            agg_df = filtered_df.resample('D').sum()
        elif agg_type == "Monthly":
            agg_df = filtered_df.resample('ME').sum()
        else:
            agg_df = filtered_df.resample('YE').sum()

        fig_agg = px.bar(agg_df, y='flow', title=f"{agg_type} Flow")
        st.plotly_chart(fig_agg, use_container_width=True)

    else:
        st.error(f"Data file not found for {from_country_name} -> {to_country_name}")
        st.info("Please run the data fetching script first or ensure data exists for this pair.")

# --- VIEW: COUNTRY TOTAL ---
elif view_mode == "Country Total":
    st.sidebar.header("Configuration")
    target_country_name = st.sidebar.selectbox("Select Country", list(country_map.keys()))
    target_code = country_map[target_country_name]
    
    # Date Range (Global for this view)
    # We need to load some data to get min/max, let's just use a default or try to find global min/max
    # For simplicity, let's default to 2023-01-01 to today
    date_range = st.sidebar.date_input(
        "Date Range",
        value=(pd.Timestamp('20230101'), pd.Timestamp.now()),
    )
    
    if len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date = date_range[0]
        end_date = date_range[0]

    st.header(f"Total Energy Balance: {target_country_name}")

    # Calculate Imports and Exports
    imports = pd.Series(dtype='float64')
    exports = pd.Series(dtype='float64')

    # Find all neighbors
    target_data = next(c for c in countries if c['code'] == target_code)
    
    # EXPORTS: target -> neighbor
    for neighbor in target_data['neighbors']:
        df = get_flow_data(target_code, neighbor)
        if df is not None:
            # Resample to hourly to ensure alignment if needed, or just add
            # Assuming 1H resolution for all
            if exports.empty:
                exports = df['flow']
            else:
                exports = exports.add(df['flow'], fill_value=0)
    
    # IMPORTS: neighbor -> target
    # We need to find who lists target as neighbor
    for c in countries:
        if target_code in c['neighbors']:
            neighbor_code = c['code']
            df = get_flow_data(neighbor_code, target_code)
            if df is not None:
                if imports.empty:
                    imports = df['flow']
                else:
                    imports = imports.add(df['flow'], fill_value=0)

    # Align dates
    if not imports.empty and not exports.empty:
        combined = pd.DataFrame({'Imports': imports, 'Exports': exports})
    elif not imports.empty:
        combined = pd.DataFrame({'Imports': imports, 'Exports': 0})
    elif not exports.empty:
        combined = pd.DataFrame({'Imports': 0, 'Exports': exports})
    else:
        st.warning("No data found for this country.")
        combined = pd.DataFrame()

    if not combined.empty:
        combined.fillna(0, inplace=True)
        combined['Net Flow'] = combined['Exports'] - combined['Imports'] # Positive = Net Exporter

        # Filter
        mask = (combined.index.date >= start_date) & (combined.index.date <= end_date)
        filtered_combined = combined.loc[mask]

        # Metrics
        tot_imp = filtered_combined['Imports'].sum()
        tot_exp = filtered_combined['Exports'].sum()
        net = filtered_combined['Net Flow'].sum()

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Imports (MWh)", f"{tot_imp:,.2f}")
        c2.metric("Total Exports (MWh)", f"{tot_exp:,.2f}")
        c3.metric("Net Balance (MWh)", f"{net:,.2f}", delta_color="normal")

        # Aggregations
        st.subheader("Aggregations")
        agg_type_total = st.selectbox("Aggregation Period", ["Daily", "Monthly", "Yearly"], key="agg_total")
        
        if agg_type_total == "Daily":
            agg_combined = filtered_combined.resample('D').sum()
        elif agg_type_total == "Monthly":
            agg_combined = filtered_combined.resample('ME').sum()
        else:
            agg_combined = filtered_combined.resample('YE').sum()
        
        fig_bal = px.bar(agg_combined, y=['Imports', 'Exports'], title=f"{agg_type_total} Imports vs Exports", barmode='group')
        st.plotly_chart(fig_bal, use_container_width=True)
        
        fig_net = px.bar(agg_combined, y='Net Flow', title=f"{agg_type_total} Net Flow (Positive = Export)", color='Net Flow')
        st.plotly_chart(fig_net, use_container_width=True)

        # Hourly Profile (Country Total)
        st.subheader("Average Hourly Profile")
        # Group by hour (0-23) and calculate mean for Imports, Exports, Net Flow
        hourly_profile_total = filtered_combined.groupby(filtered_combined.index.hour)[['Imports', 'Exports', 'Net Flow']].mean()
        
        fig_hourly_total = px.line(
            hourly_profile_total, 
            x=hourly_profile_total.index, 
            y=['Imports', 'Exports', 'Net Flow'],
            title=f"Average Hourly Energy Balance (00:00 - 23:00) - {start_date} to {end_date}",
            labels={'index': 'Hour of Day', 'value': 'Average Flow (MW)', 'variable': 'Metric'}
        )
        # Ensure x-axis shows all hours
        fig_hourly_total.update_layout(xaxis=dict(tickmode='linear', tick0=0, dtick=1))
        st.plotly_chart(fig_hourly_total, use_container_width=True)

# --- VIEW: MISSING DATA ---
elif view_mode == "Missing Data Analysis":
    st.header("Missing Data Analysis")
    
    start_check = st.date_input("Check Start Date", pd.Timestamp('20230101'))
    end_check = st.date_input("Check End Date", pd.Timestamp.now())
    expected_range = pd.date_range(start=start_check, end=end_check, freq='h')
    expected_count = len(expected_range)

    report_data = []

    progress_bar = st.progress(0)
    total_pairs = sum(len(c['neighbors']) for c in countries)
    processed = 0

    for country in countries:
        code_from = country['code']
        for code_to in country['neighbors']:
            filename = f"data/flow_{code_from}_{code_to}.json"
            status = "Missing File"
            missing_days = "All"
            completeness = 0.0
            
            if os.path.exists(filename):
                try:
                    df = pd.read_json(filename)
                    if not df.empty and 'timestamp' in df.columns:
                        df['timestamp'] = pd.to_datetime(df['timestamp'])
                        df.set_index('timestamp', inplace=True)
                        
                        # Filter to checked range
                        mask = (df.index >= pd.Timestamp(start_check).tz_localize('Europe/Brussels')) & \
                               (df.index <= pd.Timestamp(end_check).tz_localize('Europe/Brussels'))
                        df_range = df.loc[mask]
                        
                        actual_count = len(df_range)
                        # Rough completeness check (hours present vs expected hours)
                        # Note: expected_range is naive, we need to handle TZ carefully or just count hours
                        # Let's just count hours in range
                        
                        if actual_count == 0:
                            status = "No Data in Range"
                        else:
                            completeness = (actual_count / ((end_check - start_check).days * 24)) * 100
                            completeness = min(100.0, completeness) # Cap at 100
                            
                            if completeness > 99:
                                status = "Complete"
                                missing_days = "None"
                            else:
                                status = "Partial"
                                # Find missing days
                                all_days = pd.date_range(start=start_check, end=end_check, freq='D')
                                present_days = df_range.index.normalize().unique()
                                missing = all_days.difference(present_days)
                                if len(missing) > 0:
                                    if len(missing) > 10:
                                        missing_days = f"{len(missing)} days missing (e.g. {missing[0].date()}...)"
                                    else:
                                        missing_days = ", ".join([str(d.date()) for d in missing])
                                else:
                                    missing_days = "Partial hours missing"

                except Exception:
                    status = "Error Reading"
            
            report_data.append({
                "From": code_from,
                "To": code_to,
                "Status": status,
                "Completeness (%)": f"{completeness:.1f}%",
                "Missing Info": missing_days
            })
            
            processed += 1
            progress_bar.progress(processed / total_pairs)

    st.dataframe(pd.DataFrame(report_data))

