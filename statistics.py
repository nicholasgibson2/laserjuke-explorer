import streamlit as st
import polars as pl


def display_statistics(filtered_df, custom_lists, column_config):
    st.subheader("Discs")
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
    stats_df = pl.DataFrame(base_stats)

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

    st.subheader("Artists/Songs")

    top_artists = (
        filtered_df.group_by("ARTIST")
        .agg(pl.len().alias("Count"))
        .sort("Count", descending=True)
        .with_columns(pl.col("Count").rank(method="min", descending=True).alias("Rank"))
        .select(["Rank", "ARTIST", "Count"])
    )

    all_songs_ranked = (
        filtered_df.group_by(["ARTIST", "TITLE"])
        .agg(pl.len().alias("Count"))
        .sort("Count", descending=True)
        .with_columns(pl.col("Count").rank(method="min", descending=True).alias("Rank"))
        .select(["Rank", "ARTIST", "TITLE", "Count"])
    )

    col1, col2 = st.columns(2)
    with col1:
        st.dataframe(
            top_artists,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Rank": st.column_config.NumberColumn("Rank", width="small"),
                "ARTIST": st.column_config.TextColumn("Artist"),
                "Count": st.column_config.NumberColumn("Song Count"),
            },
        )
    with col2:
        st.dataframe(
            all_songs_ranked,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Rank": st.column_config.NumberColumn("Rank", width="small"),
                "ARTIST": st.column_config.TextColumn("Artist"),
                "TITLE": st.column_config.TextColumn("Song Title"),
                "Count": st.column_config.NumberColumn("Count"),
            },
        )
