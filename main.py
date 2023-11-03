
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from google.cloud import storage
from dotenv import load_dotenv
import configparser
from vertexai.language_models import TextGenerationModel
from langchain.document_loaders import PyPDFLoader
import vertexai
import os
import tempfile
from pypdf import PdfReader
from transformers import BlipProcessor, BlipForConditionalGeneration
from PIL import Image
import logging

load_dotenv()
# Load pre-trained model and processor
processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")


# Load your configurations
config = configparser.ConfigParser()
config.read('.config')
GCS_BUCKET_NAME = config['DEFAULT']['GCS_BUCKET_NAME']
SERVICE_ACCOUNT_PATH = config['DEFAULT']['SERVICE_ACCOUNT_PATH']
SECRET_KEY = config['DEFAULT']['SECRET_KEY']

app = Flask(__name__)
app.secret_key = SECRET_KEY

# Configure Flask logging
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)

storage_client = storage.Client.from_service_account_json(SERVICE_ACCOUNT_PATH)
bucket = storage_client.bucket(GCS_BUCKET_NAME)

vertexai.init(project="calm-brook-403808", location="us-central1")
text_generation_model = TextGenerationModel.from_pretrained("text-bison")

@app.route("/", methods=["GET", "POST"])
def index():
    initial_feedback = None
    pdf_url = None

    if request.method == "POST":
        pdf = request.files["file"]
        pdf_data = pdf.read()
        if not pdf_data:
            flash("Uploaded file is empty. Please upload a valid PDF.")
            return redirect(url_for("index"))

        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        temp_file.write(pdf_data)
        pdf_file_path = temp_file.name
        temp_file.close()

        # Upload to Google Cloud Storage
        blob = bucket.blob(pdf.filename)
        blob.content_type = 'application/pdf'  # Explicitly set the MIME type
        with open(pdf_file_path, "rb") as my_file:
            blob.upload_from_file(my_file)

        blob.make_public()
        blob.patch()
        pdf_url = blob.public_url

        # Load PDF using PyPDFLoader
        loader = PyPDFLoader(pdf_file_path)
        documents = loader.load()  # This will give us the list of Document objects
        num_pages = len(documents)
        app.logger.info(f"PDF loaded with {num_pages} pages.")

        def get_image_caption(image_path):
            # Load and process the image
            image = Image.open(image_path)
            inputs = processor(images=image, return_tensors="pt")

            # Generate caption
            outputs = model.generate(**inputs, max_length=128, num_beams=3)

            # Convert token ids to text
            captions = processor.decode(outputs[0], skip_special_tokens=True)
            return captions

        # Extract images and get captions
        captions = []
        reader = PdfReader(pdf_file_path)
        for page_num, page in enumerate(reader.pages):
            count = 0
            for image in page.images:
                image_filename = f"image_{page_num}_{count}.jpg"
                with open(image_filename, "wb") as fp:
                    fp.write(image.data)
                try:
                    caption = get_image_caption(image_filename)
                    captions.append(caption)
                    # Log the caption for the current image
                    app.logger.info(f"Caption for {image_filename}: {caption}")
                    os.remove(image_filename)  # Clean up the image file after getting the caption
                except Exception as e:
                    app.logger.error(f"Failed to get caption for {image_filename}: {e}")
                count += 1

        # Assuming 'captions' is a list of strings extracted from the PDF
        captions_text = "\n".join(captions)

        # Construct the prompt with the dynamic captions included
        prompt = f"""
        You are an AI-powered UX/UI design evaluator. Your objective is to analyze UI/UX elements based on provided descriptions and offer comprehensive, insightful, and actionable feedback. Your feedback should help designers, businesses, and professionals refine their creations, focusing on both usability and aesthetics. Quality and clarity in your critique are essential.

        Based on the following descriptions of images from a PDF:

        {captions_text}

        Please provide recommendations that would improve the UI/UX design of the content described. Consider the flow of information, font choices, color schemes, layout, and overall aesthetic appeal in your feedback. Highlight both strengths and areas for improvement, and explain your rationale behind each suggestion for enhancement. Thank you.
        """

        parameters = {
            "candidate_count": 1,
            "max_output_tokens": 1024,
            "temperature": 0.2,
            "top_p": 0.8,
            "top_k": 40
        }
        try:
            response = text_generation_model.predict(prompt, **parameters)
            print(f"Response from Model: {response.text}")
            initial_feedback = response.text
        except Exception as e:
            print(f"Error occurred: {e}")
            flash("Error occurred during evaluation. Please try again later.")
            return redirect(url_for("index"))
        global design_context
        design_context = captions_text

    return render_template("index.html", initial_feedback=initial_feedback, pdf_url=pdf_url)

# Global variable to store the captions context
design_context = ""

@app.route("/ask", methods=["POST"])
def ask():
    user_message = request.form["message"]

    # Formulate the prompt with the design context and the user's message
    prompt = f"""
    You are an AI that has analyzed a design with the following details:

    {design_context}

    User's question: "{user_message}"
    How would you respond to improve the design based on their query?
    """

    parameters = {
        "candidate_count": 1,
        "max_output_tokens": 1024,
        "temperature": 0.2,
        "top_p": 0.8,
        "top_k": 40
    }

    try:
        response = text_generation_model.predict(prompt, **parameters)
        return jsonify({"response": response.text})
    except Exception as e:
        print(f"Error occurred: {e}")
        return jsonify({"response": "Sorry, an error occurred. Please try again later."})

if __name__ == "__main__":
    app.run(debug=True)