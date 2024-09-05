from PyPDF2 import PdfReader, PdfWriter, PageObject, Transformation
from flask import Flask, request, send_file
import math
import os

# Run using `python main.py` and visit http://

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
PROCESSED_FOLDER = 'processed'

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
if not os.path.exists(PROCESSED_FOLDER):
    os.makedirs(PROCESSED_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def scale_and_place_page(input_page, target_width, target_height, x_offset, y_offset):
    """
    Scales a given PDF page to fit within a target area while maintaining the aspect ratio, 
    then places it within the specified position on a new blank page.

    Parameters:
    input_page (PageObject): The original PDF page to be scaled and placed.
    target_width (float): The width of the target area in points.
    target_height (float): The height of the target area in points.
    x_offset (float): The horizontal offset where the scaled page should be placed on the new page.
    y_offset (float): The vertical offset where the scaled page should be placed on the new page.

    Returns:
    PageObject: The new page with the scaled content placed at the specified offset.
    float: The horizontal offset of the placed page (unused, returned for consistency).
    float: The vertical offset of the placed page (unused, returned for consistency).
    """
    #Calculate the scaling factor to maintain aspect ratio
    original_width = float(input_page.mediabox.width)
    original_height = float(input_page.mediabox.height)
    scale_x = target_width / original_width
    scale_y = target_height / original_height
    scale = min(scale_x, scale_y)

    #Apply the scaling and translation to center the page within the target area
    transformation = Transformation().scale(scale).translate(
        tx=(target_width - original_width * scale) / 2,
        ty=(target_height - original_height * scale) / 2
    )

    #Apply the transformation to the page
    input_page.add_transformation(transformation)

    #Create a new blank page for the scaled content
    scaled_page = PageObject.create_blank_page(width=target_width, height=target_height)
    scaled_page.merge_page(input_page)

    return scaled_page, x_offset, y_offset

def process_entire_pdf(input_pdf, output_pdf):
    """
    Processes an entire PDF by scaling and placing pages into a 2x4 grid on an A4 page size.
    Each original page is scaled to fit into one quadrant of the A4-sized page, and the output
    PDF contains these grid pages.

    Parameters:
    input_pdf (str): The path to the input PDF file to be processed.
    output_pdf (str): The path to the output PDF file that will be created.

    Returns:
    None
    """
    reader = PdfReader(input_pdf)
    writer = PdfWriter()

    #Get the dimensions of A4 in points (since PyPDF2 works with points)
    a4_width = 595.28  #210 mm in points
    a4_height = 841.89  #297 mm in points

    #Calculate the target size (1/8th of A4, for the quadrants of a 2x4 grid)
    target_width = a4_width / 2
    target_height = a4_height / 4

    num_pages = len(reader.pages)

    #Iterate over all pages and add them to the grid
    for i in range(0, num_pages, 4):
        #Create a new blank A4 page
        new_page = PageObject.create_blank_page(width=a4_width, height=a4_height)

        #Process up to four pages per grid page
        for quadrant in range(4):
            page_index = i + quadrant
            if page_index < num_pages:
                input_page = reader.pages[page_index]

                #Determine the position for each quadrant on the left side
                x_offset = 0  # All on the left side
                y_offset = a4_height - (quadrant + 1) * target_height

                #Scale and place the page into the correct quadrant
                scaled_page, _, _ = scale_and_place_page(input_page, target_width, target_height, x_offset, y_offset)
                new_page.mergeTranslatedPage(scaled_page, tx=x_offset, ty=y_offset)

        #Add the grid page to the writer
        writer.add_page(new_page)

    #Save the output PDF
    with open(output_pdf, 'wb') as f:
        writer.write(f)

    print(f"Output PDF created successfully: {output_pdf}")

@app.route('/process-pdf', methods=['GET', 'POST'])
def process_pdf_api():
    if request.method == 'POST':
        # Handle file upload and PDF processing as before
        if 'file' not in request.files:
            return "No file part", 400

        file = request.files['file']
        
        if file.filename == '':
            return "No selected file", 400

        if file:
            filename = file.filename
            input_pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(input_pdf_path)

            output_pdf_path = os.path.join(PROCESSED_FOLDER, f"Notes - {filename}")
            process_entire_pdf(input_pdf_path, output_pdf_path)

            return send_file(output_pdf_path, as_attachment=True)
    else:
        # If it's a GET request, return a simple HTML form for file upload
        return '''
        <html>
            <body>
                <h1>Upload PDF</h1>
                <form method="POST" enctype="multipart/form-data">
                    <input type="file" name="file">
                    <input type="submit" value="Upload">
                </form>
            </body>
        </html>
        '''

if __name__ == '__main__':
    app.run(debug=True)

