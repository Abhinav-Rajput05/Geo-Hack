#!/usr/bin/env python3
"""
Run Neo4j Cypher migration script.

Usage:
    python scripts/run_neo4j_migration.py migrations/001_create_indexes.cypher
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from app.database.neo4j_client import Neo4jClient


async def run_migration(migration_file: Path):
    """Execute a Cypher migration file."""
    if not migration_file.exists():
        print(f"❌ Migration file not found: {migration_file}")
        return False
    
    print(f"📂 Reading migration: {migration_file.name}")
    cypher_content = migration_file.read_text(encoding="utf-8")
    
    # Split by semicolons and filter out comments/empty lines
    statements = []
    for line in cypher_content.split("\n"):
        line = line.strip()
        if line and not line.startswith("//"):
            statements.append(line)
    
    # Join and split by actual statement boundaries
    full_script = " ".join(statements)
    cypher_statements = [s.strip() for s in full_script.split(";") if s.strip()]
    
    print(f"📊 Found {len(cypher_statements)} Cypher statements")
    
    neo4j = Neo4jClient()
    success_count = 0
    error_count = 0
    
    print("\n🚀 Starting migration...\n")
    
    for idx, statement in enumerate(cypher_statements, 1):
        # Extract index name for better logging
        index_name = "unknown"
        if "CREATE INDEX" in statement:
            parts = statement.split()
            if "INDEX" in parts:
                idx_pos = parts.index("INDEX")
                if idx_pos + 1 < len(parts):
                    index_name = parts[idx_pos + 1]
        
        try:
            print(f"[{idx}/{len(cypher_statements)}] Creating index: {index_name}...", end=" ")
            await neo4j.execute_query(statement, {})
            print("✅")
            success_count += 1
        except Exception as e:
            error_msg = str(e)
            # Ignore "already exists" errors
            if "already exists" in error_msg.lower() or "equivalent index" in error_msg.lower():
                print("⚠️  (already exists)")
                success_count += 1
            else:
                print(f"❌ Error: {error_msg}")
                error_count += 1
    
    print(f"\n📈 Migration Results:")
    print(f"   ✅ Success: {success_count}")
    print(f"   ❌ Errors: {error_count}")
    
    # Verify indexes
    print("\n🔍 Verifying indexes...")
    try:
        result = await neo4j.execute_query("SHOW INDEXES", {})
        print(f"   Found {len(result)} total indexes in database")
        
        # Show newly created indexes
        print("\n📋 Index List:")
        for row in result:
            index_type = row.get("type", "unknown")
            index_name = row.get("name", "unknown")
            state = row.get("state", "unknown")
            print(f"   - {index_name} ({index_type}) - {state}")
    except Exception as e:
        print(f"   ⚠️  Could not verify indexes: {e}")
    
    return error_count == 0


async def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/run_neo4j_migration.py <migration_file.cypher>")
        print("\nExample:")
        print("  python scripts/run_neo4j_migration.py migrations/001_create_indexes.cypher")
        sys.exit(1)
    
    migration_file = Path(sys.argv[1])
    success = await run_migration(migration_file)
    
    if success:
        print("\n🎉 Migration completed successfully!")
        sys.exit(0)
    else:
        print("\n⚠️  Migration completed with errors")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
