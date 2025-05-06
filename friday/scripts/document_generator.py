"""
Document Generator for Friday CLI

This module generates realistic document content for testing the document processing
endpoint in the Friday platform.
"""

import random
import lorem
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

# Document types for generation
DOCUMENT_TYPES = [
    "requirements", "specification", "design", "architecture",
    "user_guide", "api_docs", "release_notes", "internal_memo",
    "meeting_notes", "test_plan", "postmortem", "runbook",
    "onboarding", "troubleshooting_guide"
]

# Document formats
DOCUMENT_FORMATS = ["markdown", "plain_text", "structured"]

# Teams that might create documents
TEAMS = [
    "engineering", "product", "design", "qa", "devops",
    "security", "data_science", "support", "documentation"
]

# Templates for document types
DOCUMENT_TEMPLATES = {
    "requirements": [
        "# {project} Requirements Document\n\n## Overview\n\n{overview}\n\n## Functional Requirements\n\n{requirements}\n\n## Non-Functional Requirements\n\n{non_functional}\n\n## Constraints\n\n{constraints}",
        "# Requirements Specification\n\n## Project: {project}\n\n{overview}\n\n## User Stories\n\n{requirements}\n\n## Acceptance Criteria\n\n{acceptance}\n\n## Technical Constraints\n\n{constraints}"
    ],
    "design": [
        "# {project} Design Document\n\n## Overview\n\n{overview}\n\n## Architecture\n\n{architecture}\n\n## Components\n\n{components}\n\n## Interfaces\n\n{interfaces}",
        "# Design Specification\n\n## System: {project}\n\n{overview}\n\n## Design Principles\n\n{principles}\n\n## Implementation Details\n\n{details}\n\n## Future Considerations\n\n{future}"
    ],
    "meeting_notes": [
        "# Meeting Notes: {topic}\n\n**Date**: {date}\n**Attendees**: {attendees}\n\n## Agenda\n\n{agenda}\n\n## Discussion\n\n{discussion}\n\n## Action Items\n\n{actions}",
        "# {team} Sync Meeting\n\n**When**: {date}\n**Who**: {attendees}\n\n## Topics Covered\n\n{agenda}\n\n## Key Decisions\n\n{decisions}\n\n## Follow-ups\n\n{actions}"
    ],
    "release_notes": [
        "# {project} v{version} Release Notes\n\n**Release Date**: {date}\n\n## New Features\n\n{features}\n\n## Bug Fixes\n\n{bugs}\n\n## Known Issues\n\n{issues}",
        "# Release {version} - {project}\n\n**Date**: {date}\n\n## What's New\n\n{features}\n\n## Improvements\n\n{improvements}\n\n## Fixed Issues\n\n{bugs}\n\n## Upgrade Notes\n\n{notes}"
    ],
    "api_docs": [
        "# {project} API Documentation\n\n## Overview\n\n{overview}\n\n## Authentication\n\n{auth}\n\n## Endpoints\n\n{endpoints}\n\n## Response Codes\n\n{codes}",
        "# API Reference: {project}\n\n{overview}\n\n## Getting Started\n\n{getting_started}\n\n## Resources\n\n{resources}\n\n## Error Handling\n\n{errors}"
    ]
}


class DocumentGenerator:
    """
    Generates realistic document content for testing document processing.
    """

    def __init__(self,
                 type_weights: Optional[Dict[str, float]] = None,
                 format_weights: Optional[Dict[str, float]] = None):
        """
        Initialize the document generator.

        Args:
            type_weights: Optional weights for document types
            format_weights: Optional weights for document formats
        """
        self.type_weights = type_weights or {}
        self.format_weights = format_weights or {}

    def generate_document(self,
                          doc_type: Optional[str] = None,
                          doc_format: Optional[str] = None,
                          project: Optional[str] = None,
                          team: Optional[str] = None,
                          length: Optional[str] = None,
                          timestamp: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Generate a document with the specified parameters.

        Args:
            doc_type: Type of document to generate
            doc_format: Format of the document
            project: Project the document relates to
            team: Team that created the document
            length: Desired length (short, medium, long)
            timestamp: Document timestamp

        Returns:
            Document object with text and metadata
        """
        # Set defaults if not provided
        if not doc_type:
            doc_type = self._weighted_choice(DOCUMENT_TYPES, self.type_weights)

        if not doc_format:
            doc_format = self._weighted_choice(DOCUMENT_FORMATS, self.format_weights)

        if not project:
            project = f"project-{random.randint(1, 10)}"

        if not team:
            team = random.choice(TEAMS)

        if not length:
            length = random.choice(["short", "medium", "long"])

        if not timestamp:
            timestamp = datetime.now()

        # Generate document content
        text, metadata = self._generate_content(doc_type, doc_format, project, team, length)

        # Build the document object
        document = {
            "text": text,
            "metadata": {
                "id": str(uuid.uuid4()),
                "type": doc_type,
                "format": doc_format,
                "project": project,
                "team": team,
                "created_at": timestamp.isoformat() + "Z",
                "updated_at": timestamp.isoformat() + "Z",
                "version": f"1.0.{random.randint(0, 20)}",
                "tags": self._generate_tags(doc_type, project, team),
                **metadata
            }
        }

        return document

    def _weighted_choice(self, items: List[str], weights: Dict[str, float]) -> str:
        """
        Make a weighted random choice from a list of items.

        Args:
            items: List of items to choose from
            weights: Dictionary mapping items to weights

        Returns:
            Randomly selected item
        """
        # If weights are provided for some items, use them
        if weights:
            # Filter to valid items and their weights
            valid_weights = {k: v for k, v in weights.items() if k in items}

            if valid_weights:
                # Only use weights for items that have them
                weighted_items = []
                weighted_values = []

                for item in items:
                    if item in valid_weights:
                        weighted_items.append(item)
                        weighted_values.append(valid_weights[item])

                if weighted_items:
                    return random.choices(weighted_items, weights=weighted_values, k=1)[0]

        # Default to uniform random selection
        return random.choice(items)

    def _generate_content(self,
                          doc_type: str,
                          doc_format: str,
                          project: str,
                          team: str,
                          length: str) -> Tuple[str, Dict[str, Any]]:
        """
        Generate content based on document type and format.

        Args:
            doc_type: Type of document
            doc_format: Format of the document
            project: Project name
            team: Team name
            length: Content length

        Returns:
            Tuple of (text, additional_metadata)
        """
        # Determine content length in paragraphs
        if length == "short":
            paragraphs = random.randint(3, 7)
        elif length == "medium":
            paragraphs = random.randint(8, 15)
        else:  # long
            paragraphs = random.randint(16, 30)

        metadata = {}

        # Use templates for structured content when available
        if doc_format in ["markdown", "structured"] and doc_type in DOCUMENT_TEMPLATES:
            template = random.choice(DOCUMENT_TEMPLATES[doc_type])

            # Common template variables
            template_vars = {
                "project": project,
                "date": datetime.now().strftime("%Y-%m-%d"),
                "team": team,
                "version": f"{random.randint(1, 5)}.{random.randint(0, 9)}.{random.randint(0, 20)}"
            }

            # Type-specific template variables
            if doc_type == "requirements":
                template_vars.update({
                    "overview": lorem.paragraph(),
                    "requirements": "\n".join([f"- {lorem.sentence()}" for _ in range(random.randint(5, 12))]),
                    "non_functional": "\n".join([f"- {lorem.sentence()}" for _ in range(random.randint(3, 8))]),
                    "constraints": "\n".join([f"- {lorem.sentence()}" for _ in range(random.randint(2, 6))]),
                    "acceptance": "\n".join([f"- {lorem.sentence()}" for _ in range(random.randint(4, 10))])
                })
                metadata["priority"] = random.choice(["high", "medium", "low"])

            elif doc_type == "design":
                template_vars.update({
                    "overview": lorem.paragraph(),
                    "architecture": lorem.paragraph(),
                    "components": "\n".join([f"### {self._generate_component_name()}\n{lorem.paragraph()}" for _ in
                                             range(random.randint(3, 7))]),
                    "interfaces": "\n".join([f"### {self._generate_interface_name()}\n{lorem.paragraph()}" for _ in
                                             range(random.randint(2, 5))]),
                    "principles": "\n".join([f"- {lorem.sentence()}" for _ in range(random.randint(3, 7))]),
                    "details": lorem.paragraph() + "\n\n" + lorem.paragraph(),
                    "future": "\n".join([f"- {lorem.sentence()}" for _ in range(random.randint(2, 6))])
                })
                metadata["status"] = random.choice(["draft", "review", "approved", "deprecated"])

            elif doc_type == "meeting_notes":
                template_vars.update({
                    "topic": f"{team.capitalize()} Team {random.choice(['Sprint Planning', 'Retrospective', 'Design Review', 'Status Update'])}",
                    "attendees": ", ".join([self._generate_person_name() for _ in range(random.randint(3, 8))]),
                    "agenda": "\n".join([f"- {lorem.sentence()}" for _ in range(random.randint(3, 7))]),
                    "discussion": "\n".join([lorem.paragraph() for _ in range(random.randint(2, 5))]),
                    "actions": "\n".join([f"- {lorem.sentence()} (Owner: {self._generate_person_name()})" for _ in
                                          range(random.randint(2, 6))]),
                    "decisions": "\n".join([f"- {lorem.sentence()}" for _ in range(random.randint(2, 4))])
                })
                metadata["meeting_type"] = template_vars["topic"].split()[-1].lower()

            elif doc_type == "release_notes":
                template_vars.update({
                    "features": "\n".join([f"- {lorem.sentence()}" for _ in range(random.randint(3, 8))]),
                    "bugs": "\n".join([f"- {lorem.sentence()}" for _ in range(random.randint(2, 7))]),
                    "issues": "\n".join([f"- {lorem.sentence()}" for _ in range(random.randint(0, 4))]),
                    "improvements": "\n".join([f"- {lorem.sentence()}" for _ in range(random.randint(2, 6))]),
                    "notes": lorem.paragraph()
                })
                metadata["version"] = template_vars["version"]
                metadata["release_type"] = random.choice(["major", "minor", "patch"])

            elif doc_type == "api_docs":
                template_vars.update({
                    "overview": lorem.paragraph(),
                    "auth": lorem.paragraph(),
                    "endpoints": "\n".join(
                        [f"### {self._generate_endpoint()}\n{lorem.paragraph()}" for _ in range(random.randint(3, 8))]),
                    "codes": "\n".join(
                        [f"- **{random.choice([200, 201, 400, 401, 403, 404, 500])}**: {lorem.sentence()}" for _ in
                         range(random.randint(5, 10))]),
                    "getting_started": lorem.paragraph(),
                    "resources": "\n".join([f"### {self._generate_resource_name()}\n{lorem.paragraph()}" for _ in
                                            range(random.randint(3, 7))]),
                    "errors": lorem.paragraph()
                })
                metadata["api_version"] = f"v{random.randint(1, 5)}"

            # Format the template with variables
            text = template.format(**template_vars)

        else:
            # Generate plain text content
            text = "\n\n".join([lorem.paragraph() for _ in range(paragraphs)])

        return text, metadata

    def _generate_tags(self, doc_type: str, project: str, team: str) -> List[str]:
        """
        Generate relevant tags for the document.

        Args:
            doc_type: Document type
            project: Project name
            team: Team name

        Returns:
            List of tags
        """
        # Start with standard tags
        tags = [doc_type, project, team]

        # Add type-specific tags
        if doc_type == "requirements":
            tags.extend(["requirements", "specification", random.choice(["user-story", "epic", "feature"])])
        elif doc_type == "design":
            tags.extend(["design", random.choice(["architecture", "interface", "component", "system"])])
        elif doc_type == "meeting_notes":
            tags.extend(["meeting", random.choice(["planning", "review", "sync", "retrospective"])])
        elif doc_type == "release_notes":
            tags.extend(["release", "changelog", f"v{random.randint(1, 5)}.{random.randint(0, 9)}"])
        elif doc_type == "api_docs":
            tags.extend(["api", "documentation", random.choice(["reference", "guide", "tutorial"])])

        # Add some random generic tags
        generic_tags = ["important", "draft", "reviewed", "approved", "archived", "needs-review", "wip"]
        tags.extend(random.sample(generic_tags, random.randint(1, 3)))

        return list(set(tags))  # Remove duplicates

    def _generate_component_name(self) -> str:
        """Generate a realistic component name."""
        prefixes = ["User", "Data", "Auth", "Payment", "Notification", "Search", "Analytics", "Admin", "Core"]
        suffixes = ["Service", "Controller", "Manager", "Handler", "Processor", "Repository", "Factory", "Provider"]
        return f"{random.choice(prefixes)}{random.choice(suffixes)}"

    def _generate_interface_name(self) -> str:
        """Generate a realistic interface name."""
        prefixes = ["I", ""]
        components = ["User", "Data", "Auth", "Payment", "Notification", "Search", "Analytics", "Admin"]
        actions = ["Service", "Provider", "Repository", "Manager", "Handler", "Controller", "Listener"]

        if random.choice([True, False]):
            return f"{random.choice(prefixes)}{random.choice(components)}{random.choice(actions)}"
        else:
            return f"{random.choice(components)}API"

    def _generate_person_name(self) -> str:
        """Generate a realistic person name."""
        first_names = ["Alex", "Jamie", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Sam", "Quinn", "Avery",
                       "Sophia", "Emma", "Noah", "Liam", "Olivia", "Aiden", "Ava", "Lucas", "Mia", "Ethan"]
        last_names = ["Smith", "Johnson", "Williams", "Jones", "Brown", "Davis", "Miller", "Wilson", "Moore",
                      "Taylor", "Anderson", "Thomas", "Jackson", "White", "Harris", "Martin", "Thompson", "Garcia",
                      "Martinez"]

        return f"{random.choice(first_names)} {random.choice(last_names)}"

    def _generate_endpoint(self) -> str:
        """Generate a realistic API endpoint."""
        resources = ["users", "products", "orders", "payments", "customers", "accounts", "sessions", "profiles",
                     "items", "transactions"]
        actions = ["", "create", "update", "delete", "search", "validate", "process", "activate", "deactivate", "batch"]

        if random.choice([True, False]) and actions[0] != "":
            # Resource endpoint
            return f"GET /api/{random.choice(resources)}/{{{random.choice(resources)[:-1]}_id}}"
        else:
            # Action endpoint
            action = random.choice(actions)
            if action:
                return f"POST /api/{random.choice(resources)}/{action}"
            else:
                return f"GET /api/{random.choice(resources)}"

    def _generate_resource_name(self) -> str:
        """Generate a realistic resource name."""
        prefixes = ["User", "Customer", "Product", "Order", "Payment", "Account", "Transaction", "Item", "Profile",
                    "Session"]
        suffixes = ["Resource", "Entity", "Object", "Record", "Data", "Info", "Details", ""]

        return f"{random.choice(prefixes)}{random.choice(suffixes)}"