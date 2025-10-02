from __future__ import annotations
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status, Response
from sqlalchemy import select, func, or_, asc, desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.common import ListResponse, MetaPagination, SingleResponse, DeleteResult

from app.db.session import get_session
from app.models.product import Product
from app.models.category import Category
from app.models.shop import Shop
from app.schemas.product import (
    ProductCreate,
    ProductOut,
    ProductSort,
    ProductUpdate,
    ProductUpdatePartial,
)
from app.core.slugify import slugify
from app.core.pagination import pagination_params, PaginationParams

router = APIRouter(prefix="/products", tags=["products"])


# ------------------------ Helpers ------------------------ #


async def slug_in_use(
    db: AsyncSession, *, shop_id: int, slug: str, exclude_id: int | None = None
) -> bool:
    stmt = (
        select(func.count())
        .select_from(Product)
        .where(
            Product.shop_id == shop_id,
            Product.slug == slug,
        )
    )
    if exclude_id is not None:
        stmt = stmt.where(Product.id != exclude_id)
    res = await db.execute(stmt)
    return int(res.scalar() or 0) > 0


async def ensure_category_in_shop(db: AsyncSession, *, category_id: int, shop_id: int) -> None:
    row = (
        await db.execute(select(Category.id, Category.shop_id).where(Category.id == category_id))
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="category not found")
    if row.shop_id != shop_id:
        raise HTTPException(status_code=400, detail="category belongs to a different shop")


async def fetch_product_or_404(db: AsyncSession, *, product_id: int, shop_id: int) -> Product:
    stmt = select(Product).where(
        Product.id == product_id,
        Product.shop_id == shop_id,
    )
    res = await db.execute(stmt)
    obj = res.scalar_one_or_none()
    if obj is None:
        raise HTTPException(status_code=404, detail="product not found")
    return obj


def resolve_incoming_slug(name: str | None, slug_in: str | None) -> str | None:
    if slug_in:
        return slugify(slug_in)
    if name:
        return slugify(name)
    return None


def sort_clause(sort: ProductSort):
    """
    Devuelve un par (orden_primario, orden_desempate) para orden estable.
    - name_asc/desc, price_asc/desc
    - desempate por id para evitar 'bailes' cuando hay empates
    """
    primary = {
        ProductSort.name_asc: asc(Product.name),
        ProductSort.name_desc: desc(Product.name),
        ProductSort.price_asc: asc(Product.price),
        ProductSort.price_desc: desc(Product.price),
    }[sort]

    # Si el primario es ascendente, desempata por id asc; si es descendente, por id desc
    is_desc = sort in {ProductSort.name_desc, ProductSort.price_desc}
    secondary = desc(Product.id) if is_desc else asc(Product.id)

    # devolvemos una tupla para usarla con order_by(*tuple)
    return (primary, secondary)


# ------------------------ CREATE ------------------------ #


@router.post("", response_model=SingleResponse[ProductOut], status_code=status.HTTP_201_CREATED)
async def create_product(
    payload: ProductCreate,
    resp: Response,
    db: AsyncSession = Depends(get_session),
):
    # validar shop
    shop = (
        await db.execute(select(Shop.id).where(Shop.id == payload.shop_id))
    ).scalar_one_or_none()
    if not shop:
        raise HTTPException(status_code=404, detail="shop not found")

    # validar category
    if payload.category_id is not None:
        await ensure_category_in_shop(db, category_id=payload.category_id, shop_id=payload.shop_id)

    final_slug = resolve_incoming_slug(payload.name, payload.slug)
    if not final_slug:
        raise HTTPException(status_code=422, detail="name or slug is required")

    # guard de colisión
    if await slug_in_use(db, shop_id=payload.shop_id, slug=final_slug):
        raise HTTPException(status_code=409, detail="slug already exists for this shop")

    obj = Product(
        name=payload.name,
        slug=final_slug,
        price=payload.price,
        shop_id=payload.shop_id,
        category_id=payload.category_id,
    )
    db.add(obj)
    try:
        await db.flush()
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="slug already exists for this shop")
    await db.refresh(obj)

    # Location header (REST friendly)
    if resp is not None:
        resp.headers["Location"] = f"/api/v1/products/{obj.id}?shop_id={obj.shop_id}"

    # Envelope consistente
    return {"data": obj}


# ------------------------ LIST (con paginación + headers) ------------------------ #


@router.get("", response_model=ListResponse[ProductOut], status_code=status.HTTP_200_OK)
async def list_products(
    response: Response,
    db: AsyncSession = Depends(get_session),
    pagination: PaginationParams = Depends(pagination_params),
    shop_id: int = Query(..., ge=1),
    category_id: int | None = Query(None, ge=1),
    q: str | None = Query(None, min_length=1, max_length=100),
    price_min: Decimal | None = Query(None, ge=0, description="Precio mínimo (incluyente)"),
    price_max: Decimal | None = Query(None, ge=0, description="Precio máximo (incluyente)"),
    is_active: bool | None = Query(
        None, description="Filtra por activos/inactivos si el modelo tiene esta columna"
    ),
    sort: ProductSort = ProductSort.name_asc,
):
    """
    Lista paginada y filtrada de productos de una shop.
    - Aplica filtros simétricos a datos y conteo total.
    - Devuelve headers de paginación: X-Total-Count, X-Limit, X-Offset.
    """

    # 1) Validaciones previas
    if category_id is not None:
        await ensure_category_in_shop(db, category_id=category_id, shop_id=shop_id)

    if price_min is not None and price_max is not None and price_min > price_max:
        raise HTTPException(status_code=422, detail="price_min must be <= price_max")

    # 2) Bases SIEMPRE primero (¡evita UnboundLocalError!)
    base = select(Product).where(Product.shop_id == shop_id)
    count_base = select(func.count(Product.id)).where(Product.shop_id == shop_id)

    # 3) Filtros
    if category_id is not None:
        base = base.where(Product.category_id == category_id)
        count_base = count_base.where(Product.category_id == category_id)

    if q:
        like = f"%{q.lower()}%"
        cond = or_(
            func.lower(Product.name).like(like),
            func.lower(Product.slug).like(like),
        )
        base = base.where(cond)
        count_base = count_base.where(cond)

    if price_min is not None:
        base = base.where(Product.price >= price_min)
        count_base = count_base.where(Product.price >= price_min)

    if price_max is not None:
        base = base.where(Product.price <= price_max)
        count_base = count_base.where(Product.price <= price_max)

    if is_active is not None and hasattr(Product, "is_active"):
        col = getattr(Product, "is_active")
        base = base.where(col == is_active)
        count_base = count_base.where(col == is_active)

    # 4) Conteo total (evita ORDER BY en count)
    count_q = count_base.with_only_columns(func.count(Product.id)).order_by(None)
    total = int((await db.execute(count_q)).scalar() or 0)

    # 5) Ordenamiento estable + paginación
    order1, order2 = sort_clause(sort)
    stmt = base.order_by(order1, order2).offset(pagination.offset).limit(pagination.limit)
    res = await db.execute(stmt)
    items = res.scalars().all()

    # 6) Headers
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Limit"] = str(pagination.limit)
    response.headers["X-Offset"] = str(pagination.offset)

    meta = {
        "pagination": MetaPagination(
            total=total, limit=pagination.limit, offset=pagination.offset
        ).model_dump(),
        # Filtros/orden que llegaron (útiles para front y depuración)
        "filters": {
            "shop_id": shop_id,
            "category_id": category_id,
            "q": q,
            "price_min": str(price_min) if price_min is not None else None,
            "price_max": str(price_max) if price_max is not None else None,
            "is_active": is_active,
        },
        "sort": sort.value,
    }

    return {"data": items, "meta": meta}


# ------------------------ GET by id ------------------------ #


@router.get(
    "/{product_id}", response_model=SingleResponse[ProductOut], status_code=status.HTTP_200_OK
)
async def get_product(
    db: AsyncSession = Depends(get_session),
    product_id: int = Path(..., ge=1),
    shop_id: int = Query(..., ge=1),
):
    obj = await fetch_product_or_404(db, product_id=product_id, shop_id=shop_id)
    # Envelope consistente: { "data": { ...product... } }
    return {"data": obj}


# ------------------------ PUT ------------------------ #


@router.put(
    "/{product_id}", response_model=SingleResponse[ProductOut], status_code=status.HTTP_200_OK
)
async def put_product(
    body: ProductUpdate,  # cuerpo completo (reemplazo)
    db: AsyncSession = Depends(get_session),  # sesión inyectada
    product_id: int = Path(..., ge=1),  # id en path
):
    # 1) Existe y pertenece a shop
    obj = await fetch_product_or_404(db, product_id=product_id, shop_id=body.shop_id)

    # 2) Validar category -> shop
    if body.category_id is not None:
        await ensure_category_in_shop(db, category_id=body.category_id, shop_id=body.shop_id)

    # 3) Resolver slug
    new_slug = resolve_incoming_slug(body.name, body.slug)
    if new_slug is not None and new_slug != obj.slug:
        if await slug_in_use(db, shop_id=body.shop_id, slug=new_slug, exclude_id=obj.id):
            raise HTTPException(status_code=409, detail="slug already exists for this shop")
        obj.slug = new_slug

    # 4) Actualizar campos
    obj.name = body.name
    obj.price = body.price
    obj.category_id = body.category_id

    # 5) Persistir
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="slug already exists for this shop")

    await db.commit()
    await db.refresh(obj)

    # 6) Envelope consistente
    return {"data": obj}


# ------------------------ PATCH ------------------------ #


@router.patch(
    "/{product_id}", response_model=SingleResponse[ProductOut], status_code=status.HTTP_200_OK
)
async def patch_product(
    body: ProductUpdatePartial,  # cuerpo parcial
    db: AsyncSession = Depends(get_session),
    product_id: int = Path(..., ge=1),
):
    # 1) Existe y pertenece a shop
    obj = await fetch_product_or_404(db, product_id=product_id, shop_id=body.shop_id)

    # 2) Validar category -> shop (si viene)
    if body.category_id is not None:
        await ensure_category_in_shop(db, category_id=body.category_id, shop_id=body.shop_id)

    # 3) Resolver slug (si viene nombre/slug)
    incoming_slug = resolve_incoming_slug(body.name, body.slug)
    if incoming_slug is not None and incoming_slug != obj.slug:
        if await slug_in_use(db, shop_id=body.shop_id, slug=incoming_slug, exclude_id=obj.id):
            raise HTTPException(status_code=409, detail="slug already exists for this shop")
        obj.slug = incoming_slug

    # 4) Actualizar solo lo recibido
    if body.name is not None:
        obj.name = body.name
    if body.price is not None:
        obj.price = body.price
    if body.category_id is not None:
        obj.category_id = body.category_id

    # 5) Persistir
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="slug already exists for this shop")

    await db.commit()
    await db.refresh(obj)

    # 6) Envelope consistente
    return {"data": obj}


# ------------------------ DELETE ------------------------ #


@router.delete(
    "/{product_id}", response_model=SingleResponse[DeleteResult], status_code=status.HTTP_200_OK
)
async def delete_product(
    db: AsyncSession = Depends(get_session),
    product_id: int = Path(..., ge=1),
    shop_id: int = Query(..., ge=1),
):
    # 1) Verifica que exista y pertenezca a la shop
    obj = await fetch_product_or_404(db, product_id=product_id, shop_id=shop_id)

    # 2) Borra y confirma
    await db.delete(obj)
    await db.commit()

    # 3) Envelope consistente
    return {"data": {"id": product_id, "deleted": True}}
