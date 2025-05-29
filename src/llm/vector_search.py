from dataclasses import dataclass, field
from typing import Optional
import numpy as np
import os
from pathlib import Path
from openai import OpenAI
import dill
from src.llm import claude_3_7 as claude
from src.llm.prompt_templates import search_result_filter
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
    score: float = 0
    rank: int = None  # 삭제
    rrf_score: float = 0  # 삭제
    docs: str = ""  # 삭제
    collection_name: str = ""  # 추가


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

        self.file_path = str(Path("data") / "database" / f"{file_name}.dill")
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
        similarities: list[Similarity] = []
        for doc_embedding in self.index.values():
            score = np.dot(query_embeddings, doc_embedding.embeddings) / (
                np.linalg.norm(query_embeddings)
                * np.linalg.norm(doc_embedding.embeddings)
            )
            if score < cutoff:
                continue
            similarities.append(
                Similarity(
                    id=doc_embedding.id,
                    doc=doc_embedding.doc,
                    score=float(score),
                )
            )

        similarities = sorted(similarities, key=lambda x: x.score, reverse=True)[:top_k]
        return similarities

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

from collections import defaultdict
from typing import Dict, List, Optional

# 이미 선언되어 있다고 가정
# @dataclass(slots=True)
# class Similarity:
#     id: str
#     doc: str
#     score: float
#     rank: int = None
#     rrf_score: float = None
#     docs: str = ""          # 여러 시스템 문서 병합용(필요 시)


def get_rrf_2(
    sim_dicts: list[Dict[str, Similarity]],
    k: int = 60,
    weights: list[float] | None = None,
) -> List["Similarity"]:

    n_systems = len(sim_dicts)
    if n_systems == 0:
        return []

    # 모든 id 집합
    union_ids = set().union(*(d.keys() for d in sim_dicts))

    results: List["Similarity"] = []

    for _id in union_ids:
        rrf_score = 0.0
        merged_docs: List[str] = []
        representative_obj: Optional["Similarity"] = None

        # 각 시스템별 정보 누적
        for weight, sim in zip(weights, sim_dicts):
            obj = sim.get(_id)
            if obj is None:
                continue

            if obj.rank is not None:
                rrf_score += weight / (k + obj.rank)

            merged_docs.append(obj.doc)
            if representative_obj is None:
                representative_obj = obj  # 첫 등장 객체를 대표로

        # 대표 객체는 최소 한 번 존재
        rep = representative_obj
        rep.docs = "\n".join(merged_docs).strip()
        rep.rrf_score = rrf_score
        results.append(rep)

    # RRF 점수로 내림차순 정렬
    return sorted(results, key=lambda o: o.rrf_score, reverse=True)


def get_rrf_3(
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


def get_rrf(
    ranked_lists: list[list[Similarity]],
    k: int = 60,
    weights: list[float] | None = None,
) -> list[Similarity]:

    weights = weights or [1 / len(ranked_lists)] * len(ranked_lists)
    # rrf_scores = defaultdict(float)
    rrf_sim_dict: dict[str, Similarity] = {}

    for w, ranked in zip(weights, ranked_lists):
        for rank, sim in enumerate(ranked, start=1):
            score = w / (k + rank)
            if sim.id in rrf_sim_dict:
                rrf_sim_dict[sim.id].score += score
                rrf_sim_dict[sim.id].doc += "\n" + sim.doc
            else:
                rrf_sim = Similarity(
                    id=sim.id,
                    doc=sim.doc,
                    score=score,
                )
                rrf_sim_dict[sim.id] = rrf_sim

    return sorted(rrf_sim_dict.values(), key=lambda x: x.score, reverse=True)


def filter_results(similarities: list[Similarity], query: str):

    sim_dict: dict[str, Similarity] = {}
    for sim in similarities:
        if sim.id in sim_dict:
            sim_dict[sim.id].doc += "\n" + sim.doc
        else:
            sim_dict[sim.id] = sim

    # rrf와 제목의 id가 겹치면 엎어질 수 있으므로 rrf와 마찬가지로 loop 돌면서 새로 구성
    # search_doc_results = {sim.id: sim.doc for sim in similarities}
    search_doc_results = {sim.id: sim.doc for sim in sim_dict.values()}
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
