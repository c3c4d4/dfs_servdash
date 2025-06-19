import re
import pandas as pd
from typing import Optional, List

def extrair_estado(endereco: str) -> Optional[str]:
    """Extracts the state (UF) from the address string."""
    match = re.search(r",\s*([A-Z]{2}),\s*BR", str(endereco))
    return match.group(1) if match else None

def extrair_pais(endereco: str) -> Optional[str]:
    """Extracts the country code from the address string."""
    match = re.findall(r",\s*([A-Z]{2})\s*$", str(endereco).strip())
    return match[-1] if match else None

def extrair_tags(texto: str) -> List[str]:
    """Extracts tags from the summary text."""
    if pd.isna(texto):
        return []
    tags = re.findall(r"\[(.*?)\]", texto)
    tags = [tag.strip().upper() for tag in tags]
    return list(set(tags)) if tags else ["Sem Tags"] 