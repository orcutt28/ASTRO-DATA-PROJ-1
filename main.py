from pathlib import Path

from PyPDF2 import PdfReader

def convert_pdf_to_txt_file(pdf_path, output_path):
    """
    Convert a PDF file into a text file.
    """
    try:
        reader = PdfReader(str(pdf_path))
        text = ""
        for page in reader.pages:
            text += (page.extract_text() or "") + "\n"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"Converted: {pdf_path} -> {output_path}")
    except Exception as e:
        print(f"Error converting {pdf_path}: {e}")

def convert_all_pdfs():
    base_dir = Path(__file__).resolve().parent
    pdf_folder = base_dir / "abstracts" / "pdfs"
    txt_folder = base_dir / "abstracts" / "txt"
    txt_folder.mkdir(parents=True, exist_ok=True)

    for pdf_path in sorted(pdf_folder.glob("*.pdf")):
        if pdf_path.is_file():
            filename = pdf_path.name

            txt_filename = filename.replace(".pdf", ".txt")
            output_path = txt_folder / txt_filename

            convert_pdf_to_txt_file(pdf_path, output_path)

if __name__ == "__main__":
    convert_all_pdfs()
    print("Program is running!")

import os
from collections import Counter
import numpy as np
import matplotlib.pyplot as plt

class Paper:
    """
    Represents one arXiv paper.
    Extracts title, authors, category, and abstract.
    """

    def __init__(self, filepath):
        self.filepath = filepath
        self.title = ""
        self.authors = []
        self.category = ""
        self.abstract = ""

        self.load_paper()

    
    def load_paper(self):
        """Reads file and extracts metadata."""
        try:
            with open(self.filepath, 'r', encoding="utf-8") as f:
                content = f.read()

            lines = content.split("\n")

            for line in lines:
                line = line.strip()

                if line.startswith("Title:"):
                    self.title = line.replace("Title:", "").strip()

                elif line.startswith("Authors:"):
                   authors_str = line.replace("Authors:", "").strip()
                   self.authors = [a.strip() for a in authors_str.split("'")]
                elif line.startswith("Category:"):
                    self.category = line.replace("Category:", "").strip()

            self.abstract = content.split("Abstract:")[1].strip()
            
        except Exception as e:
            print(f"Error loading {self.filepath}: {e}")

    def word_count(self):
        return len(self.abstract.split())

    def author_count(self):
        return len(self.authors)

    def keyword_frequency(self):
        words = self.abstract.lower().split()
        return Counter(words)

# TEST PAPER
test_paper = Paper("abstracts/txt/paper1.txt")

print("Filepath:", test_paper.filepath)
print("Title:", test_paper.title)
print("Authors:", test_paper.authors)
print("Category:", test_paper.category)
print("Abstract:", test_paper.abstract)



