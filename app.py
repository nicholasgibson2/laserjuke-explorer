import streamlit as st
import polars as pl
import base64
from pathlib import Path
from print_pdf import create_pdf
from statistics import display_statistics
from normalize import normalize_reference
from PIL import Image

nicksort = ["ARTIST"]


def persist_vals(cur_key, prev_key):
    st.session_state[prev_key] = st.session_state[cur_key]


def cut_list(options, column):
    key = f"cur_{column}"
    if key not in st.session_state or not st.session_state[key]:
        return options

    split_value = st.session_state[key][-1]
    if split_value not in options:
        return options

    split_index = options.index(split_value)
    first_half = options[: split_index + 1]
    second_half = options[split_index + 1 :]
    return second_half + first_half


def dynamic_dropdown(df, column, dependencies):
    for dep_column, dep_values in dependencies.items():
        if dep_values:
            df = df.filter(pl.col(dep_column).is_in(dep_values))

    options = sorted(df[column].drop_nulls().unique().to_list(), key=str)

    if column in nicksort:
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
        return df[column_name].is_in(filter_list)
    else:
        return pl.Series([True] * len(df))


def create_filters(df, filter_fields, st_container):
    selected_values = {}

    for i, field in enumerate(filter_fields):
        dependencies = {
            prev_field: selected_values[prev_field]
            for prev_field in filter_fields[:i]
            if prev_field in selected_values
        }

        with st_container:
            selected_values[field] = dynamic_dropdown(df, field, dependencies)

    st_container.divider()

    mask = pl.lit(True)
    for field in filter_fields:
        if selected_values[field]:
            mask &= pl.col(field).is_in(selected_values[field])

    filtered_df = df.filter(mask).sort(
        by=["YEAR", "MONTH", "REFERENCE", "POSITION"],
        descending=[True, True, False, False],
        nulls_last=True,
    )
    return filtered_df


@st.cache_resource
def load_css(file_name):
    with open(file_name, "r") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


@st.cache_resource
def custom_list_files(directory):
    return [file.name for file in Path(directory).iterdir() if file.is_file()]


def custom_list_name_format(filename):
    return Path(filename).stem.replace("_", " ").title()


@st.cache_resource
def read_custom_list_file(file):
    df = pl.read_csv(file).unique(subset=["REFERENCE"])
    return df


# TODO: figure out if we can use more caching for this
def load_custom_lists():
    custom_list_dir = "./custom_lists"
    files = custom_list_files(custom_list_dir)

    if "custom_lists" not in st.session_state:
        custom_lists = {}
        for file in files:
            if file == ".DS_Store":
                continue
            pretty_name = custom_list_name_format(file)
            df = read_custom_list_file(f"{custom_list_dir}/{file}")
            custom_lists[pretty_name] = {"filename": file, "df": df}

        df = pl.DataFrame({"REFERENCE": []})
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

        if normalized in discs_df["REFERENCE"].to_list():
            reference_numbers.add(normalized)
        else:
            st.error(f"No match for {reference}")

    df = pl.DataFrame({"REFERENCE": list(reference_numbers)})
    st.session_state.custom_lists["Custom"] = {"df": df}


@st.dialog("Labels", width="large")
def create_label_pdf(filtered_df):
    if filtered_df["REFERENCE"].n_unique() > 100:
        st.error("max labels 100")
        return
    labels_pdf = create_pdf(filtered_df)
    base64_pdf = base64.b64encode(labels_pdf.read()).decode("utf-8")
    pdf_iframe = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="700" height="500" type="application/pdf"></iframe>'
    st.markdown(pdf_iframe, unsafe_allow_html=True)


@st.cache_resource
def load_data():
    discs_df = pl.read_csv("./data/discs.csv")
    discs_df = discs_df.unique()

    titles_df = pl.read_csv("./data/titles.csv")
    titles_df = titles_df.unique()

    df = discs_df.join(titles_df, on="REFERENCE")
    # If you need to transform ARTIST column:
    # df = df.with_columns(
    #     pl.col("ARTIST").str.replace_all(r"^The (.+)", r"\1, The")
    # )

    return df


def main():
    im = Image.open("juke_star.png")
    st.set_page_config(page_title="Laser Juke Explorer", layout="wide", page_icon=im)
    st.image("laserjuke.png")
    load_css("style.css")

    df = load_data()

    st_sidebar = st.sidebar.container()
    custom_lists = load_custom_lists()

    for custom_name, custom_df in custom_lists.items():
        joined_df = df.join(
            custom_df.with_columns(pl.lit(True).alias(custom_name)),
            on="REFERENCE",
            how="left",
        )
        df = joined_df.with_columns(
            pl.col(custom_name).is_not_null().alias(custom_name)
        )

    with st.sidebar:
        custom_lists_df = pl.DataFrame({"Filter On": list(custom_lists.keys())})
        filtered_lists = dynamic_dropdown(custom_lists_df, "Filter On", {})

    if filtered_lists:
        filter_cond = pl.lit(False)
        for list_name in filtered_lists:
            filter_cond |= pl.col(list_name)
        df = df.filter(filter_cond)

    st.sidebar.text_area(
        "Custom List",
        on_change=paste_custom_list,
        key="custom_list_text",
        args=(df,),
    )

    filters = ["SERIES", "COUNTRY", "ARTIST", "TITLE", "REFERENCE"]
    filtered_df = create_filters(df, filters, st_sidebar)

    if st.sidebar.button("Print Labels"):
        create_label_pdf(filtered_df)

    st.sidebar.divider()

    stats_container = st.sidebar.container()
    column_order = [
        "SERIES",
        "COUNTRY",
        "NAME",
        # "REFERENCE",
        "YEAR",
        "MONTH",
    ]
    if st.sidebar.toggle("Discs Only"):
        filtered_df = filtered_df.unique(subset=column_order).sort(
            by=["YEAR", "MONTH", "REFERENCE"],
            descending=[True, True, False],
            nulls_last=True,
        )
    else:
        column_order += ["POSITION", "ARTIST", "TITLE"]

    column_config = {}
    for column in column_order:
        column_config[column] = st.column_config.TextColumn(column.title())
    column_config["YEAR"] = st.column_config.NumberColumn("Year", format="%f")
    column_order += list(custom_lists.keys())

    if stats_container.toggle("Statistics"):
        display_statistics(filtered_df, custom_lists, column_config)

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
