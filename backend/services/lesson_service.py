"""Lesson catalogue service - provides dynamic lesson data."""

from fastapi import HTTPException


# In-memory catalogue (can be replaced with DB queries later)
LESSON_CATALOGUE = [
    {
        "subject": "Math",
        "subjectId": "math",
        "descriptor": "Geometry & Trigonometry",
        "topics": [
            {
                "topicId": "pythagoras",
                "title": "Pythagoras' Theorem",
                "duration": "20 min"
            },
            {
                "topicId": "sine_cosine",
                "title": "Sine & Cosine",
                "duration": "25 min"
            }
        ]
    },
    {
        "subject": "Science",
        "subjectId": "science",
        "descriptor": "Physics & Chemistry Fundamentals",
        "topics": [
            {
                "topicId": "newton_laws",
                "title": "Newton's Laws of Motion",
                "duration": "22 min"
            },
            {
                "topicId": "periodic_table",
                "title": "Periodic Table Basics",
                "duration": "18 min"
            }
        ]
    },
    {
        "subject": "English",
        "subjectId": "english",
        "descriptor": "Literature & Grammar",
        "topics": [
            {
                "topicId": "shakespeare",
                "title": "Shakespeare's Writing Style",
                "duration": "24 min"
            },
            {
                "topicId": "grammar_tense",
                "title": "Grammar: Verb Tenses",
                "duration": "20 min"
            }
        ]
    }
]


async def get_all_lessons() -> dict:
    """Retrieve all lessons from the catalogue."""
    try:
        return {
            "lessons": LESSON_CATALOGUE,
            "total_count": len(LESSON_CATALOGUE)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve lessons: {str(e)}")
