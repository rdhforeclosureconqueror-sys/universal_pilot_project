from app.services.platform_knowledge_service import PlatformKnowledgeService


class _Query:
    def order_by(self, *_args, **_kwargs):
        return self

    def all(self):
        return []


class _DB:
    def query(self, _model):
        return _Query()


def test_platform_knowledge_service_core_methods():
    service = PlatformKnowledgeService(_DB())

    overview = service.get_platform_overview()
    capabilities = service.get_capability_summary()
    architecture = service.get_architecture_summary()
    modules = service.get_module_descriptions()
    domain = service.get_domain_capabilities("foreclosure_intelligence")

    assert "overview" in overview
    assert "domains" in capabilities
    assert "architecture_report" in architecture
    assert isinstance(modules, list)
    assert domain["domain"] == "foreclosure_intelligence"
