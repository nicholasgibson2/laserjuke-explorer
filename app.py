import streamlit as st
import pandas as pd
import base64
from pathlib import Path
from print_pdf import create_pdf
from normalize import normalize_reference
from PIL import Image


def persist_vals(cur_key, prev_key):
    st.session_state[prev_key] = st.session_state[cur_key]


def cut_list(options, column):
    key = f"cur_{column}"
    if key not in st.session_state or len(st.session_state[key]) == 0:
        return options

    split_value = st.session_state[key][-1]
    split_index = options.index(split_value)
    first_half = options[: split_index + 1]
    second_half = options[split_index + 1 :]
    return second_half + first_half


def dynamic_dropdown(df, column, dependencies, nicksort=False):
    for dep_column, dep_values in dependencies.items():
        if dep_values:
            df = df[df[dep_column].isin(dep_values)]

    options = sorted(df[column].unique())
    if nicksort:
        options = cut_list(options, column)

    prev_selections = st.session_state.get(f"prev_{column}", [])
    prev_selections = [s for s in prev_selections if s in options]

    st.session_state[f"prev_{column}"] = prev_selections

    selected = st.multiselect(
        label=column.title(),
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
    df = pd.read_csv(file)
    df = df.drop_duplicates()
    return df


@st.cache_data
def load_css(file_name):
    with open(file_name, "r") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


@st.cache_data
def custom_list_files(directory):
    return [file.name for file in Path(directory).iterdir() if file.is_file()]


def custom_list_name_format(filename):
    return Path(filename).stem.replace("_", " ").title()


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
            df["REFERENCE"] = df["REFERENCE"].apply(
                lambda ref_num: normalize_reference(discs_df, ref_num)
            )
            df.drop_duplicates(subset="REFERENCE", inplace=True)
            custom_lists[pretty_name] = {"filename": file, "df": df}

        df = pd.DataFrame([], columns=["REFERENCE"])
        custom_lists["Custom"] = {"df": df}
        st.session_state.custom_lists = custom_lists

    lists = list(st.session_state.custom_lists.keys())
    lists.sort()

    selected_lists = st.sidebar.multiselect("Lists", lists, default=["Owned"])
    selected_dict = {}
    for selected in selected_lists:
        selected_dict[selected] = st.session_state.custom_lists[selected]["df"]

    return selected_dict


def paste_custom_list(discs_df):
    reference_numbers = set()
    list_text = st.session_state.custom_list_text
    for reference in list_text.split("\n"):
        if reference.strip() == "":
            continue
        normalized = normalize_reference(discs_df, reference)

        if normalized in discs_df["REFERENCE"].values:
            reference_numbers.add(normalized)
        else:
            st.error(f"No match for {reference}")

    df = pd.DataFrame(reference_numbers, columns=["REFERENCE"])
    st.session_state.custom_lists["Custom"] = {"df": df}


@st.dialog("Labels", width="large")
def create_label_pdf(filtered_df):
    if filtered_df["REFERENCE"].nunique() > 100:
        st.error("max labels 100")
        return
    labels_pdf = create_pdf(filtered_df)
    base64_pdf = base64.b64encode(labels_pdf.read()).decode("utf-8")
    pdf_iframe = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="700" height="500" type="application/pdf"></iframe>'
    st.markdown(pdf_iframe, unsafe_allow_html=True)


def main():
    im = Image.open("juke_star.png")
    st.set_page_config(page_title="Laser Juke Explorer", layout="wide", page_icon=im)
    st.image("laserjuke.png")
    load_css("style.css")

    discs_df = read_csv_file("./data/discs.csv")
    titles_df = read_csv_file("./data/titles.csv")

    df = pd.merge(discs_df, titles_df, on="REFERENCE")

    st_sidebar = st.sidebar.container()

    custom_lists = load_custom_lists(discs_df)

    for custom_name, custom_df in custom_lists.items():
        df = df.merge(custom_df, on="REFERENCE", how="left", indicator=True)
        df[custom_name] = df["_merge"] == "both"
        df.drop(columns=["_merge"], inplace=True)

    with st.sidebar:
        custom_lists_df = pd.DataFrame(list(custom_lists.keys()), columns=["Filter On"])
        filtered_lists = dynamic_dropdown(custom_lists_df, "Filter On", {})

    if filtered_lists:
        combined_df = pd.concat(
            [custom_lists[list_name] for list_name in filtered_lists], ignore_index=True
        ).drop_duplicates()
        df = df[df["REFERENCE"].isin(combined_df["REFERENCE"])]

    st.sidebar.text_area(
        "Custom List",
        on_change=paste_custom_list,
        key="custom_list_text",
        args=(discs_df,),
    )

    with st_sidebar:
        series = dynamic_dropdown(df, "SERIES", {})
        artists = dynamic_dropdown(df, "ARTIST", {"SERIES": series}, nicksort=True)
        titles = dynamic_dropdown(df, "TITLE", {"SERIES": series, "ARTIST": artists})
        refs = dynamic_dropdown(
            df, "REFERENCE", {"SERIES": series, "ARTIST": artists, "TITLE": titles}
        )
    st_sidebar.divider()

    series_condition = filter_condition(df, "SERIES", series)
    artist_condition = filter_condition(df, "ARTIST", artists)
    title_condition = filter_condition(df, "TITLE", titles)
    ref_condition = filter_condition(df, "REFERENCE", refs)

    filtered_df = df[
        series_condition & ref_condition & artist_condition & title_condition
    ].sort_values(by=["YEAR", "REFERENCE"], ascending=False)

    if st.sidebar.button("Print Labels"):
        create_label_pdf(filtered_df)

    column_order = [
        "SERIES",
        "NAME",
        # "REFERENCE",
        "YEAR",
        "POSITION",
        "ARTIST",
        "TITLE",
    ] + list(custom_lists.keys())
    column_config = {}
    for column in ["SERIES", "NAME", "REFERENCE", "POSITION", "ARTIST", "TITLE"]:
        column_config[column] = st.column_config.TextColumn(column.title())
    column_config["YEAR"] = st.column_config.NumberColumn("Year", format="%f")

    st.data_editor(
        filtered_df,
        disabled=column_order,
        hide_index=True,
        use_container_width=True,
        column_order=column_order,
        column_config=column_config,
    )


if __name__ == "__main__":
    main()
