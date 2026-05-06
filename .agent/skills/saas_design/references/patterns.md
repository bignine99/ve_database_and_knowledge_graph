# UI Patterns Reference

Empty State, Loading, Error, Stats Card 등 SaaS에서 반복 사용되는 UI 패턴.

---

## Empty State

```tsx
interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: { label: string; onClick: () => void };
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-4 text-center">
      {icon && (
        <div className="w-12 h-12 rounded bg-gray-100 flex items-center justify-center text-2xl mb-4">
          {icon}
        </div>
      )}
      <h3 className="text-sm font-semibold text-gray-900">{title}</h3>
      {description && <p className="mt-1 text-sm text-gray-500 max-w-sm">{description}</p>}
      {action && (
        <button
          onClick={action.onClick}
          className="mt-4 h-8 px-4 text-xs font-medium bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
        >
          {action.label}
        </button>
      )}
    </div>
  );
}
```

---

## Loading Skeleton

```tsx
// 범용 스켈레톤 블록
export function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`bg-gray-100 animate-pulse rounded-md ${className}`} />;
}

// 카드 스켈레톤 예시
export function CardSkeleton() {
  return (
    <div className="bg-white rounded border border-gray-200 p-5 space-y-3">
      <Skeleton className="h-4 w-1/3" />
      <Skeleton className="h-3 w-2/3" />
      <Skeleton className="h-3 w-1/2" />
    </div>
  );
}

// 테이블 로우 스켈레톤
export function TableSkeleton({ rows = 5, cols = 4 }: { rows?: number; cols?: number }) {
  return (
    <div className="space-y-px">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex gap-4 px-4 py-3 border-b border-gray-100">
          {Array.from({ length: cols }).map((_, j) => (
            <Skeleton key={j} className={`h-4 flex-1 ${j === 0 ? 'max-w-[120px]' : ''}`} />
          ))}
        </div>
      ))}
    </div>
  );
}
```

---

## Stats Card Grid

```tsx
interface Stat {
  label: string;
  value: string | number;
  change?: { value: string; positive: boolean };
  icon?: string;
}

export function StatsGrid({ stats }: { stats: Stat[] }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {stats.map((stat, i) => (
        <div key={i} className="bg-white rounded border border-gray-200 shadow-sm p-5">
          <div className="flex items-center justify-between mb-3">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">{stat.label}</p>
            {stat.icon && <span className="text-lg">{stat.icon}</span>}
          </div>
          <p className="text-2xl font-semibold text-gray-900">{stat.value}</p>
          {stat.change && (
            <p className={`mt-1 text-xs font-medium ${stat.change.positive ? 'text-emerald-600' : 'text-red-500'}`}>
              {stat.change.positive ? '↑' : '↓'} {stat.change.value} 지난 달 대비
            </p>
          )}
        </div>
      ))}
    </div>
  );
}
```

---

## Error Boundary (React)

```tsx
import { Component, ReactNode } from 'react';

interface ErrorBoundaryState { hasError: boolean; error?: Error; }

export class ErrorBoundary extends Component<
  { children: ReactNode; fallback?: ReactNode },
  ErrorBoundaryState
> {
  state: ErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback ?? (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <div className="text-3xl mb-3">⚠</div>
          <h3 className="text-sm font-semibold text-gray-900">문제가 발생했습니다</h3>
          <p className="mt-1 text-sm text-gray-500">페이지를 새로고침 해주세요.</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-4 h-8 px-4 text-xs font-medium border border-gray-200 rounded-md hover:bg-gray-50 transition-colors"
          >
            새로고침
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
```

---

## Dropdown Menu

```tsx
import { useState, useRef, useEffect } from 'react';

interface MenuItem {
  label: string;
  icon?: string;
  onClick: () => void;
  destructive?: boolean;
}

export function DropdownMenu({
  trigger,
  items,
}: {
  trigger: React.ReactNode;
  items: MenuItem[];
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  return (
    <div className="relative inline-block" ref={ref}>
      <div onClick={() => setOpen(!open)}>{trigger}</div>
      {open && (
        <div className="absolute right-0 mt-1 w-48 bg-white border border-gray-200 rounded shadow-lg z-50 py-1 overflow-hidden">
          {items.map((item, i) => (
            <button
              key={i}
              onClick={() => { item.onClick(); setOpen(false); }}
              className={[
                'w-full flex items-center gap-2.5 px-3 py-2 text-sm text-left transition-colors',
                item.destructive
                  ? 'text-red-600 hover:bg-red-50'
                  : 'text-gray-700 hover:bg-gray-50',
              ].join(' ')}
            >
              {item.icon && <span>{item.icon}</span>}
              {item.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
```