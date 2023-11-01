from flask import Flask, render_template, request, redirect, url_for, flash
import os
from google.cloud import storage
from google.cloud import aiplatform
import PyPDF2
from io import BytesIO
import vertexai
from vertexai.language_models import TextGenerationModel

app = Flask(__name__)
app.secret_key = "your_secret_key"  # for flash messaging

# Set up Google Cloud Storage
GCS_BUCKET_NAME = "cloud-ai-platform-5b21884c-0af6-4620-9a37-b1d5f8588f35"
storage_client = storage.Client.from_service_account_json("C:\\Users\Owner\\PycharmProjects\\hackathon\\calm-brookkey.json")
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
        # Upload to GCS
        pdf = request.files["file"]
        blob = bucket.blob(pdf.filename)
        blob.upload_from_file(pdf)

        # Extract text from PDF
        pdf_data = pdf.read()
        pdf_file = BytesIO(pdf_data)
        pdf_reader = PyPDF2.PdfFileReader(pdf_file)
        text = ""
        for page_num in range(pdf_reader.numPages):
            text += pdf_reader.getPage(page_num).extractText()

        # Feed the extracted text to vertexai model
        response = model.predict(text, **parameters)

        # Optionally, you can send the vertexai response to another Vertex AI endpoint or handle it differently.
        # For this example, we'll flash the response
        flash(f"Design evaluated: {response.text}")

        return redirect(url_for("index"))

    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True)
