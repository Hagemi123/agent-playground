from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseAdapter(ABC):
    """Abstract base class for all web and social media platform adapters."""
    
    @abstractmethod
    def start(self):
        pass

    @abstractmethod
    def close(self):
        pass

    @abstractmethod
    def check_login_status(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def login(self, **kwargs) -> Dict[str, Any]:
        pass
