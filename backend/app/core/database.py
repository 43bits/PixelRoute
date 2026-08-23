"""
Database connection and utilities
"""

from prisma import Prisma

# Global Prisma client instance
prisma = Prisma()


async def get_db():
    """Dependency for FastAPI routes"""
    if not prisma.is_connected():
        await prisma.connect()
    return prisma
