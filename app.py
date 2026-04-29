import json
import csv
import io
import re
import os
import requests
import zipfile
import shutil
import tempfile
from flask import Flask, request, render_template, Response, jsonify, send_file

app = Flask(__name__)

def convert_json_to_csv(json_data, images_dir=None, tag=None, year=None, subcategory_name=None, tag_suggere=None):
    """
    Converts MCQ JSON data (DRG format) to CSV format (MBSET format).
    If images_dir is provided, it downloads images and stores them there.
    """
    output = io.StringIO()
    fieldnames = [
        "Cas", "Text", "A", "B", "C", "D", "E", "F", "G", "H", 
        "Correct", "Year", "subcategoryName", "Tag", "Type", "tagSuggere", "EXP", "Image"
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    if isinstance(json_data, str):
        data = json.loads(json_data)
    else:
        data = json_data

    quizzes = data.get("mcqQuizzes", [])
    
    image_counter = 1
    for quiz in quizzes:
        quiz_title = quiz.get("title", "")
        # Use manual year provided by user
        
        for q in quiz.get("questions", []):
            text = q.get("text", "")
            options = q.get("options", [])
            correct_index = q.get("correctOptionIndex", 0)
            explanation = q.get("explanation", "")
            image_url = q.get("image")
            
            image_filename = ""
            if image_url:
                # Generate a name: img_1, img_2, etc. or use id if available
                q_id = q.get("id") or q.get("uniqueId")
                image_name = f"image_{q_id}" if q_id else f"image_{image_counter}"
                image_filename = f"{image_name}.jpeg"
                
                if images_dir:
                    try:
                        # Download image
                        response = requests.get(image_url, stream=True, timeout=10)
                        if response.status_code == 200:
                            image_path = os.path.join(images_dir, image_filename)
                            with open(image_path, 'wb') as f:
                                shutil.copyfileobj(response.raw, f)
                        else:
                            image_filename = "" # Reset if download failed
                    except Exception as e:
                        print(f"Error downloading image {image_url}: {e}")
                        image_filename = ""
                
                image_counter += 1

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
                "subcategoryName": subcategory_name if subcategory_name else "",
                "Tag": tag,
                "Type": "QCS",
                "tagSuggere": tag_suggere if tag_suggere else "",
                "EXP": explanation,
                "Image": image_filename if image_filename else ""
            }
            writer.writerow(row)
            
    has_images = image_counter > 1
    return output.getvalue(), has_images

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
            
        tag = request.form.get('tag', '').strip()
        year = request.form.get('year', '').strip()
        lecture = request.form.get('lecture', '').strip()
        subject = request.form.get('subject', '').strip()
        
        if not tag:
            return jsonify({"error": "Tag field is required"}), 400

        csv_data, has_images = convert_json_to_csv(json_str, tag=tag, year=year, subcategory_name=lecture, tag_suggere=subject)
        return jsonify({"csv": csv_data, "has_images": has_images})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/convert', methods=['POST'])
def convert():
    try:
        # Re-handle data from either file or textarea
        if 'file' in request.files and request.files['file'] and request.files['file'].filename != '':
            json_str = request.files['file'].read().decode('utf-8')
        else:
            json_str = request.form.get('json_data', '')
        
        if not json_str:
            return "No JSON data provided", 400
            
        # Create a temporary directory for processing
        with tempfile.TemporaryDirectory() as tmp_dir:
            images_dir = os.path.join(tmp_dir, "images")
            os.makedirs(images_dir, exist_ok=True)
            
            custom_tag = request.form.get('tag', '').strip() # Changed from custom_tag to match form
            manual_year = request.form.get('year', '').strip() # Changed from manual_year to match form
            lecture = request.form.get('lecture', '').strip()
            subject = request.form.get('subject', '').strip()
            
            csv_data, has_images = convert_json_to_csv(
                json_str, 
                images_dir=images_dir, 
                tag=custom_tag, 
                year=manual_year,
                subcategory_name=lecture,
                tag_suggere=subject
            )
            
            # Create a zip file containing ONLY the images folder
            memory_file = io.BytesIO()
            with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
                
                # Add images folder
                for root, dirs, files in os.walk(images_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        # Archive path should be images/filename.jpeg
                        arcname = os.path.relpath(file_path, tmp_dir)
                        zf.write(file_path, arcname=arcname)
            
            memory_file.seek(0)
            
            return send_file(
                memory_file,
                mimetype="application/zip",
                as_attachment=True,
                download_name="images.zip"
            )
            
    except Exception as e:
        return f"Error: {str(e)}", 500

if __name__ == '__main__':
    # Use 0.0.0.0 to allow access from local network if needed
    app.run(debug=True, port=5005, host='0.0.0.0')
