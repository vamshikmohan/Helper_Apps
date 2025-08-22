import io
import pypdfium2 as pdfium
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from PIL import Image

def rearrange_pdf(input_file, output_file, gap=10*mm, dpi=150):
    pdf = pdfium.PdfDocument(input_file)
    num_pages_original = len(pdf)
    num_pages = num_pages_original

    # Pad to nearest multiple of 4
    padding_needed = (4 - (num_pages % 4)) % 4
    if padding_needed:
        print(f"⚠️ Adding {padding_needed} blank page(s) to make multiple of 4")
        num_pages += padding_needed

    # Landscape A4
    page_width, page_height = landscape(A4)
    half_width = (page_width - gap) / 2

    c = canvas.Canvas(output_file, pagesize=(page_width, page_height))

    # Process in blocks of 4
    for start in range(0, num_pages, 4):
        block = [start+1, start+2, start+3, start+4]  # 1-based indices
        pairs = [(block[1], block[2]), (block[3], block[0])]  # (2,3), (4,1)

        for left, right in pairs:
            # Dotted vertical middle line
            c.setDash(3, 3)
            c.setStrokeColor(colors.grey)
            c.line(page_width/2, 0, page_width/2, page_height)
            c.setDash()

            # ---- Helper to draw a page into a slot ----
            def draw_page(page_num, x_offset):
                if page_num <= num_pages_original:
                    page = pdf[page_num-1]
                    bitmap = page.render(scale=dpi/72).to_pil()
                else:
                    bitmap = Image.new("RGB", (100, 100), "white")  # blank

                # Rotate if page is landscape
                if bitmap.width > bitmap.height:
                    bitmap = bitmap.rotate(90, expand=True)

                img_buf = io.BytesIO()
                bitmap.save(img_buf, format="PNG")
                img_buf.seek(0)

                img = ImageReader(img_buf)
                iw, ih = bitmap.size

                # Scale while preserving aspect ratio
                scale = min(half_width/iw, page_height/ih)
                new_w, new_h = iw*scale, ih*scale
                x_pos = x_offset + (half_width - new_w) / 2
                y_pos = (page_height - new_h) / 2
                c.drawImage(img, x_pos, y_pos, width=new_w, height=new_h)

            # Left slot
            draw_page(left, 0)

            # Right slot
            draw_page(right, half_width + gap)

            c.showPage()

    c.save()
    print(f"✅ Rearranged PDF saved as {output_file}")


# Example usage
if __name__ == "__main__":
    rearrange_pdf("Solid Mechanics Notes - Math.pdf", "output_landscape.pdf")
