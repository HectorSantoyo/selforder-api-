from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy import select, func, or_, asc, desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

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
    mapping = {
        ProductSort.name_asc: asc(Product.name),
        ProductSort.name_desc: desc(Product.name),
        ProductSort.price_asc: asc(Product.price),
        ProductSort.price_desc: desc(Product.price),
    }
    return mapping[sort]


# ------------------------ CREATE ------------------------ #


@router.post("", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
async def create_product(
    payload: ProductCreate,
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

    # 👇 debug (puedes quitarlo después)
    print("DEBUG created product slug:", obj.slug)

    return obj


# ------------------------ LIST ------------------------ #


@router.get("", response_model=list[ProductOut], status_code=status.HTTP_200_OK)
async def list_products(
    db: AsyncSession = Depends(get_session),
    shop_id: int = Query(..., ge=1),
    category_id: int | None = Query(None, ge=1),
    q: str | None = Query(None, min_length=1, max_length=100),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    sort: ProductSort = ProductSort.name_asc,
):
    if category_id is not None:
        await ensure_category_in_shop(db, category_id=category_id, shop_id=shop_id)

    base = select(Product).where(Product.shop_id == shop_id)
    if category_id is not None:
        base = base.where(Product.category_id == category_id)
    if q:
        like = f"%{q.lower()}%"
        base = base.where(
            or_(
                func.lower(Product.name).like(like),
                func.lower(Product.slug).like(like),
            )
        )
    stmt = base.order_by(sort_clause(sort)).offset(offset).limit(limit)
    res = await db.execute(stmt)
    return res.scalars().all()


# ------------------------ GET by id ------------------------ #


@router.get("/{product_id}", response_model=ProductOut, status_code=status.HTTP_200_OK)
async def get_product(
    db: AsyncSession = Depends(get_session),
    product_id: int = Path(..., ge=1),
    shop_id: int = Query(..., ge=1),
):
    obj = await fetch_product_or_404(db, product_id=product_id, shop_id=shop_id)
    return obj


# ------------------------ PUT ------------------------ #


@router.put("/{product_id}", response_model=ProductOut, status_code=status.HTTP_200_OK)
async def put_product(
    body: ProductUpdate,
    db: AsyncSession = Depends(get_session),
    product_id: int = Path(..., ge=1),
):
    obj = await fetch_product_or_404(db, product_id=product_id, shop_id=body.shop_id)

    if body.category_id is not None:
        await ensure_category_in_shop(db, category_id=body.category_id, shop_id=body.shop_id)

    new_slug = resolve_incoming_slug(body.name, body.slug)
    if new_slug is not None and new_slug != obj.slug:
        if await slug_in_use(db, shop_id=body.shop_id, slug=new_slug, exclude_id=obj.id):
            raise HTTPException(status_code=409, detail="slug already exists for this shop")
        obj.slug = new_slug

    obj.name = body.name
    obj.price = body.price
    obj.category_id = body.category_id

    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="slug already exists for this shop")

    await db.commit()
    await db.refresh(obj)
    return obj


# ------------------------ PATCH ------------------------ #


@router.patch("/{product_id}", response_model=ProductOut, status_code=status.HTTP_200_OK)
async def patch_product(
    body: ProductUpdatePartial,
    db: AsyncSession = Depends(get_session),
    product_id: int = Path(..., ge=1),
):
    obj = await fetch_product_or_404(db, product_id=product_id, shop_id=body.shop_id)

    if body.category_id is not None:
        await ensure_category_in_shop(db, category_id=body.category_id, shop_id=body.shop_id)

    incoming_slug = resolve_incoming_slug(body.name, body.slug)
    if incoming_slug is not None and incoming_slug != obj.slug:
        if await slug_in_use(db, shop_id=body.shop_id, slug=incoming_slug, exclude_id=obj.id):
            raise HTTPException(status_code=409, detail="slug already exists for this shop")
        obj.slug = incoming_slug

    if body.name is not None:
        obj.name = body.name
    if body.price is not None:
        obj.price = body.price
    if body.category_id is not None:
        obj.category_id = body.category_id

    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="slug already exists for this shop")

    await db.commit()
    await db.refresh(obj)
    return obj


# ------------------------ DELETE ------------------------ #


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    db: AsyncSession = Depends(get_session),
    product_id: int = Path(..., ge=1),
    shop_id: int = Query(..., ge=1),
):
    obj = await fetch_product_or_404(db, product_id=product_id, shop_id=shop_id)
    await db.delete(obj)
    await db.commit()
    return None
