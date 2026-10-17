import { Shield, GraduationCap, User } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

export type Role = 'user' | 'teacher' | 'admin';

interface RoleStyle {
  bg: string;
  Icon: LucideIcon;
  label: string;
}

const ROLE_STYLES: Record<Role, RoleStyle> = {
  user: {
    bg: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
    Icon: User,
    label: 'Student',
  },
  teacher: {
    bg: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300',
    Icon: GraduationCap,
    label: 'Teacher',
  },
  admin: {
    bg: 'bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-300',
    Icon: Shield,
    label: 'Admin',
  },
};

export interface RoleBadgeProps {
  role: Role | string;
}

/**
 * RoleBadge — color/icon-coded role indicator (Phase 4).
 *
 * Reuses the visual style established inline in AccountManagementPage.
 * Falls back to Student styling for unknown roles.
 */
export function RoleBadge({ role }: RoleBadgeProps) {
  const style = ROLE_STYLES[role as Role] ?? ROLE_STYLES.user;
  const { Icon, label, bg } = style;
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold ${bg}`}
    >
      <Icon className="h-3 w-3" />
      {label}
    </span>
  );
}
