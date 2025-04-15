import fitz
import re
import pytesseract
import PyPDF2
from pdf2image import convert_from_path
import google.generativeai as genai
from PIL import Image
import io

# Configure Gemini API (only for student answers)
genai.configure(api_key="key")  # Replace with your actual API key

def extract_text_from_pdf(pdf_path):
    """Extract text from digital PDF using PyMuPDF"""
    doc = fitz.open(pdf_path)
    return "\n".join([page.get_text("text") for page in doc]).strip()

def extract_text_from_handwritten_pdf(pdf_path):
    """Extract text from scanned/handwritten PDF using Gemini"""
    images = convert_from_path(pdf_path)
    model = genai.GenerativeModel('gemini-1.5-flash')
    extracted_text = []
    
    for img in images:
        try:
            # Use PIL Image directly with Gemini
            response = model.generate_content([
                "Extract all text from this handwritten answer sheet exactly as written, including question numbers:",
                img  # Pass the PIL Image directly
            ])
            extracted_text.append(response.text)
        except Exception as e:
            print(f"Error processing image with Gemini: {e}")
            # Fallback to pytesseract if Gemini fails
            extracted_text.append(pytesseract.image_to_string(img))
    
    return "\n".join(extracted_text).strip()

def extract_text_from_scanned_pdf(pdf_path):
    """Extract text from scanned PDF (for question paper and model answers) using pytesseract"""
    images = convert_from_path(pdf_path)
    text = ""
    for img in images:
        text += pytesseract.image_to_string(img) + "\n"
    return text.strip()

def extract_answers(text):
    """Extract answers with flexible question number parsing"""
    answers = {}
    current_q = None
    current_ans = []
    
    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue
        
        match = re.match(r"^(?:Q(?:uestion\s*)?)?(\d+[a-zA-Z]*)[\s.):-]+\s*(.*)", line, re.IGNORECASE)
        if match:
            if current_q:
                answers[current_q] = ' '.join(current_ans).strip()
            current_q = match.group(1)
            current_ans = [match.group(2).strip()]
        else:
            current_ans.append(line)
    
    if current_q:
        answers[current_q] = ' '.join(current_ans).strip()
    
    return answers



def extract_max_marks(pdf_path):
    """
    Extracts question-mark mappings from a PDF file.
    Supports formats like: '1. a) ... (10M)' or '1. a)' on one line, '(10M)' on the next.
    
    Returns:
        dict: {'1a': 10, '1b': 4, '2a': 7, ...}
    """
    try:
        text = ""
        with open(pdf_path, "rb") as pdf_file:
            reader = PyPDF2.PdfReader(pdf_file)
            for page in reader.pages:
                text += page.extract_text() or ""

        if not text:
            return None

        lines = [line.strip() for line in text.split('\n') if line.strip()]
        question_marks = {}
        current_question_number = None
        pending_key = None

        for i, line in enumerate(lines):
            # Match full: "1. a)"
            full_match = re.match(r'^(\d+)\.\s*([a-zA-Z])\)', line)
            if full_match:
                current_question_number = full_match.group(1)
                sub_part = full_match.group(2).lower()
                pending_key = f"{current_question_number}{sub_part}"

            else:
                # Match just main number like "1."
                main_match = re.match(r'^(\d+)\.', line)
                if main_match:
                    current_question_number = main_match.group(1)

                # Match just sub-question like "a)"
                subq_match = re.match(r'^([a-zA-Z])\)', line)
                if subq_match and current_question_number:
                    sub = subq_match.group(1).lower()
                    pending_key = f"{current_question_number}{sub}"

            # Look for marks on same line
            mark_match = re.search(r'\(?(\d{1,2})M\)?', line)
            if mark_match and pending_key:
                marks = int(mark_match.group(1))
                question_marks[pending_key] = marks
                pending_key = None

            # Look for marks in the next line
            elif pending_key and i + 1 < len(lines):
                next_line = lines[i + 1]
                next_match = re.search(r'\(?(\d{1,2})M\)?', next_line)
                if next_match:
                    marks = int(next_match.group(1))
                    question_marks[pending_key] = marks
                    pending_key = None

        print("✅ Extracted question marks:", question_marks)
        return question_marks

    except Exception as e:
        print(f"❌ Error during PDF processing: {e}")
        return None











