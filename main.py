from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from google.cloud import storage
from dotenv import load_dotenv
import configparser
from io import BytesIO
from vertexai.language_models import TextGenerationModel
from langchain.document_loaders import PyPDFLoader
import vertexai
import os
import tempfile
from transformers import CLIPProcessor, CLIPModel
from PIL import Image

load_dotenv()

processor = None
model = None


def get_image_caption(image_path):
    global processor, model
    if processor is None or model is None:
        processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch16")
        model = CLIPModel.from_pretrained("openai/clip-vit-base-patch16")

    image = Image.open(image_path)
    inputs = processor(text=["a photo of a [MASK]"], images=image, return_tensors="pt", padding=True)
    outputs = model(**inputs)
    logits_per_image = outputs.logits_per_image
    probs = logits_per_image.softmax(dim=1)
    caption = processor.decode(probs.argmax(dim=1).tolist()[0])
    return caption.replace('[MASK]', '').strip()


config = configparser.ConfigParser()
config.read('.config')
GCS_BUCKET_NAME = config['DEFAULT']['GCS_BUCKET_NAME']
SERVICE_ACCOUNT_PATH = config['DEFAULT']['SERVICE_ACCOUNT_PATH']
SECRET_KEY = config['DEFAULT']['SECRET_KEY']

app = Flask(__name__)
app.secret_key = SECRET_KEY

storage_client = storage.Client.from_service_account_json(SERVICE_ACCOUNT_PATH)
bucket = storage_client.bucket(GCS_BUCKET_NAME)

vertexai.init(project="calm-brook-403808", location="us-central1")
model = TextGenerationModel.from_pretrained("text-bison@001")


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

        blob = bucket.blob(pdf.filename)
        blob.content_type = 'application/pdf'  # Explicitly set the MIME type
        with open(pdf_file_path, "rb") as my_file:
            blob.upload_from_file(my_file)

        blob.make_public()
        blob.patch()
        pdf_url = blob.public_url

        loader = PyPDFLoader(pdf_file_path)
        data = loader.load()
        os.remove(pdf_file_path)

        captions = []
        try:
            extracted_images = loader.get_extracted_images()  # Assuming this method is available in PyPDFLoader
            for image_path in extracted_images:
                caption = get_image_caption(image_path)
                captions.append(caption)
        except AttributeError:
            # If the get_extracted_images method doesn't exist, this block will catch the error.
            pass


        all_captions = ' '.join(captions)
        prompt = f'Can you please provide recommendations that would improve the design of the PDF? These can be your thoughts regarding the flow of the document, the content, or anything else you think of. Can you also explain your rationale behind these changes. Thank you... {all_captions}'
        parameters = {
            "candidate_count": 1,
            "max_output_tokens": 1024,
            "temperature": 0.2,
            "top_p": 0.8,
            "top_k": 40
        }
        try:
            response = model.predict(prompt, **parameters)
            initial_feedback = response.text
        except Exception as e:
            print(f"Error occurred: {e}")
            flash("Error occurred during evaluation. Please try again later.")
            return redirect(url_for("index"))

    return render_template("index.html", initial_feedback=initial_feedback, pdf_url=pdf_url)


@app.route("/ask", methods=["POST"])
def ask():
    user_message = request.form["message"]
    parameters = {
        "candidate_count": 1,
        "max_output_tokens": 1024,
        "temperature": 0.2,
        "top_p": 0.8,
        "top_k": 40
    }
    try:
        response = model.predict(user_message, **parameters)
        return jsonify({"response": response.text})
    except Exception as e:
        print(f"Error occurred: {e}")
        return jsonify({"response": "Sorry, an error occurred. Please try again later."})


if __name__ == "__main__":
    app.run(debug=True)
