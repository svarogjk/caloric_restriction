---
name: quiz
description: Technology knowledge quiz on project technologies like FastAPI, React, Redux, lifelines, SQLAlchemy, and more
disable-model-invocation: true
argument-hint: "[topic] [count]"
---

# Technology Knowledge Quiz

Interactive multiple-choice and code-analysis quiz covering project technologies. Tests conceptual understanding, not just coding ability.

## Usage

```
/quiz [topic] [count]
```

**Topics** (optional): `fastapi`, `react`, `redux`, `recharts`, `tailwind`, `sqlalchemy`, `survival`, `langchain`, `pandas`, `auth`, `async`, `pydantic`, `all`
**Count** (optional): Number of questions (default: 5, max: 15)

If no topic specified, defaults to `all` (mixed questions from all topics).

## Workflow

### Step 1: Parse Arguments

Parse `$ARGUMENTS`:
- First argument: topic (or `all`)
- Second argument: count (number)
- Default: `all` with 5 questions

### Step 2: Load Question Bank

Read the question bank from [references/question-bank.md](references/question-bank.md). Select questions matching the topic. If `all`, pick from across all topics ensuring variety.

### Step 3: Present Questions

For each question:

1. Display the question number, total, and topic tag
2. Use the **AskUserQuestion** tool to present the question with answer options
3. After the user answers:
   - Show whether they were correct or incorrect
   - Provide a brief explanation of the correct answer
   - Reference actual project code when relevant (e.g., "See `backend/app/services/survival_analysis_service.py:45` for an example")
4. Track running score

### Step 4: Present Results

After all questions, display:
- Final score: X/Y correct (percentage)
- Performance by topic (if `all` mode)
- Areas of strength and areas to improve
- Suggested `/practice` or `/kata` exercises for weak areas

## Question Format Guidelines

Questions should be one of these types:

### Type 1: Multiple Choice
```
Q: What does `hazard_ratio > 1` indicate in survival analysis?
A) The gene is protective
B) The gene increases risk  ✓
C) No significant effect
D) The data is censored
```

### Type 2: What's Wrong With This Code?
```
Q: What's wrong with this FastAPI endpoint?
  async def get_data(id: str):
      data = requests.get(f"https://api.example.com/{id}")
      return data.json()
A) Missing return type annotation
B) Using synchronous requests in async function  ✓
C) Missing error handling
D) Both B and C  ✓
```

### Type 3: What Does This Output?
```
Q: What does this Redux reducer produce?
  setQuery: (state, action) => { state.query = action.payload; }
A) Returns a new state object with updated query
B) Mutates the draft state directly via Immer  ✓
C) Throws an error because state is immutable
D) Creates a shallow copy of state
```

### Type 4: Fill in the Blank
```
Q: Complete the lifelines code:
  cph = CoxPHFitter()
  cph.fit(df, duration_col='time', event_col='event')
  hazard_ratio = ___
A) cph.params_['expression']
B) np.exp(cph.params_['expression'])  ✓
C) cph.hazard_ratio_
D) cph.summary['HR']
```

## Question Bank Reference

For the full question bank organized by topic and difficulty, see [references/question-bank.md](references/question-bank.md).
