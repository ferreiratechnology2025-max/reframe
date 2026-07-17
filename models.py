from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class BusinessInfo(BaseModel):
    name: str
    address: str
    phone: Optional[str] = None
    website: Optional[str] = None
    rating: Optional[float] = None
    reviews_count: Optional[int] = None
    google_maps_url: Optional[str] = None
    place_id: Optional[str] = None


class BusinessCategory(BaseModel):
    segment: str = Field(description="e.g. 'restaurante', 'advocacia'")
    confidence: float = Field(ge=0.0, le=1.0)


class LeadProfile(BaseModel):
    business_info: BusinessInfo
    category: BusinessCategory
    has_website: bool
    needs_modernization: bool = True
    notes: Optional[str] = None
    discovered_at: datetime = Field(default_factory=datetime.now)


class DesignSystem(BaseModel):
    name: str = "default"
    font_headings: str = "Inter"
    font_body: str = "Inter"
    primary_color: str = "#1a73e8"
    secondary_color: str = "#34a853"
    accent_color: str = "#ea4335"
    background_color: str = "#ffffff"
    text_color: str = "#1f1f1f"
    border_radius: str = "8px"
    spacing_unit: str = "16px"
    max_width: str = "1200px"


class ValueProposition(BaseModel):
    headline: str
    subheadline: Optional[str] = None
    key_benefits: list[str] = Field(default_factory=list)
    target_audience: Optional[str] = None
    tone_of_voice: str = Field(default="profissional", description="profissional | casual | premium | direto")


class SeoConfig(BaseModel):
    meta_title: str
    meta_description: str
    keywords: list[str] = Field(default_factory=list)


class SectionContent(BaseModel):
    hero: dict = Field(default_factory=dict)
    about: dict = Field(default_factory=dict)
    services: dict = Field(default_factory=dict)
    testimonials: dict = Field(default_factory=dict)
    contact: dict = Field(default_factory=dict)


class ImageAsset(BaseModel):
    url: str
    alt: str
    prompt_used: str
    source: str = Field(description="'unsplash' | 'picsum' | 'placeholder'")


class GeneratedSite(BaseModel):
    lead: LeadProfile
    value_proposition: ValueProposition
    seo: SeoConfig
    sections: SectionContent
    design: DesignSystem = Field(default_factory=DesignSystem)
    images: list[ImageAsset] = Field(default_factory=list)
    html: Optional[str] = None
    slug: Optional[str] = None
    published_url: Optional[str] = None
    generated_at: datetime = Field(default_factory=datetime.now)
    url: str
    alt: str
    prompt_used: str
    source: str = Field(description="'unsplash' | 'picsum' | 'placeholder'")
