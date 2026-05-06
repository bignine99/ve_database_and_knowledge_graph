# SaaS Layout Patterns

전체 페이지 레이아웃 코드 레퍼런스. React(Next.js 호환) 기준.

---

## Dashboard Layout (Sidebar + Main)

```tsx
// app/dashboard/layout.tsx (Next.js App Router)
'use client';
import { useState } from 'react';

const navItems = [
  { icon: '⊞', label: '대시보드', href: '/dashboard' },
  { icon: '◫', label: '프로젝트',  href: '/projects' },
  { icon: '◻', label: '분석',      href: '/analytics' },
  { icon: '⚙', label: '설정',      href: '/settings' },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="flex h-screen bg-[#f7f7f5] overflow-hidden">
      {/* Sidebar */}
      <aside className={[
        'hidden md:flex flex-col border-r border-gray-200 bg-white transition-all duration-200',
        collapsed ? 'w-16' : 'w-60',
      ].join(' ')}>
        {/* Logo */}
        <div className="flex items-center gap-3 h-14 px-4 border-b border-gray-100">
          <div className="w-7 h-7 rounded bg-blue-600 flex-shrink-0" />
          {!collapsed && <span className="font-semibold text-gray-900 text-sm">MyApp</span>}
        </div>

        {/* Nav */}
        <nav className="flex-1 p-2 space-y-0.5">
          {navItems.map(item => (
            <a
              key={item.href}
              href={item.href}
              className="flex items-center gap-3 px-2.5 py-2 rounded-md text-sm text-gray-600 hover:bg-gray-100 hover:text-gray-900 transition-colors"
            >
              <span className="text-base w-5 text-center flex-shrink-0">{item.icon}</span>
              {!collapsed && <span>{item.label}</span>}
            </a>
          ))}
        </nav>

        {/* Collapse toggle */}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="m-2 p-2 rounded-md text-gray-400 hover:bg-gray-100 hover:text-gray-600 text-xs"
        >
          {collapsed ? '→' : '←'}
        </button>
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="h-14 flex items-center justify-between px-6 bg-white border-b border-gray-200 flex-shrink-0">
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <span>대시보드</span>
          </div>
          <div className="flex items-center gap-3">
            {/* TODO: 알림 벨, 유저 아바타 */}
            <div className="w-8 h-8 rounded-full bg-gray-200" />
          </div>
        </header>

        {/* Content */}
        <main className="flex-1 overflow-y-auto p-6">
          <div className="max-w-7xl mx-auto">{children}</div>
        </main>
      </div>
    </div>
  );
}
```

---

## Settings Page Layout

```tsx
const settingsSections = [
  { id: 'profile',      label: '프로필' },
  { id: 'account',      label: '계정' },
  { id: 'billing',      label: '결제' },
  { id: 'integrations', label: '연동' },
  { id: 'security',     label: '보안' },
];

export default function SettingsPage() {
  const [active, setActive] = useState('profile');

  return (
    <div className="max-w-5xl mx-auto">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-gray-900">설정</h1>
        <p className="mt-1 text-sm text-gray-500">계정 및 서비스 설정을 관리합니다.</p>
      </div>

      <div className="flex gap-8">
        {/* Side nav */}
        <nav className="w-44 flex-shrink-0 space-y-0.5">
          {settingsSections.map(sec => (
            <button
              key={sec.id}
              onClick={() => setActive(sec.id)}
              className={[
                'w-full text-left px-3 py-2 rounded-md text-sm transition-colors',
                active === sec.id
                  ? 'bg-gray-100 text-gray-900 font-medium'
                  : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900',
              ].join(' ')}
            >
              {sec.label}
            </button>
          ))}
        </nav>

        {/* Content panel */}
        <div className="flex-1 min-w-0">
          <div className="bg-white rounded border border-gray-200 shadow-sm p-6">
            {/* TODO: active 값에 따라 각 섹션 컴포넌트 렌더링 */}
            <h2 className="text-base font-semibold text-gray-900 mb-4">
              {settingsSections.find(s => s.id === active)?.label}
            </h2>
            {/* Form content here */}
          </div>
        </div>
      </div>
    </div>
  );
}
```

---

## Auth / Login Page

```tsx
export default function LoginPage() {
  return (
    <div className="min-h-screen bg-[#f7f7f5] flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded bg-blue-600 mb-4">
            <span className="text-white text-xl font-bold">M</span>
          </div>
          <h1 className="text-2xl font-semibold text-gray-900">로그인</h1>
          <p className="mt-1.5 text-sm text-gray-500">계정에 접속하세요</p>
        </div>

        {/* Card */}
        <div className="bg-white rounded border border-gray-200 shadow-sm p-6 space-y-4">
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-gray-700">이메일</label>
            <input
              type="email"
              placeholder="name@company.com"
              className="w-full h-9 px-3 rounded-md border border-gray-200 text-sm focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
            />
          </div>
          <div className="space-y-1.5">
            <div className="flex justify-between">
              <label className="text-sm font-medium text-gray-700">비밀번호</label>
              <a href="#" className="text-xs text-blue-600 hover:underline">비밀번호 찾기</a>
            </div>
            <input
              type="password"
              placeholder="••••••••"
              className="w-full h-9 px-3 rounded-md border border-gray-200 text-sm focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
            />
          </div>
          <button className="w-full h-9 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-md transition-colors">
            로그인
          </button>
        </div>

        <p className="text-center mt-4 text-sm text-gray-500">
          계정이 없으신가요?{' '}
          <a href="/signup" className="text-blue-600 hover:underline font-medium">무료로 시작</a>
        </p>
      </div>
    </div>
  );
}
```

---

## Onboarding Flow (Step Wizard)

```tsx
const steps = ['팀 정보', '멤버 초대', '도구 연동', '시작'];

export default function OnboardingPage({ currentStep = 0 }: { currentStep?: number }) {
  return (
    <div className="min-h-screen bg-[#f7f7f5] flex flex-col items-center pt-16 px-4">
      {/* Progress bar */}
      <div className="w-full max-w-lg mb-8">
        <div className="flex items-center justify-between mb-2">
          {steps.map((step, i) => (
            <div key={i} className="flex items-center gap-2">
              <div className={[
                'w-7 h-7 rounded-full flex items-center justify-center text-xs font-medium',
                i < currentStep  ? 'bg-blue-600 text-white' :
                i === currentStep ? 'bg-blue-600 text-white ring-4 ring-blue-100' :
                'bg-white border-2 border-gray-200 text-gray-400',
              ].join(' ')}>
                {i < currentStep ? '✓' : i + 1}
              </div>
              {i < steps.length - 1 && (
                <div className={`w-16 sm:w-24 h-0.5 ${i < currentStep ? 'bg-blue-600' : 'bg-gray-200'}`} />
              )}
            </div>
          ))}
        </div>
        <p className="text-xs text-gray-500 text-right">{steps[currentStep]}</p>
      </div>

      {/* Step content */}
      <div className="w-full max-w-lg bg-white rounded border border-gray-200 shadow-sm p-8">
        {/* TODO: currentStep에 따라 각 스텝 컴포넌트 렌더링 */}
        <h2 className="text-lg font-semibold text-gray-900 mb-1">{steps[currentStep]}</h2>
        <p className="text-sm text-gray-500 mb-6">설정을 완료해 주세요.</p>
        {/* Form content */}
        <div className="flex justify-between mt-8">
          <button className="px-4 h-9 text-sm text-gray-600 hover:bg-gray-100 rounded-md transition-colors">이전</button>
          <button className="px-5 h-9 text-sm font-medium bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors">
            {currentStep === steps.length - 1 ? '완료' : '다음'}
          </button>
        </div>
      </div>
    </div>
  );
}
```