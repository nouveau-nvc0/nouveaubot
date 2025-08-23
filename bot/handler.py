from abc import ABC, abstractmethod

class Handler(ABC):
    @property
    @abstractmethod
    def aliases(self) -> list[str]:
        raise NotImplementedError()
    
    @property
    @abstractmethod
    def description(self) -> str:
        raise NotImplementedError()
