---
name: technology-research
description: Technology research and evaluation for emerging tech, tools, frameworks, and innovations. Use when users ask to evaluate technologies, compare tools/frameworks, research tech trends, assess technical feasibility, or understand new innovations. Triggers on queries like "research [technology]", "compare [tool A] vs [tool B]", "evaluate [framework]", "what's the best [tech solution] for X", "emerging tech in [domain]", or "should we use [technology]".
---

# Technology Research

Evaluate technologies, tools, and innovations to inform technical decisions.

## Workflow

1. **Define needs** - Clarify use case, requirements, constraints, and evaluation criteria
2. **Research** - Investigate technologies, gather benchmarks, reviews, and case studies
3. **Evaluate** - Assess against criteria, compare alternatives
4. **Deliver** - Present in requested format (report or brief)

## Output Formats

### Quick Brief (default for simple queries)

Use for fast technology assessments:

```
# [Technology] Brief

**Key Insight:** [One sentence recommendation or finding]

**What it is:** [Brief description]
**Maturity:** [Emerging / Growing / Mature / Declining]
**Adoption:** [Early adopter / Mainstream / Legacy]

**Pros:**
- [Key advantage 1]
- [Key advantage 2]

**Cons:**
- [Key drawback 1]
- [Key drawback 2]

**Best for:** [Use cases where it excels]
**Avoid if:** [Situations where it's not ideal]

**Bottom Line:** [Recommendation]
```

### Comparison Brief (for tool comparisons)

```
# [Tool A] vs [Tool B]

**Winner for your use case:** [Recommendation]

| Criteria | Tool A | Tool B |
|----------|--------|--------|
| [Criterion 1] | [Rating/Notes] | [Rating/Notes] |
| [Criterion 2] | [Rating/Notes] | [Rating/Notes] |

**Choose [Tool A] if:** [Conditions]
**Choose [Tool B] if:** [Conditions]
```

### Structured Report (for comprehensive evaluation)

Use when user requests deep tech analysis or says "full report":

```
# Technology Evaluation: [Technology/Tool]

## Executive Summary
[Key findings and recommendation in 2-3 paragraphs]

## Overview
- What it is and what problem it solves
- History and current state
- Key vendors/implementations

## Technical Assessment

### Capabilities
- Core features and functionality
- Performance characteristics
- Scalability

### Architecture
- How it works (high-level)
- Integration patterns
- Dependencies

### Maturity and Stability
- Version history and release cadence
- Breaking changes and migration path
- Long-term viability

## Ecosystem

### Community and Support
- Community size and activity
- Documentation quality
- Commercial support options

### Integrations
- Compatible tools and platforms
- Available plugins/extensions
- API quality

## Evaluation

### Strengths
- [Strength with evidence]

### Weaknesses
- [Weakness with evidence]

### Comparison to Alternatives
| Criteria | This Tech | Alternative 1 | Alternative 2 |
|----------|-----------|---------------|---------------|
| [Criterion] | [Rating] | [Rating] | [Rating] |

## Adoption Considerations

### Prerequisites
- Skills required
- Infrastructure needs
- Migration effort

### Risks
- Technical risks
- Vendor/lock-in risks
- Adoption risks

### Cost
- Licensing/pricing
- Operational costs
- Hidden costs

## Recommendation
[Clear recommendation with rationale and conditions]

## Sources
[Key sources used]
```

## Research Approach

- Focus on practical, real-world performance over marketing claims
- Seek out case studies, benchmarks, and user experiences
- Check GitHub activity, Stack Overflow trends, job postings as adoption signals
- Consider total cost of ownership, not just initial implementation
- Evaluate both current state and trajectory
- Note bias in sources (vendor docs vs. independent reviews)
- Prioritize information relevant to user's specific context
