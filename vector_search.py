from dataclasses import dataclass, field
from typing import Optional
import numpy as np
import os
from pathlib import Path
from openai import OpenAI
import dill
from llm import claude_3_7 as claude
from prompt_templates import search_result_filter
import json
import re

upstage = OpenAI(
    api_key=os.getenv("UPSTAGE_API_KEY"), base_url="https://api.upstage.ai/v1"
)


@dataclass(slots=True)
class DocEmbeddings:
    id: str
    doc: str
    embeddings: list[float] | None = None


@dataclass(slots=True)
class Similarity:
    id: str
    doc: str
    score: float
    rank: int = None
    rrf_score: float = None
    docs: str


class Collecton:

    _instances = {}

    def __new__(cls, file_name: str):
        if file_name not in cls._instances:
            instance = super().__new__(cls)
            cls._instances[file_name] = instance
        return cls._instances[file_name]

    def __init__(self, file_name: str):
        if getattr(self, "_initialized", False):
            return

        self.file_path = str(Path("scrap2") / "database" / f"{file_name}.dill")
        self.index: dict[str, DocEmbeddings] = {}
        self._initialized = True

    def load(self) -> "Collecton":
        try:
            with open(self.file_path, "rb") as f:
                self.index = dill.load(f)
        except Exception as e:
            raise e
        return self

    def add_doc(self, id: str, doc: str):
        self.index[id] = DocEmbeddings(id=id, doc=doc)

    def build(self):
        for doc_embeddings in self.index.values():
            doc_embeddings.embeddings = self._get_embeddings(doc_embeddings.doc)

        with open(self.file_path, "wb") as f:
            dill.dump(self.index, f)

    def query(self, query: str, cutoff=0.4, top_k: int = 60) -> dict[int, Similarity]:
        query_embeddings = self._get_embeddings(query)
        similarity_dict: dict[str, Similarity] = {}
        for doc_embedding in self.index.values():
            # if doc_embedding.embeddings is None:
            #     continue
            score = np.dot(query_embeddings, doc_embedding.embeddings) / (
                np.linalg.norm(query_embeddings)
                * np.linalg.norm(doc_embedding.embeddings)
            )
            if score < cutoff:
                continue
            similarity_dict[doc_embedding.id] = Similarity(
                id=doc_embedding.id,
                doc=doc_embedding.doc,
                docs=doc_embedding.doc,
                score=float(score),
            )

        top_ids = sorted(
            similarity_dict.keys(), key=lambda x: similarity_dict[x].score, reverse=True
        )[:top_k]
        ranked_dict = self._make_rank(top_ids, similarity_dict)
        return ranked_dict

    def _make_rank(self, top_ids: list[str], similarity_dict: dict[str, Similarity]):
        ranked_dict: dict[int, Similarity] = {}
        for rank, top_id in enumerate(top_ids, start=1):
            similarity_dict[top_id].rank = rank
            ranked_dict[top_id] = similarity_dict[top_id]
        return ranked_dict

    def _get_embeddings(self, text: str) -> list[float]:
        return (
            upstage.embeddings.create(input=text, model="embedding-query")
            .data[0]
            .embedding
        )

    def __len__(self) -> int:
        return len(self.index)


# def get_rrf(sim1: dict[str, Similarity], sim2: dict[str, Similarity], k: int = 60):
#     union_ids = set(sim1) | set(sim2)
#     results = []
#     for _id in union_ids:
#         r1 = sim1[_id].rank if _id in sim1 else None
#         r2 = sim2[_id].rank if _id in sim2 else None

#         score = (1 / (k + r1) if r1 is not None else 0) + (
#             1 / (k + r2) if r2 is not None else 0
#         )

#         obj = sim1.get(_id) or sim2.get(_id)  # 둘 중 하나를 대표로
#         obj.rrf_score = score
#         results.append(obj)

#     return sorted(results, key=lambda o: o.rrf_score, reverse=True)

# def get_rrf(
#     sim1: dict[str, Similarity],
#     sim2: dict[str, Similarity],
#     sim3: dict[str, Similarity],
#     k: int = 60,
# ):
#     union_ids = set(sim1) | set(sim2) | set(sim3)
#     results = []
#     for _id in union_ids:
#         r1 = sim1[_id].rank if _id in sim1 else None
#         r2 = sim2[_id].rank if _id in sim2 else None
#         r3 = sim3[_id].rank if _id in sim3 else None

#         score = (
#             (0.99 / (k + r1) if r1 is not None else 0)
#             + (0.0001 / (k + r2) if r2 is not None else 0)
#             + (0.0001 / (k + r3) if r3 is not None else 0)
#         )

#         obj = sim1.get(_id) or sim2.get(_id) or sim3.get(_id)  # 셋 중 하나를 대표로
#         obj.docs = "\n".join(
#             [
#                 sim1.get(_id).doc if sim1.get(_id) else "",
#                 sim2.get(_id).doc if sim2.get(_id) else "",
#                 sim3.get(_id).doc if sim3.get(_id) else "",
#             ]
#         ).strip()
#         obj.rrf_score = score
#         results.append(obj)

#     return sorted(results, key=lambda o: o.rrf_score, reverse=True)


def get_rrf(
    sim1: dict[str, Similarity],
    sim2: dict[str, Similarity],
    k: int = 60,
):
    union_ids = set(sim1) | set(sim2)
    results = []
    for _id in union_ids:
        r1 = sim1[_id].rank if _id in sim1 else None
        r2 = sim2[_id].rank if _id in sim2 else None

        score = (0.7 / (k + r1) if r1 is not None else 0) + (
            0.3 / (k + r2) if r2 is not None else 0
        )

        obj = sim1.get(_id) or sim2.get(_id)  # 둘 중 하나를 대표로
        obj.docs = "\n".join(
            [
                sim1.get(_id).doc if sim1.get(_id) else "",
                sim2.get(_id).doc if sim2.get(_id) else "",
            ]
        ).strip()
        obj.rrf_score = score
        results.append(obj)

    return sorted(results, key=lambda o: o.rrf_score, reverse=True)


def filter_results(similarities: list[Similarity], query: str):
    search_doc_results = {sim.id: sim.docs for sim in similarities}
    response_json_str = claude.create_response_text(
        messages=[
            {
                "role": "user",
                "content": search_result_filter.format(
                    user_query=query, search_results=search_doc_results
                ),
            },
            {"role": "assistant", "content": "<json>"},
        ],
        stop_sequences=["</json>"],
    )
    filtered_similarities: list[Similarity] = []
    search_sim_results = {sim.id: sim for sim in similarities}
    response_json: dict[str, bool] = json.loads(response_json_str)
    for id, is_valid in response_json.items():
        if is_valid:
            filtered_similarities.append(search_sim_results[id])

    return filtered_similarities


def get_rrf_bkup(
    sim1: dict[str, Similarity],
    sim2: dict[str, Similarity],
    k: int = 60,
    w1: float = 0.7,
    w2: float = 0.3,
):

    default_rank = len(sim2) + 1  # 보조 리스트 꼴찌보다 한 칸 뒤
    union_ids = set(sim1) | set(sim2)
    results = []

    for _id in union_ids:
        r1 = sim1.get(_id)  # 첫 번째는 반드시 중요
        r2 = sim2.get(_id)

        # 첫 번째 리스트에 없는 문서라면? → 완전히 제외하거나, 약한 패널티를 줘도 됨
        if r1 is None:
            continue  # '주 리스트에 없으면 버린다' 선택지

        rank1 = r1.rank
        rank2 = r2.rank if r2 else default_rank

        rrf_score = w1 / (k + rank1) + w2 / (k + rank2)

        r1.rrf_score = rrf_score
        results.append(r1)

    return sorted(results, key=lambda s: s.rrf_score, reverse=True)


HANJA_RE = re.compile(
    r"["
    r"\u4E00-\u9FFF"  # 기본
    r"\u3400-\u4DBF"  # 확장 A
    r"\uF900-\uFAFF"  # 호환 한자
    r"\U00020000-\U0002A6DF"  # 확장 B
    r"\U0002A700-\U0002B73F"  # 확장 C–D
    r"\U0002B740-\U0002B81F"  # 확장 E
    r"]+"
)


def clean_text(text: str, replace_with: str = "") -> str:
    text = re.sub(r"\([^)]*\)|,", "", text)
    text = HANJA_RE.sub(replace_with, text)
    return text


title_collection = Collecton("title").load()
content_collection = Collecton("content").load()
description_collection = Collecton("description").load()
