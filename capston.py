import streamlit as st
import pandas as pd
import plotly.express as px

# covid data from CSSE
case = pd.read_csv("https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_global.csv")
death = pd.read_csv("https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_global.csv")
recovered = pd.read_csv("https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_recovered_global.csv")

# reformat to have a long format with date as a variable
case_long = case.melt(id_vars=["Province/State", "Country/Region", "Lat", "Long"], var_name="Date", value_name="Cases")
case_long["Date"] = pd.to_datetime(case_long["Date"], format="%m/%d/%y")

case_long['Province/State'].unique()
case_long['Country/Region'].unique()
# cumulative case counts by country
case_long = case_long.groupby(["Country/Region", "Date"])["Cases"].sum().reset_index()

case_long['Cases'].isna().sum()
# reformat to have a long format with date as a variable
death_long = death.melt(id_vars=["Province/State", "Country/Region", "Lat", "Long"], var_name="Date", value_name="Deaths")
death_long["Date"] = pd.to_datetime(death_long["Date"], format="%m/%d/%y")

death_long['Province/State'].unique()
death_long['Country/Region'].unique()
# cumulative death counts by country
death_long = death_long.groupby(["Country/Region", "Date"])["Deaths"].sum().reset_index()

death_long['Deaths'].isna().sum()
# reformat to have a long format with date as a variable
recovered_long = recovered.melt(id_vars=["Province/State", "Country/Region", "Lat", "Long"], var_name="Date", value_name="Recovered")
recovered_long["Date"] = pd.to_datetime(recovered_long["Date"], format="%m/%d/%y")

recovered_long['Province/State'].unique()
recovered_long['Country/Region'].unique()
# cumulative recovered counts by country
recovered_long = recovered_long.groupby(["Country/Region", "Date"])["Recovered"].sum().reset_index()
recovered_long['Recovered'].isna().sum()

#merge the three dataframes
df = case_long.merge(death_long, on=["Country/Region", "Date"], how="left").merge(recovered_long, on=["Country/Region", "Date"], how="left")
df["Active"] = df["Cases"] - df["Deaths"] - df["Recovered"]

# new cases but corrected for negative values
df = df.sort_values(["Country/Region","Date"])

df[["New Cases","New Deaths","New Recovered"]] = (
    df.groupby("Country/Region")[["Cases","Deaths","Recovered"]]
      .diff()
      .clip(lower=0)
)
df = df.rename(columns={"Country/Region": "Country"})
df["Date"] = pd.to_datetime(df["Date"])

# change US to United States
df["Country"] = df["Country"].replace("US", "United States")

#update country names

df["Country"] = df["Country"].replace({
    "Burma": "Myanmar(Burma)",
    "Korea, South": "South Korea",
    "Korea, North": "North Korea",
    "Congo (Brazzaville)": "Republic of the Congo",
    "Congo (Kinshasa)": "Democratic Republic of the Congo",
    "Czechia": "Czech Republic",
    "Holy See": "Vatican City",
    "West Bank and Gaza": "Palestine",
    "Taiwan*": "Taiwan"
})

# remove events and cruise ships, olympic games
df = df[~df["Country"].isin(["Diamond Princess", "MS Zaandam", "Summer Olympics 2020", "Winter Olympics 2022"])]

df = df[["Country", "Date", "Cases", "Deaths", "Recovered", "Active", "New Cases", "New Deaths", "New Recovered"]]
df.columns = ["Country", "Date", "Cases", "Deaths", "Recovered", "Active", "New Cases", "Daily Deaths", "New Recovered"]

####################################################################################################
# create the app 
st.set_page_config(layout="wide")
st.title("COVID-19 Data Visualization")

# User selections
#add a slide to choose time range
min_date = df["Date"].min().date()
max_date = df["Date"].max().date()

input_col, table_col = st.columns([1, 1])

with input_col:
    date_range = st.slider(
        "Select date range",
        min_value=min_date,
        max_value=max_date,
        value=(min_date, max_date),
        format="YYYY-MM-DD"
    )

    start_date = pd.to_datetime(date_range[0])
    end_date = pd.to_datetime(date_range[1])

    country = st.multiselect("Select a country", df["Country"].unique(), default=["United States"])
    view_type = st.radio("Select view type", ["Cumulative", "Daily", "Both"], horizontal=True)

    # Define metrics based on view type
    if view_type == "Cumulative":
        default_metrics = ["Cases", "Deaths", "Recovered", "Active"]
        available_metrics = ["Cases", "Deaths", "Recovered", "Active"]
    elif view_type == "Daily":
        default_metrics = ["New Cases", "Daily Deaths"]
        available_metrics = ["New Cases", "Daily Deaths"]
    else:  # Both
        default_metrics = ["Cases", "New Cases"]
        available_metrics = ["Cases", "Deaths", "Recovered", "Active", "New Cases", "Daily Deaths", "New Recovered"]

    data_type = st.multiselect("Select metric", available_metrics, default=default_metrics)
    log_scale = st.toggle("Logarithmic scale", value=False)

with table_col:
    st.write("## Daily Data Table")
    selected_date = st.date_input("Select a date", value=max_date, min_value=min_date, max_value=max_date)
    if not country:
        st.info("Select at least one country to show the daily table.")
    else:
        # Keep the table focused on daily.
        selected_columns = ["Country", "Date", "New Cases", "Daily Deaths"]
        table_data = df.loc[
            (df["Country"].isin(country)) & (df["Date"] == pd.to_datetime(selected_date)),
            selected_columns,
        ].sort_values("Country")

        if table_data.empty:
            st.warning("No data found for the selected country/date combination.")
        else:
            display_table = table_data.copy()
            display_table["Date"] = display_table["Date"].dt.strftime("%Y-%m-%d")  # remove time
            display_table["New Cases"] = display_table["New Cases"].map(lambda x: f"{x:,.0f}")  # add commas for thousands and remove decimals
            display_table["Daily Deaths"] = display_table["Daily Deaths"].map(lambda x: f"{x:,.0f}")  # add commas for thousands and remove decimals
            st.dataframe(display_table, use_container_width=True)

# Filter by country and date range
if country:
    if not data_type:
        st.error("Please select at least one metric to visualize data.")
    else:
        country_data = df[(df["Country"].isin(country)) & (df["Date"] >= start_date) & (df["Date"] <= end_date)].copy()
        country_melt = country_data.melt(id_vars=["Country","Date"], value_vars=data_type, var_name="Metric", value_name="Count")

        # Create figure
        fig = px.line(
            country_melt,
            x="Date",
            y="Count",
            color="Country",
            line_dash="Metric",
            template="plotly",
            title=f"{view_type} COVID-19 Trends in {', '.join(country)}"
        )
        
        # Update hover template to show exact date/ WWAI copilot
        fig.update_traces(hovertemplate='<b>%{fullData.name}</b><br>Date: %{x|%Y-%m-%d}<br>Count: %{y:,.0f}<extra></extra>')
        
        # Update layout
        # add grid lines for better readability
        yaxis_config = dict(gridcolor='lightgray', zerolinecolor='lightgray')
        if log_scale:
            yaxis_config['type'] = 'log'
        # change the plotly background to white
        # make the x-axis ticks every 3 months and show the month and year
        fig.update_layout(
            template="plotly",
            plot_bgcolor='white',
            paper_bgcolor='white',
            xaxis_title="Date",
            yaxis_title=f"{view_type} Count",
            xaxis=dict(dtick="M3", tickformat="%b %Y", ticks="outside"),
            yaxis=yaxis_config
        )
        st.plotly_chart(fig, use_container_width=True)
else:
    st.error("Please select at least one country to visualize data.")