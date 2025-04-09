from fpdf import FPDF
from io import BytesIO

# Define a mapping of Unicode characters to their ASCII replacements
UNICODE_REPLACEMENTS = {
    "\u2018": "'",  # Left Single Quote
    "\u2019": "'",  # Right Single Quote
    "\u201C": '"',  # Left Double Quote
    "\u201D": '"',  # Right Double Quote
    "\u2013": "-",  # En Dash
    "\u2014": "--",  # Em Dash
    "\u2026": "...",  # Ellipsis
    "\u00A0": " ",  # Non-breaking Space
    "\u2022": "*",  # Bullet
    "\u2122": "(TM)",  # Trademark
    "\u00AE": "(R)",  # Registered Trademark
    "\u00A9": "(C)",  # Copyright
    "\u00B0": "°",  # Degree
    # Add more replacements as needed
}


def replace_unicode_chars(text):
    """
    Replaces common Unicode characters with their ASCII equivalents.

    Parameters:
        text (str): The input string to process.

    Returns:
        str: The processed string with Unicode characters replaced.
    """
    for unicode_char, replacement in UNICODE_REPLACEMENTS.items():
        text = text.replace(unicode_char, replacement)
    return text


def format_labels(df):
    """
    Formats labels by sanitizing text fields and concatenating them.

    Parameters:
        df (DataFrame): The input DataFrame containing label information.

    Returns:
        list: A list of formatted label strings.
    """
    labels = []
    for _, row in df.iterrows():
        # Sanitize each field by replacing Unicode characters
        artist = replace_unicode_chars(row["ARTIST"])
        title = replace_unicode_chars(row["TITLE"].upper())
        label = f"{artist}\n{title}\n"
        labels.append(label)
    return labels


class PDF(FPDF):
    def header(self):
        if hasattr(self, "ref_num"):
            self.set_font("Arial", "B", 10)
            self.cell(0, 10, self.ref_num, 0, 1, "C")

    def chapter_body(self, body):
        self.set_font("Arial", "", 9)
        self.multi_cell(0, 4, body, 0, "C")

    def add_labels(self, ref_num, labels):
        self.ref_num = ref_num
        self.add_page()
        self.chapter_body("\n".join(labels))


def create_pdf(df):
    """
    Creates a PDF from the provided DataFrame.

    Parameters:
        df (DataFrame): The input DataFrame containing label information.

    Returns:
        BytesIO: A BytesIO stream containing the generated PDF.
    """
    pdf = PDF()
    pdf.set_left_margin(10)
    pdf.set_right_margin(10)

    grouped = df.sort_values(by="POSITION").groupby("REFERENCE")

    for ref_num, group in grouped:
        labels = format_labels(group)
        pdf.add_labels(ref_num, labels)

    byte_string = pdf.output()
    return BytesIO(byte_string)
