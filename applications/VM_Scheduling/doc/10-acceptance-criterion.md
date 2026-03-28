# 10 — Acceptance Criterion (Late Acceptance Hill Climbing)

The ALNS solver uses **Late Acceptance Hill Climbing (LAHC)**, not Simulated Annealing. There is no temperature, no cooling schedule, and no `exp(Δ/T)` probability.

---

## LAHC Implementation (Confirmed Source)

```java
public class LateAcceptanceHillClimbingAcceptanceCriteria implements AcceptanceCriteria {
    private final Value[] values;  // circular buffer of historical values
    private int position;          // current buffer position

    public LateAcceptanceHillClimbingAcceptanceCriteria(int length) {
        values = new Value[length];  // buffer length controls "memory" depth
    }

    @Override
    public void init(Value value) {
        Arrays.fill(values, value);  // initialise all slots with the starting objective
    }

    @Override
    public boolean accept(Value oldValue, Value newValue,
                          SplittableRandom random, int stagnationSteps) {
        // Accept if improved over current OR improved over history[position]
        Value candidate;
        if (newValue.compareTo(oldValue) <= 0              // better than or equal to current
                || newValue.compareTo(values[position]) < 0) {  // strictly better than L steps ago
            candidate = newValue;
        } else {
            candidate = oldValue;  // reject — keep current
        }

        // Update history slot if candidate is better than what was stored
        if (candidate.compareTo(values[position]) < 0) {
            values[position] = candidate;
        }
        position = (position + 1) % values.length;  // advance circular buffer

        return candidate == newValue;  // true = accepted
    }
}
```

---

## How It Works

LAHC maintains a circular buffer of `L` historical objective values. A new solution is accepted if:

1. `newValue ≤ oldValue` — it's at least as good as the current working solution, **OR**
2. `newValue < values[position]` — it's strictly better than what was recorded `L` iterations ago.

Condition 2 is the escape mechanism: even if the new solution is worse than the current one, it can still be accepted if it's better than the historical value at the current buffer position. This allows escaping plateaus without any temperature parameter.

After each accept/reject decision, the buffer slot is updated if the candidate (accepted value or retained old value) is better than the stored value, and the position advances.

---

## Configuration

| Parameter | Default | Effect |
|---|---|---|
| Buffer length `L` | **10** | How many iterations of history to compare against |

**L = 10 is unusually small.** LAHC literature typically suggests L = 1000–5000. A buffer of 10 means the solver compares against the objective from just 10 iterations ago — effectively an extremely short-memory hill climber that accepts non-improving moves only if the recent history was worse.

This aggressive configuration combined with `maxStagnationSteps=500` and `timeLimit=5s` is optimized for fast convergence in production rather than deep exploration.

---

## Acceptance Scenarios

| Scenario | `newValue` vs `oldValue` | `newValue` vs `history[pos]` | Result |
|---|---|---|---|
| Improving | `≤` | any | **Accept** (condition 1) |
| Same as current | `=` | any | **Accept** (condition 1, `<=`) |
| Worse than current, better than history | `>` | `<` | **Accept** (condition 2 — plateau escape) |
| Worse than both | `>` | `≥` | **Reject** |

---

## Where Called in Main Loop

```java
// After global best check (step 5)
if (acceptanceCriteria.accept(value, newValue, random, stagnationSteps)) {
    value = newValue;
    solution = newSolution;  // adopt the candidate as working solution
} else {
    // newSolution is simply discarded — no rollback needed (copy-on-write)
}
```

Acceptance and global-best tracking are **independent**. A solution can be:
- Accepted but not global best (improves over current or history, but not over all-time best)
- Global best but... always accepted (any improvement over best will also satisfy LAHC condition 1)
- Rejected — discarded without any state change
