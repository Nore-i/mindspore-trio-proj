import pdfplumber
import re
import bibtexparser
import torch

def preprocess_string(s):
    return ' '.join(s.lower()
                    .replace('.', ' .')
                    .replace('?', ' ?')
                    .replace(',', ' ,')
                    .replace('\'', ' \'')
                    .split())


def detect_similarity(model, device, tokenizer, sentence1, sentence2):
	encoding1 = tokenizer(sentence1, return_tensors='pt', padding=True, truncation=True)
	encoding2 = tokenizer(sentence2, return_tensors='pt', padding=True, truncation=True)
	token_ids1 = torch.LongTensor(encoding1['input_ids'])
	attention_mask1 = torch.LongTensor(encoding1['attention_mask'])
	token_type_ids1 = torch.LongTensor(encoding1['token_type_ids'])
	token_ids2 = torch.LongTensor(encoding2['input_ids'])
	attention_mask2 = torch.LongTensor(encoding2['attention_mask'])
	token_type_ids2 = torch.LongTensor(encoding2['token_type_ids'])

	b_ids1 = token_ids1.to(device)
	b_mask1 = attention_mask1.to(device)
	b_ids2 = token_ids2.to(device)
	b_mask2 = attention_mask2.to(device)

	model.eval()
	cos_sim = model.predict_similarity(b_ids1, b_mask1, b_ids2, b_mask2)

	return cos_sim[0].item()

def detect_paraphrase(model, device, tokenizer, sentence1, sentence2):
	encoding1 = tokenizer(sentence1, return_tensors='pt', padding=True, truncation=True)
	encoding2 = tokenizer(sentence2, return_tensors='pt', padding=True, truncation=True)
	token_ids1 = torch.LongTensor(encoding1['input_ids'])
	attention_mask1 = torch.LongTensor(encoding1['attention_mask'])
	token_type_ids1 = torch.LongTensor(encoding1['token_type_ids'])
	token_ids2 = torch.LongTensor(encoding2['input_ids'])
	attention_mask2 = torch.LongTensor(encoding2['attention_mask'])
	token_type_ids2 = torch.LongTensor(encoding2['token_type_ids'])

	b_ids1 = token_ids1.to(device)
	b_mask1 = attention_mask1.to(device)
	b_ids2 = token_ids2.to(device)
	b_mask2 = attention_mask2.to(device)

	model.eval()
	logits = model.predict_paraphrase(b_ids1, b_mask1, b_ids2, b_mask2)
	y_hat = logits.sigmoid().round().flatten().detach().cpu().numpy()

	return y_hat[0]

def sliding_window_concatenation(strings, window_size=3, max_allowed=5):
    concatenated_strings = []
    for i in range(len(strings) - window_size + 1):
        window = strings[i:i + window_size]
        concatenated_string = ' '.join(window)
        concatenated_strings.append(concatenated_string)
        if len(concatenated_strings) >= max_allowed:
            return concatenated_strings
    return concatenated_strings

def extract_title_part_from_pdf(pdf_file):
    pattern = (r'(^[0-9])|(^research article)|(^article)|(unclassified)|(www\.)|(accepted (from|manuscript))|'
               r'(proceedings of)|(vol\.)|(volume \d)|(https?://)|(^ieee)|(sciencedirect)|(\d{4}\)$)|'
               r'(\d{1,4} – \d{1,4}$)|(\d{1,4}-\d{1,4}$)|(cid:)|(^doi:)|(^doi )|(^doi$)|(^doi )|(^doi$)|([0-9])')

    with pdfplumber.open(pdf_file) as pdf:
        first_page = pdf.pages[0]
        text = first_page.extract_text()

    lines = text.split("\n")
    
    window_size = 3
    max_allowed = 5
    concatenated_results = sliding_window_concatenation(lines, window_size, max_allowed)
    # print(concatenated_results)


    ### Concatenate version: but still buggy
    # non_matching_lines = []
    # for line in concatenated_results:
    #     if not re.findall(pattern, line.lower()):
    #         non_matching_lines.append(line)

    # if non_matching_lines:
    #     print(non_matching_lines)
    #     return non_matching_lines
    # else:
    #     return "Unknown title"

    ### Original version:
    for line in lines:
        if re.findall(pattern, line.lower()):
            continue
        return line, concatenated_results
    return "Unknown title", concatenated_results

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
        # print(authors)
        first_author = authors.split(' and ')[0]
        return first_author
    return ''

def search_bib(title, title_parts, bib_file, model, device, tokenizer):
    matches = []
    if title == 'Unknown title':
        matches.append(('Unknown title', 'Unknown author'))
        return matches
    with open(bib_file, 'r') as file:
        bib_database = bibtexparser.load(file)

    # load model here
    for entry in bib_database.entries:
        entry_title = entry.get('title', '')
        entry_title_cleaned = remove_braces(entry_title)            
        if title.lower() in entry_title_cleaned.lower():
            authors = entry.get('editor') if 'editor' in entry else entry.get('author', '')
            first_author = get_first_author(authors)
            matches.append((entry_title_cleaned, first_author))
            return matches

    highest_similairty = 0.8
    for entry in bib_database.entries:
        entry_title = entry.get('title', '')
        entry_title_cleaned = remove_braces(entry_title)
        
        for tentative_title in title_parts:
            # print(tentative_title)
            similarity = detect_similarity(model, device, tokenizer, tentative_title, entry_title_cleaned)
            if similarity > highest_similairty:
                matches = []
                highest_similairty = similarity
                # print(f"\nHigh similarity {similarity}: \nPDF parts: {tentative_title}\nTitle of paper: {entry_title_cleaned}")
                authors = entry.get('editor') if 'editor' in entry else entry.get('author', '')
                first_author = get_first_author(authors)
                matches.append((entry_title_cleaned, first_author))

    if len(matches) == 0:
        matches.append(('Unknown title', 'Unknown author'))
    return matches

def get_title_author_from_pdf(pdf_file, bib_file, model, device, tokenizer):
    title_re, title_parts = extract_title_part_from_pdf(pdf_file)
    matches = search_bib(title_re, title_parts, bib_file, model, device, tokenizer)
    if not matches:
        return (("None", "None"), None)
    return matches