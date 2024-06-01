import pdfplumber
import re
import bibtexparser

def extract_title_part_from_pdf(pdf_file):
    pattern = (r'(^[0-9])|(^research article)|(^article)|(unclassified)|(www\.)|(accepted (from|manuscript))|'
               r'(proceedings of)|(vol\.)|(volume \d)|(https?://)|(^ieee)|(sciencedirect)|(\d{4}\)$)|'
               r'(\d{1,4} – \d{1,4}$)|(\d{1,4}-\d{1,4}$)|(cid:)|(^doi:)|(^doi )|(^doi$)|(^doi )|(^doi$)|([0-9])')

    with pdfplumber.open(pdf_file) as pdf:
        first_page = pdf.pages[0]
        text = first_page.extract_text()
    
    lines = text.split("\n")

    # Extract title
    for line in lines:
        if re.findall(pattern, line.lower()):
            continue
        return line
    return "Unknown title"

def extract_title_part_from_doc(page_content):
    pattern = (r'(^[0-9])|(^research article)|(^article)|(unclassified)|(www\.)|(accepted (from|manuscript))|'
               r'(proceedings of)|(vol\.)|(volume \d)|(https?://)|(^ieee)|(sciencedirect)|(\d{4}\)$)|'
               r'(\d{1,4} – \d{1,4}$)|(\d{1,4}-\d{1,4}$)|(cid:)')

    lines = page_content.split("\n")
    for line in lines:
        if re.findall(pattern, line.lower()):
            continue
        return line
    return "Unknown title"

        

def remove_braces(text):
    return re.sub(r'[\{\}]', '', text)

def get_first_author(authors):
    if authors:
        first_author = authors.split(' and ')[0]
        return first_author
    return ''

def search_bib(title, bib_file):
    matches = []
    if title == 'Unknown title':
        matches.append(('Unknown title', 'Unknown author'))
        return matches
    with open(bib_file, 'r') as file:
        bib_database = bibtexparser.load(file)
    
    for entry in bib_database.entries:
        entry_title = entry.get('title', '')
        entry_title_cleaned = remove_braces(entry_title)
        if title.lower() in entry_title_cleaned.lower():
            authors = entry.get('author', '')
            first_author = get_first_author(authors)
            matches.append((entry_title_cleaned, first_author))
    if len(matches) == 0:
        matches.append(('Unknown title', 'Unknown author'))
    return matches

def get_title_author_from_pdf(pdf_file, bib_file):
    title_part = extract_title_part_from_pdf(pdf_file)
    matches = search_bib(title_part, bib_file)
    if not matches:
        return (("None", "None"), None)
    return matches