import pandas as pd
from fpdf import FPDF


# Function to format labels
def format_labels(df):
    labels = []
    for _, row in df.iterrows():
        label = f"{row['Artist']}\n{row['Title'].upper()}\n"
        labels.append(label)
    return labels


# Create a PDF class
class PDF(FPDF):
    def header(self):
        if hasattr(self, "ref_num"):
            self.set_font("Arial", "B", 10)
            self.cell(0, 10, self.ref_num, 0, 1, "C")

    def chapter_body(self, body):
        self.set_font("Arial", "", 9)
        self.multi_cell(0, 4, body, 0, "C")

    def add_labels(self, ref_num, labels):
        self.ref_num = ref_num  # Set the ref_num before adding the page
        self.add_page()
        self.chapter_body("\n".join(labels))


def create_pdf(df, output_path):
    pdf = PDF()
    pdf.set_left_margin(10)
    pdf.set_right_margin(10)

    # Group by "Reference Number" and sort by "Position"
    grouped = df.sort_values(by="Position").groupby("Reference Number")

    for ref_num, group in grouped:
        labels = format_labels(group)
        pdf.add_labels(ref_num, labels)

    pdf.output(output_path)
    print("PDF created successfully.")


# # Example usage:
# # Assuming df is your DataFrame with columns: "Reference Number", "Position", "Artist", "Title"
# df = pd.DataFrame(
#     {
#         "Reference Number": ["REF1", "REF1", "REF2", "REF2", "REF3"],
#         "Position": [1, 2, 1, 2, 1],
#         "Artist": ["Artist A", "Artist B", "Artist C", "Artist D", "Artist E"],
#         "Title": ["Title A", "Title B", "Title C", "Title D", "Title E"],
#     }
# )

# create_pdf(df, "output.pdf")
