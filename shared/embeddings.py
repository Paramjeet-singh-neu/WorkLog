import asyncio
from typing import Protocol

from google import genai
from google.genai import types
from openai import AsyncOpenAI

from shared.config import Settings


def split_skills(skills_text: str) -> list[str]:
    return [skill.strip() for skill in skills_text.replace("\n", ",").split(",") if skill.strip()]


def average_vectors(vectors: list[list[float]]) -> list[float]:
    if not vectors:
        return []
    width = len(vectors[0])
    return [sum(vector[i] for vector in vectors) / len(vectors) for i in range(width)]


class EmbeddingProvider(Protocol):
    async def embed(self, text: str) -> list[float]:
        pass

    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        pass


class OpenAIEmbeddingProvider:
    def __init__(self, settings: Settings) -> None:
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required when EMBEDDING_PROVIDER=openai")
        self.model = settings.openai_embedding_model
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def embed(self, text: str) -> list[float]:
        response = await self.client.embeddings.create(model=self.model, input=text)
        return response.data[0].embedding

    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        response = await self.client.embeddings.create(model=self.model, input=texts)
        return [item.embedding for item in response.data]


class GeminiEmbeddingProvider:
    def __init__(self, settings: Settings) -> None:
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is required when EMBEDDING_PROVIDER=gemini")
        self.model = settings.gemini_embedding_model
        self.dimensions = settings.embedding_dimensions
        self.client = genai.Client(api_key=settings.gemini_api_key)

    def _embed_sync(self, contents: str | list[str]) -> list[list[float]]:
        response = self.client.models.embed_content(
            model=self.model,
            contents=contents,
            config=types.EmbedContentConfig(output_dimensionality=self.dimensions),
        )
        return [embedding.values for embedding in response.embeddings or []]

    async def embed(self, text: str) -> list[float]:
        embeddings = await asyncio.to_thread(self._embed_sync, text)
        if not embeddings:
            raise RuntimeError("Gemini returned no embedding")
        return embeddings[0]

    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        embeddings = await asyncio.to_thread(self._embed_sync, texts)
        if len(embeddings) != len(texts):
            raise RuntimeError("Gemini returned an unexpected number of embeddings")
        return embeddings


def make_embedding_provider(settings: Settings) -> EmbeddingProvider:
    provider = settings.embedding_provider.lower().strip()
    if provider == "openai":
        return OpenAIEmbeddingProvider(settings)
    if provider == "gemini":
        return GeminiEmbeddingProvider(settings)
    raise RuntimeError("EMBEDDING_PROVIDER must be either 'openai' or 'gemini'")
