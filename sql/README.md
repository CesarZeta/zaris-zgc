# Migraciones SQL

Convención (heredada de ZGE): archivos numerados secuenciales, idempotentes cuando sea posible.

```
sql/
  001_nucleo_tenants_usuarios.sql
  002_bue_entidades.sql
  ...
```

- Cada migración se aplica en Supabase (prod) vía MCP `apply_migration` o SQL editor, y en local sobre `zgc_dev`.
- El historial de qué se aplicó y cuándo se lleva en `HISTORIAL_MIGRACIONES.md` (crear al aplicar la primera).
- Regla: toda tabla lleva `tenant_id` + RLS (ver CLAUDE.md §1-bis).
