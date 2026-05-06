"""
국가철도공단 2021 설계VE 사례집 추출기 (003)
=============================================
- 1페이지/제안, 107건
- 테이블: 성능평가(%), 비용평가(백만원), 가치평가(%)
"""
import fitz, json, re, sys, io, os
import psycopg2, psycopg2.extras
from pathlib import Path
from dotenv import load_dotenv

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

PDF_PATH = BASE_DIR / ".raw_data" / "002_국가철도공단_2021년 설계VE 사례집.pdf"
OUT_DIR = BASE_DIR / "data" / "extracted_003"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def get_pg():
    return psycopg2.connect(
        host=os.getenv("SUPABASE_DB_HOST"),
        port=int(os.getenv("SUPABASE_DB_PORT", 5432)),
        dbname=os.getenv("SUPABASE_DB_NAME", "postgres"),
        user=os.getenv("SUPABASE_DB_USER", "postgres"),
        password=os.getenv("SUPABASE_DB_PASS"),
        sslmode="require",
    )


def parse_num(s):
    if not s: return 0
    s = str(s).replace(',', '').replace(' ', '').replace('%', '').strip()
    m = re.search(r'-?[\d.]+', s)
    return float(m.group()) if m else 0


def detect_proposals(doc):
    proposals = []
    for i in range(len(doc)):
        text = doc[i].get_text()
        if '제안명' in text and '개선전' in text and '가치향상' in text:
            proposals.append({'page': i+1, 'text': text})
    return proposals


def extract_data(text, page_num):
    lines = text.split('\n')
    d = {
        'source_page': page_num,
        'proposal_title': '',
        'project_name': '',
        'value_type': '',
        'original_description': '',
        'alternative_description': '',
        'advantages': '',
        'disadvantages': '',
        'perf_original': 500.0,
        'perf_alternative': 500.0,
        'perf_change': 0,
        'cost_original': 0,
        'cost_alternative': 0,
        'cost_change': 0,
        'value_original': 500.0,
        'value_alternative': 500.0,
        'value_change': 0,
    }

    # 제안명 추출
    for line in lines:
        if '제안명' in line:
            m = re.search(r'제안명\(?[\d]*\)?\s*(.*)', line)
            if m:
                d['proposal_title'] = m.group(1).strip()
            break

    # 사업명
    for i, line in enumerate(lines):
        if '사업명' in line:
            if i+1 < len(lines):
                d['project_name'] = lines[i+1].strip()
            break

    # 가치유형
    for i, line in enumerate(lines):
        if '가치유형' in line:
            if i+1 < len(lines):
                d['value_type'] = lines[i+1].strip()
            break

    # 개선전/후 내용
    in_content = False
    for i, line in enumerate(lines):
        if '제안내용' in line:
            in_content = True
            continue
        if in_content and '개요도' in line:
            break
        if in_content:
            ls = line.strip()
            if ls.startswith('○') or ls.startswith('ㆍ'):
                if not d['original_description']:
                    d['original_description'] = ls.replace('○', '').strip()
                elif not d['alternative_description']:
                    d['alternative_description'] = ls.replace('○', '').strip()

    # 장점
    for i, line in enumerate(lines):
        if 'ㆍ' in line and '장' in ''.join(lines[max(0,i-3):i]):
            d['advantages'] = line.replace('ㆍ', '').strip()
            break

    # 성능/비용/가치 평가
    nums = re.findall(r'[\d,]+\.?\d*', text)

    # 성능평가 - "500" 다음에 나오는 숫자
    perf_match = re.search(r'성능평가\(%\)\s*(\d+)\s+([\d,.]+)\s+성능향상\s*([\d.]+)', text.replace('\n', ' '))
    if perf_match:
        d['perf_original'] = parse_num(perf_match.group(1))
        d['perf_alternative'] = parse_num(perf_match.group(2))
        d['perf_change'] = parse_num(perf_match.group(3))

    # 비용평가
    cost_match = re.search(r'비용평가\(백만원\)\s*([\d,.]+)\s+([\d,.]+)\s+비용절감\s*([\d.]+)', text.replace('\n', ' '))
    if cost_match:
        d['cost_original'] = parse_num(cost_match.group(1))
        d['cost_alternative'] = parse_num(cost_match.group(2))
        d['cost_change'] = parse_num(cost_match.group(3))

    # 가치평가
    value_match = re.search(r'가치평가\(%\)\s*([\d,.]+)\s+([\d,.]+)\s+가치향상\s*([\d.]+)', text.replace('\n', ' '))
    if value_match:
        d['value_original'] = parse_num(value_match.group(1))
        d['value_alternative'] = parse_num(value_match.group(2))
        d['value_change'] = parse_num(value_match.group(3))

    return d


def classify_field(title, text):
    civil_kw = ['터널', '교량', '도로', '노반', '토공', '사면', '옹벽', '흙막이', '파일', '기초',
                 '절토', '성토', '궤도', '레일', '전철', '철도', '선로', '역사', '정거장', '구조물']
    arch_kw = ['건축', '마감', '창호', '방수', '벽체', '천장', '단열', '외벽']
    mep_kw = ['전기', '기계', '설비', '신호', '통신', '전차선', '급전', '변전', '환기', '배수']

    combined = title + ' ' + text[:300]
    c = sum(1 for k in civil_kw if k in combined)
    a = sum(1 for k in arch_kw if k in combined)
    m = sum(1 for k in mep_kw if k in combined)
    if m > max(c, a): return '설비'
    elif a > c: return '건축'
    return '토목'


def insert_to_supabase(all_data):
    pg = get_pg()
    cur = pg.cursor()

    # 프로젝트 등록
    cur.execute("""
        INSERT INTO projects (project_id, project_name, file_path, total_alternatives, source_file, source_year, source_org)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (project_id) DO NOTHING
    """, ('kr_rail_2021_ve', '국가철도공단 2021년 설계VE 사례집', str(PDF_PATH), len(all_data),
          PDF_PATH.name, 2021, '국가철도공단'))

    # 기존 최대 alt_number
    cur.execute("SELECT COALESCE(MAX(alt_number), 0) FROM alternatives")
    max_num = cur.fetchone()[0]

    for i, d in enumerate(all_data):
        alt_num = max_num + i + 1
        alt_id = f"rail_{alt_num:03d}"

        cur.execute("""
            INSERT INTO alternatives (
                alt_id, project_id, alt_number, proposal_title,
                original_description, alternative_description,
                advantages, disadvantages, project_name, source_page,
                field_category, value_type_corrected, how2_code, how2_name, space
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (alt_id) DO NOTHING
        """, (alt_id, 'kr_rail_2021_ve', alt_num, d['proposal_title'],
              d['original_description'], d['alternative_description'],
              d['advantages'], d['disadvantages'], d['project_name'], d['source_page'],
              d['field_category'], d['value_type'], d.get('how2_code',''), d.get('how2_name',''), d.get('space','')))

        # 비용평가
        cur.execute("""
            INSERT INTO cost_evaluations (alt_id, cost_type, original_cost, alternative_cost, savings_amount, savings_rate)
            VALUES (%s,%s,%s,%s,%s,%s)
        """, (alt_id, 'project_lifecycle', d['cost_original'], d['cost_alternative'],
              d['cost_original'] - d['cost_alternative'], d['cost_change']))

        # 가치평가
        cur.execute("""
            INSERT INTO value_evaluations (alt_id, performance_original, performance_alternative,
                performance_change_rate, cost_change_rate, value_change_rate)
            VALUES (%s,%s,%s,%s,%s,%s)
        """, (alt_id, d['perf_original'], d['perf_alternative'],
              d['perf_change'], d['cost_change'], d['value_change']))

    pg.commit()
    pg.close()
    return max_num + 1, max_num + len(all_data)


def run():
    print("=" * 60)
    print("국가철도공단 2021 설계VE 사례집 추출")
    print("=" * 60)

    doc = fitz.open(str(PDF_PATH))
    print(f"  총 {len(doc)} 페이지")

    proposals = detect_proposals(doc)
    print(f"  VE 제안: {len(proposals)}건\n")

    sys.path.insert(0, str(BASE_DIR))
    from src.cube_taxonomy import classify_how2, classify_space

    all_data = []
    for idx, prop in enumerate(proposals):
        d = extract_data(prop['text'], prop['page'])
        d['field_category'] = classify_field(d['proposal_title'], prop['text'])

        title_text = d['proposal_title'] + ' ' + d['original_description'] + ' ' + d['alternative_description']
        how2_list = classify_how2(title_text)
        if how2_list:
            h = how2_list[0]
            d['how2_code'] = f"{h[0]}-{h[1]}" if len(h) >= 2 else ''
            d['how2_name'] = h[2] if len(h) >= 3 else ''
        else:
            d['how2_code'] = ''
            d['how2_name'] = ''

        space_list = classify_space(title_text)
        d['space'] = space_list[0] if isinstance(space_list, list) and space_list else ''

        # JSON 저장
        json_path = OUT_DIR / f"rail_{len(all_data)+1:03d}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(d, f, ensure_ascii=False, indent=2)

        all_data.append(d)
        if (idx+1) % 20 == 0:
            print(f"  ... {idx+1}/{len(proposals)}")

    print(f"  ✅ {len(all_data)}건 추출 완료")

    # Supabase 적재
    print(f"\n  DB 적재 중...")
    start, end = insert_to_supabase(all_data)
    print(f"  ✅ 대안 #{start}~#{end} 적재 완료")

    # 통계
    fields = {}
    vtypes = {}
    for d in all_data:
        fields[d['field_category']] = fields.get(d['field_category'], 0) + 1
        vtypes[d['value_type']] = vtypes.get(d['value_type'], 0) + 1

    doc.close()
    print(f"\n{'='*60}")
    print(f"  총 추출: {len(all_data)}건")
    print(f"  분야별: {fields}")
    print(f"  가치유형: {vtypes}")
    print(f"  대안: #{start} ~ #{end}")


if __name__ == "__main__":
    run()
