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
IMG_OUT_DIR = BASE_DIR / "data" / "images"

def get_pg():
    return psycopg2.connect(
        host=os.getenv("SUPABASE_DB_HOST"), port=int(os.getenv("SUPABASE_DB_PORT", 5432)),
        dbname=os.getenv("SUPABASE_DB_NAME", "postgres"), user=os.getenv("SUPABASE_DB_USER", "postgres"),
        password=os.getenv("SUPABASE_DB_PASS"), sslmode="require")

def render_and_crop(doc, page_idx, crop_rect, out_path):
    page = doc[page_idx]
    # 2x 해상도 (약 144 DPI)
    mat = fitz.Matrix(2, 2)
    pix = page.get_pixmap(matrix=mat, clip=crop_rect)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pix.save(str(out_path))

def process_pps(cur, pg):
    print("Processing 조달청 (pps) ...")
    pdf_path = RAW_DIR / "004_조달청 설계VE 사례집_2025.pdf"
    doc = fitz.open(str(pdf_path))
    
    cur.execute("SELECT alt_id, alt_number, source_page FROM alternatives WHERE project_id = 'pps_2025_ve' ORDER BY alt_number")
    alts = cur.fetchall()
    
    # 조달청 레이아웃: 좌(원안) / 우(대안)
    rect_orig = fitz.Rect(35, 195, 290, 470)
    rect_alt = fitz.Rect(305, 195, 560, 470)
    
    for alt_id, alt_num, source_page in alts:
        page_idx = source_page - 1
        
        orig_path = IMG_OUT_DIR / alt_id / f"{alt_id}_original_diagram.jpeg"
        alt_path = IMG_OUT_DIR / alt_id / f"{alt_id}_alternative_diagram.jpeg"
        
        render_and_crop(doc, page_idx, rect_orig, orig_path)
        render_and_crop(doc, page_idx, rect_alt, alt_path)
        
        for img_type, path in [("original_diagram", orig_path), ("alternative_diagram", alt_path)]:
            cur.execute("SELECT 1 FROM images WHERE alt_id = %s AND image_type = %s", (alt_id, img_type))
            if not cur.fetchone():
                cur.execute("INSERT INTO images (alt_id, image_type, file_path) VALUES (%s, %s, %s)",
                            (alt_id, img_type, str(path)))
        pg.commit()
        if alt_num % 50 == 0:
            print(f"  {alt_id} rendered")
            
    doc.close()

def process_toegye(cur, pg):
    print("Processing 퇴계동 (toegye) ...")
    FILES = {
        "건축": RAW_DIR / "005_퇴계동_국민체육센터건립_대안구체화_건축.pdf",
        "구조": RAW_DIR / "005_퇴계동_국민체육센터건립_대안구체화_구조.pdf",
        "기계": RAW_DIR / "005_퇴계동_국민체육센터건립_대안구체화_기계.pdf",
        "전기": RAW_DIR / "005_퇴계동_국민체육센터건립_대안구체화_전기.pdf",
        "토목": RAW_DIR / "005_퇴계동_국민체육센터건립_대안구체화_토목.pdf",
    }
    
    cur.execute("SELECT alt_id, alt_number, field_category, source_page FROM alternatives WHERE project_id = 'toegye_sports_2024' ORDER BY alt_number")
    alts = cur.fetchall()
    
    # 퇴계동 레이아웃: 상(원안) / 하(대안)
    rect_orig = fitz.Rect(110, 80, 560, 400)
    rect_alt = fitz.Rect(110, 410, 560, 650)
    
    docs = {}
    
    for alt_id, alt_num, field, source_page in alts:
        if field not in FILES: continue
        if field not in docs:
            docs[field] = fitz.open(str(FILES[field]))
            
        doc = docs[field]
        page_idx = source_page - 1
        
        orig_path = IMG_OUT_DIR / alt_id / f"{alt_id}_original_diagram.jpeg"
        alt_path = IMG_OUT_DIR / alt_id / f"{alt_id}_alternative_diagram.jpeg"
        
        render_and_crop(doc, page_idx, rect_orig, orig_path)
        render_and_crop(doc, page_idx, rect_alt, alt_path)
        
        for img_type, path in [("original_diagram", orig_path), ("alternative_diagram", alt_path)]:
            cur.execute("SELECT 1 FROM images WHERE alt_id = %s AND image_type = %s", (alt_id, img_type))
            if not cur.fetchone():
                cur.execute("INSERT INTO images (alt_id, image_type, file_path) VALUES (%s, %s, %s)",
                            (alt_id, img_type, str(path)))
        pg.commit()
    
    for doc in docs.values():
        doc.close()
    print("  Toegye rendered")

def run():
    pg = get_pg()
    cur = pg.cursor()
    process_pps(cur, pg)
    process_toegye(cur, pg)
    cur.close()
    pg.close()
    print("All rendering done!")

if __name__ == '__main__':
    run()
