import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List
from src.grace.models import DevelopmentPlan, Phase, Wave


def _text(elem, default: str = "") -> str:
    return elem.text.strip() if elem.text else default


def _list(elem, tag: str) -> List[str]:
    return [e.text.strip() for e in elem.findall(tag) if e.text]


def _collect_scope(elem, tag: str) -> List[str]:
    files = _list(elem, tag)
    for slice_el in elem.findall("Slice"):
        files.extend(_list(slice_el, tag))
    return files


def _collect_modules(elem) -> List[str]:
    modules = _list(elem, "Modules/Module")
    for ref in elem.findall("ModuleRef"):
        mod_id = ref.get("id", "")
        if mod_id:
            modules.append(mod_id)
    for slice_el in elem.findall("Slice"):
        for ref in slice_el.findall("ModuleRef"):
            mod_id = ref.get("id", "")
            if mod_id:
                modules.append(mod_id)
    return modules


def _collect_verification(elem) -> List[str]:
    verif = _list(elem, "Verification/Command")
    for slice_el in elem.findall("Slice"):
        verif.extend(_list(slice_el, "Verification/Command"))
    return verif


def load_development_plan(path: str) -> DevelopmentPlan:
    tree = ET.parse(Path(path))
    root = tree.getroot()

    if root.tag != "DevelopmentPlan":
        raise ValueError("Root element must be <DevelopmentPlan>")

    phases: List[Phase] = []
    for phase_el in root.findall("Phase"):
        phase_id = phase_el.get("id", "")
        phase_goal = _text(phase_el.find("Goal"))

        waves: List[Wave] = []
        for wave_el in phase_el.findall("Wave"):
            wave_id = wave_el.get("id", "")
            wave_goal = _text(wave_el.find("Goal"))

            modules = _collect_modules(wave_el)
            allowed_write_scope = _collect_scope(wave_el, "AllowedWriteScope/File")
            frozen_scope = _collect_scope(wave_el, "FrozenScope/File")
            must_preserve = _list(wave_el, "MustPreserve/Item")
            verification = _collect_verification(wave_el)

            waves.append(Wave(
                id=wave_id,
                goal=wave_goal,
                modules=modules,
                allowed_write_scope=allowed_write_scope,
                frozen_scope=frozen_scope,
                must_preserve=must_preserve,
                verification=verification,
            ))

        phases.append(Phase(id=phase_id, goal=phase_goal, waves=waves))

    return DevelopmentPlan(phases=phases)

