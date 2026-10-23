/**
 * useRole() — capability-based role abstraction (v1.15 / Phase 3).
 *
 * Replaces scattered `user?.role === 'admin'` checks across the codebase.
 * Components should query capabilities, not roles — easier to evolve
 * when we add a 4th role later.
 *
 * Capabilities are derived from role via ROLE_CAPABILITIES table.
 * Keep this list in sync with backend ROLES_PLAN.md §C.1.
 */
import { useAuth } from '@/contexts/AuthContext';

export type UserRole = 'user' | 'teacher' | 'admin';

export type UserCapability =
  // student
  | 'upload_essay'
  | 'view_own_history'
  // teacher + admin
  | 'view_class_history'
  | 'override_verdict'
  | 'view_logic_trace'
  | 'view_document_inspector'
  | 'view_orphan_detection'
  | 'create_class'
  // admin only
  | 'manage_users'
  | 'system_settings'
  | 'view_audit_log'
  | 'view_system_health';

const ROLE_CAPABILITIES: Record<UserRole, UserCapability[]> = {
  user: ['upload_essay', 'view_own_history'],
  teacher: [
    'upload_essay',
    'view_own_history',
    'view_class_history',
    'override_verdict',
    'view_logic_trace',
    'view_document_inspector',
    'view_orphan_detection',
    'create_class',
  ],
  admin: [
    'upload_essay',
    'view_own_history',
    'view_class_history',
    'override_verdict',
    'view_logic_trace',
    'view_document_inspector',
    'view_orphan_detection',
    'create_class',
    'manage_users',
    'system_settings',
    'view_audit_log',
    'view_system_health',
  ],
};

export interface UseRoleResult {
  role: UserRole;
  isUser: boolean;
  isTeacher: boolean;
  isAdmin: boolean;
  capabilities: ReadonlyArray<UserCapability>;
  has: (cap: UserCapability) => boolean;
  hasAny: (caps: UserCapability[]) => boolean;
  hasAll: (caps: UserCapability[]) => boolean;
}

export function useRole(): UseRoleResult {
  const { user } = useAuth();
  // Default to 'user' (least privilege) when unauthenticated so accidental
  // capability checks don't accidentally grant anything.
  const role: UserRole = (user?.role as UserRole) ?? 'user';
  const baseCapabilities = ROLE_CAPABILITIES[role] ?? [];
  const capabilities =
    user?.can_override_verdicts === false
      ? baseCapabilities.filter((c) => c !== 'override_verdict')
      : baseCapabilities;

  return {
    role,
    isUser: role === 'user',
    isTeacher: role === 'teacher',
    isAdmin: role === 'admin',
    capabilities,
    has: (cap) => capabilities.includes(cap),
    hasAny: (caps) => caps.some((c) => capabilities.includes(c)),
    hasAll: (caps) => caps.every((c) => capabilities.includes(c)),
  };
}
