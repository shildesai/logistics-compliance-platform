"""Import external control-test catalogues into the Compliance Control Graph.

See docs/CONTROL_IMPORT_MAPPING.md for the field-by-field mapping and the
reasoning behind what is deliberately not imported.
"""

from app.services.catalogue_import.importer import (
    CatalogueImporter,
    CatalogueImportError,
    ImportReport,
    import_catalogue,
)
from app.services.catalogue_import.parsing import (
    SourceCatalogue,
    ValidationIssue,
    load_catalogue,
)

__all__ = [
    "CatalogueImportError",
    "CatalogueImporter",
    "ImportReport",
    "SourceCatalogue",
    "ValidationIssue",
    "import_catalogue",
    "load_catalogue",
]
