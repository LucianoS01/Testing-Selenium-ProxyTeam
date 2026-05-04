"""
pagination.py — Capacidad 1: Paginación hasta 30 resultados en 3 páginas.

Patrón de URL real de MercadoLibre Argentina (verificado manualmente):
  Página 1: https://listado.mercadolibre.com.ar/{slug}
  Página 2: https://listado.mercadolibre.com.ar/{slug}_Desde_49_NoIndex_True
  Página 3: https://listado.mercadolibre.com.ar/{slug}_Desde_97_NoIndex_True

El sitio real usa incrementos de 48 items por página.
En este TP se usa el valor de `results_per_page` (default=10) como paso
configurable para que las pruebas y el entorno de desarrollo sean reproducibles.
El offset 0 → primera página (sin sufijo _Desde_), offset > 0 → _Desde_{offset+1}.
"""

import os
import logging
import urllib.parse
import time

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuración desde entorno
# ---------------------------------------------------------------------------
MAX_PAGES = int(os.getenv("MAX_PAGES", "3"))

# Base del listado de MercadoLibre Argentina
BASE_URL = "https://listado.mercadolibre.com.ar"


# ---------------------------------------------------------------------------
# Construcción de URL por página
# ---------------------------------------------------------------------------

def build_page_url(product: str, offset: int) -> str:
    """Construye la URL de búsqueda de MercadoLibre para un producto y offset dados.

    Args:
        product: Nombre del producto a buscar (ej. "bicicleta rodado 29").
        offset: Número de resultados a saltar (0 = primera página).

    Returns:
        URL completa lista para navegar.

    Ejemplos:
        >>> build_page_url("bicicleta rodado 29", 0)
        'https://listado.mercadolibre.com.ar/bicicleta+rodado+29'
        >>> build_page_url("bicicleta rodado 29", 10)
        'https://listado.mercadolibre.com.ar/bicicleta+rodado+29_Desde_11_NoIndex_True'
    """
    slug = urllib.parse.quote_plus(product)
    if offset == 0:
        return f"{BASE_URL}/{slug}"
    # MercadoLibre usa 1-indexado: offset=10 → _Desde_11_
    return f"{BASE_URL}/{slug}_Desde_{offset + 1}_NoIndex_True"


# ---------------------------------------------------------------------------
# Deduplicación por link
# ---------------------------------------------------------------------------

def deduplicate(results: list[dict]) -> list[dict]:
    """Elimina resultados duplicados basándose en el campo 'link'.

    Los resultados sin link (None o vacío) se incluyen siempre ya que no
    se puede determinar unicidad.

    Args:
        results: Lista de dicts con resultados de scraping.

    Returns:
        Lista sin duplicados, preservando el orden de primera aparición.
    """
    seen: set[str] = set()
    unique: list[dict] = []
    for r in results:
        key = r.get("link")
        if key and key not in seen:
            seen.add(key)
            unique.append(r)
        elif not key:
            unique.append(r)  # sin link: incluir igual, no se puede deduplicar
    logger.info(
        "Deduplicación completada",
        extra={
            "original_count": len(results),
            "unique_count": len(unique),
            "duplicates_removed": len(results) - len(unique)
        }
    )
    return unique


# ---------------------------------------------------------------------------
# Helpers internos usados por scrape_all_pages
# ---------------------------------------------------------------------------

def _load_page_with_retry(driver, url: str) -> None:
    """Navega a `url` y espera a que la página cargue."""
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.by import By
    import dom_selectors as selectors

    driver.get(url)
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, selectors.SELECTOR_RESULT_ITEM)
        )
    )


def _get_result_cards(driver):
    """Retorna las tarjetas de resultado presentes en la página actual."""
    from selenium.webdriver.common.by import By
    import dom_selectors as selectors

    return driver.find_elements(By.CSS_SELECTOR, selectors.SELECTOR_RESULT_ITEM)


def _extract_page_results(driver, cards, product: str, page: int) -> list[dict]:
    """Extrae los campos de cada tarjeta y retorna la lista de resultados."""
    import extractors

    results = []
    browser = driver.capabilities.get("browserName", "unknown")
    for idx, card in enumerate(cards):
        context = {
            "producto": product,
            "browser": browser,
            "resultado_index": (page - 1) * len(cards) + idx,
        }
        try:
            item = {
                "titulo": extractors.extract_titulo(card, context),
                "precio": extractors.extract_precio(card, context),
                "link": extractors.extract_link(card, context),
                "tienda_oficial": extractors.extract_tienda_oficial(card, context),
                "envio_gratis": extractors.extract_envio_gratis(card, context),
                "cuotas_sin_interes": extractors.extract_cuotas(card, context),
            }
            results.append(item)
        except Exception as e:
            logger.error(
                "Resultado descartado por error en extracción",
                extra={
                    "resultado_index": idx,
                    "producto": product,
                    "página": page,
                    "error": str(e)
                },
                exc_info=True,
            )
    return results


# ---------------------------------------------------------------------------
# Función principal de paginación
# ---------------------------------------------------------------------------

def scrape_all_pages(
    driver,
    product: str,
    max_pages: int = 3,
    results_per_page: int = 10,
) -> list[dict]:
    """Scrapea múltiples páginas de resultados de MercadoLibre.

    Navega hasta `max_pages` páginas para el `product` dado, acumulando todos
    los resultados y deteniéndose antes si una página no retorna cards.
    Al finalizar, deduplica por campo 'link'.

    Args:
        driver: Instancia de Selenium WebDriver ya inicializada.
        product: Nombre del producto a buscar.
        max_pages: Número máximo de páginas a recorrer (default=3).
        results_per_page: Items por página para calcular el offset (default=10).

    Returns:
        Lista de dicts con todos los resultados deduplicados.
    """
    all_results: list[dict] = []

    for page in range(1, max_pages + 1):
        offset = (page - 1) * results_per_page
        url = build_page_url(product, offset)
        logger.info(
            "Iniciando scrapeo de página",
            extra={
                "página": page,
                "total_páginas": max_pages,
                "producto": product,
                "offset": offset,
                "url": url
            }
        )
        try:
            _load_page_with_retry(driver, url)
            cards = _get_result_cards(driver)
            if not cards:
                logger.warning(
                    "Página %d sin resultados, deteniendo paginación | producto=%s",
                    page, product,
                )
                break
            page_results = _extract_page_results(driver, cards, product, page)
            all_results.extend(page_results)
            logger.info(
                "Página completada",
                extra={
                    "página": page,
                    "resultados_página": len(page_results),
                    "acumulado_total": len(all_results),
                    "producto": product
                }
            )
            time.sleep(3)
        except Exception as e:
            logger.error(
                "Fallo en página %d | producto=%s | %s",
                page, product, e,
                exc_info=True,
            )
            break

    return deduplicate(all_results)
