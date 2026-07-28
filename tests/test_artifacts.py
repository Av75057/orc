import xml.etree.ElementTree as ET
from pathlib import Path
import pytest
from src.grace.models import parse_development_plan

DOCS = Path(__file__).resolve().parent.parent / "docs"


class TestDevelopmentPlan:
    @pytest.fixture(autouse=True)
    def _load(self):
        self.plan = parse_development_plan(DOCS / "development-plan.xml")

    def test_five_phases(self):
        assert len(self.plan.phases) == 5

    def test_phase_ids(self):
        assert [p.id for p in self.plan.phases] == ["PHASE-1", "PHASE-2", "PHASE-3", "PHASE-4", "PHASE-5"]

    def test_wave_ids(self):
        all_waves = [w.id for p in self.plan.phases for w in p.waves]
        assert all_waves == ["WAVE-1", "WAVE-2", "WAVE-3", "WAVE-4", "WAVE-5"]

    def test_every_wave_has_goal(self):
        for p in self.plan.phases:
            for w in p.waves:
                assert w.goal, f"{w.id} empty goal"

    def test_every_wave_has_scope(self):
        for p in self.plan.phases:
            for w in p.waves:
                assert w.allowed_write_scope, f"{w.id} empty scope"

    def test_every_wave_has_acceptance_criteria(self):
        for p in self.plan.phases:
            for w in p.waves:
                assert w.acceptance_criteria, f"{w.id} no acceptance criteria"

    def test_every_wave_has_use_case_refs(self):
        for p in self.plan.phases:
            for w in p.waves:
                assert w.use_case_refs, f"{w.id} no use case refs"

    def test_every_phase_has_gate_criteria(self):
        for p in self.plan.phases:
            assert p.gate_criteria, f"{p.id} no gate criteria"

    def test_use_case_refs_valid(self):
        valid = {"UC-01", "UC-02", "UC-03", "UC-04", "UC-05", "UC-06"}
        for p in self.plan.phases:
            for w in p.waves:
                for ref in w.use_case_refs:
                    assert ref in valid, f"{w.id} references unknown {ref}"

    def test_no_write_overlap(self):
        all_scopes = [(w.id, set(w.allowed_write_scope)) for p in self.plan.phases for w in p.waves]
        for i, (id_a, sa) in enumerate(all_scopes):
            for id_b, sb in all_scopes[i + 1:]:
                overlap = sa & sb
                non_test = {f for f in overlap if not f.startswith("tests/")}
                assert not non_test, f"{id_a} <-> {id_b} overlap: {non_test}"


class TestVerificationMatrix:
    @pytest.fixture(autouse=True)
    def _load(self):
        self.path = DOCS / "verification-matrix.md"
        self.content = self.path.read_text(encoding="utf-8")

    def test_not_empty(self):
        assert len(self.content.strip()) > 0

    def test_has_use_cases(self):
        for i in range(1, 7):
            assert f"UC-{i:02d}" in self.content

    def test_has_invariants(self):
        for i in range(1, 7):
            assert f"INV-{i:02d}" in self.content

    def test_has_phase_gates(self):
        for i in range(1, 6):
            assert f"PHASE-{i}" in self.content

    def test_has_trace_assertions(self):
        assert "VM-T01" in self.content
        assert "VM-T10" in self.content


class TestKnowledgeGraph:
    @pytest.fixture(autouse=True)
    def _load(self):
        self.tree = ET.parse(str(DOCS / "knowledge-graph.xml"))
        self.root = self.tree.getroot()

    def test_has_modules(self):
        modules = self.root.findall(".//Module")
        assert len(modules) >= 6

    def test_module_ids(self):
        ids = {m.get("id") for m in self.root.findall(".//Module")}
        assert {"M-MODELS", "M-EVENTBUS", "M-SENSORS", "M-ACTUATORS", "M-CONTROLLER", "M-MAIN"}.issubset(ids)

    def test_has_use_cases(self):
        ucs = self.root.findall(".//UseCase")
        assert len(ucs) == 6

    def test_has_invariants(self):
        assert len(self.root.findall(".//Invariant")) >= 6

    def test_has_cross_links(self):
        links = self.root.findall(".//Link")
        assert len(links) >= 5

    def test_has_defects(self):
        assert len(self.root.findall(".//Defect")) >= 1


class TestCrossArtifactConsistency:
    def test_plan_ucs_in_kg(self):
        plan = parse_development_plan(DOCS / "development-plan.xml")
        kg = ET.parse(str(DOCS / "knowledge-graph.xml"))
        kg_ucs = {uc.get("id") for uc in kg.getroot().findall(".//UseCase")}
        for p in plan.phases:
            for w in p.waves:
                for ref in w.use_case_refs:
                    assert ref in kg_ucs, f"{w.id} refs {ref} not in KG"

    def test_plan_modules_in_kg(self):
        plan = parse_development_plan(DOCS / "development-plan.xml")
        kg = ET.parse(str(DOCS / "knowledge-graph.xml"))
        kg_mods = {m.get("id") for m in kg.getroot().findall(".//Module")}
        for p in plan.phases:
            for w in p.waves:
                for mod in w.modules:
                    assert mod in kg_mods, f"{w.id} refs module {mod} not in KG"

    def test_matrix_covers_all_ucs(self):
        content = (DOCS / "verification-matrix.md").read_text()
        for i in range(1, 7):
            assert f"UC-{i:02d}" in content, f"matrix missing UC-{i:02d}"

    def test_matrix_covers_all_invs(self):
        content = (DOCS / "verification-matrix.md").read_text()
        for i in range(1, 7):
            assert f"INV-{i:02d}" in content, f"matrix missing INV-{i:02d}"
