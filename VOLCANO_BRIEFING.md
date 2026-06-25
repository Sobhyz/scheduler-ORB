# Volcano Scheduler — Complete Briefing

> A single reference for understanding and presenting the Volcano-based job
> scheduling system: what it is, how it works, its strengths, the cases it does
> not cover, and its weaknesses.

---

## Table of Contents

1. [The Problem Being Solved](#1-the-problem-being-solved)
2. [What Volcano Is](#2-what-volcano-is)
3. [Master and Worker Nodes](#3-master-and-worker-nodes)
4. [How Scheduling Decisions Are Made](#4-how-scheduling-decisions-are-made)
5. [Key Concepts](#5-key-concepts)
6. [Worked Example — How Ordering Changes](#6-worked-example--how-ordering-changes)
7. [Strengths](#7-strengths)
8. [Cases Not Covered Out of the Box](#8-cases-not-covered-out-of-the-box)
9. [Weaknesses and Risks](#9-weaknesses-and-risks)
10. [What Has Been Verified](#10-what-has-been-verified)
11. [Executive Summary](#11-executive-summary)

---

## 1. The Problem Being Solved

The task is a competition in which participants submit AI models that segment
brain tumors in MRI scans. Every model must run on the same evaluation dataset,
be scored, and be compared to select a winner.

Each model runs as a **job** that requests computing resources — GPUs, CPUs,
memory, and storage — for some duration. Because the hardware is shared and
finite, a scheduler must decide which job runs first when not everything fits at
once. The chosen scheduler is **Volcano**, running on **Kubernetes**.

---

## 2. What Volcano Is

Kubernetes manages containers but has a weak, one-at-a-time scheduler unsuited to
batch AI workloads. Volcano adds the intelligent scheduling layer on top: it
decides the order and placement of jobs using priority, fairness, grouping, and
backfill rules.

The system is three layers:

| Layer | Role | What it does |
|-------|------|--------------|
| **Docker** | Engine | Runs a single container (one isolated program) |
| **Kubernetes** | Orchestrator | Manages many containers across machines |
| **Volcano** | Scheduler | Decides which jobs run first, and where |

---

## 3. Master and Worker Nodes

A Kubernetes cluster is made of **nodes** (machines), of two kinds:

| Node type | Nickname | Responsibility |
|-----------|----------|----------------|
| **Master (control-plane)** | The brain | Runs Kubernetes core + the Volcano scheduler; makes all decisions; by default runs no user jobs |
| **Worker** | The muscle | Runs the actual jobs (the models), taking orders from the master |

Volcano fully supports this multi-node arrangement: the scheduler runs on the
master and assigns jobs across the worker nodes. This is how production operates
— the master coordinates, the workers (with the GPUs) execute.

> **Note on the current phase (development laptop).**
> The local cluster has only **one node**, created as a single-node cluster, so
> there are no separate workers. That one node is therefore **both master and
> worker at once**: it runs Volcano and also runs the jobs. The local cluster
> tool removes the usual restriction that prevents the master from running jobs,
> because in a single-node setup there is nowhere else for jobs to go. This is
> why the test jobs ran on the control-plane node. In production this changes
> automatically — jobs run on worker nodes — and **no configuration needs to
> change.**

---

## 4. How Scheduling Decisions Are Made

Volcano runs a cycle of stages called **actions**, applying **plugins**
(decision rules) to choose what runs.

### Actions (the stages, in order)

| Action | Purpose |
|--------|---------|
| `enqueue` | Admit jobs into the competition |
| `allocate` | Assign resources to jobs by priority |
| `backfill` | Fit small jobs into idle gaps left while large jobs wait |
| `preempt` | Allow a higher-priority job to displace a lower-priority one |

### Plugins (the decision rules)

| Plugin | What it does |
|--------|--------------|
| `priority` | Who is more important (priority → arrival → ID) |
| `gang` | All-or-nothing (all of a job's pods together, or none) |
| `conformance` | Protect critical system pods (safety) |
| `overcommit` | Allow a bit beyond strict capacity |
| `drf` | Favor fewer-resource jobs + fairness across resource types |
| `predicates` | Filter: can this job fit on this node? |
| `proportion` | Fair share per queue (anti-hogging) |
| `nodeorder` | Pick the best node for placement |
| `binpack` | Pack tightly, leaving room for big jobs |
| `sla` | Anti-starvation (force jobs waiting beyond the limit through) |

The plugins fall into three kinds of work:

- **Ordering** (who runs first): `priority`, `drf`, `gang`, `sla`
- **Placement** (where it runs): `predicates`, `nodeorder`, `binpack`, `overcommit`
- **Safety / fairness**: `conformance`, `proportion`

Plugins are grouped into **tiers**; earlier tiers override later ones when rules
conflict. The order *within* a tier matters only when two plugins decide the same
kind of thing (for example, two ordering rules); plugins doing different jobs
(such as `priority` and `gang`) can be listed in either order with the same
result.

---

## 5. Key Concepts

### Gang Scheduling

A job may consist of several pods that must run together (for example, a model
needing four GPUs at once). Gang scheduling guarantees **all of them start
together, or none do.** This prevents a deadlock in which a job grabs some
resources and waits forever for the rest. It is the single most important reason
Volcano was chosen.

### DRF (Dominant Resource Fairness)

A fairness rule for when jobs request different mixes of resources (some need
more GPU, others more CPU). DRF looks at each job's largest ("dominant")
resource demand and balances those across jobs, so no single type of job
monopolizes the cluster. In practice it tends to favor jobs requesting fewer
resources.

### Preemption — Important Clarification

Preemption means a higher-priority job can displace a lower-priority job that is
already running, to take its resources. **Preemption is driven by priority, not
by time.** It does not, on its own, stop a job for running too long.

> **Design decision to confirm with the team.**
> The competition's requirement is different: stop *only* the jobs that exceed
> their declared time limit, and never disturb any other job. That is **not
> preemption** — it is a **per-job time limit**, after which Kubernetes stops the
> job automatically, independent of the scheduler.
>
> Therefore, if no job should ever be displaced except those that overrun their
> declared time, the correct design is to **disable preemption** and instead
> **set a time limit on each job.** Preemption and time limits are two separate
> mechanisms and must not be confused.

### Maximum Waiting Time (ETA) per Job

A scheduler cannot promise an *exact* wait time, because it depends on what else
is submitted and on resource availability at that moment. However, an **upper
bound can be enforced**: the `sla-waiting-time` setting forces any job that has
waited longer than that limit to proceed.

- **Maximum wait** ≈ the configured `sla-waiting-time` (e.g. one hour) — a guaranteed ceiling.
- **Typical wait** — shorter, load-dependent, and cannot be calculated precisely in advance.

---

## 6. Worked Example — How Ordering Changes

The same three jobs are ordered differently depending on which plugins are
active and how the tiers are arranged.

**The three jobs:**

| Job | Priority | Arrived | Resources | Time |
|-----|----------|---------|-----------|------|
| A | low | 1st | 1 CPU | 10 min |
| B | high | 2nd | 4 CPUs | 2 min |
| C | low | 3rd | 1 CPU | 5 min |

### Case 1 — Priority plugin only

The priority plugin's fixed internal order is **priorityClass → arrival → ID**.

- B is high → B first.
- A and C tie (both low) → arrival decides → A before C.

**Order: B → A → C.** These three checks cannot be reordered; the order is
hardcoded in the plugin.

### Case 2 — Add the `drf` plugin (favors fewer resources)

B wants 4 CPUs (large); A and C want 1 CPU each (small). DRF makes the small
jobs more attractive because they fit easily.

**Order might become: A → C → B** — even though B is high priority, DRF pulls the
small jobs up. *Same jobs, different order, achieved by adding a plugin — not by
reordering the internal chain.*

### Case 3 — Tiers resolve conflicts

Priority says "B first"; DRF says "A first." They conflict. The earlier tier
wins.

```yaml
# Version 1 — priority leads
tiers:
- plugins:
  - name: priority     # tier 1 (stronger)
- plugins:
  - name: drf          # tier 2 (weaker)
# Result: B → A → C
```

```yaml
# Version 2 — drf leads
tiers:
- plugins:
  - name: drf          # tier 1 (stronger)
- plugins:
  - name: priority     # tier 2 (weaker)
# Result: A → C → B
```

*Identical jobs and plugins — swapping the tier order flips the result.*

### Case 4 — A custom `area` plugin (area = resources × time)

| Job | Area (resources × time) |
|-----|-------------------------|
| C | 1 × 5 = **5** |
| B | 4 × 2 = **8** |
| A | 1 × 10 = **10** |

Smallest area first → **Order: C → B → A.** A new ordering, because a custom
plugin introduced a rule that does not exist built-in.

### Summary of the example

| Configuration | Resulting order | Rule that dominates |
|---------------|-----------------|---------------------|
| Priority plugin only | B → A → C | Priority |
| + DRF added | A → C → B | Small jobs favored |
| DRF in top tier | A → C → B | DRF wins conflicts |
| Priority in top tier | B → A → C | Priority wins conflicts |
| Custom area plugin | C → B → A | Area |

### What can and cannot be changed

- **Cannot change:** the internal order inside the priority plugin — always
  priority, then arrival, then ID.
- **Can change:** which plugins are active; which tier each sits in (top tier
  wins conflicts); and adding a custom plugin for entirely new rules (area,
  duration).

> **Analogy.** The priority plugin is one judge with a fixed personal rulebook.
> The scheduler is a *panel* of judges: you choose which judges sit on the panel
> (which plugins), who leads it (tier order), and you can hire a new judge with
> new rules (a custom plugin). You cannot change one judge's rulebook, but you
> can change the whole panel and who leads it.

---

## 7. Strengths

- **Gang scheduling** — all-or-nothing allocation prevents multi-GPU deadlocks.
- **Multi-resource requests** — a job can request GPU, CPU, and memory together,
  allocated as a unit.
- **Priority scheduling** with deterministic tie-breaks (priority → arrival → ID,
  lowest ID first).
- **Backfill** — small jobs fill idle gaps, improving utilization.
- **Fairness** — DRF and proportion prevent any participant from monopolizing
  resources.
- **Anti-starvation** — the SLA plugin guarantees a maximum waiting time.
- **Native AI/ML support** — works with PyTorch, TensorFlow, and Ray.
- **Customizable** — behavior is set via configuration, and new rules can be
  added as plugins.
- **Production-ready scaling** — the same configuration runs unchanged from a
  single laptop node to a multi-node GPU cluster.

---

## 8. Cases Not Covered Out of the Box

| Gap | Why | Resolution |
|-----|-----|------------|
| Ordering by duration or area (resources × time) | Built-in plugins judge by resources and priority, never duration; DRF covers the resource dimension only | Custom Go plugin, **or** compute area before submission and map to priority classes |
| Stopping jobs that exceed their declared time | Not a scheduler function | Per-job time limit |
| Exact waiting-time prediction | Depends on live load | Only an upper bound (the SLA limit) can be guaranteed |

### Writing a Custom Plugin (Go) — Brief Example

A custom rule, such as ordering by area (resources × time), is not a
configuration change — it is **Go code compiled into Volcano**. The rule lives in
a function called `jobOrderFn`, which compares two jobs and decides which goes
first. A minimal sketch:

```go
package area

// the plugin compares two jobs by area = resources × time limit
func (ap *areaPlugin) OnSessionOpen(ssn *framework.Session) {
    ssn.AddJobOrderFn(ap.Name(), func(l, r interface{}) int {
        jobL := l.(*api.JobInfo)
        jobR := r.(*api.JobInfo)

        areaL := totalResources(jobL) * timeLimit(jobL)
        areaR := totalResources(jobR) * timeLimit(jobR)

        if areaL < areaR {
            return -1   // smaller area runs first
        }
        return 1
    })
}
```

The steps to use it:

1. Write the plugin in Go (the function above).
2. Register it in Volcano's plugin list in the source.
3. Recompile Volcano into a new container image.
4. Deploy that image to the cluster.
5. Reference it by name in the config: `- name: area`.

The config line `- name: area` does nothing unless the compiled Volcano binary
contains this code. Because of this overhead, the **area-to-priority mapping
shortcut** (computing area before submission and assigning a priority class) is
usually preferred, as it needs no custom code.

---

## 9. Weaknesses and Risks

- **Operational complexity.** Volcano on Kubernetes is a real distributed system
  with a learning curve; diagnosis requires Kubernetes knowledge.
- **Custom rules require Go.** Any policy beyond the built-in plugins must be
  written and maintained as code.
- **The scheduler neither scores models nor enforces time limits.** Those are
  separate components built around it.
- **Development testing is hardware-limited.** A laptop cannot represent real
  load or real GPUs; multi-GPU behavior is only fully verifiable on the real
  cluster.
- **Tooling is Kubernetes-specific.** If production provides a different system
  (such as Slurm), the concepts transfer but the tooling and some work would
  change.

---

## 10. What Has Been Verified

On a local single-node cluster with Volcano installed, the following behaviors
were confirmed by submitting jobs and observing the scheduler:

| Test | Result |
|------|--------|
| **Gang scheduling (fits)** | A three-pod job started all pods together and completed together |
| **Gang scheduling (cannot fit)** | A job requesting more than the available resources started zero pods and stayed Pending — proving all-or-nothing behavior |
| **Priority and preemption** | A high-priority job displaced a running low-priority job; the low-priority job returned to Pending and resumed once resources freed |

---

## 11. Summary

Volcano is the scheduling brain that sits on Kubernetes and decides which
competing model-jobs run, in what order, and where. Its decisive strength is
**gang scheduling**, which safely handles multi-GPU jobs. It provides priority,
fairness, backfill, and a guaranteed maximum wait time, all through a single
configuration that scales unchanged from the test laptop to a production GPU
cluster.

It does **not** natively order jobs by duration or area, does not by itself stop
overrunning jobs or score models, and cannot predict exact wait times. These are
addressed respectively by a custom plugin (or the area-to-priority mapping
shortcut), per-job time limits, a separate scoring pipeline, and the SLA upper
bound.

> **Key decision for the team:** how preemption should be treated. If the only
> jobs that should ever be stopped are those exceeding their declared time,
> preemption should be **disabled** and **per-job time limits** used instead.
