"""
Insights Service - Real-time Risk Analysis and Analytics
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dateutil import parser as date_parser
from app.ontology.ontology_service import ontology_service


class InsightsService:
    """Service for generating real-time insights and risk analysis"""
    DOMAIN_WEIGHTS = {
        "geopolitical": 0.90,
        "economic": 0.72,
        "defense": 0.85,
        "technology": 0.68,
        "climate": 0.60,
        "energy": 0.65,
        "social": 0.52,
    }
    CATEGORY_CONFIG = [
        {"name": "Geopolitical", "key": "geopolitical", "entity_type": "Country"},
        {"name": "Economic", "key": "economic", "entity_type": "Organization"},
        {"name": "Defense", "key": "defense", "entity_type": "System"},
        {"name": "Technology", "key": "technology", "entity_type": "System"},
        {"name": "Climate", "key": "climate", "entity_type": "Event"},
        {"name": "Energy", "key": "energy", "entity_type": "Resource"},
        {"name": "Social", "key": "social", "entity_type": "Individual"},
    ]
    
    # Cache for expensive operations to prevent N+1 queries on every request
    _cache: Dict[str, Any] = {}
    _cache_ttl: int = 300  # 5 minutes cache TTL
    _last_cache_update: Optional[datetime] = None
    
    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid"""
        if self._last_cache_update is None:
            return False
        age = (datetime.utcnow() - self._last_cache_update).total_seconds()
        return age < self._cache_ttl
    
    def _invalidate_cache(self) -> None:
        """Invalidate all caches"""
        self._cache.clear()
        self._last_cache_update = None
    
    async def get_risk_analysis(
        self, 
        category: Optional[str] = None,
        region: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get risk analysis by category and/or region"""
        
        # Use cache to prevent N+1 queries on every request
        cache_key = f"risk_analysis_{category}_{region}"
        if cache_key in self._cache and self._is_cache_valid():
            return self._cache[cache_key]
        
        # Calculate risk scores based on entity relationships
        risk_scores = await self._calculate_risk_scores(category, region)
        
        # Get trends
        trends = await self._calculate_trends(risk_scores)
        
        result = {
            'overall_risk': self._calculate_overall_risk(risk_scores),
            'categories': risk_scores,
            'trends': trends,
            'last_updated': datetime.utcnow().isoformat(),
        }
        
        # Cache the result
        self._cache[cache_key] = result
        self._last_cache_update = datetime.utcnow()
        
        return result
    
    async def _calculate_risk_scores(
        self, 
        category: Optional[str],
        region: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Calculate risk scores for different categories"""
        stats = await ontology_service.get_graph_statistics()
        total_nodes = max(stats.get("total_nodes", 0), 1)
        total_relationships = max(stats.get("total_relationships", 0), 0)
        density_raw = total_relationships / max(total_nodes * (total_nodes - 1), 1)
        relationship_density = min(density_raw * 1000, 1.0)

        categories = self.CATEGORY_CONFIG
        if category:
            categories = [
                c for c in categories
                if c["name"].lower() == category.lower() or c["key"] == category.lower()
            ]

        results: List[Dict[str, Any]] = []
        for config in categories:
            centrality = await self._estimate_category_centrality(config["entity_type"])
            recent_events = await self._estimate_recent_event_frequency(config["key"])
            domain_weight = self.DOMAIN_WEIGHTS.get(config["key"], 0.5)

            risk_score = (
                0.4 * centrality +
                0.3 * relationship_density +
                0.2 * recent_events +
                0.1 * domain_weight
            )
            level = int(max(0.0, min(risk_score, 1.0)) * 100)

            if level >= 70:
                trend = "up"
            elif level <= 45:
                trend = "down"
            else:
                trend = "stable"

            factors = [
                f"Entity centrality {round(centrality * 100, 1)}%",
                f"Relationship density {round(relationship_density * 100, 1)}%",
                f"Recent events {round(recent_events * 100, 1)}%",
                f"Domain weight {round(domain_weight * 100, 1)}%",
            ]

            results.append(
                {
                    "category": config["name"],
                    "level": level,
                    "trend": trend,
                    "factors": factors,
                }
            )

        return results
    
    async def _calculate_trends(self, risk_scores: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate risk trends over time"""
        score_map = {item["category"].lower(): item["level"] for item in risk_scores}

        weekly = []
        for idx in range(4):
            week = {"week": f"W{idx + 1}"}
            drift = (idx - 2) * 2
            for key in ("geopolitical", "economic", "defense", "technology", "climate", "energy", "social"):
                base = score_map.get(key, 50)
                week[key] = int(max(0, min(100, base + drift)))
            weekly.append(week)

        changes = {}
        for key in ("geopolitical", "economic", "defense", "technology", "climate", "energy", "social"):
            change = weekly[-1].get(key, 0) - weekly[0].get(key, 0)
            sign = "+" if change > 0 else ""
            changes[key] = f"{sign}{change}"

        return {"weekly": weekly, "changes": changes}
    
    def _calculate_overall_risk(self, scores: List[Dict]) -> Dict[str, Any]:
        """Calculate overall risk level"""
        
        if not scores:
            return {'level': 'low', 'score': 0}
        
        avg_score = sum(s['level'] for s in scores) / len(scores)
        
        if avg_score >= 75:
            level = 'critical'
        elif avg_score >= 60:
            level = 'high'
        elif avg_score >= 40:
            level = 'medium'
        else:
            level = 'low'
        
        return {
            'level': level,
            'score': round(avg_score, 1),
            'trend': 'up' if avg_score > 60 else 'stable'
        }
    
    async def get_map_data(self) -> Dict[str, Any]:
        """Get country impact data for world map visualization"""
        # Use cache to prevent N+1 queries on every request
        cache_key = "map_data"
        if cache_key in self._cache and self._is_cache_valid():
            return self._cache[cache_key]
        
        countries = await ontology_service.search_entities(
            query="",
            entity_type="Country",
            limit=50
        )

        country_impacts = []
        for country in countries:
            name = country.get("name", "Unknown")
            code = (
                country.get("code")
                or country.get("iso_code")
                or name[:3].upper()
            )
            risk_data = await self._get_country_risk_factors(code)
            country_impacts.append(
                {
                    "country": name,
                    "code": code,
                    "impact": risk_data["score"],
                    "risk": risk_data["level"],
                    "lat": float(country.get("lat", 0.0) or 0.0),
                    "lng": float(country.get("lng", 0.0) or 0.0),
                    "categories": risk_data["categories"],
                    "recent_events": risk_data.get("recent_events", 0),
                }
            )
        
        result = {
            'countries': country_impacts,
            'last_updated': datetime.utcnow().isoformat(),
        }
        
        # Cache the result
        self._cache[cache_key] = result
        self._last_cache_update = datetime.utcnow()
        
        return result
    
    async def get_country_risk(self, country_code: str) -> Dict[str, Any]:
        """Get detailed risk analysis for a specific country"""
        
        # Find country entity
        country = await ontology_service.get_entity(country_code)
        
        # Get related entities
        related = await ontology_service.get_related_entities(country_code, limit=10)
        
        # Get risk factors
        risk_factors = await self._get_country_risk_factors(country_code)
        
        return {
            'country': country_code,
            'risk_level': risk_factors['level'],
            'risk_score': risk_factors['score'],
            'categories': risk_factors['categories'],
            'factors': risk_factors['factors'],
            'related_entities': related,
            'last_updated': datetime.utcnow().isoformat(),
        }
    
    async def _get_country_risk_factors(self, country_code: str) -> Dict[str, Any]:
        """Get risk factors for a specific country"""
        relationships = await ontology_service.get_relationships(
            country_code,
            direction="both",
            limit=100
        )
        related_entities = await ontology_service.get_related_entities(country_code, limit=50)
        recent_events = await self._estimate_recent_event_frequency("geopolitical", related_entities)

        relationship_count = len(relationships)
        centrality = min(relationship_count / 40.0, 1.0)
        density = min(len(related_entities) / 50.0, 1.0)
        score = int(
            max(0.0, min(
                0.45 * centrality + 0.35 * density + 0.20 * recent_events,
                1.0
            )) * 100
        )

        if score >= 85:
            level = "critical"
        elif score >= 70:
            level = "high"
        elif score >= 45:
            level = "medium"
        else:
            level = "low"

        categories = []
        for entity in related_entities:
            entity_type = entity.get("type", "")
            if entity_type and entity_type not in categories:
                categories.append(entity_type)
            if len(categories) >= 3:
                break

        factors = [
            f"{relationship_count} active graph relationships",
            f"{len(related_entities)} connected entities",
            f"{int(recent_events * 100)}% recent event pressure",
        ]

        return {
            "level": level,
            "score": score,
            "categories": categories,
            "factors": factors,
            "recent_events": int(recent_events * 100),
        }

    async def _estimate_category_centrality(self, entity_type: str) -> float:
        # Cache centrality calculations to prevent N+1 queries
        cache_key = f"centrality_{entity_type}"
        if cache_key in self._cache and self._is_cache_valid():
            return self._cache[cache_key]
        
        entities = await ontology_service.search_entities(
            query="",
            entity_type=entity_type,
            limit=15
        )
        if not entities:
            return 0.0

        relationship_total = 0
        for entity in entities:
            identifier = entity.get("id") or entity.get("name")
            if not identifier:
                continue
            rels = await ontology_service.get_relationships(
                identifier,
                direction="both",
                limit=50
            )
            relationship_total += len(rels)

        avg_degree = relationship_total / max(len(entities), 1)
        centrality = min(avg_degree / 30.0, 1.0)
        
        # Cache the centrality value
        self._cache[cache_key] = centrality
        
        return centrality

    async def _estimate_recent_event_frequency(
        self,
        domain_key: str,
        related_entities: Optional[List[Dict[str, Any]]] = None
    ) -> float:
        # Cache event frequency calculations
        cache_key = f"event_freq_{domain_key}"
        if cache_key in self._cache and self._is_cache_valid():
            return self._cache[cache_key]
        
        now = datetime.utcnow()
        threshold = now - timedelta(days=14)

        if related_entities:
            events = [e for e in related_entities if e.get("type", "").lower() == "event"]
        else:
            events = await ontology_service.search_entities(
                query="",
                entity_type="Event",
                limit=200
            )

        recent_count = 0
        relevant_count = 0
        for event in events:
            name_blob = f"{event.get('name', '')} {event.get('description', '')}".lower()
            if domain_key and domain_key not in name_blob and domain_key != "geopolitical":
                continue
            relevant_count += 1

            date_value = (
                event.get("date")
                or event.get("published_at")
                or event.get("created_at")
                or event.get("updated_at")
            )
            if not date_value:
                continue

            try:
                parsed = date_parser.parse(str(date_value))
                if parsed.tzinfo is not None:
                    parsed = parsed.replace(tzinfo=None)
                if parsed >= threshold:
                    recent_count += 1
            except Exception:
                continue

        frequency = 0.0
        if relevant_count > 0:
            frequency = min(recent_count / relevant_count, 1.0)
        
        # Cache the frequency value
        self._cache[cache_key] = frequency
        
        return frequency


# Singleton instance
insights_service = InsightsService()
