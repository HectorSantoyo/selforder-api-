from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.shop import Shop
from app.schemas.shop import ShopCreate, ShopOut

router = APIRouter(prefix="/shops", tags=["shops"])


@router.get("", response_model=List[ShopOut])
async def list_shops(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Shop))
    rows = result.scalars().all()
    return rows


@router.post("", response_model=ShopOut, status_code=status.HTTP_201_CREATED)
async def create_shop(payload: ShopCreate, session: AsyncSession = Depends(get_session)):
    # validar slug único
    exists = await session.execute(select(Shop).where(Shop.slug == payload.slug))
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Slug already exists")

    shop = Shop(
        tenant_id=payload.tenant_id,
        name=payload.name,
        slug=payload.slug,
        timezone=payload.timezone,
        address=payload.address,
    )
    session.add(shop)
    await session.commit()
    await session.refresh(shop)
    return shop
