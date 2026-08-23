# Feature: Admin Full Access
**Owner:** Backend | **Module:** Assignment & RBAC

## Goal
Let admins bypass the ownership restrictions that apply to agents/customers.

## Scope
- Permission dependency checks: if `current_user.role == "admin"`, skip the ownership filter and allow the action.
