from pathlib import Path

from PyPDF2 import PdfReader
from openai import OpenAI

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
                   self.authors = [a.strip() for a in authors_str.split(",")]
                elif line.startswith("Category:"):
                    self.category = line.replace("Category:", "").strip()
 
                if "Abstract:" in content:
                    self.abstract = content.split("Abstract:", 1)[1].strip()
                else:
                    print("Abstract not found.") 
            
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
print(f"Filepath:", test_paper.filepath)
print(f"Title:", test_paper.title)
print(f"Authors:", test_paper.authors)
print(f"Category:", test_paper.category)
print(f"Abstract:", test_paper.abstract)

class Archive:
    """
    Stores and analyzes multiple papers
    """
    def __init__(self, folder_path):
        self.folder_path = folder_path
        self.papers = []
        self.load_papers()
    def load_papers(self):
        for filename in os.listdir(self.folder_path):
            if filename.endswith(".txt"):
                path = os.path.join(self.folder_path, filename)
                paper = Paper(path)
                self.papers.append(paper)
    def average_word_count(self):
        counts = [paper.word_count() for paper in self.papers]
        return np.mean(counts) 
    def category_counts(self):
        categories = [paper.category for paper in self.paper]
        return Counter(categories)

archive = Archive("abstracts")
print("Total papers:", len(archive.papers))
print("Average word count:", archive.average_word_count())
print("category distribution:", archive.categroy_counts())

import numpy as np
def average_word_count(self):
    counts = [paper.word_count() for paper in self.papers]
    return np.mean(counts)
def average_author_count(self):
    counts = [paper.author_count() for paper in self.papers]
    return np.mean(counts)

from collections import Counter
def most_common_words(self, n=10):
    all_words = Counter()
    for paper in self.papers:
        all_words.update(paper.keyword_frequency())
    return all_words.most_common(n)

archive = Archive("abstracts/txt")
print("Total papers:", len(archive.papers))
print("Average abstract length:", archive.average_word_count())
print("Average author count:", archive.average_author_count())
print("Most common words:", archive.most_common_words(10))

import matplotlib.pyplot as plt
word_counts = [paper.word_count() for paper in archive.papers]
plt.hist(word_counts)
plt.title("Distribution of Abstract Word Counts")
plt.xlabel("Word Count")
plt.ylabel("Number of Papers")
plt.show()

author_counts = [paper.author_count() for paper in archive.papers]
plt.bar(range(len(author_counts)), author_counts)
plt.title("Number of Authors per Paper")
plt.xlabel("Paper Index")
plt.ylabel("Author Count")
plt.show()
    
from llm_units import summarize_text
archive = Archive("abstracts/txt")
for paper in archive.papers:
    summary = summarize_text(paper.abstract)
    print("\n--- AI Summary ---")
    print(summary)

client = OpenAI

def detect_theme(text):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Classify the research topic in one short phrase."},
            {"role": "user", "content": text}
        ],
    )
    return response.choices[0].message.content
 
def compare_papers(text1, text2):
    prompt = f"""
    Compare these two research abstracts.
    Highlight similarities and differences.

    Paper 1:
    {text}

    Paper 2:
    {text}
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content

    combined = "\n\n".join([p.abstract for p in archive.papers])
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You answer questions based only on the provided research abstracts."},
            {"role": "user", "content": f"Abstracts:\n{combined}\n\nQuestion: {question}"}
        ],
    )

    

    
