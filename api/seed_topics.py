"""Seed the conversation-topic bank (idempotent). Run: python -m api.seed_topics"""

import asyncio

from sqlalchemy import select

from api import db as dbmod
from api.models import Topic
from api.services.embeddings import embed

# (title, description, minimum difficulty on the 1–6 scale)
TOPICS = [
    ("Introducing yourself", "Name, where you're from, what you do.", 1.0),
    ("Ordering at a café", "Drinks, snacks, prices and small talk with the barista.", 1.0),
    ("Family and friends", "Describe the people close to you.", 1.0),
    ("Your daily routine", "What a typical weekday looks like.", 1.5),
    ("Food and cooking", "Favorite dishes, recipes and what you can't stand.", 1.5),
    ("Shopping for clothes", "Sizes, colors, prices and bargaining.", 1.5),
    ("Weather and seasons", "What you like to do in each season.", 1.5),
    ("Getting around town", "Asking for and giving directions, public transport.", 2.0),
    ("Hobbies and free time", "What you do for fun and why.", 2.0),
    ("Weekend plans", "Making and discussing plans with a friend.", 2.0),
    ("At the doctor", "Describing symptoms and understanding advice.", 2.5),
    ("Booking a hotel", "Reservations, amenities and solving problems.", 2.5),
    ("Last vacation", "Tell the story of a trip in the past tense.", 2.5),
    ("Movies and TV", "Recommend and review what you've watched.", 3.0),
    ("Music you love", "Artists, concerts and how music shapes your mood.", 3.0),
    ("Your hometown", "What's special about where you grew up.", 3.0),
    ("Job interview", "Talk about experience, strengths and goals.", 3.5),
    ("Sports and fitness", "Teams, training and staying healthy.", 3.0),
    ("Technology in daily life", "Phones, apps and whether they help or hurt.", 3.5),
    ("Travel disasters", "Lost luggage, missed trains and how it all worked out.", 3.5),
    ("Childhood memories", "Describe how things used to be.", 3.5),
    ("Environment and climate", "Everyday habits and bigger policy questions.", 4.0),
    ("Cultural differences", "Compare customs, manners and traditions.", 4.0),
    ("Books and storytelling", "Retell a story you love and explain why.", 4.0),
    ("Future dreams", "Hypotheticals: what would you do if...", 4.5),
    ("Education systems", "Compare schools and learning styles.", 4.5),
    ("Social media debate", "Take a position and defend it politely.", 5.0),
    ("Work-life balance", "Opinions on careers, remote work and burnout.", 5.0),
    ("Current events", "Discuss a news story and its consequences.", 5.5),
    ("Ethics of AI", "Argue the pros and cons of artificial intelligence.", 5.5),
]


async def seed() -> int:
    async with dbmod.SessionLocal() as db:
        existing = set(await db.scalars(select(Topic.title)))
        new = [t for t in TOPICS if t[0] not in existing]
        if not new:
            return 0
        vecs = await embed([f"{title}: {desc}" for title, desc, _ in new])
        db.add_all(
            Topic(title=title, description=desc, cefr_min=lvl, embedding=v)
            for (title, desc, lvl), v in zip(new, vecs)
        )
        await db.commit()
        return len(new)


if __name__ == "__main__":
    async def _main():
        await dbmod.init_db()
        print(f"seeded {await seed()} topics")

    asyncio.run(_main())
