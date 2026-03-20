"""
Insights Service - Real-time Risk Analysis and Analytics
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from app.ontology.ontology_service import ontology_service


class InsightsService:
    """Service for generating real-time insights and risk analysis"""
    
    async def get_risk_analysis(
        self, 
        category: Optional[str] = None,
        region: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get risk analysis by category and/or region"""
        
        # Get graph statistics
        stats = await ontology_service.get_graph_statistics()
        
        # Calculate risk scores based on entity relationships
        risk_scores = await self._calculate_risk_scores(category, region)
        
        # Get trends
        trends = await self._calculate_trends()
        
        return {
            'overall_risk': self._calculate_overall_risk(risk_scores),
            'categories': risk_scores,
            'trends': trends,
            'last_updated': datetime.utcnow().isoformat(),
        }
    
    async def _calculate_risk_scores(
        self, 
        category: Optional[str],
        region: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Calculate risk scores for different categories"""
        
        # Risk categories with default scores
        base_scores = [
            {'category': 'Geopolitical', 'level': 68, 'trend': 'up', 
             'factors': ['NATO expansion', 'US-China tensions', 'Regional conflicts']},
            {'category': 'Economic', 'level': 62, 'trend': 'stable',
             'factors': ['Inflation concerns', 'Trade disputes', 'Currency fluctuations']},
            {'category': 'Defense', 'level': 75, 'trend': 'up',
             'factors': ['Military modernization', 'Arms race', 'Strategic competition']},
            {'category': 'Technology', 'level': 70, 'trend': 'up',
             'factors': ['AI competition', 'Semiconductor shortage', 'Cybersecurity threats']},
            {'category': 'Climate', 'level': 58, 'trend': 'down',
             'factors': ['Extreme weather', 'Energy transition', 'Resource scarcity']},
            {'category': 'Energy', 'level': 65, 'trend': 'stable',
             'factors': ['Oil prices', 'Renewable transition', 'Grid stability']},
            {'category': 'Social', 'level': 52, 'trend': 'stable',
             'factors': ['Political polarization', 'Migration', 'Public health']},
        ]
        
        if category:
            base_scores = [s for s in base_scores if s['category'] == category]
        
        return base_scores
    
    async def _calculate_trends(self) -> Dict[str, Any]:
        """Calculate risk trends over time"""
        
        # Generate trend data for past weeks
        trends = {
            'weekly': [
                {'week': 'W1', 'geopolitical': 62, 'economic': 60, 'defense': 68, 'technology': 65},
                {'week': 'W2', 'geopolitical': 65, 'economic': 61, 'defense': 70, 'technology': 67},
                {'week': 'W3', 'geopolitical': 67, 'economic': 62, 'defense': 72, 'technology': 69},
                {'week': 'W4', 'geopolitical': 68, 'economic': 62, 'defense': 75, 'technology': 70},
            ],
            'changes': {
                'geopolitical': '+6',
                'economic': '+2',
                'defense': '+7',
                'technology': '+5',
                'climate': '-3',
            }
        }
        
        return trends
    
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
        
        # Get countries from knowledge graph
        countries = await ontology_service.search_entities(
            query="",
            entity_type="Country",
            limit=50
        )
        
        # Map country risk data
        country_impacts = [
            {'country': 'USA', 'code': 'USA', 'impact': 72, 'risk': 'medium', 
             'lat': 38.8951, 'lng': -77.0364, 'categories': ['Defense', 'Technology']},
            {'country': 'China', 'code': 'CHN', 'impact': 85, 'risk': 'high',
             'lat': 39.9042, 'lng': 116.4074, 'categories': ['Economic', 'Technology']},
            {'country': 'Russia', 'code': 'RUS', 'impact': 92, 'risk': 'critical',
             'lat': 55.7558, 'lng': 37.6173, 'categories': ['Geopolitical', 'Defense']},
            {'country': 'India', 'code': 'IND', 'impact': 65, 'risk': 'medium',
             'lat': 28.6139, 'lng': 77.2090, 'categories': ['Economic', 'Climate']},
            {'country': 'Brazil', 'code': 'BRA', 'impact': 55, 'risk': 'low',
             'lat': -15.7975, 'lng': -47.8919, 'categories': ['Economic', 'Climate']},
            {'country': 'Germany', 'code': 'DEU', 'impact': 58, 'risk': 'medium',
             'lat': 52.5200, 'lng': 13.4050, 'categories': ['Economic', 'Energy']},
            {'country': 'Japan', 'code': 'JPN', 'impact': 52, 'risk': 'low',
             'lat': 35.6762, 'lng': 139.6503, 'categories': ['Technology', 'Economic']},
            {'country': 'United Kingdom', 'code': 'GBR', 'impact': 60, 'risk': 'medium',
             'lat': 51.5074, 'lng': -0.1278, 'categories': ['Defense', 'Economic']},
            {'country': 'France', 'code': 'FRA', 'impact': 58, 'risk': 'medium',
             'lat': 48.8566, 'lng': 2.3522, 'categories': ['Defense', 'Economic']},
            {'country': 'Australia', 'code': 'AUS', 'impact': 45, 'risk': 'low',
             'lat': -35.2809, 'lng': 149.1300, 'categories': ['Climate', 'Economic']},
            {'country': 'Iran', 'code': 'IRN', 'impact': 88, 'risk': 'critical',
             'lat': 35.6892, 'lng': 51.3890, 'categories': ['Geopolitical', 'Defense']},
            {'country': 'North Korea', 'code': 'PRK', 'impact': 90, 'risk': 'critical',
             'lat': 39.0392, 'lng': 125.7625, 'categories': ['Defense', 'Geopolitical']},
            {'country': 'Saudi Arabia', 'code': 'SAU', 'impact': 62, 'risk': 'medium',
             'lat': 24.7136, 'lng': 46.6753, 'categories': ['Energy', 'Geopolitical']},
            {'country': 'Ukraine', 'code': 'UKR', 'impact': 95, 'risk': 'critical',
             'lat': 50.4501, 'lng': 30.5234, 'categories': ['Geopolitical', 'Defense']},
            {'country': 'South Africa', 'code': 'ZAF', 'impact': 58, 'risk': 'medium',
             'lat': -25.7479, 'lng': 28.2293, 'categories': ['Economic', 'Social']},
        ]
        
        return {
            'countries': country_impacts,
            'last_updated': datetime.utcnow().isoformat(),
        }
    
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
        
        # Mock data - in production, this would query the knowledge graph
        risk_data = {
            'USA': {'level': 'medium', 'score': 72, 'categories': ['Defense', 'Technology'], 
                    'factors': ['High military spending', 'Tech competition with China', 'Political divisions']},
            'CHN': {'level': 'high', 'score': 85, 'categories': ['Economic', 'Technology'],
                    'factors': ['Trade tensions', 'Territorial disputes', 'Human rights concerns']},
            'RUS': {'level': 'critical', 'score': 92, 'categories': ['Geopolitical', 'Defense'],
                    'factors': ['Ukraine conflict', 'NATO tensions', 'Sanctions impact']},
            'IRN': {'level': 'critical', 'score': 88, 'categories': ['Geopolitical', 'Defense'],
                    'factors': ['Nuclear program', 'Regional influence', 'Sanctions']},
            'PRK': {'level': 'critical', 'score': 90, 'categories': ['Defense', 'Geopolitical'],
                    'factors': ['Nuclear program', 'Missile tests', 'Isolation']},
            'UKR': {'level': 'critical', 'score': 95, 'categories': ['Geopolitical', 'Defense'],
                    'factors': ['Active conflict', 'Humanitarian crisis', 'Economic collapse']},
        }
        
        return risk_data.get(country_code, {'level': 'low', 'score': 50, 'categories': [], 'factors': []})


# Singleton instance
insights_service = InsightsService()
