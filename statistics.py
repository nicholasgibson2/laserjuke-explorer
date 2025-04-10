import streamlit as st
import polars as pl


def display_statistics(filtered_df, custom_lists, column_config):
    base_stats = {
        "Statistic": ["Unique Artists", "Unique Songs", "Total Songs", "Total Discs"],
        "Total": [
            filtered_df["ARTIST"].n_unique(),
            filtered_df.select(["TITLE", "ARTIST"]).unique().height,
            filtered_df.height,
            filtered_df["REFERENCE"].n_unique(),
        ],
    }

    for col in custom_lists:
        list_df = filtered_df.filter(pl.col(col))
        base_stats[col] = [
            list_df["ARTIST"].n_unique(),
            list_df.select(["TITLE", "ARTIST"]).unique().height,
            list_df.height,
            list_df["REFERENCE"].n_unique(),
        ]

    # Create stats DataFrame
    stats_df = pl.DataFrame(base_stats)

    # Function to get counts by groupby columns
    def get_counts(groupby_cols):
        base_counts = filtered_df.group_by(groupby_cols).agg(
            pl.col("REFERENCE").n_unique().alias("Total")
        )

        for col in custom_lists:
            true_counts = (
                filtered_df.filter(pl.col(col))
                .group_by(groupby_cols)
                .agg(pl.col("REFERENCE").n_unique().alias(col))
            )
            base_counts = base_counts.join(
                true_counts, on=groupby_cols, how="left"
            ).fill_null(0)

        return base_counts

    country_counts = get_counts(["COUNTRY"]).sort("COUNTRY", nulls_last=True)
    year_counts = get_counts(["YEAR"]).sort("YEAR", descending=True, nulls_last=True)
    country_year_counts = get_counts(["COUNTRY", "YEAR"]).sort(
        ["YEAR", "COUNTRY"], descending=[True, False], nulls_last=True
    )

    st.dataframe(
        stats_df,
        hide_index=True,
        use_container_width=True,
    )

    col1, col2, col3 = st.columns(3)

    col1.dataframe(
        country_counts,
        column_config=column_config,
        hide_index=True,
        use_container_width=True,
    )
    col2.dataframe(
        year_counts,
        column_config=column_config,
        hide_index=True,
        use_container_width=True,
    )
    col3.dataframe(
        country_year_counts,
        column_config=column_config,
        hide_index=True,
        use_container_width=True,
    )
