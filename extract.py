import fitz
import os

os.makedirs("images", exist_ok=True)
doc = fitz.open("1.pdf")
for i, page in enumerate(doc):
    pix = page.get_pixmap(dpi=200) # Good DPI for OCR and table structure
    pix.save(f"images/page_{i+1:02d}.png")
print(f"Extracted {len(doc)} pages.")
