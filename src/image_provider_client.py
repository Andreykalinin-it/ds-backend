import requests
import logging


class ImageProviderClient:
    """Клиент для получения изображений от внешнего сервиса."""

    def __init__(self, host: str, timeout: int = 5):
        self.host = host
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)

    def get_image(self, image_id: int):
        url = f"{self.host}/images/{image_id}"
        self.logger.info(f"Fetching image with ID {image_id} from {url}")
        try:
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            self.logger.info(f"Successfully fetched image with ID {image_id}")
            return response.content, None, None
        except requests.Timeout:
            self.logger.error(f"Timeout when fetching image ID {image_id}")
            return None, {'error': 'external service timeout'}, 504
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                self.logger.warning(f"Image with ID {image_id} not found")
                return None, {'error': f'image with ID {image_id} not found'}, 404
            else:
                self.logger.error(f"HTTP error when fetching image ID {image_id}: {e}")
                return None, {'error': 'external service error'}, 502 
        except requests.RequestException as e:
            self.logger.error(f"Error fetching image ID {image_id}: {e}")
            return None, {'error': 'external service unavailable'}, 503
        except Exception as e:
            self.logger.error(f"Unexpected error processing image ID {image_id}: {e}")
            return None, {'error': 'internal server error'}, 500