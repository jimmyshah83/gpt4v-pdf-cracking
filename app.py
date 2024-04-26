import os
from dotenv import load_dotenv

from PyPDF2 import PdfReader, PdfWriter
from pdf2image import convert_from_path

from azure.storage.blob import BlobServiceClient

import base64
from mimetypes import guess_type
from openai import AzureOpenAI

load_dotenv()

def process_pdfs_in_azure_container(storage_connection_string, container_name):
    blob_service_client = BlobServiceClient.from_connection_string(storage_connection_string)
    container_client = blob_service_client.get_container_client(container_name)

    for blob in container_client.list_blobs():
        if blob.name.endswith(".pdf"):
            blob_client = blob_service_client.get_blob_client(container_name, blob.name)

            # Download the blob to a local file
            download_file_path = os.path.join("/tmp", blob.name)
            with open(download_file_path, "wb") as download_file:
                download_file.write(blob_client.download_blob().readall())

            split_pdf_pages(download_file_path, 'output/split_pdfs')
            convert_pdf_to_jpeg(download_file_path, 'output/jpeg_images')

def split_pdf_pages(pdf_path, output_folder):
    pdf = PdfReader(pdf_path)
    for page in range(len(pdf.pages)):
        pdf_writer = PdfWriter()
        pdf_writer.add_page(pdf.pages[page])

        output_filename = f"{output_folder}/{os.path.splitext(os.path.basename(pdf_path))[0]}_page_{page + 1}.pdf"

        with open(output_filename, 'wb') as out:
            pdf_writer.write(out)

        print(f'Created: {output_filename}')

def convert_pdf_to_jpeg(pdf_path, output_folder):
    images = convert_from_path(pdf_path)
    for i, image in enumerate(images):
        image.save(f'{output_folder}/{os.path.splitext(os.path.basename(pdf_path))[0]}_image_{i + 1}.jpeg', 'JPEG')

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
    content_list = [] 
    
    api_base = os.getenv('AZURE_OPENAI_ENDPOINT')
    api_key=os.getenv('AZURE_OPENAI_KEY')
    deployment_name = os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME')
    api_version = '2023-12-01-preview'

    client = AzureOpenAI(
        api_key=api_key,  
        api_version=api_version,
        base_url=f"{api_base}openai/deployments/{deployment_name}/extensions",
    )

    # Iterate over each file in the jpeg_images folder
    for filename in os.listdir('output/jpeg_images'):
        if filename.endswith('.jpeg'):
            file_path = os.path.join('output/jpeg_images', filename)
            
            base64Image = local_image_to_data_url(file_path)
            
            response = client.chat.completions.create(
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
                max_tokens=2000 
            )

            content = response['choices'][0]['message']['content']
            print(content)
            
            # Add the content to the list
            content_list.append(content)
            
    return content_list
 
if __name__ == "__main__":
    # process_pdfs_in_azure_container(os.environ['AZURE_STORAGE_CONNECTION_STRING'], os.environ['AZURE_STORAGE_CONTAINER_NAME'])
    content_list = call_openai_api()