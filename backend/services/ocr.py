"""manga-ocr wrapper, loaded lazily because the import and model are heavy."""
_ocr = None


def get_ocr():
    global _ocr
    if _ocr is None:
        from manga_ocr import MangaOcr

        _ocr = MangaOcr()
    return _ocr
