# app/api/v1/routers/categories.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryOut
from app.core.slugify import slugify

router = APIRouter(prefix="/categories", tags=["categories"])


@router.post("", response_model=CategoryOut, status_code=201)
async def create_category(payload: CategoryCreate, db: AsyncSession = Depends(get_session)):
    obj = Category(
        name=payload.name,
        slug=slugify(payload.slug),  # <-- aquí, dentro de la función
        shop_id=payload.shop_id,
    )
    db.add(obj)
    try:
        await db.flush()  # dispara UNIQUE antes del commit
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="slug already exists for this shop")
    await db.refresh(obj)
    return obj


@router.get("", response_model=list[CategoryOut])
async def list_categories(
    shop_id: int = Query(..., description="Shop ID"),
    db: AsyncSession = Depends(get_session),
):
    res = await db.execute(
        select(Category).where(Category.shop_id == shop_id).order_by(Category.id)
    )
    return res.scalars().all()
