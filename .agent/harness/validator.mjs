import fs from 'fs';
import path from 'path';
import { execSync } from 'child_process';

console.log('==================================================');
console.log('🛡️ Ninetynine Inc. AI Harness Validation System');
console.log('==================================================');

const IGNORE_DIRS = ['.git', 'node_modules', '.next', '.agent', 'chroma_db', 'public'];
const IGNORE_FILES = ['.rule.md', '.env', '.env.local', 'package-lock.json', 'development_processes_modification_history.md'];

// 보안 검색 패턴 (회사 자산 및 민감 정보)
const SENSITIVE_PATTERNS = [
  { name: 'Gemini API Key', regex: /AIzaSy[A-Za-z0-9\-_]{33}/ },
  { name: 'Naver Cloud IP', regex: /110\.165\.17\.170/ },
  { name: 'Naver Console 로그인 정보', regex: /(nine@0172|bignine99@naver\.com.*nine@0172)/i },
  { name: 'Root SSH 비밀번호', regex: /J9\?GfqNT5FTq/ }
];

let issuesFound = 0;

function walkDir(dir) {
  let files = [];
  const list = fs.readdirSync(dir);
  
  for (let file of list) {
    const fullPath = path.join(dir, file);
    const stat = fs.statSync(fullPath);
    
    if (stat && stat.isDirectory()) {
      if (!IGNORE_DIRS.includes(file)) {
        files = files.concat(walkDir(fullPath));
      }
    } else {
      const ext = path.extname(file).toLowerCase();
      const validExts = ['.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs', '.py', '.sh', '.bat', '.ps1', '.json', '.yml', '.yaml', '.html', '.css'];
      if (!IGNORE_FILES.includes(file) && validExts.includes(ext)) {
        files.push(fullPath);
      }
    }
  }
  return files;
}

function checkSecurity(files) {
  console.log('\n[1] 보안 및 시크릿 키 유출 검사 시작...');
  let passed = true;
  
  files.forEach(file => {
    const content = fs.readFileSync(file, 'utf8');
    SENSITIVE_PATTERNS.forEach(pattern => {
      if (pattern.regex.test(content)) {
        console.error(`  ❌ [보안 위반] ${file} 파일에 '${pattern.name}' 패턴이 평문으로 하드코딩 되어 있습니다!`);
        passed = false;
        issuesFound++;
      }
    });
  });

  if (passed) {
    console.log('  ✅ 모든 파일이 보안 스캔을 통과했습니다. (Zero-Leakage)');
  }
}

function checkProcessHistory() {
  console.log('\n[2] 작업 프로세스 검사 시작...');
  const historyFilePathV1 = path.join(process.cwd(), 'development_processes_modification_history.md');
  const historyFilePathV2 = path.join(process.cwd(), 'development_processes_modification_history_v2.md');
  const planFilePath = path.join(process.cwd(), 'implementation-plan.md');

  const v1Exists = fs.existsSync(historyFilePathV1);
  const v2Exists = fs.existsSync(historyFilePathV2);

  if (!v1Exists && !v2Exists) {
    console.error('  ❌ [프로세스 위반] development_processes_modification_history.md (v1 또는 v2) 파일이 존재하지 않습니다.');
    issuesFound++;
  } else {
    // v2 우선, 없으면 v1 사용
    const historyFilePath = v2Exists ? historyFilePathV2 : historyFilePathV1;
    const versionLabel = v2Exists ? 'v2' : 'v1';
    const stat = fs.statSync(historyFilePath);
    const diffHours = (new Date() - stat.mtime) / (1000 * 60 * 60);
    if (diffHours > 24) {
      console.warn(`  ⚠️ [권고] 작업 이력 문서(${versionLabel})가 24시간 내에 업데이트되지 않았습니다. 작업 이력을 기록하십시오.`);
    } else {
      console.log(`  ✅ 작업 이력 문서(${versionLabel})가 최신 상태로 유지되고 있습니다.`);
    }
  }

  if (fs.existsSync(planFilePath)) {
     console.log('  ✅ 초기 설계 PRD(implementation-plan.md) 파일이 파악되었습니다.');
  } else {
     console.warn('  ⚠️ 초기 설계 PRD(implementation-plan.md) 파일이 존재하지 않습니다.');
  }
}

// ─── [3] 변경 범위 감사 (Surgical Change Audit) ───

const CHANGED_FILES_THRESHOLD = 10;

function checkSurgicalChanges() {
  console.log('\n[3] 변경 범위 감사 (Surgical Change Audit)...');

  let gitAvailable = false;
  try {
    execSync('git rev-parse --is-inside-work-tree', { cwd: process.cwd(), stdio: 'pipe' });
    gitAvailable = true;
  } catch {
    console.log('  ⏭️ Git 저장소가 아닙니다. 변경 범위 감사를 건너뜁니다.');
    return;
  }

  if (!gitAvailable) return;

  try {
    // staged + unstaged 변경 파일 목록
    const diffOutput = execSync('git diff --name-only HEAD 2>nul || git diff --name-only', {
      cwd: process.cwd(),
      encoding: 'utf8',
      stdio: ['pipe', 'pipe', 'pipe']
    }).trim();

    const stagedOutput = execSync('git diff --cached --name-only', {
      cwd: process.cwd(),
      encoding: 'utf8',
      stdio: ['pipe', 'pipe', 'pipe']
    }).trim();

    const allChanged = new Set([
      ...diffOutput.split('\n').filter(f => f.trim()),
      ...stagedOutput.split('\n').filter(f => f.trim())
    ]);

    if (allChanged.size === 0) {
      console.log('  ✅ 변경된 파일이 없습니다.');
      return;
    }

    console.log(`  📊 변경된 파일 수: ${allChanged.size}개`);

    if (allChanged.size > CHANGED_FILES_THRESHOLD) {
      console.warn(`  ⚠️ [권고] 변경 파일이 ${CHANGED_FILES_THRESHOLD}개를 초과합니다 (${allChanged.size}개). 외과적 변경 원칙(§3-3)을 준수하고 있는지 확인하십시오.`);
    } else {
      console.log('  ✅ 변경 범위가 적정 수준입니다.');
    }
  } catch {
    console.log('  ⏭️ Git diff 실행 중 오류가 발생했습니다. 변경 범위 감사를 건너뜁니다.');
  }
}

// ─── [4] 코드 위생 검사 (Code Hygiene) ───

const HYGIENE_PATTERNS = [
  { name: 'console.log', regex: /console\.log\s*\(/, severity: 'warn' },
  { name: 'debugger 문', regex: /^\s*debugger\s*;?\s*$/m, severity: 'error' },
  { name: 'TODO 주석', regex: /\/\/\s*(TODO|FIXME|HACK)\b/i, severity: 'warn' },
];

// src/ 내 프로덕션 코드만 대상 (JS/TS)
const HYGIENE_EXTS = ['.js', '.jsx', '.ts', '.tsx'];

function checkCodeHygiene(files) {
  console.log('\n[4] 코드 위생 검사 (Code Hygiene)...');
  let passed = true;
  const srcDir = path.join(process.cwd(), 'src');

  const targetFiles = files.filter(f => {
    const ext = path.extname(f).toLowerCase();
    return HYGIENE_EXTS.includes(ext) && f.startsWith(srcDir);
  });

  if (targetFiles.length === 0) {
    console.log('  ⏭️ src/ 내 JS/TS 대상 파일이 없습니다.');
    return;
  }

  targetFiles.forEach(file => {
    const content = fs.readFileSync(file, 'utf8');
    const relativePath = path.relative(process.cwd(), file);

    HYGIENE_PATTERNS.forEach(pattern => {
      if (pattern.regex.test(content)) {
        if (pattern.severity === 'error') {
          console.error(`  ❌ [코드 위생] ${relativePath} 에 '${pattern.name}'이(가) 잔존합니다. 프로덕션 코드에서 제거하십시오.`);
          passed = false;
          issuesFound++;
        } else {
          console.warn(`  ⚠️ [권고] ${relativePath} 에 '${pattern.name}'이(가) 발견되었습니다.`);
        }
      }
    });
  });

  if (passed) {
    console.log('  ✅ 프로덕션 코드에 디버그 잔재가 없습니다.');
  }
}

// ─── [5] 스타일 일관성 검사 (Style Consistency — 경고만) ───

function checkStyleConsistency(files) {
  console.log('\n[5] 스타일 일관성 검사 (Style Consistency)...');
  let warned = false;
  const srcDir = path.join(process.cwd(), 'src');

  const targetFiles = files.filter(f => {
    const ext = path.extname(f).toLowerCase();
    return HYGIENE_EXTS.includes(ext) && f.startsWith(srcDir);
  });

  if (targetFiles.length === 0) {
    console.log('  ⏭️ src/ 내 JS/TS 대상 파일이 없습니다.');
    return;
  }

  targetFiles.forEach(file => {
    const content = fs.readFileSync(file, 'utf8');
    const relativePath = path.relative(process.cwd(), file);
    const lines = content.split('\n');

    // 따옴표 혼용 검사: import/require 구문에서만 체크 (전체 파일은 오탐 위험)
    let singleCount = 0;
    let doubleCount = 0;

    lines.forEach(line => {
      const trimmed = line.trim();
      if (trimmed.startsWith('import ') || trimmed.startsWith('from ') || trimmed.includes('require(')) {
        if (/\'/.test(trimmed)) singleCount++;
        if (/\"/.test(trimmed)) doubleCount++;
      }
    });

    if (singleCount > 0 && doubleCount > 0) {
      console.warn(`  ⚠️ [스타일] ${relativePath}: import 구문에서 작은따옴표(${singleCount}회)와 큰따옴표(${doubleCount}회)가 혼용됩니다.`);
      warned = true;
    }
  });

  if (!warned) {
    console.log('  ✅ import 구문의 따옴표 스타일이 일관적입니다.');
  }
}

// ─── 메인 실행 ───

const allTargetFiles = walkDir(process.cwd());
checkSecurity(allTargetFiles);
checkProcessHistory();
checkSurgicalChanges();
checkCodeHygiene(allTargetFiles);
checkStyleConsistency(allTargetFiles);

console.log('\n==================================================');
if (issuesFound > 0) {
  console.error(`🚨 검증 실패: 총 ${issuesFound}건의 하네스 규칙 위반이 발견되었습니다.`);
  console.error('코드를 병합(Merge)하거나 배포하기 전에 위의 문제를 반드시 해결하십시오.');
  process.exit(1);
} else {
  console.log('🎉 하네스 검증 통과! 프로덕션 수준의 안정성과 보안이 유지되고 있습니다.');
  process.exit(0);
}

