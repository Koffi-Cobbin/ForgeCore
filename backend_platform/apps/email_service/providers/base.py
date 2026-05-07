from abc import ABC, abstractmethod


class BaseEmailProvider(ABC):
    @abstractmethod
    def send(self, to_email, subject, body_html, body_text=None, from_email=None, **kwargs):
        pass

    def get_provider_name(self):
        return self.__class__.__name__.lower().replace('emailprovider', '')
