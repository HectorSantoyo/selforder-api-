from pydantic import BaseModel, Field


class CategoryCreate(BaseModel):
    name: str
    slug: str = Field(min_length=1)
    shop_id: int


class CategoryOut(BaseModel):
    id: int
    name: str
    slug: str
    shop_id: int

    class Config:
        from_attributes = True
