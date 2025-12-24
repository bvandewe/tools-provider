"""Namespace query handlers."""

from application.queries.namespace.get_namespace_query import GetNamespaceQuery, GetNamespaceQueryHandler
from application.queries.namespace.get_namespaces_query import GetNamespacesQuery, GetNamespacesQueryHandler
from application.queries.namespace.get_term_query import GetTermQuery, GetTermQueryHandler
from application.queries.namespace.get_terms_query import GetTermsQuery, GetTermsQueryHandler

__all__ = [
    "GetNamespaceQuery",
    "GetNamespaceQueryHandler",
    "GetNamespacesQuery",
    "GetNamespacesQueryHandler",
    "GetTermQuery",
    "GetTermQueryHandler",
    "GetTermsQuery",
    "GetTermsQueryHandler",
]
