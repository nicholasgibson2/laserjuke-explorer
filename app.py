import streamlit as st
import pandas as pd
from pathlib import Path


def persist_vals(cur_key, prev_key):
    st.session_state[prev_key] = st.session_state[cur_key]


def dynamic_dropdown(df, column, dependencies):
    for dep_column, dep_values in dependencies.items():
        if dep_values:
            df = df[df[dep_column].isin(dep_values)]

    options = sorted(df[column].unique())

    prev_selections = st.session_state.get(f"prev_{column}", [])
    prev_selections = [s for s in prev_selections if s in options]

    st.session_state[f"prev_{column}"] = prev_selections

    selected = st.multiselect(
        label=column,
        options=options,
        default=prev_selections,
        on_change=persist_vals,
        args=(f"cur_{column}", f"prev_{column}"),
        key=f"cur_{column}",
    )

    return selected


def filter_condition(df, column_name, filter_list):
    return (
        df[column_name].isin(filter_list)
        if filter_list
        else pd.Series([True] * len(df), index=df.index)
    )


@st.cache_data
def read_csv_file(file):
    return pd.read_csv(file)


@st.cache_data
def load_css(file_name):
    with open(file_name, "r") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


@st.cache_data
def custom_list_files(directory):
    return [file.name for file in Path(directory).iterdir() if file.is_file()]


def custom_list_name_format(filename):
    return Path(filename).stem.replace("_", " ").title()


def custom_list():
    custom_list_dir = "./custom_lists"
    files = custom_list_files(custom_list_dir)

    selected = st.sidebar.selectbox(
        "List",
        files,
        format_func=custom_list_name_format,
        index=files.index("juke_night.csv"),
    )

    selected_str = custom_list_name_format(selected)
    selected_df = read_csv_file(f"{custom_list_dir}/{selected}")
    return selected_str, selected_df


def main():
    st.set_page_config(page_title="Laser Juke Explorer", layout="wide")
    st.image("laserjuke.png")
    load_css("style.css")

    discs_df = read_csv_file("tino_discs.csv")
    titles_df = read_csv_file("tino_titles.csv")
    owned_df = read_csv_file("owned_discs.csv")

    df = pd.merge(discs_df, titles_df, on="Reference Number")

    st_sidebar = st.sidebar.container()
    df["Owned"] = df["Reference Number"].isin(owned_df["Reference Number"])
    if st_sidebar.checkbox("Owned"):
        df = df[df["Owned"]]

    custom_name, custom_df = custom_list()
    df[custom_name] = df["Reference Number"].isin(custom_df["Reference Number"])

    if st.sidebar.checkbox("Filter"):
        df = df[df[custom_name]]

    with st_sidebar:
        artists = dynamic_dropdown(df, "Artist", {})
        titles = dynamic_dropdown(df, "Title", {"Artist": artists})
        refs = dynamic_dropdown(
            df, "Reference Number", {"Artist": artists, "Title": titles}
        )
    st_sidebar.divider()

    artist_condition = filter_condition(df, "Artist", artists)
    title_condition = filter_condition(df, "Title", titles)
    ref_condition = filter_condition(df, "Reference Number", refs)

    filtered_df = df[ref_condition & artist_condition & title_condition].sort_values(
        by=["Year", "Reference Number"], ascending=False
    )

    column_order = ["Reference Number", "Year", "Artist", "Title", "Owned", custom_name]
    column_config = {"Year": st.column_config.NumberColumn(format="%f")}

    st.dataframe(
        filtered_df,
        hide_index=True,
        use_container_width=True,
        column_order=column_order,
        column_config=column_config,
    )


if __name__ == "__main__":
    main()
