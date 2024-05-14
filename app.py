import os
from dotenv import load_dotenv
from PyPDF2 import PdfReader, PdfWriter
from pdf2image import convert_from_path
from azure.storage.blob import BlobServiceClient
import base64
from mimetypes import guess_type
from openai import AzureOpenAI
from flask import Flask, jsonify

app = Flask(__name__)

load_dotenv()

pdf_container_name = os.environ['AZURE_STORAGE_CONTAINER_NAME']
blob_service_client = BlobServiceClient.from_connection_string(os.environ['AZURE_STORAGE_CONNECTION_STRING'])
response_container_client = blob_service_client.get_container_client(os.environ['AZURE_STORAGE_RESPONSE_CONTAINER_NAME'])

def process_pdfs_in_azure_container():
    
    container_client = blob_service_client.get_container_client(pdf_container_name)

    for blob in container_client.list_blobs():
        if blob.name.endswith(".pdf"):
            
            blob_client = blob_service_client.get_blob_client(pdf_container_name, blob.name)

            # Download the blob to a local file
            download_file_path = os.path.join("/tmp", blob.name)
            with open(download_file_path, "wb") as download_file:
                download_file.write(blob_client.download_blob().readall())

            split_pdf_pages(download_file_path)

def split_pdf_pages(pdf_path, output_folder='output/pdf_pages'):
    
    pdf = PdfReader(pdf_path)
    container_client = blob_service_client.get_container_client(os.environ['AZURE_STORAGE_PAGE_CONTAINER_NAME'])
    
    for page in range(len(pdf.pages)):
        pdf_writer = PdfWriter()
        pdf_writer.add_page(pdf.pages[page])

        output_filename = f"{output_folder}/{os.path.splitext(os.path.basename(pdf_path))[0]}_page_{page + 1}.pdf"

        with open(output_filename, 'wb') as out:
            pdf_writer.write(out)
        
        print(f'Created: {output_filename}')
        
        # Upload the created file to Azure Blob Storage
        with open(output_filename, "rb") as data:
            raw_file_name = os.path.basename(output_filename)
            blob_client = container_client.get_blob_client(raw_file_name)
            blob_client.upload_blob(data, overwrite=True)
            print(f'Uploaded: {raw_file_name} to Azure Blob Storage')

def convert_pdf_to_jpeg(pdf_path = 'output/pdf_pages', output_folder = 'output/jpeg_images'):
    #  Iterate over each file in the pdf_pages folder
    for filename in os.listdir(pdf_path):
        file_path = os.path.join(pdf_path, filename)
        images = convert_from_path(file_path)
        for i, image in enumerate(images): 
            image.save(f'{output_folder}/{os.path.splitext(os.path.basename(file_path))[0]}.jpeg', 'JPEG')

# Function to encode a local image into data URL 
def local_image_to_data_url(image_path):
    # Guess the MIME type of the image based on the file extension
    mime_type, _ = guess_type(image_path)
    if mime_type is None:
        mime_type = 'application/octet-stream'  # Default MIME type if none is found

    # Read and encode the image file
    with open(image_path, "rb") as image_file:
        base64_encoded_data = base64.b64encode(image_file.read()).decode('utf-8')

    # Construct the data URL
    return f"data:{mime_type};base64,{base64_encoded_data}"

def call_openai_api():
    
    api_base = os.getenv('AZURE_OPENAI_ENDPOINT')
    api_key=os.getenv('AZURE_OPENAI_KEY')
    deployment_name = os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME')
    api_version = '2023-12-01-preview'
    temperature = os.getenv('AZURE_OPENAI_TEMPERATURE')
    top_p = os.getenv('AZURE_OPENAI_TOP_P')
    
    cv_endpoint = os.getenv('AZURE_COMPUTER_VISION_ENDPOINT')
    cv_key = os.getenv('AZURE_COMPUTER_VISION_KEY')

    client = AzureOpenAI(
        api_key=api_key,  
        api_version=api_version,
        base_url=f"{api_base}openai/deployments/{deployment_name}/extensions",
    )

    # Iterate over each file in the jpeg_images folder
    for filename in os.listdir('output/jpeg_images_tbd'):
        print(f"Processing: {filename}")
        
        if filename.endswith('.jpeg'):
            file_path = os.path.join('output/jpeg_images_tbd', filename)
            
            base64Image = local_image_to_data_url(file_path)
            
            response = client.chat.completions.create(
                temperature=temperature,
                top_p=top_p,
                model=deployment_name,
                messages=[
                    { "role": "system", "content": os.environ['AZURE_OPENAI_SYSTEM_MESSAGE'] },
                    { "role": "user", "content": [  
                        { 
                            "type": "image_url",
                            "image_url": {
                                "url": base64Image,
                            }
                        }
                    ] } 
                ],
                extra_body={
                    "dataSources": [
                        {
                            "type": "AzureComputerVision",
                            "parameters": {
                                "endpoint": cv_endpoint,
                                "key": cv_key
                            }
                        }],
                    "enhancements": {
                        "ocr": {
                            "enabled": True
                        },
                        "grounding": {
                            "enabled": True
                        }
                    }
                },
                max_tokens=2000 
            )

            content = response.choices[0].message.content
            
            push_content_to_azure_container(content, os.path.splitext(filename)[0])
            
            os.remove(file_path)

def push_content_to_azure_container(content, blob_name):
    
    # Convert content to bytes
    content_bytes = content.encode('utf-8')
        
    # Upload content to the container
    response_container_client.upload_blob(name=blob_name, data=content_bytes, overwrite=True)
        
    print(f"Uploaded content to Azure Blob Storage: {blob_name}")
        

@app.route('/process_pdfs', methods=['GET'])
def process_pdfs():
    process_pdfs_in_azure_container()
    return jsonify({"status": "success"}), 200
 
@app.route('/convert_pdfs', methods=['GET'])
def convert_pdfs():
    convert_pdf_to_jpeg()
    return jsonify({"status": "success"}), 200

@app.route('/generate_summary', methods=['GET'])
def generate_summary():
    call_openai_api()    
    return jsonify({"status": "success"}), 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True, port=3000)