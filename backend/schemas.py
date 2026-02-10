from pydantic import BaseModel, Field


class ExtractedFact(BaseModel):
    """
    Represents a fact extracted by the AI service.
    """

    entity: str = Field(
        ..., description="The subject of the fact (e.g., 'User's Name', 'Project X')"
    )
    value: str = Field(..., description="The detailed content of the fact")
    category: str = Field(
        default="general",
        description="Category: pessoal, trabalho, agenda, local, tech, opiniao, relacionamento",
    )
