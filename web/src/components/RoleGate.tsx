/**
 * <RoleGate> — declarative permission gate (v1.15 / Phase 3).
 *
 * Renders children only when the current user satisfies all the given
 * constraints (capability / capabilities / anyOf / roles). Otherwise
 * renders `fallback` (default: nothing).
 *
 * Multiple constraints are AND-combined (must satisfy all).
 *
 * Usage:
 *   <RoleGate capability="manage_users">
 *     <DeleteUserButton />
 *   </RoleGate>
 *
 *   <RoleGate anyOf={['override_verdict', 'manage_users']} fallback={<LockedHint />}>
 *     <OverrideControls />
 *   </RoleGate>
 */
import { useRole, type UserCapability, type UserRole } from '@/hooks/useRole';
import type { ReactNode } from 'react';

interface RoleGateProps {
  /** Require a single capability. */
  capability?: UserCapability;
  /** Require ALL listed capabilities. */
  capabilities?: UserCapability[];
  /** Require ANY of the listed capabilities. */
  anyOf?: UserCapability[];
  /** Require user role to be one of these. */
  roles?: UserRole[];
  /** Rendered when access is denied. Default: nothing. */
  fallback?: ReactNode;
  children: ReactNode;
}

export function RoleGate({
  capability,
  capabilities,
  anyOf,
  roles,
  fallback = null,
  children,
}: RoleGateProps) {
  const { has, hasAll, hasAny, role } = useRole();

  if (capability && !has(capability)) return <>{fallback}</>;
  if (capabilities && !hasAll(capabilities)) return <>{fallback}</>;
  if (anyOf && !hasAny(anyOf)) return <>{fallback}</>;
  if (roles && !roles.includes(role)) return <>{fallback}</>;

  return <>{children}</>;
}
