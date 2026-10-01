# Role-Based Access Control (RBAC) in Maintenance Operations

## 1. Role Capabilities Matrix

MachIntel enforces role-based access control across all maintenance API endpoints and frontend controls:

| Role | Read Work Orders & Summaries | Draft Recommendations | Acknowledge Work Orders | Start / Complete Orders | Cancel Work Orders |
|---|:---:|:---:|:---:|:---:|:---:|
| **VIEWER** | ✅ | ❌ (403 Forbidden) | ❌ (403 Forbidden) | ❌ (403 Forbidden) | ❌ (403 Forbidden) |
| **OPERATOR** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **ADMIN** | ✅ | ✅ | ✅ | ✅ | ✅ |

---

## 2. Backend Enforcement

All mutation routes in `backend/app/api/v1/endpoints/maintenance.py` use the dependency:
```python
current_user: User = Depends(require_roles([UserRole.OPERATOR, UserRole.ADMIN]))
```
If a user with `VIEWER` credentials attempts any mutation, FastAPI raises a `PermissionDeniedException` resulting in a standard HTTP 403 response:
```json
{
  "error": {
    "code": "PERMISSION_DENIED",
    "message": "Action requires one of roles: ['OPERATOR', 'ADMIN']",
    "details": {
      "user_role": "VIEWER",
      "required_roles": ["OPERATOR", "ADMIN"]
    }
  }
}
```

---

## 3. Frontend UI Adaptation

- In `frontend/app/maintenance/page.tsx`:
  - `const canMutate = user && user.role !== "VIEWER";`
  - Action buttons (`ACKNOWLEDGE WORK ORDER`, `START EXECUTION`, `COMPLETE & RECORD OUTCOME`, `CREATE RECOMMENDATION`) are conditionally rendered only when `canMutate` is true.
  - When viewed by a user with role `VIEWER`, the interface explicitly renders an informational notice:
    *"Viewer role: Read-only access. Operator or Admin credentials required to execute transitions."*
