import pandas as pd
import re


def normalize_reference(discs_df, reference):
    pattern = r"(\d{2}\.\d{2}\.\d{2})(.*)"
    if len(reference) == 6:
        reference = reference[:2] + "." + reference[2:4] + "." + reference[4:]
    match = re.match(pattern, reference)
    if match:
        base = match.group(1)
        suffix = match.group(2)
        corresponding_row = discs_df[discs_df["Reference Number"].str.startswith(base)]
        if not corresponding_row.empty:
            suffix = corresponding_row.iloc[0]["Reference Number"][len(base) :]
        return f"{base}{suffix}"
    return None


def main():
    tino_discs_df = pd.read_csv("./tino_discs.csv")
    orig_df = pd.read_csv("./orig.csv")
    normalized_references = []
    for ref in orig_df["Reference Number"]:
        normalized_ref = normalize_reference(tino_discs_df, ref)
        normalized_references.append(normalized_ref)
        if normalized_ref is None:
            print(f"No match found for: {ref}")

    output_df = pd.DataFrame({"Reference Number": normalized_references})
    output_df.to_csv("./normalized.csv", index=False)

    print("Normalization complete")


if __name__ == "__main__":
    main()