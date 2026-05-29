import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    bot_token: str
    user_llm_workers: int
    nlp_llm_workers: int
    llm_queue_size: int


def load_config() -> Config:
    bot_token = os.getenv("BOT_TOKEN", "8254653713:AAErzikwSYYLQUthSx1s5DmBsfEmXSQTwKQ").strip()
    if not bot_token:
        raise RuntimeError("BOT_TOKEN is not set")
    user_llm_workers = int(os.getenv("USER_LLM_WORKERS", "2").strip() or "2")
    nlp_llm_workers = int(os.getenv("NLP_LLM_WORKERS", "1").strip() or "1")
    llm_queue_size = int(os.getenv("LLM_QUEUE_SIZE", "200").strip() or "200")
    if user_llm_workers < 1:
        user_llm_workers = 1
    if nlp_llm_workers < 1:
        nlp_llm_workers = 1
    if llm_queue_size < 10:
        llm_queue_size = 10
    return Config(bot_token=bot_token, user_llm_workers=user_llm_workers, nlp_llm_workers=nlp_llm_workers, llm_queue_size=llm_queue_size)
