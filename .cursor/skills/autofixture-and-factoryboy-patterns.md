# Skill: AutoFixture and FactoryBoy Patterns

**Capability Domain**: TEST_DATA
**Technology Stack**: FactoryBoy+Django+AutoFixture

## Overview

Patterns for dynamic test data generation using FactoryBoy and AutoFixture. Covers when to use JSON fixtures vs factories, scoping strategies, preset patterns, and the lazy AutoFixture approach.

## Reference Implementation

### Pattern 1: FactoryBoy Model Factories

```python
import factory
from factory.django import DjangoModelFactory

class UserFactory(DjangoModelFactory):
    class Meta:
        model = 'auth.User'
    username = factory.Sequence(lambda n: f'user_{n}')
    email = factory.LazyAttribute(lambda o: f'{o.username}@example.com')
    is_active = True

class PlaybookFactory(DjangoModelFactory):
    class Meta:
        model = 'methodology.Playbook'
    name = factory.Sequence(lambda n: f'Playbook {n}')
    description = factory.Faker('paragraph')
    author = factory.SubFactory(UserFactory)
```

### Pattern 2: AutoFixture — For Lazy Guys

Create model instances with sensible random defaults when you don't care about specific field values.

### Pattern 3: Four Fixture Tiers

| Tier | Tool | Scope | When |
|------|------|-------|------|
| Session | JSON (seed.json) | Entire test run | Static reference data |
| Suite | JSON (presets/) | Group of tests | Shared scenario setup |
| Test | FactoryBoy | Single test | Dynamic, parameterized |
| Lazy | AutoFixture | Single test | Don't care about specifics |
