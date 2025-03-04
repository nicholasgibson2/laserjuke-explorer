import pandas as pd
import re


def normalize_reference(discs_df, reference):
    pattern = r"(\d{2}\.\d{2}\.\d+)(.*)"
    match = re.match(pattern, reference)
    if match:
        base = match.group(1)
        suffix = match.group(2)
        corresponding_row = discs_df[discs_df["REFERENCE"].str.startswith(base)]
        if not corresponding_row.empty:
            suffix = corresponding_row.iloc[0]["REFERENCE"][len(base) :]
        return f"{base}{suffix}"
    return reference


def main():
    discs_df = pd.read_csv("./data/discs.csv")
    orig_df = pd.read_csv("./orig.csv")
    normalized_references = []
    for ref in orig_df["REFERENCE"]:
        normalized_ref = normalize_reference(discs_df, ref)
        normalized_references.append(normalized_ref)
        if normalized_ref is None:
            print(f"No match found for: {ref}")

    output_df = pd.DataFrame({"REFERENCE": normalized_references})
    output_df.to_csv("./normalized.csv", index=False)

    print("Normalization complete")


if __name__ == "__main__":
    main()
