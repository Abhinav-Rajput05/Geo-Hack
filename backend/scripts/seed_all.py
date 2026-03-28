"""
Complete seed script — populates Neo4j, PostgreSQL, and Vector store
Run: cd backend && python scripts/seed_all.py
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.neo4j_client import neo4j_client
from app.database.postgres_client import postgres_client
from app.vectorstore.chroma_service import chroma_service
from loguru import logger

# ─── NEO4J SEED DATA ──────────────────────────────────────────────────────────
ENTITIES = [
    {"name": "India", "type": "Country", "region": "South Asia", "lat": 20.59, "lng": 78.96, "description": "Republic of India - world's largest democracy, fastest growing major economy"},
    {"name": "China", "type": "Country", "region": "East Asia", "lat": 35.86, "lng": 104.19, "description": "People's Republic of China - second largest economy, military superpower"},
    {"name": "United States", "type": "Country", "region": "North America", "lat": 37.09, "lng": -95.71, "description": "USA - world's largest economy, global military superpower"},
    {"name": "Russia", "type": "Country", "region": "Europe/Asia", "lat": 61.52, "lng": 105.31, "description": "Russian Federation - nuclear power, major energy exporter"},
    {"name": "Pakistan", "type": "Country", "region": "South Asia", "lat": 30.37, "lng": 69.34, "description": "Islamic Republic of Pakistan - nuclear state, India's neighbor"},
    {"name": "Japan", "type": "Country", "region": "East Asia", "lat": 36.20, "lng": 138.25, "description": "Japan - third largest economy, US ally in Indo-Pacific"},
    {"name": "Germany", "type": "Country", "region": "Europe", "lat": 51.16, "lng": 10.45, "description": "Federal Republic of Germany - largest European economy"},
    {"name": "Israel", "type": "Country", "region": "Middle East", "lat": 31.04, "lng": 34.85, "description": "State of Israel - advanced military technology, US ally"},
    {"name": "Iran", "type": "Country", "region": "Middle East", "lat": 32.42, "lng": 53.68, "description": "Islamic Republic of Iran - regional power, nuclear program"},
    {"name": "Saudi Arabia", "type": "Country", "region": "Middle East", "lat": 23.88, "lng": 45.07, "description": "Kingdom of Saudi Arabia - world's largest oil exporter"},
    {"name": "ISRO", "type": "Organization", "sector": "Space Technology", "description": "Indian Space Research Organisation - Chandrayaan, Mangalyaan missions"},
    {"name": "DRDO", "type": "Organization", "sector": "Defense", "description": "Defence Research and Development Organisation - BrahMos, Tejas development"},
    {"name": "NATO", "type": "Organization", "sector": "Defense Alliance", "description": "North Atlantic Treaty Organization - 31 member military alliance"},
    {"name": "SCO", "type": "Organization", "sector": "Political", "description": "Shanghai Cooperation Organisation - China-Russia led bloc"},
    {"name": "BRICS", "type": "Organization", "sector": "Economic", "description": "Brazil Russia India China South Africa - emerging economies bloc"},
    {"name": "Quad", "type": "Organization", "sector": "Defense Alliance", "description": "Quadrilateral Security Dialogue - US India Japan Australia"},
    {"name": "OPEC", "type": "Organization", "sector": "Energy", "description": "Organization of Petroleum Exporting Countries"},
    {"name": "IMF", "type": "Organization", "sector": "Finance", "description": "International Monetary Fund - global financial stability"},
    {"name": "BrahMos Missile", "type": "System", "category": "Defense", "description": "India-Russia joint supersonic cruise missile - 290km range, Mach 2.8"},
    {"name": "Tejas Fighter Jet", "type": "System", "category": "Defense", "description": "India's indigenous light combat aircraft - 4th generation"},
    {"name": "Chandrayaan-3", "type": "System", "category": "Space", "description": "India's lunar mission - successfully landed near south pole Aug 2023"},
    {"name": "UPI Payment System", "type": "System", "category": "Technology", "description": "Unified Payments Interface - India's digital payment backbone, 10B+ monthly transactions"},
    {"name": "Semiconductor Chips", "type": "System", "category": "Technology", "description": "Advanced semiconductor integrated circuits - critical for defense and tech"},
    {"name": "India-China Border Tensions", "type": "Event", "event_type": "ConflictEvent", "severity": 0.75, "description": "Ongoing LAC border disputes in Ladakh, Galwan Valley clash 2020"},
    {"name": "US Semiconductor Export Controls", "type": "Event", "event_type": "PolicyChange", "severity": 0.85, "description": "US CHIPS Act restricting advanced chip exports to China, affecting global supply chains"},
    {"name": "Russia-Ukraine War", "type": "Event", "event_type": "ConflictEvent", "severity": 0.95, "description": "Ongoing armed conflict since Feb 2022, global energy and food security impact"},
    {"name": "India GDP Growth 2024", "type": "Event", "event_type": "Indicator", "severity": 0.3, "description": "India 7.6% GDP growth - fastest among G20 economies"},
    {"name": "India Defense Budget 2024", "type": "Event", "event_type": "PolicyChange", "severity": 0.6, "description": "India defense budget $75B - 4th largest globally, 13% increase"},
    {"name": "Iran Nuclear Program", "type": "Event", "event_type": "PolicyChange", "severity": 0.9, "description": "Iran uranium enrichment to 60%, IAEA concerns, US sanctions"},
    {"name": "India-Middle East Corridor", "type": "Event", "event_type": "TradeAgreement", "severity": 0.6, "description": "IMEC - India Middle East Europe Economic Corridor announced G20 2023"},
]

RELATIONSHIPS = [
    # India alliances & conflicts
    ("India", "Russia", "SUPPLIES", {"type": "defense_supply", "confidence": 0.92, "description": "Russia supplies 60% of India defense equipment including S-400, MiG-29"}),
    ("India", "United States", "ALLIES_WITH", {"type": "strategic_partnership", "confidence": 0.85, "description": "India-US Comprehensive Global Strategic Partnership, QUAD member"}),
    ("India", "Japan", "ALLIES_WITH", {"type": "strategic_partnership", "confidence": 0.82, "description": "India-Japan Special Strategic and Global Partnership"}),
    ("India", "Israel", "TRADES_WITH", {"type": "defense_trade", "confidence": 0.88, "description": "Israel 2nd largest defense supplier to India - drones, missiles, surveillance"}),
    ("India", "China", "CONFLICT_WITH", {"type": "border_dispute", "confidence": 0.92, "description": "LAC border disputes, Galwan clash 2020, economic competition"}),
    ("India", "Pakistan", "CONFLICT_WITH", {"type": "territorial_dispute", "confidence": 0.96, "description": "Kashmir dispute, cross-border terrorism, nuclear standoff"}),
    ("India", "BRICS", "MEMBER_OF", {"confidence": 0.99}),
    ("India", "SCO", "MEMBER_OF", {"confidence": 0.99}),
    ("India", "Quad", "MEMBER_OF", {"confidence": 0.99}),
    ("India", "IMF", "MEMBER_OF", {"confidence": 0.99}),
    ("India", "DRDO", "FUNDS", {"confidence": 0.99}),
    ("India", "ISRO", "FUNDS", {"confidence": 0.99}),
    ("India", "BrahMos Missile", "OPERATES", {"confidence": 0.99}),
    ("India", "Tejas Fighter Jet", "OPERATES", {"confidence": 0.99}),
    ("India", "Semiconductor Chips", "DEPENDS_ON", {"confidence": 0.92, "description": "India imports 100% advanced semiconductors, building domestic fab capacity"}),
    # US relationships
    ("United States", "China", "CONFLICT_WITH", {"type": "trade_tech_rivalry", "confidence": 0.93, "description": "Trade war, semiconductor export controls, Taiwan tensions"}),
    ("United States", "Iran", "CONFLICT_WITH", {"type": "sanctions_conflict", "confidence": 0.95, "description": "Nuclear deal collapse, maximum pressure sanctions, proxy conflicts"}),
    ("United States", "Israel", "ALLIES_WITH", {"type": "strategic_alliance", "confidence": 0.98, "description": "Ironclad US-Israel security partnership, $3.8B annual military aid"}),
    ("United States", "Japan", "ALLIES_WITH", {"type": "security_treaty", "confidence": 0.97, "description": "US-Japan Security Treaty, 54000 US troops in Japan"}),
    ("United States", "NATO", "MEMBER_OF", {"confidence": 0.99}),
    ("United States", "Quad", "MEMBER_OF", {"confidence": 0.99}),
    ("United States", "Semiconductor Chips", "CONTROLS", {"confidence": 0.96, "description": "US controls advanced chip exports via CHIPS Act and EAR regulations"}),
    # China relationships
    ("China", "Russia", "ALLIES_WITH", {"type": "strategic_partnership", "confidence": 0.88, "description": "No-limits partnership, energy trade, anti-US alignment"}),
    ("China", "Pakistan", "ALLIES_WITH", {"type": "all_weather_friendship", "confidence": 0.94, "description": "CPEC $62B investment, military cooperation, all-weather strategic partnership"}),
    ("China", "BRICS", "MEMBER_OF", {"confidence": 0.99}),
    ("China", "SCO", "MEMBER_OF", {"confidence": 0.99}),
    ("China", "Semiconductor Chips", "DEPENDS_ON", {"confidence": 0.95, "description": "China faces US export restrictions on advanced chips below 14nm"}),
    # Russia relationships
    ("Russia", "India", "SUPPLIES", {"type": "defense_supply", "confidence": 0.92}),
    ("Russia", "BRICS", "MEMBER_OF", {"confidence": 0.99}),
    ("Russia", "SCO", "MEMBER_OF", {"confidence": 0.99}),
    # Iran relationships
    ("Iran", "Israel", "CONFLICT_WITH", {"type": "proxy_war", "confidence": 0.96, "description": "Direct missile attacks April 2024, proxy conflicts via Hezbollah Hamas"}),
    ("Iran", "Saudi Arabia", "CONFLICT_WITH", {"type": "regional_rivalry", "confidence": 0.88, "description": "Sunni-Shia proxy wars, Yemen conflict, regional hegemony competition"}),
    ("Iran", "Russia", "ALLIES_WITH", {"type": "tactical_alignment", "confidence": 0.82, "description": "Iran supplies drones to Russia for Ukraine war"}),
    ("Iran", "OPEC", "MEMBER_OF", {"confidence": 0.99}),
    # Events impact
    ("India-China Border Tensions", "India", "IMPACTS", {"confidence": 0.92, "severity": 0.75}),
    ("India-China Border Tensions", "China", "IMPACTS", {"confidence": 0.88, "severity": 0.6}),
    ("US Semiconductor Export Controls", "India", "IMPACTS", {"confidence": 0.82, "description": "Affects India chip access, opportunity for domestic manufacturing"}),
    ("US Semiconductor Export Controls", "China", "IMPACTS", {"confidence": 0.96, "description": "Direct target - restricts China AI and military chip access"}),
    ("Russia-Ukraine War", "India", "IMPACTS", {"confidence": 0.87, "description": "India buys discounted Russian oil, faces Western pressure, defense supply disruption"}),
    ("Russia-Ukraine War", "Germany", "IMPACTS", {"confidence": 0.94, "description": "Energy crisis, Nord Stream sabotage, economic recession risk"}),
    ("Iran Nuclear Program", "Israel", "IMPACTS", {"confidence": 0.95, "severity": 0.9}),
    ("Iran Nuclear Program", "United States", "IMPACTS", {"confidence": 0.92, "severity": 0.85}),
    ("India-Middle East Corridor", "India", "BENEFITS", {"confidence": 0.82}),
    ("India Defense Budget 2024", "DRDO", "IMPACTS", {"confidence": 0.92}),
    ("Japan", "Quad", "MEMBER_OF", {"confidence": 0.99}),
    ("Saudi Arabia", "OPEC", "MEMBER_OF", {"confidence": 0.99}),
    ("Russia", "BrahMos Missile", "SUPPLIES", {"confidence": 0.92, "description": "Joint development with India, Russia provides propulsion technology"}),
]

# ─── POSTGRESQL SEED ARTICLES ─────────────────────────────────────────────────
ARTICLES = [
    {
        "id": "art-001", "title": "India's Defense Budget Reaches $75 Billion in 2024-25",
        "summary": "India has increased its defense budget by 13% to $75 billion for 2024-25, making it the fourth largest defense spender globally. The budget focuses on indigenous manufacturing under Atmanirbhar Bharat, with DRDO receiving increased funding for BrahMos upgrades and Tejas Mk2 development.",
        "source": "Defense News", "url": "https://defensenews.com/india-defense-budget-2024",
        "domain": "defense", "region": "South Asia", "credibility": 0.92,
        "categories": ["defense", "india", "economy"]
    },
    {
        "id": "art-002", "title": "US Semiconductor Export Controls Target China's AI Ambitions",
        "summary": "The United States has expanded semiconductor export controls under the CHIPS Act, restricting China's access to advanced chips below 14nm. This affects China's AI development, military modernization, and Huawei's smartphone business. India sees opportunity to attract semiconductor manufacturing.",
        "source": "Reuters", "url": "https://reuters.com/us-china-chips-2024",
        "domain": "technology", "region": "Global", "credibility": 0.95,
        "categories": ["technology", "geopolitics", "economy"]
    },
    {
        "id": "art-003", "title": "India-China LAC Border Tensions: Current Status",
        "summary": "India and China have completed partial disengagement at Depsang and Demchok in Ladakh after four years of standoff. However, underlying tensions remain with China's infrastructure buildup along LAC. India has deployed additional troops and built border roads under Project Himank.",
        "source": "The Hindu", "url": "https://thehindu.com/india-china-lac-2024",
        "domain": "geopolitics", "region": "South Asia", "credibility": 0.93,
        "categories": ["geopolitics", "defense", "india"]
    },
    {
        "id": "art-004", "title": "Russia-Ukraine War: Impact on Global Energy Markets",
        "summary": "The ongoing Russia-Ukraine conflict has fundamentally reshaped global energy markets. Europe has reduced Russian gas dependence from 40% to 8%. India has increased Russian oil imports to 40% of total imports at discounted prices. Global food prices remain elevated due to Black Sea grain disruptions.",
        "source": "BBC World", "url": "https://bbc.com/russia-ukraine-energy-2024",
        "domain": "economy", "region": "Europe", "credibility": 0.94,
        "categories": ["economy", "geopolitics", "climate"]
    },
    {
        "id": "art-005", "title": "Iran Nuclear Program: IAEA Reports 60% Uranium Enrichment",
        "summary": "Iran has enriched uranium to 60% purity, approaching weapons-grade 90%. The IAEA reports Iran has enough enriched uranium for multiple nuclear devices if further processed. US and Israel have warned of military action. Iran-Israel direct conflict escalated with missile exchanges in April 2024.",
        "source": "Al Jazeera", "url": "https://aljazeera.com/iran-nuclear-2024",
        "domain": "geopolitics", "region": "Middle East", "credibility": 0.91,
        "categories": ["geopolitics", "defense"]
    },
    {
        "id": "art-006", "title": "India's Chandrayaan-3 Success Boosts Space Economy Ambitions",
        "summary": "India's Chandrayaan-3 successfully landed near the lunar south pole in August 2023, making India the fourth country to land on the Moon. ISRO's success has attracted $100M+ in private space investments. India aims to launch its own space station by 2035 and send astronauts to the Moon by 2040.",
        "source": "Times of India", "url": "https://timesofindia.com/chandrayaan3-impact",
        "domain": "technology", "region": "South Asia", "credibility": 0.90,
        "categories": ["technology", "india"]
    },
    {
        "id": "art-007", "title": "QUAD Summit: Indo-Pacific Security Framework Strengthened",
        "summary": "The Quad summit (US, India, Japan, Australia) has strengthened the Indo-Pacific security framework with new agreements on semiconductor supply chains, critical minerals, and maritime domain awareness. China has criticized the Quad as an Asian NATO. India maintains strategic autonomy while deepening Quad engagement.",
        "source": "Foreign Policy", "url": "https://foreignpolicy.com/quad-summit-2024",
        "domain": "geopolitics", "region": "Indo-Pacific", "credibility": 0.93,
        "categories": ["geopolitics", "defense"]
    },
    {
        "id": "art-008", "title": "India GDP Growth: 7.6% Makes It Fastest Growing Major Economy",
        "summary": "India's GDP grew at 7.6% in FY2024, making it the fastest growing major economy globally. IMF projects India to become the third largest economy by 2027. Key drivers include manufacturing growth under PLI schemes, digital economy expansion, and infrastructure investment. India's UPI processed 10 billion transactions monthly.",
        "source": "Economic Times", "url": "https://economictimes.com/india-gdp-2024",
        "domain": "economy", "region": "South Asia", "credibility": 0.91,
        "categories": ["economy", "india"]
    },
    {
        "id": "art-009", "title": "BrahMos Missile: India Exports to Philippines, Eyes More Markets",
        "summary": "India has successfully delivered BrahMos supersonic cruise missiles to the Philippines in its first major defense export. The $375M deal marks India's emergence as a defense exporter. Vietnam, Indonesia, and Saudi Arabia are in advanced talks. BrahMos 2 with hypersonic capability is under development with Russia.",
        "source": "Defense News", "url": "https://defensenews.com/brahmos-export-2024",
        "domain": "defense", "region": "Indo-Pacific", "credibility": 0.92,
        "categories": ["defense", "india", "geopolitics"]
    },
    {
        "id": "art-010", "title": "Saudi Arabia-Iran Normalization: China-Brokered Deal Impact",
        "summary": "China brokered a historic Saudi Arabia-Iran normalization deal in March 2023, restoring diplomatic relations after 7 years. This reduces US influence in the Middle East and strengthens China's role as a global mediator. India-Middle East Corridor (IMEC) announced at G20 offers alternative connectivity bypassing Iran.",
        "source": "Al Jazeera", "url": "https://aljazeera.com/saudi-iran-china-2024",
        "domain": "geopolitics", "region": "Middle East", "credibility": 0.92,
        "categories": ["geopolitics", "economy"]
    },
    {
        "id": "art-011", "title": "Pakistan Economic Crisis: IMF Bailout and India Relations",
        "summary": "Pakistan secured a $3B IMF bailout amid severe economic crisis with 30% inflation and foreign exchange reserves at critical levels. Pakistan's dependence on China's CPEC debt has increased. India-Pakistan relations remain frozen with no trade or diplomatic engagement since 2019 Article 370 revocation.",
        "source": "The Diplomat", "url": "https://thediplomat.com/pakistan-crisis-2024",
        "domain": "economy", "region": "South Asia", "credibility": 0.91,
        "categories": ["economy", "geopolitics"]
    },
    {
        "id": "art-012", "title": "Climate Change: India's Extreme Heat and Agricultural Impact",
        "summary": "India experienced record heat waves in 2024 with temperatures exceeding 50°C in Rajasthan. Agricultural output of wheat and rice affected, raising food security concerns. India's climate vulnerability index ranks it among top 10 most affected nations. India has committed to 500GW renewable energy by 2030.",
        "source": "NASA Climate", "url": "https://climate.nasa.gov/india-heat-2024",
        "domain": "climate", "region": "South Asia", "credibility": 0.96,
        "categories": ["climate", "india"]
    },
]

# ─── VECTOR STORE TEXTS ───────────────────────────────────────────────────────
VECTOR_TEXTS = [
    ("India defense strategy relies on Russia for 60% of military equipment including S-400 air defense systems, MiG-29 fighters, and T-90 tanks. India is diversifying with US F-35 negotiations and Israeli drone purchases.", {"domain": "defense", "country": "India"}),
    ("US semiconductor export controls under CHIPS Act restrict China's access to advanced chips below 14nm. This affects Huawei, SMIC, and China's AI military applications. India benefits as alternative manufacturing destination.", {"domain": "technology", "country": "China"}),
    ("India China border LAC dispute in Ladakh involves 3488km contested boundary. Galwan Valley clash June 2020 killed 20 Indian and 4 Chinese soldiers. Partial disengagement achieved at Depsang Demchok in 2024.", {"domain": "geopolitics", "country": "India"}),
    ("Russia Ukraine war impact on India: India imports 40% oil from Russia at discounted prices saving $35B annually. India faces Western pressure but maintains strategic autonomy. Defense supply chains disrupted for spare parts.", {"domain": "geopolitics", "country": "Russia"}),
    ("Iran nuclear program enriched uranium to 60% purity. IAEA estimates Iran has enough material for 3 nuclear devices if enriched to 90%. US maximum pressure sanctions. Israel conducted strikes on Iranian nuclear facilities.", {"domain": "defense", "country": "Iran"}),
    ("India GDP growth 7.6% fastest among G20 economies. IMF projects India third largest economy by 2027. Manufacturing PLI schemes attracting Apple Samsung investments. Digital economy UPI 10 billion monthly transactions.", {"domain": "economy", "country": "India"}),
    ("Quad security dialogue US India Japan Australia focuses on Indo-Pacific security, semiconductor supply chains, critical minerals, maritime domain awareness. China views Quad as containment strategy.", {"domain": "geopolitics", "country": "India"}),
    ("BrahMos supersonic cruise missile India Russia joint development. Range 290km speed Mach 2.8. Philippines export deal $375M first major Indian defense export. Vietnam Indonesia Saudi Arabia in talks.", {"domain": "defense", "country": "India"}),
    ("Saudi Arabia Iran normalization China brokered March 2023. Reduces US Middle East influence. India Middle East Europe Corridor IMEC alternative to China Belt Road Initiative announced G20 2023.", {"domain": "geopolitics", "country": "Saudi Arabia"}),
    ("Pakistan economic crisis 30% inflation IMF bailout $3B. CPEC China debt trap concerns. India Pakistan relations frozen since 2019 Article 370. Nuclear standoff risk remains high.", {"domain": "economy", "country": "Pakistan"}),
    ("Chandrayaan-3 India lunar south pole landing August 2023 fourth country Moon landing. ISRO space economy $100M private investment. India space station 2035 Moon mission 2040 target.", {"domain": "technology", "country": "India"}),
    ("India climate vulnerability extreme heat 50 degrees Rajasthan 2024. Agricultural wheat rice output affected food security. 500GW renewable energy target 2030. Climate finance demand from developed nations.", {"domain": "climate", "country": "India"}),
    ("BRICS expansion 2024 Saudi Arabia UAE Egypt Ethiopia Argentina joined. New Development Bank alternative to IMF World Bank. De-dollarization push trade in local currencies.", {"domain": "economy", "country": "India"}),
    ("NATO expansion Finland Sweden joined 2023 2024. Russia response nuclear threats. China Russia no-limits partnership military exercises. SCO expansion India Pakistan full members.", {"domain": "geopolitics", "country": "Russia"}),
    ("India semiconductor manufacturing PLI scheme $10B incentive. Micron $2.75B chip assembly plant Gujarat. TATA semiconductor fab planned. Reduce import dependence from Taiwan China.", {"domain": "technology", "country": "India"}),
]


async def seed_neo4j():
    logger.info("=== Seeding Neo4j ===")
    await neo4j_client.connect()

    for entity in ENTITIES:
        props = {k: v for k, v in entity.items() if k not in ("name", "type")}
        await neo4j_client.execute_query("""
            MERGE (e:Entity {name: $name})
            SET e.type = $type, e.confidence = 0.95,
                e.sources = ['seed_data'], e.created_at = datetime(),
                e.updated_at = datetime()
            SET e += $props
        """, {"name": entity["name"], "type": entity["type"], "props": props})
        logger.info(f"  ✅ {entity['name']} ({entity['type']})")

    for src, tgt, rel_type, props in RELATIONSHIPS:
        await neo4j_client.execute_query(f"""
            MATCH (a:Entity {{name: $src}})
            MATCH (b:Entity {{name: $tgt}})
            MERGE (a)-[r:RELATES {{type: $rel_type}}]->(b)
            SET r += $props, r.created_at = datetime()
        """, {"src": src, "tgt": tgt, "rel_type": rel_type, "props": props})
        logger.info(f"  🔗 {src} --[{rel_type}]--> {tgt}")

    stats = await neo4j_client.execute_query("MATCH (e:Entity) RETURN count(e) as n")
    rels = await neo4j_client.execute_query("MATCH ()-[r]->() RETURN count(r) as n")
    logger.info(f"Neo4j: {stats[0]['n']} nodes, {rels[0]['n']} relationships")
    await neo4j_client.close()


async def seed_postgres():
    logger.info("=== Seeding PostgreSQL ===")
    await postgres_client.connect()

    await postgres_client.execute_write("""
        CREATE TABLE IF NOT EXISTS articles (
            id VARCHAR(255) PRIMARY KEY,
            title TEXT NOT NULL,
            summary TEXT,
            content TEXT,
            source VARCHAR(255),
            url TEXT UNIQUE,
            published_at TIMESTAMP DEFAULT NOW(),
            categories JSONB DEFAULT '[]',
            entities JSONB DEFAULT '[]',
            domain VARCHAR(100),
            region VARCHAR(100),
            sentiment VARCHAR(50),
            relevance_score DOUBLE PRECISION,
            source_credibility DOUBLE PRECISION,
            event_key VARCHAR(255),
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    from datetime import datetime, timedelta
    import random
    import json

    for i, art in enumerate(ARTICLES):
        published = datetime.utcnow() - timedelta(hours=random.randint(1, 72))
        await postgres_client.execute_write("""
            INSERT INTO articles (id, title, summary, source, url, published_at,
                categories, entities, domain, region, source_credibility)
            VALUES (:id, :title, :summary, :source, :url, :published_at,
                CAST(:categories AS JSONB), '[]'::jsonb, :domain, :region, :credibility)
            ON CONFLICT (url) DO UPDATE SET
                title = EXCLUDED.title, summary = EXCLUDED.summary,
                updated_at = NOW()
        """, {
            "id": art["id"], "title": art["title"], "summary": art["summary"],
            "source": art["source"], "url": art["url"], "published_at": published,
            "categories": json.dumps(art["categories"]),
            "domain": art["domain"], "region": art["region"],
            "credibility": art["credibility"]
        })
        logger.info(f"  ✅ Article: {art['title'][:50]}...")

    count = await postgres_client.execute_query("SELECT COUNT(*) as n FROM articles")
    logger.info(f"PostgreSQL: {count[0]['n']} articles")
    await postgres_client.close()


async def seed_vector():
    logger.info("=== Seeding Vector Store ===")
    texts = [t for t, _ in VECTOR_TEXTS]
    metas = [m for _, m in VECTOR_TEXTS]
    count = await chroma_service.add_documents(texts, metas)
    logger.info(f"Vector store: {count} documents added")


async def main():
    logger.info("🚀 Starting full seed...")
    await seed_neo4j()
    await seed_postgres()
    await seed_vector()
    logger.info("✅ All databases seeded successfully!")
    logger.info("")
    logger.info("Now you can ask queries like:")
    logger.info("  - How do US chip controls affect India's defense?")
    logger.info("  - What is India's relationship with Russia?")
    logger.info("  - Explain Iran nuclear program impact on Middle East")
    logger.info("  - What is India's GDP growth and economic outlook?")


if __name__ == "__main__":
    asyncio.run(main())
