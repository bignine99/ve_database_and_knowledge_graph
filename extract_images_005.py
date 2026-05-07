import fitz
import sys
import io
import os
from pathlib import Path
from dotenv import load_dotenv
import psycopg2

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
BASE_DIR = Path(r"c:\Users\cho\Desktop\Temp\05_1_code\260504_ve_database_development")
load_dotenv(BASE_DIR / ".env")
RAW_DIR = BASE_DIR / ".raw_data"

PDF_PATH = RAW_DIR / "004_조달청 설계VE 사례집_2025.pdf"

def get_pg():
    return psycopg2.connect(
        host=os.getenv("SUPABASE_DB_HOST"), port=int(os.getenv("SUPABASE_DB_PORT", 5432)),
        dbname=os.getenv("SUPABASE_DB_NAME", "postgres"), user=os.getenv("SUPABASE_DB_USER", "postgres"),
        password=os.getenv("SUPABASE_DB_PASS"), sslmode="require")

def extract_images_from_page(doc, page, alt_id):
    imgs = page.get_images(full=True)
    candidates = []
    for img_info in imgs:
        xref = img_info[0]
        base_img = doc.extract_image(xref)
        w, h = base_img["width"], base_img["height"]
        if w < 100 or h < 100: continue
        
        rects = page.get_image_rects(img_info)
        y_pos = rects[0].y0 if rects else 9999
        candidates.append({"xref": xref, "data": base_img["image"], "ext": base_img["ext"], "y_pos": y_pos})
        
    candidates.sort(key=lambda c: c["y_pos"])
    
    saved_paths = []
    for idx, c in enumerate(candidates[:2]):
        label = "original" if idx == 0 else "alternative"
        out_dir = BASE_DIR / "data" / "images" / alt_id
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{alt_id}_{label}_diagram.{c['ext']}"
        out_path.write_bytes(c["data"])
        saved_paths.append((f"{label}_diagram", str(out_path)))
    return saved_paths

def run():
    pg = get_pg()
    cur = pg.cursor()
    
    cur.execute("SELECT alt_id, alt_number, source_page FROM alternatives WHERE project_id = 'pps_2025_ve' ORDER BY alt_number")
    alts = cur.fetchall()
    
    doc = fitz.open(str(PDF_PATH))
    
    for alt in alts:
        alt_id, alt_number, source_page = alt
        
        # source_page는 1-based
        page_idx = source_page - 1
        page = doc[page_idx]
        
        saved = extract_images_from_page(doc, page, alt_id)
        
        for img_type, path in saved:
            cur.execute("SELECT 1 FROM images WHERE alt_id = %s AND image_type = %s", (alt_id, img_type))
            if not cur.fetchone():
                cur.execute("INSERT INTO images (alt_id, image_type, file_path) VALUES (%s, %s, %s)",
                            (alt_id, img_type, path))
        pg.commit()
        if alt_number % 20 == 0:
            print(f"[{alt_number}] {alt_id} - {len(saved)} images extracted")
            
    doc.close()
    pg.close()

if __name__ == '__main__':
    run()
