import os
from PyPDF2 import PdfReader, PdfWriter
from pdf2image import convert_from_path

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

def process_pdfs_in_folder(folder_path):
    for filename in os.listdir(folder_path):
        if filename.endswith(".pdf"):
            pdf_path = os.path.join(folder_path, filename)
            split_pdf_pages(pdf_path, 'output/split_pdfs')
            convert_pdf_to_jpeg(pdf_path, 'output/jpeg_images')

process_pdfs_in_folder('data')