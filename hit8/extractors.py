import logging
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import dom_selectors as selectors

logger = logging.getLogger(__name__)

def extract_titulo(element, context: dict):
    try:
        try:
            return element.find_element(By.CSS_SELECTOR, selectors.SELECTOR_TITULO).text.strip()
        except NoSuchElementException:
            return element.find_element(By.CSS_SELECTOR, selectors.SELECTOR_LINK).text.strip()
    except Exception as e:
        logger.warning(
            "Campo ausente o error: titulo",
            extra={
                "producto": context.get("producto"),
                "browser": context.get("browser"),
                "selector": selectors.SELECTOR_TITULO,
                "error": type(e).__name__
            }
        )
        return None

def extract_precio(element, context: dict):
    try:
        precio_str = element.find_element(By.CSS_SELECTOR, selectors.SELECTOR_PRECIO).text
        precio_str = precio_str.replace(".", "").replace(",", ".")
        return float(precio_str)
    except Exception as e:
        logger.warning(
            "Campo ausente o error: precio",
            extra={
                "producto": context.get("producto"),
                "browser": context.get("browser"),
                "selector": selectors.SELECTOR_PRECIO,
                "error": type(e).__name__
            }
        )
        return None

def extract_link(element, context: dict):
    try:
        url = element.find_element(By.CSS_SELECTOR, selectors.SELECTOR_LINK).get_attribute("href")
        if not url or not url.startswith("http"):
            return None
        return url
    except Exception as e:
        logger.warning(
            "Campo ausente o error: link",
            extra={
                "producto": context.get("producto"),
                "browser": context.get("browser"),
                "selector": selectors.SELECTOR_LINK,
                "error": type(e).__name__
            }
        )
        return None

def extract_tienda_oficial(element, context: dict):
    try:
        text = element.find_element(By.CSS_SELECTOR, selectors.SELECTOR_TIENDA_OFICIAL).text.strip()
        if text.lower().startswith("por "):
            return text[4:] or None
        return text or None
    except Exception:
        logger.warning(
            "Campo ausente: tienda_oficial",
            extra={
                "producto": context.get("producto"),
                "browser": context.get("browser"),
                "selector": selectors.SELECTOR_TIENDA_OFICIAL
            }
        )
        return None

def extract_envio_gratis(element, context: dict):
    try:
        element.find_element(By.CSS_SELECTOR, selectors.SELECTOR_ENVIO_GRATIS)
        return True
    except Exception:
        # Envio gratis es usualmente False si no esta, no lo tratamos como error pero devolvemos False
        # Igual dejamos un debug log por si acaso, pero warning capaz es mucho, aunque el prompt
        # dice "Cada función en extractors.py debe cumplir este contrato explicito: [...] loggear en nivel WARNING"
        # Así que loggeamos warning.
        logger.warning(
            "Campo ausente: envio_gratis",
            extra={
                "producto": context.get("producto"),
                "browser": context.get("browser"),
                "selector": selectors.SELECTOR_ENVIO_GRATIS
            }
        )
        return False

def extract_cuotas(element, context: dict):
    try:
        return element.find_element(By.CSS_SELECTOR, selectors.SELECTOR_CUOTAS).text.strip() or None
    except Exception:
        logger.warning(
            "Campo ausente: cuotas_sin_interes",
            extra={
                "producto": context.get("producto"),
                "browser": context.get("browser"),
                "selector": selectors.SELECTOR_CUOTAS
            }
        )
        return None
