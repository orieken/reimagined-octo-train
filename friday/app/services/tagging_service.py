from typing import List, Dict
from app.models.domain import Feature, Scenario, Step


class TaggingService:
    def __init__(self):
        self.keywords = {
            "auth": ["login", "signup", "authentication", "password"],
            "critical": ["critical", "@critical"],
            "slow": [],
            "flaky": ["flaky", "intermittent"],
        }

    def tag_feature(self, feature: Feature) -> List[str]:
        tags = set(tag.lower() for tag in feature.tags or [])
        name = feature.name.lower()
        desc = (feature.description or "").lower()

        for label, keywords in self.keywords.items():
            if any(k in name or k in desc for k in keywords):
                tags.add(label)

        return list(tags)

    def tag_scenario(self, scenario: Scenario) -> List[str]:
        tags = set(tag.lower() for tag in scenario.tags or [])
        name = scenario.name.lower()

        if "flaky" in name or scenario.is_flaky:
            tags.add("flaky")

        if "login" in name:
            tags.add("auth")

        if scenario.duration and scenario.duration > 5.0:
            tags.add("slow")

        return list(tags)

    def tag_step(self, step: Step) -> List[str]:
        tags = []

        if step.status == "FAILED":
            tags.append("error")

        if "assert" in (step.name or "").lower():
            tags.append("assertion")

        return tags
