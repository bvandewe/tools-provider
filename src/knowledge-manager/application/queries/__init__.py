"""Query handlers for Knowledge Manager."""

from application.queries.namespace.get_namespace_query import GetNamespaceQuery, GetNamespaceQueryHandler
from application.queries.namespace.get_namespaces_query import GetNamespacesQuery, GetNamespacesQueryHandler
from application.queries.namespace.get_term_query import GetTermQuery, GetTermQueryHandler
from application.queries.namespace.get_terms_query import GetTermsQuery, GetTermsQueryHandler

__all__ = [
    # Namespace queries
    "GetNamespaceQuery",
    "GetNamespaceQueryHandler",
    "GetNamespacesQuery",
    "GetNamespacesQueryHandler",
    # Term queries
    "GetTermQuery",
    "GetTermQueryHandler",
    "GetTermsQuery",
    "GetTermsQueryHandler",
]
