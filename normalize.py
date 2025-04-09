import polars as pl
import re


def normalize_reference(discs_df, reference):
    pattern = r"(\d{2}\.\d{2}\.\d+)(.*)"
    match = re.match(pattern, reference)
    if match:
        base = match.group(1)
        suffix = match.group(2)
        corresponding_row = discs_df.filter(pl.col("REFERENCE").str.starts_with(base))
        if corresponding_row.height > 0:
            suffix = corresponding_row["REFERENCE"][0][len(base) :]
        return f"{base}{suffix}"
    return reference


def main():
    discs_df = pl.read_csv("./data/discs.csv")
    orig_df = pl.read_csv("./orig.csv")

    normalized_references = []
    for ref in orig_df["REFERENCE"]:
        normalized_ref = normalize_reference(discs_df, ref)
        normalized_references.append(normalized_ref)
        if normalized_ref is None:
            print(f"No match found for: {ref}")

    output_df = pl.DataFrame({"REFERENCE": normalized_references})
    output_df.write_csv("./normalized.csv")

    print("Normalization complete")


if __name__ == "__main__":
    main()
