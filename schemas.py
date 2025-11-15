"""
Database Schemas for Department Store E‑commerce

Each Pydantic model represents a MongoDB collection. The collection name is the lowercase
of the class name (e.g., Product -> "product").
"""
from __future__ import annotations
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict
from datetime import datetime


class Category(BaseModel):
    name: str = Field(..., description="Category display name")
    slug: str = Field(..., description="URL-friendly unique slug")
    image: Optional[str] = Field(None, description="Category image URL")
    description: Optional[str] = Field(None, description="Short description")
    parent_id: Optional[str] = Field(None, description="Optional parent category id")


class Product(BaseModel):
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Price in dollars")
    compare_at_price: Optional[float] = Field(None, ge=0, description="Original price for discounts")
    category_slug: str = Field(..., description="Slug of category this product belongs to")
    brand: Optional[str] = Field(None, description="Brand name")
    sku: Optional[str] = Field(None, description="SKU / Identifier")
    images: List[str] = Field(default_factory=list, description="Image URLs")
    rating: float = Field(4.5, ge=0, le=5, description="Average rating")
    stock: int = Field(0, ge=0, description="Units in stock")
    attributes: Dict[str, str] = Field(default_factory=dict, description="Key/value attributes")


class Customer(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    address_line1: str
    address_line2: Optional[str] = None
    city: str
    state: str
    postal_code: str
    country: str = "US"


class CartItem(BaseModel):
    product_id: str
    title: str
    price: float
    quantity: int = Field(1, ge=1)
    image: Optional[str] = None


class Cart(BaseModel):
    session_id: str
    items: List[CartItem] = Field(default_factory=list)
    subtotal: float = 0.0
    updated_at: Optional[datetime] = None


class OrderItem(BaseModel):
    product_id: str
    title: str
    price: float
    quantity: int
    image: Optional[str] = None


class Order(BaseModel):
    session_id: str
    customer: Customer
    items: List[OrderItem]
    subtotal: float
    tax: float
    total: float
    status: str = Field("processing", description="Order status")
    placed_at: Optional[datetime] = None
