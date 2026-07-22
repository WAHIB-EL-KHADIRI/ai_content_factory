"""Brand Center - manages brand identity and voice"""

import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class BrandService:
    def __init__(self, db=None):
        self.db = db

    def create_brand(self, project_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        brand = {
            "id": f"brand_{project_id}_{data.get('name', 'default')}",
            "project_id": project_id,
            "name": data.get("name", "Default Brand"),
            "description": data.get("description", ""),
            "voice_tone": data.get("voice_tone", "professional"),
            "target_audience": data.get("target_audience", ""),
            "keywords": data.get("keywords", []),
            "style_guide": data.get("style_guide", {}),
            "color_palette": data.get("color_palette", []),
            "logo_url": data.get("logo_url"),
            "guidelines": data.get("guidelines", ""),
        }

        if self.db:
            from backend.db.models import Brand

            db_brand = Brand(**brand)
            self.db.add(db_brand)
            self.db.commit()
            self.db.refresh(db_brand)
            return {
                "id": db_brand.id,
                "name": db_brand.name,
                "voice_tone": db_brand.voice_tone,
                "target_audience": db_brand.target_audience,
                "keywords": db_brand.keywords,
                "color_palette": db_brand.color_palette,
            }

        return brand

    def get_brand(self, brand_id: str) -> Optional[Dict[str, Any]]:
        if self.db:
            from backend.db.models import Brand

            brand = self.db.query(Brand).filter(Brand.id == brand_id).first()
            if brand:
                return {
                    "id": brand.id,
                    "name": brand.name,
                    "description": brand.description,
                    "voice_tone": brand.voice_tone,
                    "target_audience": brand.target_audience,
                    "keywords": brand.keywords,
                    "style_guide": brand.style_guide,
                    "color_palette": brand.color_palette,
                    "logo_url": brand.logo_url,
                    "guidelines": brand.guidelines,
                }
        return None

    def update_brand(
        self, brand_id: str, data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        if self.db:
            from backend.db.models import Brand

            brand = self.db.query(Brand).filter(Brand.id == brand_id).first()
            if brand:
                for key, value in data.items():
                    if hasattr(brand, key) and value is not None:
                        setattr(brand, key, value)
                self.db.commit()
                self.db.refresh(brand)
                return self.get_brand(brand_id)
        return None

    def delete_brand(self, brand_id: str) -> bool:
        if self.db:
            from backend.db.models import Brand

            brand = self.db.query(Brand).filter(Brand.id == brand_id).first()
            if brand:
                self.db.delete(brand)
                self.db.commit()
                return True
        return False

    def get_project_brands(self, project_id: str) -> List[Dict[str, Any]]:
        if self.db:
            from backend.db.models import Brand

            brands = self.db.query(Brand).filter(Brand.project_id == project_id).all()
            return [
                {
                    "id": b.id,
                    "name": b.name,
                    "voice_tone": b.voice_tone,
                    "keywords": b.keywords,
                }
                for b in brands
            ]
        return []

    def get_brand_context(self, brand_id: str) -> Dict[str, Any]:
        brand = self.get_brand(brand_id)
        if not brand:
            return {}

        return {
            "voice_tone": brand.get("voice_tone", "professional"),
            "target_audience": brand.get("target_audience", ""),
            "keywords": brand.get("keywords", []),
            "style_guide": brand.get("style_guide", {}),
            "color_palette": brand.get("color_palette", []),
            "guidelines": brand.get("guidelines", ""),
            "name": brand.get("name", ""),
            "description": brand.get("description", ""),
        }

    def analyze_brand_consistency(self, content: str, brand_id: str) -> Dict[str, Any]:
        brand = self.get_brand(brand_id)
        if not brand:
            return {"consistent": True, "score": 100, "issues": []}

        issues = []
        score = 100

        keywords = brand.get("keywords", [])
        if keywords:
            found = sum(1 for kw in keywords if kw.lower() in content.lower())
            coverage = found / len(keywords) * 100 if keywords else 100
            if coverage < 30:
                issues.append(
                    {
                        "type": "keywords",
                        "message": f"Low keyword coverage: {coverage:.0f}%",
                        "severity": "medium",
                    }
                )
                score -= 10

        word_count = len(content.split())
        if word_count < 100:
            issues.append(
                {
                    "type": "length",
                    "message": "Content is too short",
                    "severity": "low",
                }
            )
            score -= 5

        return {
            "consistent": len(issues) == 0,
            "score": max(0, score),
            "issues": issues,
            "brand_name": brand.get("name", ""),
        }
