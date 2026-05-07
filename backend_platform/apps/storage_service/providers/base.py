from abc import ABC, abstractmethod


class BaseStorageProvider(ABC):
    @abstractmethod
    def upload(self, file_obj, file_key, content_type=None, **kwargs):
        pass

    @abstractmethod
    def delete(self, file_key, **kwargs):
        pass

    @abstractmethod
    def generate_signed_url(self, file_key, expires_in=3600, **kwargs):
        pass

    @abstractmethod
    def get_url(self, file_key, **kwargs):
        pass

    def get_provider_name(self):
        return self.__class__.__name__.lower().replace('storageprovider', '')
