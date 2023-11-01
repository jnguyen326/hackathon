from flask import Flask, render_template, request, redirect, url_for, flash
import os
from google.cloud import storage
import vertexai
from vertexai.language_models import TextGenerationModel
from dotenv import load_dotenv
import configparser
import PyPDF2
from io import BytesIO

load_dotenv()

# Getter config variables
config = configparser.ConfigParser()
config.read('.config')
GCS_BUCKET_NAME = config['DEFAULT']['GCS_BUCKET_NAME']
SERVICE_ACCOUNT_PATH = config['DEFAULT']['SERVICE_ACCOUNT_PATH']
SECRET_KEY = config['DEFAULT']['SECRET_KEY']

app = Flask(__name__)
app.secret_key = SECRET_KEY

# Set up Google Cloud Storage
storage_client = storage.Client.from_service_account_json(SERVICE_ACCOUNT_PATH)
bucket = storage_client.bucket(GCS_BUCKET_NAME)

# Initialize vertexai
vertexai.init(project="calm-brook-403808", location="us-central1")
parameters = {
    "candidate_count": 1,
    "max_output_tokens": 1024,
    "temperature": 0.2,
    "top_p": 0.8,
    "top_k": 40
}
model = TextGenerationModel.from_pretrained("text-bison")

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # Extract text from PDF
        pdf = request.files["file"]
        pdf_data = pdf.read()
        if not pdf_data:
            return "Uploaded file is empty. Please upload a valid PDF."

        pdf_file = BytesIO(pdf_data)

        # Upload to GCS
        blob = bucket.blob(pdf.filename)
        blob.upload_from_file(pdf_file)  # We're uploading pdf_file, not pdf

        # Process the PDF content
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:  # Iterating directly over pages
            text += page.extract_text()  # Changed this line to use the new method

        # Feed the extracted text to vertexai model
        response = model.predict(text, **parameters)

        flash(f"Design evaluated: {response.text}")
        return redirect(url_for("index"))

    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)
