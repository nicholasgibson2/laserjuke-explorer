import streamlit as st
import pandas as pd


def persist_vals(cur_key, prev_key):
    st.session_state[prev_key] = st.session_state[cur_key]


def artists_dropdown(df):
    artists = df["Artist"].unique()
    artists.sort()

    prev_artists = st.session_state.get("prev_artists", [])
    return st.sidebar.multiselect(
        "Artist",
        options=artists,
        default=prev_artists,
        on_change=persist_vals,
        args=("cur_artists", "prev_artists"),
        key="cur_artists",
    )


def titles_dropdown(df, artists):
    filtered_df = df[df["Artist"].isin(artists)] if artists else df
    titles = filtered_df["Title"].unique()
    titles.sort()

    prev_titles = st.session_state.get("prev_titles", [])
    prev_titles = [title for title in prev_titles if title in titles]
    st.session_state.prev_titles = prev_titles

    return st.sidebar.multiselect(
        "Title",
        options=titles,
        default=prev_titles,
        on_change=persist_vals,
        args=("cur_titles", "prev_titles"),
        key="cur_titles",
    )


def reference_number_dropdown(df, artists, titles):
    if artists and not titles:
        filtered_df = df[df["Artist"].isin(artists)]
    elif titles:
        filtered_df = (
            df[(df["Artist"].isin(artists)) & (df["Title"].isin(titles))]
            if artists
            else df[df["Title"].isin(titles)]
        )
    else:
        filtered_df = df

    refs = filtered_df["Reference Number"].unique()
    refs.sort()

    prev_refs = st.session_state.get("prev_refs", [])
    prev_refs = [ref for ref in prev_refs if ref in refs]
    st.session_state.prev_refs = prev_refs

    return st.sidebar.multiselect(
        "Reference Number",
        options=refs,
        default=prev_refs,
        on_change=persist_vals,
        args=("cur_refs", "prev_refs"),
        key="cur_refs",
    )


@st.cache_data
def read_file(file):
    return pd.read_csv(file)


def main():
    st.set_page_config(page_title="Laser Juke Explorer", layout="wide")
    st.image("laserjuke.png")

    st.markdown(
        f"""
            <style>
                   .st-emotion-cache-z5fcl4 {{
                        padding-top: 2.5rem;
                    }}
                   .st-emotion-cache-9tg1hl {{
                        padding-top: 2.5rem;
                    }}
                   .st-emotion-cache-18ni7ap {{
                        height: 0rem;
                    }}
            </style>
        """,
        unsafe_allow_html=True,
    )

    discs_df = read_file("tino_discs.csv")
    titles_df = read_file("tino_titles.csv")
    owned_discs_df = read_file("owned_discs.csv")

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

    column_order = ["Reference Number", "Year", "Artist", "Title", "Owned"]

    column_config = {"Year": st.column_config.NumberColumn(format="%f")}

    df["Owned"] = df["Reference Number"].apply(
        lambda x: any(
            x.startswith(owned_ref) for owned_ref in owned_discs_df["Reference Number"]
        )
    )

    if st.sidebar.checkbox("Owned"):
        df = df[df["Owned"] == True]

    artists = artists_dropdown(df)
    titles = titles_dropdown(df, artists)
    ref_number = reference_number_dropdown(df, artists, titles)

    ref_condition = (
        df["Reference Number"].isin(ref_number)
        if ref_number
        else pd.Series([True] * len(df), index=df.index)
    )
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
    filtered_df = df[ref_condition & artist_condition & title_condition]
    st.dataframe(
        filtered_df,
        hide_index=True,
        use_container_width=True,
        column_order=column_order,
        column_config=column_config,
    )


if __name__ == "__main__":
    main()
