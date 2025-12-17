---
name: ui-ux-design
description: Practical UI/UX design fundamentals including grid systems, spacing, component consistency, and common beginner mistakes to avoid. Use when building interfaces, reviewing designs for usability issues, or applying professional design systems. Complements creative aesthetic choices with solid structural foundations.
---

# UI/UX Design Fundamentals

Apply these principles when building or reviewing interfaces.

## Core Philosophy

**Creativity is connecting ideas** - not inventing from scratch. Study existing great designs and remix them thoughtfully.

**Less is more** - Focus on essential features first. Avoid starting with structure questions ("how wide is the section?"). Start with content and purpose.

## Design Systems

### Grid System

Use a **4-point grid** (or 8-point for larger elements):
- All spacing, sizing, and positioning use multiples of 4px
- Creates visual harmony and consistent rhythm
- Common values: 4, 8, 12, 16, 24, 32, 48, 64px

### Units

Use **REM units** for scalable, accessible sizing:
- Divide pixel values by 16 to get REM
- 16px = 1rem, 24px = 1.5rem, 32px = 2rem
- Respects user font-size preferences

### Law of Proximity

Group related elements together, separate unrelated ones:
- Elements close together appear related
- Use spacing to create visual hierarchy
- White space is a design tool, not empty space

## The Zoom-Out Test

Periodically zoom out to 50% or smaller:
- Do key elements still stand out?
- Is the hierarchy clear at a glance?
- Can you identify the primary action?

## Common UI/UX Mistakes

### 1. Missing Navigation Shortcuts

Always consider:
- Search functionality for long lists
- Skip buttons for optional flows
- Quick filters and sorting options

### 2. Harsh Shadows & Gradients

**Shadows**: Avoid Figma/CSS defaults. Use subtle, diffused shadows:
```css
/* Bad */
box-shadow: 0 4px 6px rgba(0,0,0,0.5);

/* Good */
box-shadow: 0 4px 12px rgba(0,0,0,0.08);
```

**Gradients**: Stick to variations of the same color family. Avoid rainbow gradients.

### 3. Inconsistent Spacing

Use Auto-Layout (Figma) or CSS Flexbox/Grid with consistent gap values:
- Pick 2-3 spacing values and reuse them
- Never eyeball spacing manually

### 4. Inconsistent Components

Buttons doing similar actions should look similar:
- "Back" and "Cancel" = same style (secondary)
- "Submit" and "Confirm" = same style (primary)
- Don't mix styles for equivalent functions

### 5. Inconsistent Icons

Use a single icon library (Feather, Phosphor, Heroicons):
- Same stroke width across all icons
- Same visual weight and style
- Never mix filled and outlined icons randomly

### 6. Redundant Visual Cues

Remove unnecessary affordances:
- Swipeable cards on mobile don't need arrows
- Obvious buttons don't need "click here" text
- Trust users to understand standard patterns

### 7. Missing Feedback

Every action needs acknowledgment:
- Loading states (spinners, skeletons)
- Success confirmations (checkmarks, toasts)
- Error states (red highlights, clear messages)
- Notification indicators (red dots, badges)

### 8. Unreadable Data Visualization

Charts must be functional, not just aesthetic:
- Readable axis labels (not tiny/rotated)
- Clear legends
- Appropriate chart type for the data
- Avoid "Dribbble aesthetic" over usability

## Creative Process

1. **Input**: Gather inspiration from quality sources (Mobbin, Dribbble, Awwwards)
2. **Inspiration**: Find 3-5 reference designs that match your vision
3. **Incubation**: Step away. Let ideas connect subconsciously
4. **Implementation**: Return with fresh perspective and execute
