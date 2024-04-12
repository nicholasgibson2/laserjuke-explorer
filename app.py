import streamlit as st
import pandas as pd


def artists_dropdown(df):
    artists = df["Artist"].unique()
    artists.sort()
    return st.sidebar.multiselect("Artist", options=artists)


def titles_dropdown(df, artists):
    filtered_df = df[df["Artist"].isin(artists)] if artists else df
    titles = filtered_df["Title"].unique()
    titles.sort()
    return st.sidebar.multiselect("Title", options=titles)


def main():
    st.set_page_config(page_title="Laser Juke Explorer", layout="wide")
    st.image("laserjuke.png")

    st.markdown(
        f"""
            <style>
                   .st-emotion-cache-z5fcl4 {{
                        padding-top: 1rem;
                    }}
                   .st-emotion-cache-9tg1hl {{
                        padding-top: 1rem;
                    }}
                   .st-emotion-cache-18ni7ap {{
                        height: 0rem;
                    }}
            </style>
        """,
        unsafe_allow_html=True,
    )

    discs_df = pd.read_csv("tino_discs.csv")
    titles_df = pd.read_csv("tino_titles.csv")

    df = pd.merge(discs_df, titles_df, on="Reference Number")

    df["Month"] = df["Reference Number"].str.extract(r"\d{2}\.\d{2}\.(\d{2}).*")
    df["Month"] = pd.to_numeric(df["Month"], errors="coerce").astype("Int64")

    df.dropna(subset=["Month"], inplace=True)

    df["Year"] = df["Year"].fillna(1900).astype(int)
    df["Year"] = df["Year"].astype(int)
    df["Month"] = df["Month"].astype(int)

    df["Date"] = pd.to_datetime(
        df["Year"].astype(int).astype(str)
        + "-"
        + df["Month"].fillna(1).astype(int).astype(str)
        + "-01",
        format="%Y-%m-%d",
        errors="coerce",
    )
    df.loc[df["Month"].isna(), "Date"] = pd.to_datetime(
        df["Year"].astype(int).astype(str) + "-01-01"
    )

    column_order = ["Reference Number", "Date", "Year", "Artist", "Title"]

    column_config = {"Year": st.column_config.NumberColumn(format="%f")}

    artists = artists_dropdown(df)
    titles = titles_dropdown(df, artists)

    artist_condition = (
        df["Artist"].isin(artists)
        if artists
        else pd.Series([True] * len(df), index=df.index)
    )
    title_condition = (
        df["Title"].isin(titles)
        if titles
        else pd.Series([True] * len(df), index=df.index)
    )
    filtered_df = df[artist_condition & title_condition]

    st.data_editor(
        filtered_df,
        hide_index=True,
        use_container_width=True,
        column_order=column_order,
        column_config=column_config,
    )


if __name__ == "__main__":
    main()
