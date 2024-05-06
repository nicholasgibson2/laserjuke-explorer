import streamlit as st
import pandas as pd
from pathlib import Path


custom_list_columns = ["Reference Number", "Artist", "Title"]


def reset_last_change():
    st.session_state.last_diffs = {}


def persist_vals(cur_key, prev_key):
    st.session_state[prev_key] = st.session_state[cur_key]
    reset_last_change()


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


# @st.cache_data
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


def save_custom_lists():
    for custom_list in st.session_state.custom_lists.values():
        custom_list["df"].to_csv(
            "./custom_lists/" + custom_list["filename"], columns=custom_list_columns
        )


def custom_list():
    custom_list_dir = "./custom_lists"
    files = custom_list_files(custom_list_dir)

    if "custom_lists" not in st.session_state:
        custom_lists = {}
        for file in files:
            pretty_name = custom_list_name_format(file)
            df = read_csv_file(f"{custom_list_dir}/{file}")
            custom_lists[pretty_name] = {"filename": file, "df": df}
        st.session_state.custom_lists = custom_lists

    selected = st.sidebar.selectbox(
        "List",
        files,
        format_func=custom_list_name_format,
        index=files.index("juke_night.csv"),
        on_change=reset_last_change,
    )

    selected_str = custom_list_name_format(selected)
    selected_df = st.session_state.custom_lists[selected_str]["df"]

    return selected_str, selected_df


def update_custom_val():
    last_diffs = st.session_state.get("last_diffs", {})
    cur_diffs = st.session_state.cur_diffs["edited_rows"]

    for key, val in cur_diffs.items():
        if (key not in last_diffs) or (last_diffs[key] != val):
            updated_index = key
            updated_row = val
            break

    row = st.session_state.diffs_df.iloc[[updated_index]][custom_list_columns]

    df_name, updated_val = next(iter(updated_row.items()))
    custom_df = st.session_state.custom_lists[df_name]["df"]

    if updated_val:
        updated_df = pd.concat([custom_df, row], ignore_index=True)
    else:
        matched_df = custom_df.merge(
            row, on=custom_list_columns, how="left", indicator=True
        )
        updated_df = matched_df[matched_df["_merge"] == "left_only"].drop(
            columns="_merge"
        )
    st.session_state.custom_lists[df_name]["df"] = updated_df

    st.session_state.last_diffs = cur_diffs


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
    if st_sidebar.checkbox("Owned", on_change=reset_last_change):
        df = df[df["Owned"]]

    custom_name, custom_df = custom_list()

    common_columns = custom_list_columns
    df = df.merge(custom_df, on=common_columns, how="left", indicator=True)
    df[custom_name] = df["_merge"] == "both"
    df.drop(columns=["_merge"], inplace=True)

    if st.sidebar.checkbox("Filter", on_change=reset_last_change):
        df = df[df[custom_name]]
    st.sidebar.button("Save", on_click=save_custom_lists)

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

    st.session_state.diffs_df = st.data_editor(
        filtered_df,
        disabled=column_order[:-1],
        hide_index=True,
        use_container_width=True,
        column_order=column_order,
        column_config=column_config,
        on_change=update_custom_val,
        key="cur_diffs",
    )


if __name__ == "__main__":
    main()
