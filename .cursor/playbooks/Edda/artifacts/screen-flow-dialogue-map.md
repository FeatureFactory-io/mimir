OUTPUT: docs/ux/2_dialogue-maps/screen-flow.drawio (also referenced as docs/architecture/screen-flow.drawio in EST activities)
FORMAT: Draw.io diagram with domain model and MVP flow swimlanes

TEMPLATE: See .windsurf/workflows/FeatureFactory/ESM/artifacts/dialogue_map_template.drawio
- Tab 1: Domain Model (entities, relationships, cardinality)
- Tab 2: MVP Flow (swimlanes by persona/system, screen boxes with Screen IDs)
- Each screen labeled with pattern: {PROJECT}-{ENTITY}-{OPERATION}-{VERSION}
- Arrows show navigation flow between screens
- Color coding: Entry screens (green), CRUD operations (blue), Delete (red)
