from PyPDF2 import PdfReader, PdfWriter, PageObject, Transformation
from flask import Flask, request, send_file
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from io import BytesIO

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
    """
    original_width = float(input_page.mediabox.width)
    original_height = float(input_page.mediabox.height)
    scale_x = target_width / original_width
    scale_y = target_height / original_height
    scale = min(scale_x, scale_y)

    transformation = Transformation().scale(scale).translate(
        tx=(target_width - original_width * scale) / 2,
        ty=(target_height - original_height * scale) / 2
    )

    input_page.add_transformation(transformation)

    scaled_page = PageObject.create_blank_page(width=target_width, height=target_height)
    scaled_page.merge_page(input_page)

    return scaled_page, x_offset, y_offset

def draw_grid_on_top(page_width, page_height):
    """
    Draws a vertical line at the center and three horizontal lines to create a 4x2 grid on the page.
    
    Returns:
    BytesIO: A byte stream of the PDF content with the grid drawn on it.
    """
    # Create a PDF in memory
    packet = BytesIO()
    can = canvas.Canvas(packet, pagesize=A4)

    # Draw the vertical line at the center of the page
    center_x = page_width / 2
    can.setStrokeColorRGB(0, 0, 0)  # Set line color to black
    can.setLineWidth(1)  # Set line width
    can.line(center_x, 0, center_x, page_height)  # Draw vertical line

    # Draw horizontal lines to create 4 equal horizontal sections
    section_height = page_height / 4
    for i in range(1, 4):
        y_position = section_height * i
        can.line(0, y_position, page_width, y_position)  # Draw horizontal lines

    # Finalize and save the canvas
    can.save()

    # Move the pointer to the beginning of the BytesIO buffer
    packet.seek(0)
    
    return packet

def process_entire_pdf(input_pdf, output_pdf):
    """
    Processes an entire PDF by scaling and placing pages into a 2x4 grid on an A4 page size.
    Each original page is scaled to fit into one quadrant of the A4-sized page, and the output
    PDF contains these grid pages with a vertical line in the middle and horizontal lines to create a 4x2 grid.
    The grid lines are drawn on top of the inserted PDF content.
    """
    reader = PdfReader(input_pdf)
    writer = PdfWriter()

    a4_width, a4_height = A4  # A4 dimensions in points

    target_width = a4_width / 2
    target_height = a4_height / 4

    num_pages = len(reader.pages)

    for i in range(0, num_pages, 4):
        # Create a new blank A4 page for the scaled content
        new_page = PageObject.create_blank_page(width=a4_width, height=a4_height)

        # Process up to four pages per grid page
        for quadrant in range(4):
            page_index = i + quadrant
            if page_index < num_pages:
                input_page = reader.pages[page_index]

                x_offset = 0  # All on the left side
                y_offset = a4_height - (quadrant + 1) * target_height

                # Scale and place the page into the correct quadrant
                scaled_page, _, _ = scale_and_place_page(input_page, target_width, target_height, x_offset, y_offset)
                new_page.mergeTranslatedPage(scaled_page, tx=x_offset, ty=y_offset)

        # Now, draw the grid on top of the scaled PDF content
        grid_pdf_stream = draw_grid_on_top(a4_width, a4_height)
        grid_pdf_reader = PdfReader(grid_pdf_stream)
        grid_page = grid_pdf_reader.pages[0]  # Use the page with the drawn grid
        new_page.merge_page(grid_page)  # Merge the grid lines on top of the content

        # Add the page with the grid and content to the writer
        writer.add_page(new_page)

    with open(output_pdf, 'wb') as f:
        writer.write(f)

    print(f"Output PDF created successfully: {output_pdf}")

@app.route('/process-pdf', methods=['GET', 'POST'])
def process_pdf_api():
    if request.method == 'POST':
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
