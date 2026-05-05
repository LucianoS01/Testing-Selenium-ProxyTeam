"""
scraper.py — Orquestador principal del scraper de MercadoLibre Argentina.

Hit #8: integra paginación (hasta 30 resultados en 3 páginas),
estadísticas de precios por producto y escritura opcional a Postgres.

Variables de entorno relevantes:
  BROWSER    — "chrome" | "firefox" (default: "chrome")
  HEADLESS   — "true" | "false" (default: "false")
  PRODUCTS   — lista de productos separados por newline
  MAX_PAGES  — páginas a paginar por producto (default: "3")
  POSTGRES_HOST — si está definido, activa la escritura a Postgres
  DELAY_BETWEEN_PRODUCTS — segundos entre productos (default: "5")
"""

import os
import json
import logging
import re
import time
from pathlib import Path

from selenium.webdriver.support.ui import WebDriverWait

from logging_setup import setup_logging
from driver_factory import build_driver
from pagination import scrape_all_pages, MAX_PAGES
from stats import compute_stats, print_stats_table, save_stats
from db import run_migrations, save_results, postgres_enabled

OUTPUT_DIR = Path(__file__).parent / "output"

logger = logging.getLogger(__name__)

DELAY_BETWEEN_PRODUCTS = int(os.getenv("DELAY_BETWEEN_PRODUCTS", "5"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def slug(text: str) -> str:
    """Convierte un texto en un nombre de archivo seguro (snake_case ASCII)."""
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def get_products() -> list[str]:
    """Retorna la lista de productos desde la variable de entorno o un default."""
    env_products = os.getenv("PRODUCTS", "")
    if env_products.strip():
        return [p.strip() for p in env_products.splitlines() if p.strip()]
    return [
        "bicicleta rodado 29",
        "iPhone 16 Pro Max",
        "GeForce RTX 5090",
    ]


def save_json(results: list[dict], product: str) -> None:
    """Persiste los resultados de un producto en output/<slug>.json."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    filename = slug(product)
    out_path = OUTPUT_DIR / f"{filename}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    logger.info(
        "JSON escrito exitosamente",
        extra={"output_path": str(out_path), "product": product}
    )


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------

def main() -> None:
    setup_logging()
    products = get_products()
    browser = os.getenv("BROWSER", "chrome")
    headless = os.getenv("HEADLESS", "false").lower() == "true"
    max_pages = MAX_PAGES

    logger.info(
        "Iniciando scraper",
        extra={
            "productos_count": len(products),
            "browser": browser,
            "headless": headless,
            "max_pages": max_pages,
            "delay": DELAY_BETWEEN_PRODUCTS,
        },
    )

    # Ejecutar migrations de Postgres (solo si está habilitado)
    if postgres_enabled():
        logger.info("Postgres habilitado — ejecutando migrations")
        run_migrations()

    OUTPUT_DIR.mkdir(exist_ok=True)
    driver = build_driver(browser=browser, headless=headless)

    all_stats = []

    try:
        for idx, product in enumerate(products):
            logger.info("Procesando producto", extra={"producto": product})
            results = scrape_all_pages(
                driver, product, max_pages=max_pages, results_per_page=10
            )

            # Persistir JSON local
            if results:
                save_json(results, product)
            else:
                logger.warning(
                    "Sin resultados para el producto, no se escribe JSON",
                    extra={"producto": product}
                )

            # Persistir en Postgres (opcional)
            if postgres_enabled():
                save_results(results, product, browser)

            # Calcular estadísticas para la tabla resumen
            stats = compute_stats(results, product)
            all_stats.append(stats)

            # Pausa entre productos para evitar throttling (excepto el último)
            if idx < len(products) - 1:
                logger.info(
                    "Esperando antes del siguiente producto",
                    extra={"delay_seconds": DELAY_BETWEEN_PRODUCTS}
                )
                time.sleep(DELAY_BETWEEN_PRODUCTS)

    finally:
        driver.quit()
        logger.info("Driver cerrado correctamente")

    # Imprimir tabla de resumen y guardar stats.json
    print_stats_table(all_stats)
    save_stats(all_stats, output_dir=str(OUTPUT_DIR))


if __name__ == "__main__":
    main()