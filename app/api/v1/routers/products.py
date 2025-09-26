from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.product import Product
from app.models.category import Category
from app.models.shop import Shop
from app.schemas.product import ProductCreate, ProductOut
from app.core.slugify import slugify

router = APIRouter(prefix="/products", tags=["products"])


@router.post("", response_model=ProductOut, status_code=201)
async def create_product(payload: ProductCreate, db: AsyncSession = Depends(get_session)):
    # validar shop
    shop = (
        await db.execute(select(Shop.id).where(Shop.id == payload.shop_id))
    ).scalar_one_or_none()
    if not shop:
        raise HTTPException(status_code=404, detail="shop not found")

    # validar category si viene y que pertenezca a la misma shop
    if payload.category_id is not None:
        q = select(Category.id, Category.shop_id).where(Category.id == payload.category_id)
        cat = (await db.execute(q)).first()
        if not cat:
            raise HTTPException(status_code=404, detail="category not found")
        if cat.shop_id != payload.shop_id:
            raise HTTPException(status_code=400, detail="category belongs to a different shop")

    obj = Product(
        name=payload.name,
        slug=slugify(payload.slug),
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
    return obj


@router.get("", response_model=list[ProductOut])
async def list_products(
    shop_id: int = Query(...),
    category_id: int | None = Query(None),
    db: AsyncSession = Depends(get_session),
):
    stmt = select(Product).where(Product.shop_id == shop_id)
    if category_id is not None:
        stmt = stmt.where(Product.category_id == category_id)
    stmt = stmt.order_by(Product.id)
    res = await db.execute(stmt)
    return res.scalars().all()
