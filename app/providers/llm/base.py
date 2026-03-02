from abc import ABC, abstractmethod


class LLMProvider(ABC):

    @abstractmethod
    def generate_question_set(self, job_description: str, resume: str):
        pass
