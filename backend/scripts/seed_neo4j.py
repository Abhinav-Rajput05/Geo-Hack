"""
Seed Neo4j with India-centric knowledge graph data for demo.
Run: cd backend && python scripts/seed_neo4j.py
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.neo4j_client import neo4j_client
from loguru import logger


ENTITIES = [
    # Countries
    {"name": "India", "type": "Country", "region": "South Asia", "iso_code": "IN", "lat": 20.5937, "lng": 78.9629, "description": "Republic of India - largest democracy"},
    {"name": "China", "type": "Country", "region": "East Asia", "iso_code": "CN", "lat": 35.8617, "lng": 104.1954, "description": "People's Republic of China"},
    {"name": "United States", "type": "Country", "region": "North America", "iso_code": "US", "lat": 37.0902, "lng": -95.7129, "description": "United States of America"},
    {"name": "Pakistan", "type": "Country", "region": "South Asia", "iso_code": "PK", "lat": 30.3753, "lng": 69.3451, "description": "Islamic Republic of Pakistan"},
    {"name": "Russia", "type": "Country", "region": "Europe/Asia", "iso_code": "RU", "lat": 61.5240, "lng": 105.3188, "description": "Russian Federation"},
    {"name": "Japan", "type": "Country", "region": "East Asia", "iso_code": "JP", "lat": 36.2048, "lng": 138.2529, "description": "Japan"},
    {"name": "Germany", "type": "Country", "region": "Europe", "iso_code": "DE", "lat": 51.1657, "lng": 10.4515, "description": "Federal Republic of Germany"},
    {"name": "Israel", "type": "Country", "region": "Middle East", "iso_code": "IL", "lat": 31.0461, "lng": 34.8516, "description": "State of Israel"},
    {"name": "Iran", "type": "Country", "region": "Middle East", "iso_code": "IR", "lat": 32.4279, "lng": 53.6880, "description": "Islamic Republic of Iran"},
    {"name": "Saudi Arabia", "type": "Country", "region": "Middle East", "iso_code": "SA", "lat": 23.8859, "lng": 45.0792, "description": "Kingdom of Saudi Arabia"},

    # Organizations
    {"name": "ISRO", "type": "Organization", "sector": "Space Technology", "description": "Indian Space Research Organisation - India's national space agency"},
    {"name": "DRDO", "type": "Organization", "sector": "Defense", "description": "Defence Research and Development Organisation"},
    {"name": "NATO", "type": "Organization", "sector": "Defense Alliance", "description": "North Atlantic Treaty Organization"},
    {"name": "SCO", "type": "Organization", "sector": "Political", "description": "Shanghai Cooperation Organisation"},
    {"name": "BRICS", "type": "Organization", "sector": "Economic", "description": "Brazil, Russia, India, China, South Africa bloc"},
    {"name": "IMF", "type": "Organization", "sector": "Finance", "description": "International Monetary Fund"},
    {"name": "World Bank", "type": "Organization", "sector": "Finance", "description": "World Bank Group"},
    {"name": "UN Security Council", "type": "Organization", "sector": "Political", "description": "United Nations Security Council"},
    {"name": "Quad", "type": "Organization", "sector": "Defense Alliance", "description": "Quadrilateral Security Dialogue - US, India, Japan, Australia"},
    {"name": "OPEC", "type": "Organization", "sector": "Energy", "description": "Organization of Petroleum Exporting Countries"},

    # Technologies / Systems
    {"name": "BrahMos Missile", "type": "System", "category": "Defense", "description": "India-Russia joint supersonic cruise missile"},
    {"name": "Tejas Fighter Jet", "type": "System", "category": "Defense", "description": "India's indigenous light combat aircraft"},
    {"name": "Chandrayaan-3", "type": "System", "category": "Space", "description": "India's lunar exploration mission - successfully landed 2023"},
    {"name": "UPI Payment System", "type": "System", "category": "Technology", "description": "Unified Payments Interface - India's digital payment backbone"},
    {"name": "Semiconductor Chips", "type": "System", "category": "Technology", "description": "Advanced semiconductor integrated circuits"},
    {"name": "5G Network", "type": "System", "category": "Technology", "description": "Fifth generation wireless technology"},
    {"name": "Nuclear Arsenal", "type": "System", "category": "Defense", "description": "Nuclear weapons and delivery systems"},

    # Events
    {"name": "India-China Border Tensions 2024", "type": "Event", "event_type": "ConflictEvent", "severity": 0.7, "description": "Ongoing border disputes along LAC in Ladakh region"},
    {"name": "US Semiconductor Export Controls", "type": "Event", "event_type": "PolicyChange", "severity": 0.8, "description": "US restrictions on advanced chip exports to China affecting global supply chains"},
    {"name": "India GDP Growth 2024", "type": "Event", "event_type": "Indicator", "severity": 0.3, "description": "India projected 7%+ GDP growth, fastest among major economies"},
    {"name": "Russia-Ukraine War", "type": "Event", "event_type": "ConflictEvent", "severity": 0.9, "description": "Ongoing armed conflict impacting global energy and food security"},
    {"name": "India Defense Budget Increase", "type": "Event", "event_type": "PolicyChange", "severity": 0.6, "description": "India increased defense budget to $75 billion for 2024-25"},
    {"name": "Climate Extreme Heat India 2024", "type": "Event", "event_type": "ExtremeWeatherEvent", "severity": 0.7, "description": "Record heat waves across India affecting agriculture and economy"},
    {"name": "India-Middle East Trade Corridor", "type": "Event", "event_type": "TradeAgreement", "severity": 0.6, "description": "IMEC - India-Middle East-Europe Economic Corridor initiative"},
]

RELATIONSHIPS = [
    # India alliances
    ("India", "Russia", "SUPPLIES", {"type": "defense_supply", "confidence": 0.9, "description": "Russia supplies ~60% of India's defense equipment"}),
    ("India", "United States", "ALLIES_WITH", {"type": "strategic_partnership", "confidence": 0.8, "description": "India-US Comprehensive Global Strategic Partnership"}),
    ("India", "Japan", "ALLIES_WITH", {"type": "strategic_partnership", "confidence": 0.8, "description": "India-Japan Special Strategic and Global Partnership"}),
    ("India", "Israel", "TRADES_WITH", {"type": "defense_trade", "confidence": 0.85, "description": "Israel major defense supplier to India"}),

    # India tensions
    ("India", "China", "CONFLICT_WITH", {"type": "border_dispute", "confidence": 0.9, "description": "LAC border disputes, economic competition"}),
    ("India", "Pakistan", "CONFLICT_WITH", {"type": "territorial_dispute", "confidence": 0.95, "description": "Kashmir dispute, cross-border terrorism"}),

    # India organizations
    ("India", "BRICS", "MEMBER_OF", {"confidence": 0.99}),
    ("India", "SCO", "MEMBER_OF", {"confidence": 0.99}),
    ("India", "Quad", "MEMBER_OF", {"confidence": 0.99}),
    ("India", "UN Security Council", "MEMBER_OF", {"confidence": 0.7, "description": "Non-permanent member, seeking permanent seat"}),

    # Technology dependencies
    ("India", "Semiconductor Chips", "DEPENDS_ON", {"confidence": 0.9, "description": "India imports 100% of advanced semiconductors"}),
    ("United States", "Semiconductor Chips", "CONTROLS", {"confidence": 0.95, "description": "US controls advanced chip exports via CHIPS Act"}),
    ("China", "Semiconductor Chips", "DEPENDS_ON", {"confidence": 0.95, "description": "China faces US export restrictions on advanced chips"}),

    # Defense systems
    ("India", "BrahMos Missile", "OPERATES", {"confidence": 0.99}),
    ("India", "Tejas Fighter Jet", "OPERATES", {"confidence": 0.99}),
    ("India", "DRDO", "FUNDS", {"confidence": 0.99}),
    ("India", "ISRO", "FUNDS", {"confidence": 0.99}),
    ("India", "Chandrayaan-3", "OPERATES", {"confidence": 0.99}),
    ("Russia", "BrahMos Missile", "SUPPLIES", {"confidence": 0.9, "description": "Joint development with India"}),

    # Events impact
    ("India-China Border Tensions 2024", "India", "IMPACTS", {"confidence": 0.9, "severity": 0.7}),
    ("India-China Border Tensions 2024", "China", "IMPACTS", {"confidence": 0.9, "severity": 0.6}),
    ("US Semiconductor Export Controls", "India", "IMPACTS", {"confidence": 0.8, "description": "Affects India's chip access and tech growth"}),
    ("US Semiconductor Export Controls", "China", "IMPACTS", {"confidence": 0.95, "description": "Direct target of export controls"}),
    ("Russia-Ukraine War", "India", "IMPACTS", {"confidence": 0.85, "description": "India buys discounted Russian oil, faces Western pressure"}),
    ("India Defense Budget Increase", "DRDO", "IMPACTS", {"confidence": 0.9}),
    ("India-Middle East Trade Corridor", "India", "BENEFITS", {"confidence": 0.8}),
    ("India-Middle East Trade Corridor", "Saudi Arabia", "BENEFITS", {"confidence": 0.75}),

    # Economic
    ("India", "IMF", "MEMBER_OF", {"confidence": 0.99}),
    ("India", "World Bank", "MEMBER_OF", {"confidence": 0.99}),
    ("China", "BRICS", "MEMBER_OF", {"confidence": 0.99}),
    ("Russia", "BRICS", "MEMBER_OF", {"confidence": 0.99}),
    ("Russia", "SCO", "MEMBER_OF", {"confidence": 0.99}),
    ("China", "SCO", "MEMBER_OF", {"confidence": 0.99}),
    ("United States", "NATO", "MEMBER_OF", {"confidence": 0.99}),
    ("United States", "Quad", "MEMBER_OF", {"confidence": 0.99}),
    ("Japan", "Quad", "MEMBER_OF", {"confidence": 0.99}),
    ("Saudi Arabia", "OPEC", "MEMBER_OF", {"confidence": 0.99}),
    ("Iran", "OPEC", "MEMBER_OF", {"confidence": 0.99}),
    # US-Iran conflict
    ("United States", "Iran", "CONFLICT_WITH", {"type": "sanctions_conflict", "confidence": 0.95, "description": "US sanctions on Iran, nuclear deal tensions, proxy conflicts"}),
    ("Iran", "United States", "CONFLICT_WITH", {"type": "geopolitical_rivalry", "confidence": 0.95, "description": "Iran opposes US hegemony, nuclear program disputes"}),
    # US-Israel alliance
    ("United States", "Israel", "ALLIES_WITH", {"type": "strategic_alliance", "confidence": 0.98, "description": "Strong US-Israel security partnership"}),
    # Russia-US conflict
    ("Russia", "United States", "CONFLICT_WITH", {"type": "geopolitical_rivalry", "confidence": 0.95, "description": "NATO expansion, Ukraine war, sanctions"}),
    # China-US trade/conflict
    ("China", "United States", "CONFLICT_WITH", {"type": "trade_tech_rivalry", "confidence": 0.92, "description": "Trade war, semiconductor controls, Taiwan tensions"}),
    # Pakistan-US
    ("Pakistan", "United States", "DEPENDS_ON", {"type": "aid_dependency", "confidence": 0.75, "description": "Historical US military and economic aid"}),
]


async def seed():
    await neo4j_client.connect()
    logger.info("Connected to Neo4j, starting seed...")

    # Create entities
    for entity in ENTITIES:
        props = {k: v for k, v in entity.items() if k not in ("name", "type")}
        query = """
        MERGE (e:Entity {name: $name})
        SET e.type = $type,
            e.confidence = 0.95,
            e.sources = ['seed_data'],
            e.created_at = datetime(),
            e.updated_at = datetime()
        SET e += $props
        RETURN e.name as name
        """
        await neo4j_client.execute_query(query, {"name": entity["name"], "type": entity["type"], "props": props})
        logger.info(f"  ✅ Entity: {entity['name']} ({entity['type']})")

    # Create relationships
    for src, tgt, rel_type, props in RELATIONSHIPS:
        query = f"""
        MATCH (a:Entity {{name: $src}})
        MATCH (b:Entity {{name: $tgt}})
        MERGE (a)-[r:RELATES {{type: $rel_type}}]->(b)
        SET r += $props,
            r.created_at = datetime()
        RETURN type(r) as rel
        """
        await neo4j_client.execute_query(query, {
            "src": src, "tgt": tgt, "rel_type": rel_type, "props": props
        })
        logger.info(f"  🔗 {src} --[{rel_type}]--> {tgt}")

    # Stats
    stats = await neo4j_client.execute_query("MATCH (e:Entity) RETURN count(e) as nodes")
    rels = await neo4j_client.execute_query("MATCH ()-[r]->() RETURN count(r) as rels")
    logger.info(f"\n✅ Seed complete! Nodes: {stats[0]['nodes']}, Relationships: {rels[0]['rels']}")

    await neo4j_client.close()


if __name__ == "__main__":
    asyncio.run(seed())
