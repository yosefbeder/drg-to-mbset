import json
import csv
import io
import re
from flask import Flask, request, render_template, Response, jsonify

app = Flask(__name__)

def convert_json_to_csv(json_data):
    """
    Converts MCQ JSON data (DRG format) to CSV format (MBSET format).
    """
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=[
        "Cas", "Text", "A", "B", "C", "D", "E", "F", "G", "H", 
        "Correct", "Year", "subcategoryName", "Tag", "Type", "tagSuggere", "EXP"
    ])
    writer.writeheader()

    if isinstance(json_data, str):
        data = json.loads(json_data)
    else:
        data = json_data

    quizzes = data.get("mcqQuizzes", [])
    
    for quiz in quizzes:
        quiz_title = quiz.get("title", "")
        # Extract year from title (e.g., "End 2024" -> 2024)
        year_match = re.search(r'\d{4}', quiz_title)
        year = year_match.group(0) if year_match else ""
        
        for q in quiz.get("questions", []):
            text = q.get("text", "")
            options = q.get("options", [])
            correct_index = q.get("correctOptionIndex", 0)
            explanation = q.get("explanation", "")
            
            # Map correctOptionIndex to letter (0 -> A, 1 -> B, ...)
            correct_letter = chr(ord('A') + correct_index) if 0 <= correct_index < 26 else ""
            
            row = {
                "Cas": "",
                "Text": text,
                "A": options[0] if len(options) > 0 else "",
                "B": options[1] if len(options) > 1 else "",
                "C": options[2] if len(options) > 2 else "",
                "D": options[3] if len(options) > 3 else "",
                "E": options[4] if len(options) > 4 else "",
                "F": options[5] if len(options) > 5 else "",
                "G": options[6] if len(options) > 6 else "",
                "H": options[7] if len(options) > 7 else "",
                "Correct": correct_letter,
                "Year": year,
                "subcategoryName": "",
                "Tag": f"Exams, {quiz_title}",
                "Type": "QCS",
                "tagSuggere": "",
                "EXP": explanation
            }
            writer.writerow(row)
            
    return output.getvalue()

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/generate-csv', methods=['POST'])
def generate_csv():
    try:
        if 'file' in request.files and request.files['file'].filename != '':
            json_str = request.files['file'].read().decode('utf-8')
        else:
            json_str = request.form.get('json_data', '')
        
        if not json_str:
            return jsonify({"error": "No JSON data provided"}), 400
            
        csv_data = convert_json_to_csv(json_str)
        return jsonify({"csv": csv_data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/convert', methods=['POST'])
def convert():
    # Keep download endpoint just in case, but primary usage will be via generate-csv
    try:
        # Re-handle data from either file or textarea
        if 'file' in request.files and request.files['file'] and request.files['file'].filename != '':
            json_str = request.files['file'].read().decode('utf-8')
        else:
            json_str = request.form.get('json_data', '')
        
        if not json_str:
            return "No JSON data provided", 400
            
        csv_data = convert_json_to_csv(json_str)
        
        return Response(
            csv_data,
            mimetype="text/csv",
            headers={"Content-disposition": "attachment; filename=mbset_converted.csv"}
        )
    except Exception as e:
        return f"Error: {str(e)}", 500

if __name__ == '__main__':
    # Use 0.0.0.0 to allow access from local network if needed
    app.run(debug=True, port=5005, host='0.0.0.0')
