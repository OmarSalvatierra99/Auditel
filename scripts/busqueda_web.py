import requests
from bs4 import BeautifulSoup
import urllib.parse

def buscar_en_periodico_tlaxcala(query):
    """
    Busca en el Periódico Oficial de Tlaxcala.
    Devuelve la URL de búsqueda.
    """
    search_encoded = urllib.parse.quote_plus(query)
    url = f"https://periodico.tlaxcala.gob.mx/index.php/buscar?texto={search_encoded}"
    return url

def buscar_en_dof(query):
    """
    Simula una búsqueda en el Diario Oficial de la Federación (DOF) usando su motor de búsqueda.
    Devuelve una URL de Google que busca dentro del sitio dof.gob.mx
    """
    search_encoded = urllib.parse.quote_plus(f"site:dof.gob.mx {query}")
    url = f"https://www.google.com/search?q={search_encoded}"
    return url

if __name__ == '__main__':
    # Ejemplo de uso
    consulta = "Ley de ingresos Tlaxcala"
    enlace_tlaxcala = buscar_en_periodico_tlaxcala(consulta)
    enlace_dof = buscar_en_dof(consulta)
    print(f"Búsqueda en Periódico de Tlaxcala: {enlace_tlaxcala}")
    print(f"Búsqueda en el Diario Oficial de la Federación: {enlace_dof}")
