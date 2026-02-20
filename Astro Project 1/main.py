from pathlib import Path
from collections import Counter
import re

try:
    from PyPDF2 import PdfReader
except ImportError:
    PdfReader = None


def convert_pdf_to_txt_file(pdf_path, output_path):
    """
    Convert a PDF file into a text file.
    """
    if PdfReader is None:
        print("Error: PyPDF2 is not installed. Please install it with: pip install PyPDF2")
        return
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
            
            # Check if file uses labeled format (Title:, Authors:, etc.)
            has_labels = any(line.strip().startswith("Title:") for line in lines[:20])
            
            if has_labels:
                # Original labeled format
                for line in lines:
                    line = line.strip()

                    if line.startswith("Title:"):
                        self.title = line.replace("Title:", "").strip()

                    elif line.startswith("Authors:"):
                        authors_str = line.replace("Authors:", "").strip()
                        self.authors = [a.strip() for a in authors_str.split(",") if a.strip()]

                    elif line.startswith("Category:"):
                        self.category = line.replace("Category:", "").strip()

                # Extract abstract safely
                if "Abstract:" in content:
                    self.abstract = content.split("Abstract:")[1].strip()
                else:
                    self.abstract = ""
            else:
                # PDF-extracted format: parse title, authors, abstract from raw text
                # Find title (usually early lines, before authors)
                title_lines = []
                author_start_idx = None
                
                for i, line in enumerate(lines[:20]):  # Check first 20 lines
                    stripped = line.strip()
                    # Skip header lines (journal names, dates, etc.)
                    if not stripped or len(stripped) < 10:
                        continue
                    # Skip lines that look like headers (all caps, dates, etc.)
                    if stripped.isupper() or any(x in stripped.lower() for x in ['preprint', 'doi:', 'accepted', 'received']):
                        continue
                    # Title is usually before authors (which have numbers/superscripts)
                    if not any(char.isdigit() for char in stripped[:5]) and not stripped.startswith('*'):
                        if author_start_idx is None:
                            title_lines.append(stripped)
                        else:
                            break
                    else:
                        # Found author line (has numbers or starts with *)
                        if author_start_idx is None:
                            author_start_idx = i
                            # Join accumulated title lines
                            self.title = " ".join(title_lines).strip()
                            break
                
                # If title not found yet, try simpler approach
                if not self.title and len(lines) > 2:
                    # Title is often on lines 2-5
                    potential_title = []
                    for i in range(1, min(6, len(lines))):
                        stripped = lines[i].strip()
                        if stripped and len(stripped) > 10:
                            # Stop if we hit authors (has numbers or email markers)
                            if any(char.isdigit() for char in stripped[:5]) or '@' in stripped:
                                break
                            potential_title.append(stripped)
                    if potential_title:
                        self.title = " ".join(potential_title).strip()
                
                # Extract authors (lines with numbers/superscripts after title)
                author_lines = []
                if author_start_idx is not None:
                    for i in range(author_start_idx, min(author_start_idx + 10, len(lines))):
                        stripped = lines[i].strip()
                        if not stripped:
                            break
                        # Author lines typically have numbers or email markers
                        if any(char.isdigit() for char in stripped[:10]) or '@' in stripped or '*' in stripped:
                            author_lines.append(stripped)
                        elif stripped.startswith('1') or stripped.startswith('*'):
                            author_lines.append(stripped)
                        else:
                            # Stop at affiliations
                            if any(x in stripped.lower() for x in ['department', 'university', 'institute', 'school']):
                                break
                
                # Parse authors from author lines
                if author_lines:
                    # Extract author names (before numbers/email)
                    authors_text = " ".join(author_lines)
                    # Split by common delimiters
                    # Remove email addresses and ORCID
                    authors_text = re.sub(r'\S+@\S+', '', authors_text)
                    authors_text = re.sub(r'ORCID:\s*\d+[-\d\s]*', '', authors_text)
                    # Split by commas and 'and'
                    author_parts = re.split(r',\s*and\s*|,\s*|\s+and\s+', authors_text)
                    self.authors = [a.strip() for a in author_parts if a.strip() and len(a.strip()) > 2]
                    # Clean up author names (remove numbers, asterisks)
                    self.authors = [re.sub(r'[\d★*]', '', a).strip() for a in self.authors]
                    self.authors = [a for a in self.authors if len(a) > 2]
                
                # Extract abstract (starts with "ABSTRACT" or "Abstract")
                abstract_start = None
                for i, line in enumerate(lines):
                    stripped = line.strip().upper()
                    if stripped == "ABSTRACT" or (stripped.startswith("ABSTRACT") and len(stripped) < 20):
                        abstract_start = i + 1
                        break
                
                if abstract_start is not None:
                    abstract_lines = []
                    # Abstract continues until introduction section
                    for i in range(abstract_start, len(lines)):
                        stripped = lines[i].strip()
                        # Stop at introduction or keywords section
                        if re.match(r'^\d+\s+(INTRODUCTION|Introduction|INTRO)', stripped) or \
                           stripped.upper().startswith('KEY WORDS') or \
                           stripped.upper().startswith('KEYWORDS'):
                            break
                        if stripped:
                            abstract_lines.append(stripped)
                    self.abstract = " ".join(abstract_lines).strip()
                else:
                    # Fallback: try to find abstract section
                    abstract_match = re.search(r'(?i)abstract[:\s]*(.+?)(?=\d+\s+(?:INTRODUCTION|Introduction|INTRO)|Keywords|Key words)', content, re.DOTALL)
                    if abstract_match:
                        self.abstract = abstract_match.group(1).strip()
                    else:
                        self.abstract = ""
                
                # Extract category from keywords if available
                keywords_match = re.search(r'(?i)(?:Keywords|Key words)[:\s]*(.+?)(?=\d+\s+(?:INTRODUCTION|Introduction|INTRO)|$)', content, re.DOTALL)
                if keywords_match:
                    self.category = keywords_match.group(1).strip()[:100]  # Limit length

        except Exception as e:
            print(f"Error loading {self.filepath}: {e}")

    def word_count(self):
        return len(self.abstract.split()) if self.abstract else 0

    def author_count(self):
        return len(self.authors)

    def keyword_frequency(self):
        words = self.abstract.lower().split() if self.abstract else []
        return Counter(words)

    def get_searchable_text(self):
        """
        Get combined title and abstract text for searching.
        """
        return f"{self.title} {self.abstract}"

    def contains_keywords(self, keywords, case_sensitive=False):
        """
        Check if the paper contains any of the specified keywords.
        
        Args:
            keywords: List of keywords to search for
            case_sensitive: If False, search is case-insensitive (default)
        
        Returns:
            bool: True if any keyword is found in title or abstract
        """
        if not keywords:
            return True
        
        search_text = self.get_searchable_text()
        
        if not case_sensitive:
            search_text = search_text.lower()
            keywords = [kw.lower() for kw in keywords]
        
        # Check if any keyword appears in the text
        for keyword in keywords:
            if keyword in search_text:
                return True
        
        return False

    def get_matching_keywords(self, keywords, case_sensitive=False):
        """
        Get the list of keywords that match in this paper.
        
        Args:
            keywords: List of keywords to search for
            case_sensitive: If False, search is case-insensitive (default)
        
        Returns:
            list: List of matching keywords
        """
        if not keywords:
            return []
        
        search_text = self.get_searchable_text()
        
        if not case_sensitive:
            search_text = search_text.lower()
            keywords_lower = [kw.lower() for kw in keywords]
        else:
            keywords_lower = keywords
        
        matching = []
        for i, keyword in enumerate(keywords_lower):
            if keyword in search_text:
                matching.append(keywords[i] if case_sensitive else keywords[i])
        
        return matching


# Default astrophysics keywords
DEFAULT_ASTROPHYSICS_KEYWORDS = [
    "galaxy", "galaxies", "galactic",
    "star", "stars", "stellar",
    "black hole", "blackhole", "black holes",
    "nebula",
    "supernova", "supernovae",
    "quasar", "quasars",
    "cosmic", "cosmology", "cosmological",
    "dark matter", "dark energy",
    "redshift",
    "spectroscopy", "spectroscopic",
    "exoplanet", "exoplanets",
    "planet", "planetary",
    "asteroid", "asteroids",
    "comet", "comets",
    "meteor", "meteors",
    "pulsar", "pulsars",
    "neutron star", "neutron stars",
    "white dwarf", "white dwarfs",
    "interstellar", "intergalactic",
    "magnetic field", "magnetic fields",
    "radiation", "radiative",
    "emission", "emission line",
    "absorption", "absorption line",
    "wavelength", "wavelengths",
    "infrared", "ultraviolet", "x-ray", "gamma ray",
    "telescope", "observatory",
    "hubble", "jwst", "chandra", "spitzer",
    "merger", "mergers", "merging",
    "starburst", "star formation",
    "metallicity", "metallicities",
    "evolution", "evolutionary",
    "cluster", "clusters",
    "halo", "halos"
]


def filter_papers_by_keywords(papers, keywords=None, case_sensitive=False):
    """
    Filter papers by multiple astrophysics keywords.
    
    Args:
        papers: List of Paper objects to filter
        keywords: List of keywords to search for. If None, uses DEFAULT_ASTROPHYSICS_KEYWORDS
        case_sensitive: If False, search is case-insensitive (default)
    
    Returns:
        list: Filtered list of Paper objects (papers containing ANY keyword)
    """
    if keywords is None:
        keywords = DEFAULT_ASTROPHYSICS_KEYWORDS
    
    if not keywords:
        return papers
    
    filtered_papers = []
    
    for paper in papers:
        # Paper must contain ANY keyword
        if paper.contains_keywords(keywords, case_sensitive):
            filtered_papers.append(paper)
    
    return filtered_papers


def filter_papers_from_files(file_paths, keywords=None, case_sensitive=False):
    """
    Load papers from file paths and filter them by keywords.
    
    Args:
        file_paths: List of file paths (strings or Path objects) to paper text files
        keywords: List of keywords to search for. If None, uses DEFAULT_ASTROPHYSICS_KEYWORDS
        case_sensitive: If False, search is case-insensitive (default)
    
    Returns:
        list: Filtered list of Paper objects (papers containing ANY keyword)
    """
    papers = [Paper(path) for path in file_paths]
    return filter_papers_by_keywords(papers, keywords, case_sensitive)


def load_all_papers(base_dir=None):
    """
    Load all papers from paper1.txt through paper10.txt.
    
    Args:
        base_dir: Base directory path. If None, uses the directory containing main.py
    
    Returns:
        list: List of Paper objects (may contain None for missing files)
    """
    if base_dir is None:
        base_dir = Path(__file__).resolve().parent
    else:
        base_dir = Path(base_dir)
    
    # Papers are in the 'papers' subdirectory
    papers_dir = base_dir / "papers"
    
    papers = []
    for i in range(1, 11):
        paper_file = papers_dir / f"paper{i}.txt"
        if paper_file.exists():
            papers.append(Paper(paper_file))
        else:
            print(f"Warning: {paper_file} not found, skipping...")
            papers.append(None)
    
    # Filter out None values (missing files)
    return [p for p in papers if p is not None]


if __name__ == "__main__":
    convert_all_pdfs()
    print("Program is running!")

    # Import all papers (paper1.txt through paper10.txt)
    print("\n" + "="*60)
    print("LOADING ALL PAPERS")
    print("="*60)
    all_papers = load_all_papers()
    print(f"\nLoaded {len(all_papers)} papers")
    
    # Display loaded papers
    for i, paper in enumerate(all_papers, 1):
        if paper:
            print(f"\nPaper {i}:")
            print(f"  Filepath: {paper.filepath}")
            print(f"  Title: {paper.title[:80]}..." if len(paper.title) > 80 else f"  Title: {paper.title}")
            print(f"  Authors: {len(paper.authors)} author(s)")
            print(f"  Category: {paper.category}")
            print(f"  Abstract length: {paper.word_count()} words")
    
    # TEST PAPER (keeping original test code)
    print("\n" + "="*60)
    print("TEST PAPER (paper1.txt)")
    print("="*60)
    test_paper = Paper(Path(__file__).resolve().parent / "papers" / "paper1.txt")
    print("Filepath:", test_paper.filepath)
    print("Title:", test_paper.title)
    print("Authors:", test_paper.authors)
    print("Category:", test_paper.category)
    print("Abstract:", test_paper.abstract[:200] + "..." if len(test_paper.abstract) > 200 else test_paper.abstract)
    
    # Example: Filter papers by keywords
    print("\n" + "="*60)
    print("FILTERING PAPERS BY KEYWORDS")
    print("="*60)
    
    if all_papers:
        # Example 1: Filter using default astrophysics keywords
        print("\n--- Example 1: Filter by default astrophysics keywords ---")
        filtered_papers = filter_papers_by_keywords(all_papers)
        print(f"Found {len(filtered_papers)} papers matching default keywords")
        for paper in filtered_papers[:3]:  # Show first 3
            print(f"  - {paper.title[:60]}...")
        
        # Example 2: Filter by custom keywords
        print("\n--- Example 2: Filter by custom keywords ---")
        custom_keywords = ["galaxy", "merger", "starburst"]
        filtered_custom = filter_papers_by_keywords(all_papers, keywords=custom_keywords)
        print(f"Found {len(filtered_custom)} papers containing: {custom_keywords}")
        for paper in filtered_custom[:3]:  # Show first 3
            matching = paper.get_matching_keywords(custom_keywords)
            print(f"  - {paper.title[:60]}...")
            print(f"    Matching keywords: {matching}")
    else:
        print("\nNo papers loaded")



