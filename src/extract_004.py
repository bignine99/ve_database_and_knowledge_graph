"""대구 VE 2023 — 빠른 제안페이지 감지 (CID 숫자 패턴) + OCR 추출"""
import fitz, json, re, sys, io, os
import psycopg2, psycopg2.extras
import pytesseract
from PIL import Image
from pathlib import Path
from dotenv import load_dotenv

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

PDF_PATH = BASE_DIR / ".raw_data" / "003_대구광역시_2023 설계경제성검토(VE) 사례집.pdf"
OUT_DIR = BASE_DIR / "data" / "extracted_004"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def parse_num(s):
    if not s: return 0
    s = str(s).replace(',', '').replace(' ', '').replace('%', '').strip()
    m = re.search(r'-?[\d.]+', s)
    return float(m.group()) if m else 0


def ocr_page(page):
    mat = fitz.Matrix(2.0, 2.0)
    pix = page.get_pixmap(matrix=mat)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    return pytesseract.image_to_string(img, lang='kor+eng')


def fast_detect_proposals(doc):
    """CID 텍스트에서 제안 페이지 후보 빠르게 감지 — OCR 없이"""
    candidates = []
    for i in range(len(doc)):
        raw = doc[i].get_text()
        # 제안 페이지 특성: 많은 라인(>20) + '과' 키워드 근처
        lines = raw.strip().split('\n')
        # '개선' 에 해당하는 CID 패턴 또는 라인수가 40-100 사이
        if 30 < len(lines) < 120:
            # 이미지 많은 페이지 (도면 포함)
            images = doc[i].get_images()
            if len(images) >= 3:
                candidates.append(i)
    return candidates


def extract_data_from_ocr(text, page_num):
    d = {
        'source_page': page_num,
        'project_name': '', 'proposal_title': '',
        'original_description': '', 'alternative_description': '',
        'value_type': '가치혁신형', 'field_category': '토목',
        'cost_original': 0, 'cost_alternative': 0, 'cost_savings': 0,
        'cost_change': 0, 'value_change': 0,
        'how2_code': '', 'how2_name': '', 'space': '',
        'advantages': '', 'disadvantages': '',
    }

    # 과업명
    m = re.search(r'과업\s*명\s+(.+?)(?:\s+발주|\s+담당|\n)', text)
    if m: d['project_name'] = m.group(1).strip()[:80]
    
    # 제안 타이틀 — 첫 의미있는 한글 줄
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    for line in lines[:5]:
        hangul = re.findall(r'[\uAC00-\uD7A3]', line)
        if len(hangul) >= 5:
            d['proposal_title'] = line[:100]
            break

    # 개선전/후
    before = re.search(r'개선\s*전\s*(.*?)(?=개선\s*후)', text, re.DOTALL)
    after = re.search(r'개선\s*후\s*(.*?)(?=(?:개요|성능|비용|가치|생애|제안|$))', text, re.DOTALL)
    if before: d['original_description'] = re.sub(r'\s+', ' ', before.group(1).strip())[:300]
    if after: d['alternative_description'] = re.sub(r'\s+', ' ', after.group(1).strip())[:300]

    # 가치유형
    for vt in ['가치혁신형', '기능강조형', '비용절감형', '성능향상형']:
        if vt in text: d['value_type'] = vt; break

    # 비용/가치 숫자
    val_m = re.search(r'가치향상\s*(?:효과)?\s*[:\s]*([,\d.]+)', text)
    if val_m: d['value_change'] = parse_num(val_m.group(1))
    
    sav_m = re.search(r'(?:절감|저감)\s*(?:효과|액)?\s*[:\s]*([,\d.]+)', text)
    if sav_m: d['cost_savings'] = parse_num(sav_m.group(1))

    # 분야
    civil_kw = ['터널','교량','도로','토공','사면','옹벽','흙막이','기초','포장','배수','관로','하수','암거','교각','말뚝']
    arch_kw = ['건축','마감','창호','방수','벽체','천장','단열','외벽','철근','콘크리트','거푸집','청사','주차장']
    mep_kw = ['전기','기계','설비','환기','소방','통신','CCTV','조명']
    land_kw = ['조경','식재','잔디','식생','녹화']
    c = sum(1 for k in civil_kw if k in text)
    a = sum(1 for k in arch_kw if k in text)
    m2 = sum(1 for k in mep_kw if k in text)
    l = sum(1 for k in land_kw if k in text)
    scores = {'토목':c,'건축':a,'설비':m2,'조경':l}
    d['field_category'] = max(scores, key=scores.get) if max(scores.values()) > 0 else '토목'

    return d


def get_pg():
    return psycopg2.connect(
        host=os.getenv("SUPABASE_DB_HOST"), port=int(os.getenv("SUPABASE_DB_PORT", 5432)),
        dbname=os.getenv("SUPABASE_DB_NAME", "postgres"), user=os.getenv("SUPABASE_DB_USER", "postgres"),
        password=os.getenv("SUPABASE_DB_PASS"), sslmode="require")


def insert_to_supabase(all_data):
    pg = get_pg(); cur = pg.cursor()
    cur.execute("""INSERT INTO projects (project_id, project_name, file_path, total_alternatives, source_file, source_year, source_org)
        VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (project_id) DO UPDATE SET total_alternatives = EXCLUDED.total_alternatives""",
        ('daegu_2023_ve', '대구광역시 2023년 설계경제성검토(VE) 사례집', str(PDF_PATH), len(all_data), PDF_PATH.name, 2023, '대구광역시'))
    cur.execute("SELECT COALESCE(MAX(alt_number), 0) FROM alternatives")
    max_num = cur.fetchone()[0]
    for i, d in enumerate(all_data):
        alt_num = max_num + i + 1; alt_id = f"daegu_{alt_num:03d}"
        cur.execute("""INSERT INTO alternatives (alt_id, project_id, alt_number, proposal_title, original_description, alternative_description,
            advantages, disadvantages, project_name, source_page, field_category, value_type_corrected, how2_code, how2_name, space)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (alt_id) DO NOTHING""",
            (alt_id, 'daegu_2023_ve', alt_num, d['proposal_title'], d['original_description'], d['alternative_description'],
             d.get('advantages',''), d.get('disadvantages',''), d['project_name'], d['source_page'],
             d['field_category'], d['value_type'], d.get('how2_code',''), d.get('how2_name',''), d.get('space','')))
        cur.execute("""INSERT INTO cost_evaluations (alt_id, cost_type, original_cost, alternative_cost, savings_amount, savings_rate)
            VALUES (%s,%s,%s,%s,%s,%s)""", (alt_id, 'project_lifecycle', d.get('cost_original',0), d.get('cost_alternative',0), d.get('cost_savings',0), d.get('cost_change',0)))
        cur.execute("""INSERT INTO value_evaluations (alt_id, performance_original, performance_alternative, performance_change_rate, cost_change_rate, value_change_rate)
            VALUES (%s,%s,%s,%s,%s,%s)""", (alt_id, 0, 0, 0, d.get('cost_change',0), d.get('value_change',0)))
    pg.commit(); pg.close()
    return max_num + 1, max_num + len(all_data)


def run():
    print("=" * 60, flush=True)
    print("대구광역시 2023 VE 사례집 추출 (OCR)", flush=True)
    print("=" * 60, flush=True)

    doc = fitz.open(str(PDF_PATH))
    total = len(doc)
    print(f"  총 {total} 페이지", flush=True)

    # Phase 1: 빠른 후보 감지 (CID 패턴, ~10초)
    print(f"\n  Phase 1: 후보 페이지 빠른 감지...", flush=True)
    candidates = fast_detect_proposals(doc)
    print(f"  후보: {len(candidates)} 페이지", flush=True)

    # Phase 2: 후보만 OCR
    print(f"\n  Phase 2: 후보 OCR 추출...", flush=True)
    sys.path.insert(0, str(BASE_DIR))
    from src.cube_taxonomy import classify_how2, classify_space

    all_data = []
    seen_titles = set()

    for idx, pg_idx in enumerate(candidates):
        text = ocr_page(doc[pg_idx])
        
        # 제안 페이지 확인: '개선전' + '개선후'
        if '개선' not in text:
            continue
        has_before = bool(re.search(r'개선\s*전', text))
        has_after = bool(re.search(r'개선\s*후', text))
        if not (has_before and has_after):
            continue
        
        d = extract_data_from_ocr(text, pg_idx + 1)
        
        # 중복 제거 (같은 제목)
        title_key = d['proposal_title'][:30]
        if title_key in seen_titles:
            continue
        seen_titles.add(title_key)

        # CUBE 분류
        title_text = d['proposal_title'] + ' ' + d['original_description'] + ' ' + d['alternative_description']
        how2_list = classify_how2(title_text)
        if how2_list:
            h = how2_list[0]
            d['how2_code'] = f"{h[0]}-{h[1]}" if len(h) >= 2 else ''
            d['how2_name'] = h[2] if len(h) >= 3 else ''
        space_list = classify_space(title_text)
        d['space'] = space_list[0] if isinstance(space_list, list) and space_list else ''

        json_path = OUT_DIR / f"daegu_{len(all_data)+1:03d}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(d, f, ensure_ascii=False, indent=2)

        all_data.append(d)
        
        if (idx + 1) % 20 == 0:
            print(f"  ... {idx+1}/{len(candidates)} 스캔 ({len(all_data)}건 추출)", flush=True)

    print(f"\n  {len(all_data)}건 추출 완료", flush=True)

    if not all_data:
        print("  추출된 데이터 없음. 종료.", flush=True)
        doc.close()
        return

    # Supabase 적재
    print(f"\n  DB 적재 중...", flush=True)
    start, end = insert_to_supabase(all_data)
    print(f"  대안 #{start}~#{end} 적재 완료", flush=True)

    fields = {}; vtypes = {}
    for d in all_data:
        fields[d['field_category']] = fields.get(d['field_category'], 0) + 1
        vtypes[d['value_type']] = vtypes.get(d['value_type'], 0) + 1

    doc.close()
    print(f"\n{'='*60}", flush=True)
    print(f"  총 추출: {len(all_data)}건", flush=True)
    print(f"  분야별: {fields}", flush=True)
    print(f"  가치유형: {vtypes}", flush=True)
    print(f"  대안: #{start} ~ #{end}", flush=True)


if __name__ == "__main__":
    run()
