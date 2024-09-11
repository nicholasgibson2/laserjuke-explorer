import streamlit as st
import pandas as pd
import re
from pathlib import Path
from print_pdf import create_pdf
from normalize import normalize_reference


custom_list_columns = ["REFERENCE"]


# REFERENCE,Position,Artist,Title,Length
# REFERENCE,Year,Company
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
    if filter_list:
        return df[column_name].isin(filter_list)
    else:
        return pd.Series([True] * len(df), index=df.index)


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


def save_custom_lists():
    for custom_list in st.session_state.custom_lists.values():
        custom_list["df"].to_csv(
            "./custom_lists/" + custom_list["filename"], columns=custom_list_columns
        )


def load_custom_lists(discs_df):
    custom_list_dir = "./custom_lists"
    files = custom_list_files(custom_list_dir)

    if "custom_lists" not in st.session_state:
        custom_lists = {}
        for file in files:
            if file == ".DS_Store":
                continue
            pretty_name = custom_list_name_format(file)
            df = read_csv_file(f"{custom_list_dir}/{file}")
            custom_lists[pretty_name] = {"filename": file, "df": df}

        df = pd.DataFrame([], columns=["REFERENCE"])
        df["REFERENCE"] = df["REFERENCE"].apply(
            lambda ref_num: normalize_reference(discs_df, ref_num)
        )

        custom_lists["Uploaded"] = {"filename": "uploaded.csv", "df": df}
        st.session_state.custom_lists = custom_lists

    lists = list(st.session_state.custom_lists.keys())

    selected_lists = st.sidebar.multiselect(
        "Select Custom Lists",
        lists,
        default=["Owned"],
        on_change=reset_last_change,
    )
    selected_dict = {}
    for selected in selected_lists:
        selected_dict[selected] = st.session_state.custom_lists[selected]["df"]

    return selected_dict


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


def paste_custom_list(discs_df):
    reference_numbers = set()
    list_text = st.session_state.custom_list_text
    for reference in list_text.split("\n"):
        if reference.strip() == "":
            continue
        normalized = normalize_reference(discs_df, reference)
        if normalized:
            reference_numbers.add(normalized)
        else:
            st.error(f"no match for {reference}")

    df = pd.DataFrame(reference_numbers, columns=["REFERENCE"])
    st.session_state.custom_lists["Uploaded"] = {"filename": "uploaded.csv", "df": df}


def main():
    st.set_page_config(page_title="Laser Juke Explorer", layout="wide")
    st.image("laserjuke.png")
    load_css("style.css")

    discs_df = read_csv_file("./data/discs.csv")
    titles_df = read_csv_file("./data/titles.csv")

    df = pd.merge(discs_df, titles_df, on="REFERENCE")

    st_sidebar = st.sidebar.container()

    custom_lists = load_custom_lists(discs_df)

    for custom_name, custom_df in custom_lists.items():
        df = df.merge(custom_df, on=custom_list_columns, how="left", indicator=True)
        df[custom_name] = df["_merge"] == "both"
        df.drop(columns=["_merge"], inplace=True)

    # Add a multiselect to allow the user to select specific dataframes
    selected_lists = st.sidebar.multiselect(
        "filter on", list(custom_lists.keys()), default=list(custom_lists.keys())
    )

    # Proceed with the filter only if there are selected lists
    if st.sidebar.checkbox("Filter", on_change=reset_last_change) and selected_lists:
        # Concatenate only the selected dataframes
        combined_df = pd.concat(
            [custom_lists[list_name] for list_name in selected_lists], ignore_index=True
        ).drop_duplicates()

        # Filter your main df based on the combined selected dataframe's 'REFERENCE'
        df = df[df["REFERENCE"].isin(combined_df["REFERENCE"])]

    st.sidebar.text_area(
        "Custom List",
        on_change=paste_custom_list,
        key="custom_list_text",
        args=(discs_df,),
    )

    with st_sidebar:
        series = dynamic_dropdown(df, "SERIES", {})
        artists = dynamic_dropdown(df, "ARTIST", {"SERIES": series})
        titles = dynamic_dropdown(df, "TITLE", {"ARTIST": artists})
        refs = dynamic_dropdown(df, "REFERENCE", {"ARTIST": artists, "TITLE": titles})
    st_sidebar.divider()

    series_condition = filter_condition(df, "SERIES", series)
    artist_condition = filter_condition(df, "ARTIST", artists)
    title_condition = filter_condition(df, "TITLE", titles)
    ref_condition = filter_condition(df, "REFERENCE", refs)

    filtered_df = df[
        series_condition & ref_condition & artist_condition & title_condition
    ].sort_values(by=["YEAR", "REFERENCE"], ascending=False)

    # print_labels = st.sidebar.button("Print Labels")
    # if print_labels:
    #     create_pdf(filtered_df, "output.pdf")

    column_order = [
        "SERIES",
        "REFERENCE",
        "NAME",
        "YEAR",
        "POSITION",
        "ARTIST",
        "TITLE",
    ] + list(custom_lists.keys())
    column_config = {"YEAR": st.column_config.NumberColumn(format="%f")}

    st.session_state.diffs_df = st.data_editor(
        filtered_df,
        # disabled=column_order[:-1],
        disabled=column_order,
        hide_index=True,
        use_container_width=True,
        column_order=column_order,
        column_config=column_config,
        on_change=update_custom_val,
        key="cur_diffs",
    )


if __name__ == "__main__":
    main()
