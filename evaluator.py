from sentence_transformers import SentenceTransformer, util
from utils import extract_text_from_pdf, extract_text_from_handwritten_pdf, extract_text_from_scanned_pdf, extract_answers
import re

model = SentenceTransformer("paraphrase-mpnet-base-v2")

def correct_ocr_text(student_text, model_answer):
    """Basic OCR error correction using model answer as reference"""
    corrections = {
        r'\+ake': 'make',
        r'teh': 'the',
        r'adn': 'and',
        r'wih': 'with',
        r'[l1]ike': 'like'
    }
    
    for pattern, replacement in corrections.items():
        student_text = re.sub(pattern, replacement, student_text, flags=re.IGNORECASE)
    
    return student_text

def evaluate_similarity(student_answer, model_answer):
    emb1 = model.encode(student_answer, convert_to_tensor=True)
    emb2 = model.encode(model_answer, convert_to_tensor=True)
    similarity = util.pytorch_cos_sim(emb1, emb2).item()
    return round(similarity * 100, 2)

def evaluate_pdfs(student_pdf, model_pdf, max_marks):
    # Use Gemini for student answers
    student_text = extract_text_from_handwritten_pdf(student_pdf)
    print(student_text)
    # Use pytesseract for model answers (assuming they might be scanned)
    model_text = extract_text_from_scanned_pdf(model_pdf)

    student_answers = extract_answers(student_text)
    model_answers = extract_answers(model_text)

    results = []
    total_marks = 0

    student_question_numbers = list(student_answers.keys()) # Get the keys of the students answer dict.

    # Handle unit completion logic
    processed_units = set()
    for q_num, model_ans in model_answers.items():
        unit_num = q_num[0] # Extract the unit number (e.g., '1' from '1a')

        if unit_num in processed_units:
            continue # Skip if unit is already processed

        # Check if both 'a' and 'b' are answered
        a_part = f"{unit_num}a"
        b_part = f"{unit_num}b"

        if a_part in student_question_numbers and b_part in student_question_numbers:
            # Both parts are answered, evaluate them
            question_max_a = max_marks.get(a_part, 7)
            student_ans_a = student_answers.get(a_part, "No answer provided.")
            corrected_ans_a = correct_ocr_text(student_ans_a, model_answers.get(a_part, ""))
            similarity_a = evaluate_similarity(corrected_ans_a, model_answers.get(a_part, ""))
            score_a = round((similarity_a / 100) * question_max_a, 2)
            total_marks += score_a

            results.append({
                "question": f"Q{a_part}",
                "max_marks": question_max_a,
                "score": score_a,
                "similarity": similarity_a,
                "student_answer": corrected_ans_a,
                "model_answer": model_answers.get(a_part, "")
            })

            question_max_b = max_marks.get(b_part, 7)
            student_ans_b = student_answers.get(b_part, "No answer provided.")
            corrected_ans_b = correct_ocr_text(student_ans_b, model_answers.get(b_part, ""))
            similarity_b = evaluate_similarity(corrected_ans_b, model_answers.get(b_part, ""))
            score_b = round((similarity_b / 100) * question_max_b, 2)
            total_marks += score_b

            results.append({
                "question": f"Q{b_part}",
                "max_marks": question_max_b,
                "score": score_b,
                "similarity": similarity_b,
                "student_answer": corrected_ans_b,
                "model_answer": model_answers.get(b_part, "")
            })

            processed_units.add(unit_num) # Mark unit as processed
        else:
            # Handle cases where only 'a' or 'b' is answered
            if a_part in student_question_numbers:
                question_max_a = max_marks.get(a_part, 7)
                student_ans_a = student_answers.get(a_part, "No answer provided.")
                corrected_ans_a = correct_ocr_text(student_ans_a, model_answers.get(a_part, ""))
                similarity_a = evaluate_similarity(corrected_ans_a, model_answers.get(a_part, ""))
                score_a = round((similarity_a / 100) * question_max_a, 2)
                total_marks += score_a

                results.append({
                    "question": f"Q{a_part}",
                    "max_marks": question_max_a,
                    "score": score_a,
                    "similarity": similarity_a,
                    "student_answer": corrected_ans_a,
                    "model_answer": model_answers.get(a_part, "")
                })
                processed_units.add(unit_num)

            if b_part in student_question_numbers:
                question_max_b = max_marks.get(b_part, 7)
                student_ans_b = student_answers.get(b_part, "No answer provided.")
                corrected_ans_b = correct_ocr_text(student_ans_b, model_answers.get(b_part, ""))
                similarity_b = evaluate_similarity(corrected_ans_b, model_answers.get(b_part, ""))
                score_b = round((similarity_b / 100) * question_max_b, 2)
                total_marks += score_b

                results.append({
                    "question": f"Q{b_part}",
                    "max_marks": question_max_b,
                    "score": score_b,
                    "similarity": similarity_b,
                    "student_answer": corrected_ans_b,
                    "model_answer": model_answers.get(b_part, "")
                })
                processed_units.add(unit_num)

    return results, round(total_marks, 2)