# ADR: Slug único por tienda

## Contexto
Necesitamos identificar categorías y productos dentro de cada tienda de forma estable. El campo `slug` se usa en rutas y para búsquedas rápidas.

## Decisión
- `slug` es único por tienda vía índice único `(shop_id, slug)`.
- Distintas tiendas pueden reutilizar el mismo `slug`.
- Se normaliza el `slug` server-side: lowercase, sin acentos, espacios→guiones (ver `app/core/slugify.py`).

## Consecuencias
- Búsquedas simples: `WHERE shop_id = ? AND slug = ?`.
- Evita colisiones entre tiendas distintas.
- Tests cubren duplicado en misma tienda (409) y permitido en otra tienda.
