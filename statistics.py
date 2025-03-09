import streamlit as st
import pandas as pd


def display_statistics(filtered_df, custom_lists, column_config):
    base_stats = {
        "Statistic": ["Unique Artists", "Unique Songs", "Total Songs", "Total Discs"],
        "Total": [
            filtered_df["ARTIST"].nunique(),
            filtered_df[["TITLE", "ARTIST"]].drop_duplicates().shape[0],
            len(filtered_df),
            filtered_df["REFERENCE"].nunique(),
        ],
    }

    for col in custom_lists:
        list_df = filtered_df[filtered_df[col]]
        base_stats[col] = [
            list_df["ARTIST"].nunique(),
            list_df[["TITLE", "ARTIST"]].drop_duplicates().shape[0],
            len(list_df),
            list_df["REFERENCE"].nunique(),
        ]

    # Create stats DataFrame
    stats_df = pd.DataFrame(base_stats)

    # Function to get counts by groupby columns
    def get_counts(groupby_cols):
        base_counts = (
            filtered_df.groupby(groupby_cols)["REFERENCE"]
            .nunique()
            .reset_index(name="Total")
        )
        for col in custom_lists:
            true_counts = (
                filtered_df[filtered_df[col]]
                .groupby(groupby_cols)["REFERENCE"]
                .nunique()
                .reset_index(name=col)
            )
            base_counts = base_counts.merge(
                true_counts, on=groupby_cols, how="left"
            ).fillna(0)
        return base_counts

    country_counts = get_counts(["COUNTRY"]).sort_values(by="COUNTRY")
    year_counts = get_counts(["YEAR"]).sort_values(by="YEAR", ascending=False)
    country_year_counts = get_counts(["COUNTRY", "YEAR"]).sort_values(
        by=["YEAR", "COUNTRY"], ascending=[False, True]
    )

    # Display the stats
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
