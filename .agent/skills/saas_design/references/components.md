# Core Components Reference

Notion/Figma 스타일 SaaS UI 핵심 컴포넌트 코드 레퍼런스.

---

## Button

```tsx
type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger';
type ButtonSize = 'sm' | 'md' | 'lg';

interface ButtonProps {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  disabled?: boolean;
  children: React.ReactNode;
  onClick?: () => void;
}

const variantClasses: Record<ButtonVariant, string> = {
  primary:   'bg-blue-600 text-white hover:bg-blue-700 border-transparent',
  secondary: 'bg-white text-gray-700 hover:bg-gray-50 border-gray-200',
  ghost:     'bg-transparent text-gray-600 hover:bg-gray-100 border-transparent',
  danger:    'bg-red-600 text-white hover:bg-red-700 border-transparent',
};

const sizeClasses: Record<ButtonSize, string> = {
  sm: 'h-7  px-3  text-xs  rounded-md',
  md: 'h-9  px-4  text-sm  rounded-md',
  lg: 'h-11 px-5  text-base rounded-lg',
};

export function Button({
  variant = 'secondary', size = 'md',
  loading, disabled, children, onClick,
}: ButtonProps) {
  return (
    <button
      onClick={onClick}
      disabled={disabled || loading}
      className={[
        'inline-flex items-center gap-2 font-medium border transition-colors',
        'focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        variantClasses[variant],
        sizeClasses[size],
      ].join(' ')}
    >
      {loading && <Spinner className="w-3.5 h-3.5" />}
      {children}
    </button>
  );
}
```

---

## Input

```tsx
interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  hint?: string;
  error?: string;
  leftIcon?: React.ReactNode;
}

export function Input({ label, hint, error, leftIcon, className, ...props }: InputProps) {
  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label className="text-sm font-medium text-gray-700">{label}</label>
      )}
      <div className="relative">
        {leftIcon && (
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">
            {leftIcon}
          </span>
        )}
        <input
          className={[
            'w-full h-9 rounded-md border border-gray-200 bg-white px-3 text-sm',
            'placeholder:text-gray-400 text-gray-900',
            'transition-colors focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20',
            error ? 'border-red-400 focus:border-red-400 focus:ring-red-400/20' : '',
            leftIcon ? 'pl-9' : '',
            className,
          ].join(' ')}
          {...props}
        />
      </div>
      {error && <p className="text-xs text-red-500">{error}</p>}
      {hint && !error && <p className="text-xs text-gray-400">{hint}</p>}
    </div>
  );
}
```

---

## Badge

```tsx
type BadgeVariant = 'default' | 'success' | 'warning' | 'danger' | 'info';

const badgeStyles: Record<BadgeVariant, string> = {
  default: 'bg-gray-100 text-gray-600',
  success: 'bg-emerald-50 text-emerald-700',
  warning: 'bg-amber-50  text-amber-700',
  danger:  'bg-red-50    text-red-700',
  info:    'bg-blue-50   text-blue-700',
};

export function Badge({ variant = 'default', children }: { variant?: BadgeVariant; children: React.ReactNode }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium ${badgeStyles[variant]}`}>
      {children}
    </span>
  );
}
```

---

## Card

```tsx
interface CardProps {
  title?: string;
  description?: string;
  action?: React.ReactNode;
  children: React.ReactNode;
  padding?: 'sm' | 'md' | 'lg';
}

const paddingMap = { sm: 'p-4', md: 'p-5', lg: 'p-6' };

export function Card({ title, description, action, children, padding = 'md' }: CardProps) {
  return (
    <div className="bg-white rounded border border-gray-200 shadow-sm overflow-hidden">
      {(title || action) && (
        <div className="flex items-start justify-between px-5 pt-5 pb-0">
          <div>
            {title && <h3 className="text-sm font-semibold text-gray-900">{title}</h3>}
            {description && <p className="mt-0.5 text-xs text-gray-500">{description}</p>}
          </div>
          {action}
        </div>
      )}
      <div className={paddingMap[padding]}>{children}</div>
    </div>
  );
}
```

---

## Modal

```tsx
interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  size?: 'sm' | 'md' | 'lg';
}

const sizeMap = { sm: 'max-w-sm', md: 'max-w-lg', lg: 'max-w-2xl' };

export function Modal({ open, onClose, title, description, children, footer, size = 'md' }: ModalProps) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={onClose} />
      {/* Panel */}
      <div className={`relative w-full ${sizeMap[size]} bg-white rounded shadow-xl`}>
        <div className="flex items-start justify-between p-5 border-b border-gray-100">
          <div>
            <h2 className="text-base font-semibold text-gray-900">{title}</h2>
            {description && <p className="mt-0.5 text-sm text-gray-500">{description}</p>}
          </div>
          <button onClick={onClose} className="p-1 rounded-md hover:bg-gray-100 text-gray-400" aria-label="닫기">✕</button>
        </div>
        <div className="p-5">{children}</div>
        {footer && <div className="flex justify-end gap-2 px-5 py-4 border-t border-gray-100 bg-gray-50/50">{footer}</div>}
      </div>
    </div>
  );
}
```

---

## Table

```tsx
interface Column<T> {
  key: keyof T;
  label: string;
  render?: (value: T[keyof T], row: T) => React.ReactNode;
}

interface TableProps<T extends { id: string | number }> {
  columns: Column<T>[];
  data: T[];
  loading?: boolean;
  emptyMessage?: string;
}

export function Table<T extends { id: string | number }>({
  columns, data, loading, emptyMessage = '데이터가 없습니다.',
}: TableProps<T>) {
  return (
    <div className="overflow-x-auto rounded border border-gray-200">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200 bg-gray-50/80">
            {columns.map(col => (
              <th key={String(col.key)} className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {loading ? (
            Array.from({ length: 4 }).map((_, i) => (
              <tr key={i}>
                {columns.map((col, j) => (
                  <td key={j} className="px-4 py-3">
                    <div className="h-4 bg-gray-100 rounded animate-pulse w-3/4" />
                  </td>
                ))}
              </tr>
            ))
          ) : data.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="px-4 py-12 text-center text-sm text-gray-400">
                {emptyMessage}
              </td>
            </tr>
          ) : (
            data.map(row => (
              <tr key={row.id} className="hover:bg-gray-50/60 transition-colors">
                {columns.map(col => (
                  <td key={String(col.key)} className="px-4 py-3 text-gray-700">
                    {col.render ? col.render(row[col.key], row) : String(row[col.key] ?? '')}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
```

---

## Toast (간단 구현)

```tsx
// 사용: toast.success('저장됐습니다'), toast.error('오류가 발생했습니다')
// zustand 또는 context로 전역 관리 권장

export function Toast({ message, type }: { message: string; type: 'success' | 'error' | 'info' }) {
  const styles = {
    success: 'bg-emerald-600',
    error:   'bg-red-600',
    info:    'bg-gray-900',
  };
  return (
    <div className={`fixed bottom-4 right-4 z-50 flex items-center gap-3 px-4 py-3 rounded-lg text-white text-sm shadow-lg ${styles[type]}`}>
      {message}
    </div>
  );
}
```