import streamlit as st
import io, base64
import pypdfium2 as pdfium
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from PIL import Image

def rearrange_pdf(pdf_bytes, gap=0, dpi=150, landscape_mode=True, auto_pad=True):
    pdf = pdfium.PdfDocument(io.BytesIO(pdf_bytes))
    num_pages_original = len(pdf)
    num_pages = num_pages_original

    # Pad to nearest multiple of 4
    if auto_pad:
        padding_needed = (4 - (num_pages % 4)) % 4
        num_pages += padding_needed
    else:
        padding_needed = 0

    # Page size
    if landscape_mode:
        page_width, page_height = landscape(A4)
    else:
        page_width, page_height = A4
    half_width = (page_width - gap) / 2

    out_buf = io.BytesIO()
    c = canvas.Canvas(out_buf, pagesize=(page_width, page_height))

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
                if bitmap.width > bitmap.height and landscape_mode:
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
    out_buf.seek(0)
    return out_buf


# ---------------- Streamlit UI ----------------
st.title("📄 PDF to Booklet Converter")
st.write("Rearranges your PDF into 2-up booklet style with order (2,3,4,1), (6,7,8,5), ...")

uploaded_file = st.file_uploader("Upload a PDF", type=["pdf"])
dpi = st.slider("Render DPI (higher = sharper, bigger file)", 72, 300, 150)
landscape_mode = st.checkbox("Landscape Mode", value=True)

use_gap = st.checkbox("Add gap between pages?", value=False)
gap_mm = st.slider("Gap (mm)", 0, 20, 10) if use_gap else 0

auto_pad = st.checkbox("Auto-pad to multiple of 4 pages?", value=True)

if uploaded_file is not None:
    if st.button("Convert PDF"):
        with st.spinner("Processing..."):
            output_pdf = rearrange_pdf(
                uploaded_file.read(),
                gap=gap_mm*mm,
                dpi=dpi,
                landscape_mode=landscape_mode,
                auto_pad=auto_pad
            )
        st.success("✅ Conversion complete!")

        # Download button
        st.download_button(
            label="⬇️ Download rearranged PDF",
            data=output_pdf,
            file_name="booklet.pdf",
            mime="application/pdf"
        )

        # Preview
        st.subheader("🔎 Preview")
        b64 = base64.b64encode(output_pdf.getvalue()).decode()
        pdf_display = f'<iframe src="data:application/pdf;base64,{b64}" width="100%" height="600"></iframe>'
        st.markdown(pdf_display, unsafe_allow_html=True)
